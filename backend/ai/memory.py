from typing import Dict, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from .models import ChatSession, ChatMessage
import uuid

class SessionMemory:
    """
    基于 Django ORM 的通用对话记忆存储
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session, _ = ChatSession.objects.get_or_create(
            session_id=session_id
        )

    @staticmethod
    def create_session() -> str:
        """创建一个新的会话ID"""
        return str(uuid.uuid4())

    def get_messages(self, limit: int = 10) -> List[BaseMessage]:
        """
        获取 LangChain 格式的历史消息列表
        """
        messages = ChatMessage.objects.filter(session=self.session).order_by('-created_at')[:limit]
        # 因为是倒序取 limit，需要再反转回正序
        messages = list(messages)[::-1]
        
        result = []
        for msg in messages:
            if msg.role == 'user':
                result.append(HumanMessage(content=msg.content))
            elif msg.role == 'assistant':
                result.append(AIMessage(content=msg.content))
            elif msg.role == 'system':
                result.append(SystemMessage(content=msg.content))
        
        return result

    def get_history_dicts(self, limit: int = 50) -> List[Dict]:
        """
        获取字典格式的历史消息列表（用于前端展示）
        """
        messages = ChatMessage.objects.filter(session=self.session).order_by('-created_at')[:limit]
        messages = list(messages)[::-1]
        
        result = []
        for msg in messages:
            result.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'thoughts': msg.thoughts,
                'status': msg.status,
                'error_message': msg.error_message
            })
        return result

    def save_context(self, inputs: Dict[str, str], outputs: Dict[str, str]):
        """
        保存对话上下文到数据库
        """
        user_input = inputs.get('input', '')
        ai_output = outputs.get('response', '')
        
        # 保存用户消息
        if user_input:
            existing = ChatMessage.objects.filter(
                session=self.session,
                role='user',
                content=user_input
            ).order_by('-created_at').first()
            
            if not existing:
                ChatMessage.objects.create(
                    session=self.session,
                    role='user',
                    content=user_input
                )
        
        # 保存助手回复
        if ai_output:
            ChatMessage.objects.create(
                session=self.session,
                role='assistant',
                content=ai_output,
                thoughts=outputs.get('thoughts', [])
            )

    def load_memory_variables(self, inputs: Dict[str, str]) -> Dict[str, str]:
        """
        加载历史对话
        """
        messages = ChatMessage.objects.filter(session=self.session).order_by('created_at')
        history = []
        
        for msg in messages:
            if msg.role == 'user':
                history.append(f"用户: {msg.content}")
            elif msg.role == 'assistant':
                history.append(f"助手: {msg.content}")
        
        return {'history': '\n'.join(history) if history else ''}

    def clear(self):
        ChatMessage.objects.filter(session=self.session).delete()
