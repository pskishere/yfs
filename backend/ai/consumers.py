"""
WebSocket 消费者，处理通用 AI 对话
"""
import json
import asyncio
import logging
from typing import Optional, Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer

from ai.models import ChatSession, ChatMessage
from ai.engine import AIAgentEngine
from ai.tasks import generate_chat_response

logger = logging.getLogger(__name__)


class AIChatConsumer(AsyncWebsocketConsumer):
    """
    通用 WebSocket 消费者，处理 AI 聊天消息
    支持多业务命名空间、流式输出、停止生成、获取历史记录等功能
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.namespace = None
        self.model_name = None
        self.room_group_name = None
        self.current_streaming_task: Optional[asyncio.Task] = None
        self.current_message_id: Optional[int] = None
        self.should_cancel: bool = False
        self.streaming_lock = asyncio.Lock()
        self.agent_service = None
    
    async def send_json(self, content, close=False):
        """
        发送 JSON 消息
        """
        await self.send(text_data=json.dumps(content), close=close)

    async def connect(self):
        """
        连接 WebSocket（无需认证）
        URL 格式: ws/chat/<namespace>/<session_id>/
        """
        self.namespace = self.scope['url_route']['kwargs'].get('namespace')
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        
        # 获取查询参数中的 model
        from urllib.parse import parse_qs
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        logger.info(f"WebSocket raw query string: {query_string}")
        query_params = parse_qs(query_string)
        model = query_params.get('model', [None])[0]
        
        # 如果提供了 model，记录它
        if model:
            logger.info(f"WebSocket 连接请求使用模型: {model}")
            self.model_name = model
        
        if not self.namespace:
            logger.error("Missing namespace in WebSocket URL")
            await self.close()
            return

        # 初始化 AI Agent 服务
        try:
            self.agent_service = AIAgentEngine(self.namespace, model_name=model)
        except Exception as e:
            logger.error(f"Failed to initialize AI Agent for {self.namespace}: {e}")
            await self.close()
            return

        # 如果没有 session_id，创建新会话
        if not self.session_id:
            # 这里需要 SessionMemory 逻辑或者直接创建 Session
            # 简化起见，我们假设前端必须提供 session_id，或者我们在这里创建
            # 但 SessionMemory 是 sync 的，这里是 async
            # 暂时假设 session_id 是必须的，或者如果为空，我们在 handle_message 时创建？
            # 路由通常要求 session_id。如果是新建会话，前端应该先请求 API 创建会话，或者生成一个 UUID。
            pass
        
        # 创建房间组名 (使用 namespace 区分)
        self.room_group_name = f'chat_{self.namespace}_{self.session_id}'
        
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
            'session_id': self.session_id,
            'namespace': self.namespace
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
                    namespace=self.namespace,
                    model_name=self.model_name
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
                    namespace=self.namespace,
                    model_name=self.agent_service.model_name
                )
            )

    async def handle_edit_message(self, data: Dict[str, Any]):
        """处理编辑消息请求"""
        async with self.streaming_lock:
            message_id = data.get('message_id')
            new_content = data.get('content')
            
            if not message_id or not new_content:
                await self.send_json({
                    'type': 'error',
                    'message': '缺少 message_id 或 content'
                })
                return
            
            # 获取要编辑的消息
            message = await self.get_message(message_id)
            if not message:
                await self.send_json({
                    'type': 'error',
                    'message': '消息不存在'
                })
                return
            
            # 更新消息内容
            await self.update_message_content(message_id, new_content)
            
            # 删除该消息之后的所有消息
            await self.delete_messages_after(message_id)
            
            # 获取更新后的消息列表并发送给前端（同步状态）
            updated_messages = await self.get_session_history(100)
            await self.send_json({
                'type': 'messages_updated',
                'messages': updated_messages
            })

            # 重置取消标志
            self.should_cancel = False
            
            # 创建新的 AI 消息占位符
            ai_message_id = await self.create_ai_message_placeholder()
            self.current_message_id = ai_message_id
            
            # 发送生成开始消息
            await self.send_json({
                'type': 'generation_started',
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
                    user_input=new_content,
                    namespace=self.namespace,
                    model_name=self.model_name
                )
            )

    async def chat_stream(self, event):
        """
        处理来自 Channel Layer 的流式消息
        """
        await self.send_json(event['data'])

    # -------------------------------------------------------------------------
    # 数据库辅助方法 (使用 sync_to_async 包装)
    # -------------------------------------------------------------------------
    
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_session_history(self, limit: int = 50):
        messages = ChatMessage.objects.filter(session__session_id=self.session_id).order_by('-created_at')[:limit]
        result = []
        for msg in reversed(messages):
            result.append(msg.to_dict())
        return result

    @sync_to_async
    def save_user_message(self, content: str):
        # 确保 Session 存在
        session, _ = ChatSession.objects.get_or_create(session_id=self.session_id)
             
        msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content=content,
            status='completed'
        )
        return msg.id

    @sync_to_async
    def create_ai_message_placeholder(self, parent_id: int = None):
        try:
            session = ChatSession.objects.get(session_id=self.session_id)
        except ChatSession.DoesNotExist:
            # 理论上不应该发生，因为 save_user_message 已经创建了
            session = ChatSession.objects.create(session_id=self.session_id)
            
        msg = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content='',
            status='pending'
        )
        return msg.id

    @sync_to_async
    def update_message_status(self, message_id: int, status: str):
        ChatMessage.objects.filter(id=message_id).update(status=status)

    @sync_to_async
    def get_last_ai_message(self):
        msg = ChatMessage.objects.filter(session__session_id=self.session_id, role='assistant').order_by('-created_at').first()
        return msg.to_dict() if msg else None

    @sync_to_async
    def get_message(self, message_id: int):
        try:
            return ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return None

    @sync_to_async
    def get_parent_user_message(self, message):
        # 简单的逻辑：找上一条 User 消息
        # 实际逻辑可能更复杂，或者通过 parent_id 关联
        # 这里假设按时间顺序的前一条就是
        try:
            return ChatMessage.objects.filter(
                session__session_id=self.session_id, 
                role='user', 
                created_at__lt=message.created_at
            ).order_by('-created_at').first()
        except Exception:
            return None

    @sync_to_async
    def delete_message_and_children(self, message_id: int):
        # 简单实现：删除该消息及其后所有消息
        try:
            msg = ChatMessage.objects.get(id=message_id)
            ChatMessage.objects.filter(
                session__session_id=self.session_id,
                created_at__gte=msg.created_at
            ).delete()
        except ChatMessage.DoesNotExist:
            pass

    @sync_to_async
    def update_message_content(self, message_id: int, content: str):
        ChatMessage.objects.filter(id=message_id).update(content=content)

    @sync_to_async
    def delete_messages_after(self, message_id: int):
        try:
            msg = ChatMessage.objects.get(id=message_id)
            ChatMessage.objects.filter(
                session__session_id=self.session_id,
                created_at__gt=msg.created_at
            ).delete()
        except ChatMessage.DoesNotExist:
            pass
