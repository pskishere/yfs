#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扩展数据保存模块 - 保存机构持仓、内部交易、分析师推荐、新闻等数据
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from .settings import DB_PATH, logger


def save_institutional_holders(symbol: str, holders: List[Dict[str, Any]]):
    """
    保存机构持仓数据到数据库
    """
    if not holders:
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for holder in holders:
            cursor.execute('''
                INSERT OR REPLACE INTO institutional_holders 
                (symbol, date_reported, holder, shares, value, pct_change, pct_held, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                holder.get('Date Reported'),
                holder.get('Holder'),
                holder.get('Shares'),
                holder.get('Value'),
                holder.get('pctChange'),
                holder.get('pctHeld'),
                datetime.now()
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"已保存机构持仓数据: {symbol}, {len(holders)}条")
    except Exception as e:
        logger.error(f"保存机构持仓数据失败: {symbol}, 错误: {e}")


def save_insider_transactions(symbol: str, transactions: List[Dict[str, Any]]):
    """
    保存内部交易数据到数据库
    """
    if not transactions:
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for trans in transactions:
            cursor.execute('''
                INSERT OR REPLACE INTO insider_transactions 
                (symbol, insider, ownership, position, shares, start_date, text, trans_type, value, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                trans.get('Insider'),
                trans.get('Ownership'),
                trans.get('Position'),
                trans.get('Shares'),
                trans.get('Start Date'),
                trans.get('Text'),
                trans.get('Transaction'),
                trans.get('Value'),
                datetime.now()
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"已保存内部交易数据: {symbol}, {len(transactions)}条")
    except Exception as e:
        logger.error(f"保存内部交易数据失败: {symbol}, 错误: {e}")


def save_analyst_recommendations(symbol: str, recommendations: List[Dict[str, Any]]):
    """
    保存分析师推荐数据到数据库
    """
    if not recommendations:
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for rec in recommendations:
            cursor.execute('''
                INSERT OR REPLACE INTO analyst_recommendations 
                (symbol, date, firm, from_grade, to_grade, action, current_price_target, prior_price_target, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                rec.get('Date'),
                rec.get('Firm'),
                rec.get('From Grade'),
                rec.get('To Grade'),
                rec.get('Action'),
                rec.get('currentPriceTarget'),
                rec.get('priorPriceTarget'),
                datetime.now()
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"已保存分析师推荐数据: {symbol}, {len(recommendations)}条")
    except Exception as e:
        logger.error(f"保存分析师推荐数据失败: {symbol}, 错误: {e}")


def save_stock_news(symbol: str, news: List[Dict[str, Any]]):
    """
    保存股票新闻数据到数据库
    """
    if not news:
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for item in news:
            cursor.execute('''
                INSERT OR IGNORE INTO stock_news 
                (symbol, title, publisher, link, publish_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                symbol,
                item.get('title'),
                item.get('publisher'),
                item.get('link'),
                item.get('providerPublishTime')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"已保存股票新闻数据: {symbol}, {len(news)}条")
    except Exception as e:
        logger.error(f"保存股票新闻数据失败: {symbol}, 错误: {e}")


def save_earnings_data(symbol: str, earnings: Dict[str, Any]):
    """
    保存收益数据到数据库
    """
    if not earnings or 'quarterly' not in earnings:
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for quarter_data in earnings.get('quarterly', []):
            cursor.execute('''
                INSERT OR REPLACE INTO earnings_data 
                (symbol, quarter, revenue, earnings, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                symbol,
                quarter_data.get('quarter'),
                quarter_data.get('Revenue'),
                quarter_data.get('Earnings'),
                datetime.now()
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"已保存收益数据: {symbol}, {len(earnings.get('quarterly', []))}条")
    except Exception as e:
        logger.error(f"保存收益数据失败: {symbol}, 错误: {e}")


def save_extra_data(symbol: str, extra_data: Dict[str, Any]):
    """
    保存所有extra_data到数据库
    """
    if not extra_data:
        return
    
    # 保存机构持仓
    if 'institutional_holders' in extra_data:
        save_institutional_holders(symbol, extra_data['institutional_holders'])
    
    # 保存内部交易
    if 'insider_transactions' in extra_data:
        save_insider_transactions(symbol, extra_data['insider_transactions'])
    
    # 保存分析师推荐
    if 'analyst_recommendations' in extra_data:
        save_analyst_recommendations(symbol, extra_data['analyst_recommendations'])
    
    # 保存新闻
    if 'news' in extra_data:
        save_stock_news(symbol, extra_data['news'])
    
    # 保存收益数据
    if 'earnings' in extra_data:
        save_earnings_data(symbol, extra_data['earnings'])


def get_institutional_holders(symbol: str, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
    """
    从数据库获取机构持仓数据
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date_reported, holder, shares, value, pct_change, pct_held
            FROM institutional_holders
            WHERE symbol = ?
            ORDER BY shares DESC
            LIMIT ?
        ''', (symbol, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        result = []
        for row in rows:
            result.append({
                'Date Reported': row[0],
                'Holder': row[1],
                'Shares': row[2],
                'Value': row[3],
                'pctChange': row[4],
                'pctHeld': row[5]
            })
        
        return result
    except Exception as e:
        logger.error(f"获取机构持仓数据失败: {symbol}, 错误: {e}")
        return None


def get_insider_transactions(symbol: str, limit: int = 15) -> Optional[List[Dict[str, Any]]]:
    """
    从数据库获取内部交易数据
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT insider, ownership, position, shares, start_date, text, trans_type, value
            FROM insider_transactions
            WHERE symbol = ?
            ORDER BY start_date DESC
            LIMIT ?
        ''', (symbol, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        result = []
        for row in rows:
            result.append({
                'Insider': row[0],
                'Ownership': row[1],
                'Position': row[2],
                'Shares': row[3],
                'Start Date': row[4],
                'Text': row[5],
                'Transaction': row[6],
                'Value': row[7]
            })
        
        return result
    except Exception as e:
        logger.error(f"获取内部交易数据失败: {symbol}, 错误: {e}")
        return None


def get_analyst_recommendations(symbol: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
    """
    从数据库获取分析师推荐数据
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, firm, from_grade, to_grade, action, current_price_target, prior_price_target
            FROM analyst_recommendations
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (symbol, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        result = []
        for row in rows:
            result.append({
                'Date': row[0],
                'Firm': row[1],
                'From Grade': row[2],
                'To Grade': row[3],
                'Action': row[4],
                'currentPriceTarget': row[5],
                'priorPriceTarget': row[6]
            })
        
        return result
    except Exception as e:
        logger.error(f"获取分析师推荐数据失败: {symbol}, 错误: {e}")
        return None


def get_stock_news(symbol: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    从数据库获取股票新闻数据
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT title, publisher, link, publish_time
            FROM stock_news
            WHERE symbol = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (symbol, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        result = []
        for row in rows:
            result.append({
                'title': row[0],
                'publisher': row[1],
                'link': row[2],
                'providerPublishTime': row[3]
            })
        
        return result
    except Exception as e:
        logger.error(f"获取股票新闻数据失败: {symbol}, 错误: {e}")
        return None
