"""
后台任务模块 - 异步执行股票分析任务
"""
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
import logging

from .models import ChatMessage
from .agent import StockAIAgent

logger = logging.getLogger(__name__)


async def generate_chat_response(session_id: str, message_id: int, user_input: str, model_name: str = None):
    """
    后台异步任务：生成 AI 回复并推送到 WebSocket 组
    即便 WebSocket 断开也能继续执行
    """
    channel_layer = get_channel_layer()
    group_name = f'stock_chat_{session_id}'
    
    agent_service = StockAIAgent(model_name=model_name) if model_name else StockAIAgent()
    
    full_response = ""
    current_thoughts = []
    
    try:
        # 更新状态为 streaming
        await sync_to_async(ChatMessage.objects.filter(id=message_id).update)(status='streaming')
        
        async for chunk in agent_service.stream_chat(
            session_id=session_id,
            user_input=user_input,
            skip_save_context=True  # 我们自己保存
        ):
            payload = {}
            
            if chunk["type"] == "token":
                token = chunk["content"]
                full_response += token
                payload = {
                    'type': 'token',
                    'message_id': message_id,
                    'token': token,
                    'status': 'streaming'
                }
            elif chunk["type"] == "thought":
                # 更新本地思维链记录
                thought_data = {
                    'key': chunk.get("tool"),
                    'title': chunk["content"],
                    'status': chunk["status"]
                }
                
                # 查找是否已存在该工具的记录
                existing_index = -1
                for i, t in enumerate(current_thoughts):
                    if t.get('key') == thought_data['key']:
                        existing_index = i
                        break
                
                if existing_index > -1:
                    current_thoughts[existing_index] = thought_data
                else:
                    current_thoughts.append(thought_data)
                
                payload = {
                    'type': 'thought',
                    'message_id': message_id,
                    'thought': chunk["content"],
                    'status': chunk["status"],
                    'tool': chunk.get("tool")
                }

            # 发送到 Group
            if payload:
                await channel_layer.group_send(
                    group_name,
                    {
                        "type": "chat_stream",  # Consumer 对应的方法名
                        "data": payload
                    }
                )
        
        # 完成 - 保存完整回复和思维链
        await sync_to_async(ChatMessage.objects.filter(id=message_id).update)(
            content=full_response,
            thoughts=current_thoughts,
            status='completed'
        )
        
        # 发送完成消息
        await channel_layer.group_send(
            group_name,
            {
                "type": "chat_stream",
                "data": {
                    'type': 'generation_completed',
                    'message_id': message_id,
                    'message': full_response,
                    'status': 'completed'
                }
            }
        )

    except Exception as e:
        logger.error(f"Task generation error: {e}", exc_info=True)
        await sync_to_async(ChatMessage.objects.filter(id=message_id).update)(
            status='error',
            error_message=str(e)
        )
        await channel_layer.group_send(
            group_name,
            {
                "type": "chat_stream",
                "data": {
                    'type': 'generation_error',
                    'message_id': message_id,
                    'error': str(e),
                    'status': 'error'
                }
            }
        )



