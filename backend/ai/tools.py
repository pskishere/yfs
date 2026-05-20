import logging
from langchain_core.tools import tool
from langchain_community.document_loaders import WebBaseLoader, TextLoader, CSVLoader

logger = logging.getLogger(__name__)


@tool
def internet_search(query: str) -> str:
    """
    Search the internet for current information using DuckDuckGo.

    Args:
        query: The search query string

    Returns:
        Search results as text
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"**{r.get('title', '')}**\n{r.get('body', '')}\n{r.get('href', '')}")
        return "\n\n".join(lines)
    except Exception as e:
        logger.error(f"internet_search failed: {e}")
        return f"Search failed: {e}"


@tool
def load_document(source: str, type: str = "auto") -> str:
    """
    Load and parse document content from a URL or local file path.

    Args:
        source: URL (http/https) or absolute local file path
        type: 'auto' | 'web' | 'pdf' | 'csv' | 'txt'

    Returns:
        Parsed text content (truncated to 20 000 characters)
    """
    try:
        source = source.strip()

        if type == "auto":
            if source.startswith(("http://", "https://")):
                type = "web"
            elif source.lower().endswith(".pdf"):
                type = "pdf"
            elif source.lower().endswith(".csv"):
                type = "csv"
            else:
                type = "txt"

        if type == "web":
            loader = WebBaseLoader(source)
        elif type == "csv":
            loader = CSVLoader(source)
        elif type == "pdf":
            try:
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(source)
            except ImportError:
                return "Error: pypdf not installed. Run: pip install pypdf"
        else:
            loader = TextLoader(source)

        docs = loader.load()
        content = "\n\n".join(d.page_content for d in docs)
        if len(content) > 20_000:
            content = content[:20_000] + "\n...(truncated)"
        return content

    except Exception as e:
        logger.error(f"load_document({source}): {e}")
        return f"Error loading document: {e}"
