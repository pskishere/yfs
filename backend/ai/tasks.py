"""
后台任务模块 - 异步执行 AI 对话任务
"""
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
import logging

from ai.models import ChatMessage, ChatSession
from ai.engine import AIAgentEngine

logger = logging.getLogger(__name__)

async def generate_title(session_id: str, content: str, namespace: str, model_name: str = None):
    """
    异步任务：生成会话标题
    """
    try:
        # 如果标题已存在，跳过
        session = await sync_to_async(ChatSession.objects.get)(session_id=session_id)
        if session.title:
            return

        # 使用轻量级模型或当前模型生成标题
        agent_service = AIAgentEngine(namespace, model_name=model_name)
        
        # 构造生成标题的 Prompt
        prompt = f"请为以下对话内容生成一个简短的标题（不超过10个字），直接返回标题内容，不要加引号或其他修饰：\n\n{content[:500]}"
        
        # 调用 LLM (非流式)
        # 注意：这里我们直接用 process_message 或者单独的 invoke 逻辑
        # 为了简单，我们临时构造一个 HumanMessage
        from langchain_core.messages import HumanMessage
        response = await agent_service.llm.ainvoke([HumanMessage(content=prompt)])
        title = response.content.strip().strip('"').strip("'")
        
        # 更新数据库
        session.title = title
        await sync_to_async(session.save)()
        
        # 推送标题更新事件
        channel_layer = get_channel_layer()
        group_name = f'chat_{namespace}_{session_id}'
        await channel_layer.group_send(
            group_name,
            {
                "type": "chat_stream",
                "data": {
                    'type': 'title_generated',
                    'title': title,
                    'session_id': session_id
                }
            }
        )
        logger.info(f"Generated title for session {session_id}: {title}")
        
    except Exception as e:
        logger.error(f"Failed to generate title for session {session_id}: {e}")

async def generate_chat_response(session_id: str, message_id: int, user_input: str, namespace: str, model_name: str = None):
    """
    后台异步任务：生成 AI 回复并推送到 WebSocket 组
    即便 WebSocket 断开也能继续执行
    
    Args:
        session_id: 会话ID
        message_id: AI回复消息的数据库ID
        user_input: 用户输入
        namespace: 业务命名空间 (e.g. 'stock')
        model_name: 模型名称覆盖
    """
    channel_layer = get_channel_layer()
    group_name = f'chat_{namespace}_{session_id}'
    
    # 使用 AI 引擎，指定业务命名空间
    try:
        agent_service = AIAgentEngine(namespace, model_name=model_name)
        
        # 触发标题生成任务 (不等待)
        asyncio.create_task(generate_title(session_id, user_input, namespace, model_name))
        
    except Exception as e:
        logger.error(f"Failed to initialize AI Agent for namespace {namespace}: {e}")
        await _send_error(channel_layer, group_name, message_id, str(e))
        return
    
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
        await _send_error(channel_layer, group_name, message_id, str(e))

async def _send_error(channel_layer, group_name, message_id, error_msg):
    """发送错误消息并更新数据库"""
    await sync_to_async(ChatMessage.objects.filter(id=message_id).update)(
        status='error',
        error_message=error_msg
    )
    await channel_layer.group_send(
        group_name,
        {
            "type": "chat_stream",
            "data": {
                'type': 'generation_error',
                'message_id': message_id,
                'error': error_msg,
                'status': 'error'
            }
        }
    )
