from typing import Dict, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from .models import ChatSession, ChatMessage
import logging
import uuid

logger = logging.getLogger(__name__)

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


class VectorMemory:
    """
    基于 ChromaDB 的语义记忆。

    首次使用时自动下载 ~80 MB 的 all-MiniLM-L6-v2 嵌入模型（本地推理，无需 API）。
    数据持久化到 data/chroma/ 目录。
    """

    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            import chromadb
            from django.conf import settings
            path = str(settings.BASE_DIR / 'data' / 'chroma')
            cls._client = chromadb.PersistentClient(path=path)
        return cls._client

    def __init__(self, session_id: str):
        self.session_id = session_id
        client = self._get_client()
        # ChromaDB 集合名只允许 3-63 字符，字母数字加连字符/下划线
        safe = 's_' + session_id.replace('-', '_')
        self._col = client.get_or_create_collection(name=safe)

    def add_message(self, message_id: int, role: str, content: str) -> None:
        if not content or not content.strip():
            return
        try:
            self._col.upsert(
                ids=[str(message_id)],
                documents=[content],
                metadatas=[{'role': role, 'message_id': message_id}],
            )
        except Exception as e:
            logger.warning(f"VectorMemory.add_message failed: {e}")

    def search(self, query: str, k: int = 5, exclude_ids: Optional[List[int]] = None) -> List[Dict]:
        """返回与 query 语义最相关的 k 条消息，排除 exclude_ids 中的 ID。"""
        try:
            count = self._col.count()
            if count == 0:
                return []
            results = self._col.query(
                query_texts=[query],
                n_results=min(k + len(exclude_ids or []), count),
            )
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            exclude = set(exclude_ids or [])
            out = []
            for doc, meta in zip(docs, metas):
                if meta['message_id'] not in exclude:
                    out.append({'content': doc, 'role': meta['role'], 'message_id': meta['message_id']})
                    if len(out) >= k:
                        break
            return out
        except Exception as e:
            logger.warning(f"VectorMemory.search failed: {e}")
            return []
