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
        连接 WebSocket
        """
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        
        # 如果没有 session_id，创建新会话
        if not self.session_id:
            self.session_id = await self.create_new_session()
        
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
            recent_history = await self.get_session_history(10)
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
        # 取消正在进行的生成任务
        if self.current_streaming_task and not self.current_streaming_task.done():
            self.should_cancel = True
            self.current_streaming_task.cancel()
            if self.current_message_id:
                await self.update_message_status(self.current_message_id, 'cancelled')
        
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
            
            # 启动流式生成任务
            self.current_streaming_task = asyncio.create_task(
                self.stream_generation(user_input, ai_message_id)
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
    
    async def stream_generation(self, user_input: str, message_id: int):
        """流式生成 AI 回复"""
        try:
            full_response = ""
            
            async for token in self.agent_service.stream_chat(
                session_id=self.session_id,
                user_input=user_input,
                skip_save_context=True  # 消息已由 consumer 管理
            ):
                if self.should_cancel:
                    break
                
                full_response += token
                
                await self.send_json({
                    'type': 'token',
                    'message_id': message_id,
                    'token': token,
                    'status': 'streaming'
                })
            
            if not self.should_cancel:
                # 保存完整回复
                await self.update_message_content(message_id, full_response)
                await self.update_message_status(message_id, 'completed')
                
                await self.send_json({
                    'type': 'generation_completed',
                    'message_id': message_id,
                    'message': full_response,
                    'status': 'completed'
                })
            else:
                # 保存部分回复（如果有的话）
                if full_response:
                    await self.update_message_content(message_id, full_response)
                    
        except asyncio.CancelledError:
            # 任务被取消
            if 'full_response' in locals() and full_response:
                await self.update_message_content(message_id, full_response)
            await self.update_message_status(message_id, 'cancelled')
            raise
        except Exception as e:
            # 处理错误
            error_msg = str(e)
            logger.error(f"生成回复时出错: {error_msg}", exc_info=True)
            await self.update_message_status(message_id, 'error', error_msg)
            await self.send_json({
                'type': 'generation_error',
                'message_id': message_id,
                'error': error_msg,
                'status': 'error'
            })
        finally:
            self.current_message_id = None
            self.current_streaming_task = None
    
    async def send_json(self, data: Dict[str, Any]):
        """发送 JSON 消息"""
        await self.send(text_data=json.dumps(data, ensure_ascii=False))
    
    @database_sync_to_async
    def create_new_session(self) -> str:
        """
        创建新会话
        
        Returns:
            会话ID
        """
        return self.agent_service.create_new_session()
    
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
    def create_ai_message_placeholder(self) -> int:
        """创建 AI 消息占位符"""
        session, _ = ChatSession.objects.get_or_create(
            session_id=self.session_id
        )
        
        message = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content='',
            status='pending'
        )
        return message.id
    
    @database_sync_to_async
    def update_message_content(self, message_id: int, content: str):
        """更新消息内容"""
        ChatMessage.objects.filter(id=message_id).update(content=content)
    
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
