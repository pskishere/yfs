import json
import asyncio
import logging
import threading
import queue
import os
import yfinance as yf
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Stock

logger = logging.getLogger(__name__)

class StockConsumer(AsyncWebsocketConsumer):
    """
    股票实时数据消费者
    连接时自动订阅数据库中所有的股票代码
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribed_symbols = set()
        self.yf_ws = None
        self.listen_thread = None
        self.stop_event = threading.Event()
        self.update_queue = queue.Queue()
        self.queue_processor_task = None
        self.polling_task = None
        self.ws_active = False

    async def connect(self):
        """连接 WebSocket"""
        await self.accept()
        logger.info("Stock WebSocket connected")
        
        # 启动队列处理器任务
        self.queue_processor_task = asyncio.create_task(self.process_update_queue())
        
        # 从数据库加载股票并订阅
        await self.load_stocks_and_subscribe()

    async def load_stocks_and_subscribe(self):
        """从数据库加载所有股票代码并启动订阅"""
        try:
            # 使用 sync_to_async 获取数据库中的所有股票信息
            stocks_data = await sync_to_async(
                lambda: list(Stock.objects.select_related('quote').all())
            )()
            
            if stocks_data:
                symbols = [s.symbol for s in stocks_data]
                self.subscribed_symbols = set(symbols)
                logger.info(f"Auto-subscribing to stocks from DB: {self.subscribed_symbols}")
                
                # 发送初始数据给前端，避免列表为空
                initial_data = []
                for s in stocks_data:
                    quote = getattr(s, 'quote', None)
                    if quote:
                        initial_data.append({
                            'symbol': s.symbol,
                            'price': float(quote.price) if quote.price else None,
                            'change': float(quote.change) if quote.change else None,
                            'change_pct': float(quote.change_pct) if quote.change_pct else None
                        })
                    else:
                        initial_data.append({'symbol': s.symbol})
                
                await self.send_json({
                    'type': 'subscribed',
                    'symbols': symbols,
                    'initial_data': initial_data
                })
                
                # 启动 yfinance 实时推流
                await self.start_live_stream_with_retry()
            else:
                logger.warning("No stocks found in database to subscribe")
        except Exception as e:
            logger.error(f"Error loading stocks from DB: {e}")
            await self.send_json({
                'type': 'error',
                'message': f"加载股票列表失败: {str(e)}"
            })

    async def disconnect(self, close_code):
        """断开连接"""
        logger.info(f"Stock WebSocket disconnected: {close_code}")
        self.stop_live_stream()
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
        if self.polling_task:
            self.polling_task.cancel()
        
        try:
            if self.queue_processor_task:
                await self.queue_processor_task
            if self.polling_task:
                await self.polling_task
        except asyncio.CancelledError:
            pass

    async def receive(self, text_data):
        """接收客户端消息"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            symbols = data.get('symbols', [])
            
            if not isinstance(symbols, list):
                symbols = [symbols]
            
            if action == 'subscribe':
                await self.handle_subscribe(symbols)
            elif action == 'unsubscribe':
                await self.handle_unsubscribe(symbols)
            else:
                await self.send_json({
                    'type': 'error',
                    'message': f'未知操作: {action}'
                })
        except json.JSONDecodeError:
            await self.send_json({
                'type': 'error',
                'message': '无效的 JSON 数据'
            })
        except Exception as e:
            logger.error(f"Error in StockConsumer receive: {e}")
            await self.send_json({
                'type': 'error',
                'message': str(e)
            })

    async def handle_subscribe(self, symbols):
        """处理订阅请求"""
        new_symbols = [s for s in symbols if s not in self.subscribed_symbols]
        if not new_symbols:
            return
            
        self.subscribed_symbols.update(new_symbols)
        logger.info(f"Subscribing to symbols: {new_symbols}")
        
        # 重新启动实时推流以包含新股票
        await self.start_live_stream_with_retry()
        
        await self.send_json({
            'type': 'subscribed',
            'symbols': list(self.subscribed_symbols)
        })

    async def handle_unsubscribe(self, symbols):
        """处理取消订阅请求"""
        removed_symbols = [s for s in symbols if s in self.subscribed_symbols]
        if not removed_symbols:
            return
            
        for s in removed_symbols:
            self.subscribed_symbols.remove(s)
        logger.info(f"Unsubscribing from symbols: {removed_symbols}")
        
        # 如果还有订阅，重新启动；否则停止
        if self.subscribed_symbols:
            await self.start_live_stream_with_retry()
        else:
            self.stop_live_stream()
            
        await self.send_json({
            'type': 'unsubscribed',
            'symbols': list(self.subscribed_symbols)
        })

    async def start_live_stream_with_retry(self, max_retries=3):
        """启动实时推流，带重试机制"""
        if not self.subscribed_symbols:
            logger.warning("No symbols to subscribe to, skipping live stream")
            return

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to start yfinance WebSocket (attempt {attempt+1}/{max_retries})...")
                self.restart_live_stream()
                self.ws_active = True
                if self.polling_task:
                    self.polling_task.cancel()
                    self.polling_task = None
                logger.info("yfinance WebSocket started successfully")
                return
            except Exception as e:
                logger.error(f"Failed to start yfinance WebSocket (attempt {attempt+1}/{max_retries}): {e}")
                if "proxy" in str(e).lower():
                    logger.error("Detected proxy connection error. Please check your network/proxy settings.")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time}s before next retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.warning("WebSocket failed after all retries, falling back to polling mode")
                    self.ws_active = False
                    if not self.polling_task:
                        self.polling_task = asyncio.create_task(self.poll_stock_prices())

    async def poll_stock_prices(self):
        """当 WebSocket 不可用时，通过 API 轮询价格"""
        logger.info("Starting price polling fallback")
        while not self.ws_active:
            try:
                if not self.subscribed_symbols:
                    await asyncio.sleep(5)
                    continue

                # 批量获取数据
                symbols = list(self.subscribed_symbols)
                for symbol in symbols:
                    try:
                        ticker = yf.Ticker(symbol)
                        # 尝试获取 fast_info，因为它比 info 快
                        info = ticker.fast_info
                        price = info.get('last_price')
                        
                        if price:
                            await self.send_json({
                                'type': 'price_update',
                                'data': {
                                    'symbol': symbol,
                                    'price': price,
                                    'change': info.get('day_change'),
                                    'change_pct': info.get('day_change_percent'),
                                    'source': 'polling'
                                }
                            })
                    except Exception as inner_e:
                        logger.error(f"Polling error for {symbol}: {inner_e}")
                
                # 每 10 秒轮询一次，避免请求过频
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Global polling error: {e}")
                await asyncio.sleep(30)

    def restart_live_stream(self):
        """重新启动 yfinance WebSocket 监听线程"""
        self.stop_live_stream()
        if not self.subscribed_symbols:
            return
            
        self.stop_event.clear()
        
        # 使用 monkey-patch 方式外科手术式修复 yfinance WebSocket 代理问题
        # 这种方式直接针对 websockets 的连接调用，不干扰系统的 HTTP_PROXY 环境变量
        from unittest.mock import patch
        import yfinance.live
        import websockets.sync.client
        
        original_connect = websockets.sync.client.connect
        
        def no_proxy_connect(*args, **kwargs):
            # 强制设置 proxy 为 None，绕过所有自动识别的代理
            kwargs['proxy'] = None
            return original_connect(*args, **kwargs)
            
        try:
            logger.info("Attempting to connect to yfinance WebSocket with forced no-proxy patch")
            # 针对 yfinance.live 中已经导入的 sync_connect 进行 patch
            with patch('yfinance.live.sync_connect', side_effect=no_proxy_connect):
                self.yf_ws = yf.WebSocket()
                self.yf_ws.subscribe(list(self.subscribed_symbols))
            logger.info("Successfully connected to yfinance WebSocket (proxy bypassed surgically)")
        except Exception as e:
            logger.error(f"Surgical proxy bypass failed: {e}. Falling back to default connection.")
            try:
                # 如果 patch 方式失败，尝试最后一次默认连接
                self.yf_ws = yf.WebSocket()
                self.yf_ws.subscribe(list(self.subscribed_symbols))
            except Exception as e2:
                raise e2
        
        # 定义消息回调
        def on_message(data):
            try:
                # data 是 PricingData 对象
                symbol = getattr(data, 'id', None)
                price = getattr(data, 'price', None)
                if symbol and price:
                    self.update_queue.put({
                        'symbol': symbol,
                        'price': price,
                        'change': getattr(data, 'change', None),
                        'change_pct': getattr(data, 'changePercent', None),
                        'time': getattr(data, 'time', None),
                        'source': 'websocket'
                    })
            except Exception as e:
                logger.error(f"Error in yf_ws on_message: {e}")

        # 启动监听线程
        def listen_worker():
            try:
                while not self.stop_event.is_set():
                    self.yf_ws.listen(on_message)
            except Exception as e:
                if not self.stop_event.is_set():
                    logger.error(f"yfinance WebSocket listen error: {e}")
                    # 如果监听线程挂了，且不是手动停止的，尝试触发重试（这里简单处理，让 polling 接管）
                    self.ws_active = False

        self.listen_thread = threading.Thread(target=listen_worker, daemon=True)
        self.listen_thread.start()
        logger.info(f"Started yfinance live stream for: {self.subscribed_symbols}")

    def stop_live_stream(self):
        """停止 yfinance WebSocket"""
        self.stop_event.set()
        if self.yf_ws:
            try:
                self.yf_ws.close()
            except Exception:
                pass
            self.yf_ws = None
        
        if self.listen_thread:
            # 不等待线程结束，它是 daemon 的且 ws.close() 会让 listen 返回
            self.listen_thread = None

    async def process_update_queue(self):
        """处理来自线程的更新队列并推送到客户端"""
        while True:
            try:
                # 使用 run_in_executor 避免阻塞事件循环
                update = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self.update_queue.get(timeout=0.1)
                )
                
                await self.send_json({
                    'type': 'price_update',
                    'data': update
                })
            except queue.Empty:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing update queue: {e}")
                await asyncio.sleep(1)

    async def send_json(self, content):
        """发送 JSON 消息"""
        await self.send(text_data=json.dumps(content))
