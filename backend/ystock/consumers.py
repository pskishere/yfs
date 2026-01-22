"""
WebSocket 消费者，处理实时股票分析对话
"""
import json
import asyncio
import logging
from typing import Optional, Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .agent import StockAIAgent
from .models import ChatSession, ChatMessage
from .tasks import generate_chat_response

logger = logging.getLogger(__name__)


class StockChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket 消费者，处理股票分析聊天消息
    支持流式输出、停止生成、获取历史记录等功能
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.agent_service = StockAIAgent()
        self.room_group_name = None
        self.current_streaming_task: Optional[asyncio.Task] = None
        self.current_message_id: Optional[int] = None
        self.should_cancel: bool = False
        self.streaming_lock = asyncio.Lock()
    
    async def connect(self):
        """
        连接 WebSocket（无需认证）
        """
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        
        # 获取查询参数中的 symbol 和 model
        from urllib.parse import parse_qs
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        symbol = query_params.get('symbol', [None])[0]
        model = query_params.get('model', [None])[0]
        
        # 如果提供了 model，初始化 agent_service 时使用它
        if model:
            logger.info(f"WebSocket 连接请求使用模型: {model}")
            self.agent_service = StockAIAgent(model_name=model)
        else:
            self.agent_service = StockAIAgent()
        
        # 如果没有 session_id，创建新会话
        if not self.session_id:
            self.session_id = await self.create_new_session(model=model)
        
        # 创建房间组名
        self.room_group_name = f'stock_chat_{self.session_id}'
        
        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 发送连接成功消息
        await self.send_json({
            'type': 'connection',
            'status': 'connected',
            'session_id': self.session_id
        })
        
        # 发送最近的历史记录
        try:
            recent_history = await self.get_session_history(50)
            if recent_history:
                await self.send_json({
                    'type': 'history',
                    'messages': recent_history,
                })
        except Exception as e:
            logger.warning(f"获取历史记录失败: {e}")
    
    async def disconnect(self, close_code):
        """
        断开 WebSocket 连接
        """
        # 注意：不再取消正在进行的生成任务，让其在后台继续运行
        # if self.current_streaming_task and not self.current_streaming_task.done():
        #     self.should_cancel = True
        #     self.current_streaming_task.cancel()
        
        if self.room_group_name:
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            except Exception:
                pass
    
    async def receive(self, text_data):
        """
        接收 WebSocket 消息
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            handlers = {
                'message': self.handle_message,
                'cancel': self.handle_cancel,
                'get_history': self.handle_get_history,
                'regenerate': self.handle_regenerate,
                'edit_message': self.handle_edit_message,
            }
            
            handler = handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                await self.send_json({
                    'type': 'error',
                    'message': f'未知的消息类型: {message_type}'
                })
                
        except json.JSONDecodeError:
            await self.send_json({
                'type': 'error',
                'message': '无效的 JSON 数据'
            })
        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            await self.send_json({
                'type': 'error',
                'message': str(e)
            })
    
    async def handle_message(self, data: Dict[str, Any]):
        """处理新消息"""
        async with self.streaming_lock:
            user_input = data.get('message', '').strip()
            
            if not user_input:
                await self.send_json({
                    'type': 'error',
                    'message': '消息内容不能为空'
                })
                return
            
            # 重置取消标志
            self.should_cancel = False
            
            # 保存用户消息
            user_msg_id = await self.save_user_message(user_input)
            
            # 创建 AI 消息占位符
            ai_message_id = await self.create_ai_message_placeholder()
            self.current_message_id = ai_message_id
            
            # 发送消息创建确认
            await self.send_json({
                'type': 'message_created',
                'user_message_id': user_msg_id,
                'ai_message_id': ai_message_id,
                'status': 'pending'
            })
            
            # 开始流式生成
            await self.send_json({
                'type': 'generation_started',
                'message_id': ai_message_id,
                'status': 'streaming'
            })
            
            # 更新消息状态
            await self.update_message_status(ai_message_id, 'streaming')
            
            # 启动流式生成任务（后台执行）
            self.current_streaming_task = asyncio.create_task(
                generate_chat_response(
                    session_id=self.session_id,
                    message_id=ai_message_id,
                    user_input=user_input,
                    model_name=self.agent_service.model_name
                )
            )
    
    async def handle_cancel(self, data: Dict[str, Any]):
        """处理停止生成请求"""
        async with self.streaming_lock:
            self.should_cancel = True
            
            # 取消正在进行的生成任务
            if self.current_streaming_task and not self.current_streaming_task.done():
                self.current_streaming_task.cancel()
            
            # 更新消息状态
            if self.current_message_id:
                await self.update_message_status(self.current_message_id, 'cancelled')
                await self.send_json({
                    'type': 'generation_cancelled',
                    'message_id': self.current_message_id,
                    'status': 'cancelled'
                })
    
    async def handle_get_history(self, data: Dict[str, Any]):
        """处理获取历史记录请求"""
        limit = data.get('limit', 50)
        history = await self.get_session_history(limit)
        await self.send_json({
            'type': 'history',
            'messages': history
        })
    
    async def handle_regenerate(self, data: Dict[str, Any]):
        """处理重新生成请求（完整版）"""
        async with self.streaming_lock:
            message_id = data.get('message_id')
            
            # 如果没有提供 message_id，获取最后一条 AI 消息
            if not message_id:
                last_ai_message = await self.get_last_ai_message()
                if last_ai_message:
                    message_id = last_ai_message.get('id')
            
            if not message_id:
                await self.send_json({
                    'type': 'error',
                    'message': '找不到要重新生成的消息'
                })
                return
            
            # 获取要重新生成的消息（应该是AI消息）
            message = await self.get_message(message_id)
            if not message:
                await self.send_json({
                    'type': 'error',
                    'message': '消息不存在'
                })
                return
            
            # 获取父用户消息
            parent_message = await self.get_parent_user_message(message)
            if not parent_message:
                await self.send_json({
                    'type': 'error',
                    'message': '找不到原始用户消息'
                })
                return
            
            # 删除原AI消息及其后续所有消息
            await self.delete_message_and_children(message.id)
            
            # 获取更新后的消息列表
            updated_messages = await self.get_session_history(100)
            await self.send_json({
                'type': 'messages_deleted',
                'deleted_from_message_id': message.id,
                'messages': updated_messages
            })
            
            # 重置取消标志
            self.should_cancel = False
            
            # 创建新的 AI 消息占位符
            ai_message_id = await self.create_ai_message_placeholder(parent_id=parent_message.id)
            self.current_message_id = ai_message_id
            
            # 发送重新生成开始消息
            await self.send_json({
                'type': 'regeneration_started',
                'message_id': ai_message_id,
                'status': 'streaming'
            })
            
            # 更新消息状态
            await self.update_message_status(ai_message_id, 'streaming')
            
            # 启动流式生成任务
            self.current_streaming_task = asyncio.create_task(
                generate_chat_response(
                    session_id=self.session_id,
                    message_id=ai_message_id,
                    user_input=parent_message.content or '',
                    model_name=self.agent_service.model_name
                )
            )
    
    async def handle_edit_message(self, data: Dict[str, Any]):
        """处理编辑消息请求"""
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()
        
        if not message_id:
            await self.send_json({
                'type': 'error',
                'message': '消息ID不能为空'
            })
            return
        
        if not new_content:
            await self.send_json({
                'type': 'error',
                'message': '新消息内容不能为空'
            })
            return
        
        try:
            # 获取消息
            message = await self.get_message(message_id)
            if not message:
                await self.send_json({
                    'type': 'error',
                    'message': '消息不存在'
                })
                return
            
            # 只能编辑用户消息
            if message.role != 'user':
                await self.send_json({
                    'type': 'error',
                    'message': '只能编辑用户消息'
                })
                return
            
            # 更新消息内容
            await self.update_message_content(message_id, new_content)
            
            # 删除该消息之后的所有消息
            await self.delete_messages_after(message_id)
            
            # 获取更新后的消息列表
            updated_messages = await self.get_session_history(100)
            
            await self.send_json({
                'type': 'edit_started',
                'message_id': message_id,
                'status': 'processing'
            })
            
            # 重置取消标志
            self.should_cancel = False
            
            # 创建新的 AI 消息占位符
            ai_message_id = await self.create_ai_message_placeholder()
            self.current_message_id = ai_message_id
            
            # 发送消息更新通知
            await self.send_json({
                'type': 'messages_updated',
                'messages': updated_messages
            })
            
            # 开始生成新回复
            await self.send_json({
                'type': 'generation_started',
                'message_id': ai_message_id,
                'status': 'streaming'
            })
            
            await self.update_message_status(ai_message_id, 'streaming')
            
            # 启动流式生成任务
            self.current_streaming_task = asyncio.create_task(
                generate_chat_response(
                    session_id=self.session_id,
                    message_id=ai_message_id,
                    user_input=new_content,
                    model_name=self.agent_service.model_name
                )
            )
            
        except Exception as e:
            logger.error(f"编辑消息失败: {e}", exc_info=True)
            await self.send_json({
                'type': 'error',
                'message': f'编辑消息时出错: {str(e)}'
            })
    
    
    async def chat_stream(self, event):
        """处理来自后台任务的流式消息"""
        await self.send_json(event['data'])

    # async def stream_generation(self, user_input: str, message_id: int):
    #    ... 已移动到 tasks.py ...
    
    async def send_json(self, data: Dict[str, Any]):
        """发送 JSON 消息"""
        await self.send(text_data=json.dumps(data, ensure_ascii=False))
    
    @database_sync_to_async
    def create_new_session(self, model: Optional[str] = None) -> str:
        """
        创建新会话
        
        Args:
            model: 使用的模型名称
            
        Returns:
            会话ID
        """
        return self.agent_service.create_new_session(model=model)
    
    @database_sync_to_async
    def save_user_message(self, content: str) -> int:
        """
        保存用户消息到数据库
        
        Args:
            content: 消息内容
            
        Returns:
            消息ID
        """
        session, _ = ChatSession.objects.get_or_create(
            session_id=self.session_id
        )
        message = ChatMessage.objects.create(
            session=session,
            role='user',
            content=content,
            status='completed'
        )
        return message.id
    
    @database_sync_to_async
    def create_ai_message_placeholder(self, parent_id: Optional[int] = None) -> int:
        """创建 AI 消息占位符"""
        session, _ = ChatSession.objects.get_or_create(
            session_id=self.session_id
        )
        
        params = {
            'session': session,
            'role': 'assistant',
            'content': '',
            'status': 'pending'
        }
        
        if parent_id:
            params['parent_message_id'] = parent_id
            
        message = ChatMessage.objects.create(**params)
        return message.id
    
    @database_sync_to_async
    def update_message_content(self, message_id: int, content: str):
        """更新消息内容"""
        ChatMessage.objects.filter(id=message_id).update(content=content)
    
    @database_sync_to_async
    def update_message_thoughts(self, message_id: int, thoughts: list):
        """更新消息思维链"""
        ChatMessage.objects.filter(id=message_id).update(thoughts=thoughts)
    
    @database_sync_to_async
    def update_message_status(self, message_id: int, status: str, error_msg: Optional[str] = None):
        """更新消息状态"""
        update_data = {'status': status}
        if error_msg:
            update_data['error_message'] = error_msg
        ChatMessage.objects.filter(id=message_id).update(**update_data)
    
    @database_sync_to_async
    def get_session_history(self, limit: int = 50) -> list:
        """
        获取会话历史记录
        
        Args:
            limit: 返回的最大消息数量
            
        Returns:
            历史消息列表
        """
        return self.agent_service.get_session_history(self.session_id, limit)
    
    @database_sync_to_async
    def get_last_user_message(self) -> Optional[Dict]:
        """
        获取最后一条用户消息
        
        Returns:
            消息字典或None
        """
        try:
            session = ChatSession.objects.get(session_id=self.session_id)
            last_msg = ChatMessage.objects.filter(
                session=session,
                role='user'
            ).order_by('-created_at').first()
            
            if last_msg:
                return {
                    'id': last_msg.id,
                    'content': last_msg.content,
                    'created_at': last_msg.created_at.isoformat()
                }
            return None
        except ChatSession.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_last_ai_message(self) -> Optional[Dict]:
        """
        获取最后一条 AI 消息
        
        Returns:
            消息字典或None
        """
        try:
            session = ChatSession.objects.get(session_id=self.session_id)
            last_msg = ChatMessage.objects.filter(
                session=session,
                role='assistant'
            ).order_by('-created_at').first()
            
            if last_msg:
                return {
                    'id': last_msg.id,
                    'content': last_msg.content,
                    'created_at': last_msg.created_at.isoformat()
                }
            return None
        except ChatSession.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_message(self, message_id: int) -> Optional[ChatMessage]:
        """获取消息"""
        try:
            return ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_parent_user_message(self, message: ChatMessage) -> Optional[ChatMessage]:
        """获取父用户消息"""
        if message.parent_message:
            return message.parent_message
        # 如果没有父消息，找到前一条用户消息
        previous_msg = ChatMessage.objects.filter(
            session=message.session,
            created_at__lt=message.created_at,
            role='user'
        ).order_by('-created_at').first()
        return previous_msg
    
    @database_sync_to_async
    def delete_message_and_children(self, message_id: int):
        """删除消息及其所有后续消息"""
        try:
            message = ChatMessage.objects.get(id=message_id)
            session = message.session
            created_at = message.created_at
            
            # 删除该消息及之后的所有消息
            ChatMessage.objects.filter(
                session=session,
                created_at__gte=created_at
            ).delete()
        except ChatMessage.DoesNotExist:
            pass
    
    @database_sync_to_async
    def delete_messages_after(self, message_id: int):
        """删除指定消息之后的所有消息"""
        try:
            message = ChatMessage.objects.get(id=message_id)
            session = message.session
            created_at = message.created_at
            
            # 删除该消息之后的所有消息（不包括该消息本身）
            ChatMessage.objects.filter(
                session=session,
                created_at__gt=created_at
            ).delete()
        except ChatMessage.DoesNotExist:
            pass
    