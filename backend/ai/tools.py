import logging
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from langchain_community.document_loaders import (
    WebBaseLoader,
    TextLoader,
    CSVLoader,
)

logger = logging.getLogger(__name__)

@tool
def load_document(source: str, type: str = "auto") -> str:
    """
    加载并解析文档内容。支持 URL (网页) 和本地文件路径。
    
    Args:
        source: 文档来源，可以是 URL (以 http/https 开头) 或本地文件绝对路径
        type: 文档类型，可选值: 'auto', 'web', 'pdf', 'csv', 'txt'。默认为 'auto' (根据后缀或内容推断)
        
    Returns:
        解析后的文档文本内容
    """
    try:
        loader = None
        source = source.strip()
        
        # 自动推断类型
        if type == "auto":
            if source.startswith("http://") or source.startswith("https://"):
                type = "web"
            elif source.lower().endswith(".pdf"):
                type = "pdf"
            elif source.lower().endswith(".csv"):
                type = "csv"
            elif source.lower().endswith(".txt") or source.lower().endswith(".md"):
                type = "txt"
            else:
                # 默认尝试 TextLoader
                type = "txt"
        
        # 选择 Loader
        if type == "web":
            # WebBaseLoader requires beautifulsoup4
            loader = WebBaseLoader(source)
        elif type == "csv":
            loader = CSVLoader(source)
        elif type == "txt":
            loader = TextLoader(source)
        elif type == "pdf":
            try:
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(source)
            except ImportError:
                return "Error: pypdf package not installed. Cannot load PDF."
        else:
            return f"Error: Unsupported document type: {type}"
            
        # 加载文档
        docs = loader.load()
        
        # 合并内容
        content = "\n\n".join([d.page_content for d in docs])
        
        # 限制返回长度，避免 Context Window 爆炸
        if len(content) > 20000:
            content = content[:20000] + "\n...(content truncated)..."
            
        return content
        
    except Exception as e:
        logger.error(f"Failed to load document {source}: {e}")
        return f"Error loading document: {str(e)}"
