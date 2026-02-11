import os
import requests
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

logger = logging.getLogger(__name__)

def fetch_news_api(query: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    使用 NewsAPI.org 获取新闻
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        logger.warning("未配置 NEWS_API_KEY，跳过 NewsAPI 抓取")
        return []

    try:
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": api_key,
            "pageSize": 10
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"NewsAPI 返回错误: {response.status_code}, {response.text}")
            return []

        data = response.json()
        articles = data.get('articles', [])
        
        results = []
        for art in articles:
            results.append({
                'title': art.get('title'),
                'publisher': art.get('source', {}).get('name'),
                'link': art.get('url'),
                'provider_publish_time': art.get('publishedAt'),
                'provider_publish_time_fmt': art.get('publishedAt')[:10] if art.get('publishedAt') else '',
                'summary': art.get('description'),
                'thumbnail': art.get('urlToImage'),
                'content': art.get('content')
            })
        return results
    except Exception as e:
        logger.error(f"NewsAPI 抓取失败: {e}")
        return []
