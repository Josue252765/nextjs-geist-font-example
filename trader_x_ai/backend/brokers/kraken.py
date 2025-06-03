import httpx
import hmac
import base64
import hashlib
import time
import urllib.parse
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from ..config import get_decrypted_credentials
import websockets
import pandas as pd
import numpy as np
from decimal import Decimal

class KrakenAPI:
    def __init__(self):
        credentials = get_decrypted_credentials()
        if not credentials:
            raise ValueError("Could not initialize Kraken API - missing credentials")
            
        self.api_key = credentials['api_key']
        self.api_secret = credentials['api_secret']
        self.base_url = "https://api.kraken.com"
        self.ws_url = "wss://ws.kraken.com"
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        
        # Trading State
        self.active_trades = {}
        self.positions = {}
        self.order_book = {}
        self.price_cache = {}
        self.trade_history = []
        
        # Risk Management
        self.max_position_size = Decimal('0.1')  # 10% of balance
        self.max_leverage = 5
        self.stop_loss_pct = Decimal('0.02')    # 2% stop loss
        self.take_profit_pct = Decimal('0.06')  # 6% take profit
        
        # WebSocket
        self.ws = None
        self._running = False
        self._price_queue = asyncio.Queue()
        self._order_updates = asyncio.Queue()
        
    async def _sign_request(self, endpoint: str, data: dict) -> Tuple[str, dict]:
        """Sign a private API request"""
        urlpath = f'/0/private/{endpoint}'
        nonce = str(int(time.time() * 1000))
        data['nonce'] = nonce

        post_data = urllib.parse.urlencode(data)
        encoded = (str(nonce) + post_data).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        signature = base64.b64encode(
            hmac.new(base64.b64decode(self.api_secret),
                    message,
                    hashlib.sha512).digest()
        ).decode()
        
        headers = {
            'API-Key': self.api_key,
            'API-Sign': signature
        }
        
        return urlpath, headers

    async def _private_request(self, endpoint: str, data: dict = None) -> dict:
        """Execute a private API request"""
        if data is None:
            data = {}
            
        urlpath, headers = await self._sign_request(endpoint, data)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{urlpath}",
                    data=data,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get('error'):
                    raise Exception(f"Kraken API error: {result['error']}")
                    
                return result['result']
        except Exception as e:
            print(f"Error in private request {endpoint}: {str(e)}")
            raise

    async def start_websocket(self, pairs: List[str]):
        """Start WebSocket connection for real-time data"""
        self._running = True
        
        while self._running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.ws = websocket
                    
                    # Subscribe to relevant feeds
                    await websocket.send(json.dumps({
                        "event": "subscribe",
                        "pair": pairs,
                        "subscription": {
                            "name": "ticker"
                        }
                    }))
                    
                    await websocket.send(json.dumps({
                        "event": "subscribe",
                        "pair": pairs,
                        "subscription": {
                            "name": "trade"
                        }
                    }))
                    
                    while self._running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if isinstance(data, list):
                            await self._handle_websocket_data(data)
                            
            except Exception as e:
                print(f"WebSocket error: {str(e)}")
                await asyncio.sleep(5)  # Retry delay

    async def _handle_websocket_data(self, data: list):
        """Process incoming WebSocket data"""
        try:
            if len(data) < 3:
                return
                
            channel_name = data[2]
            pair = data[3]
            
            if channel_name == "ticker":
                ticker_data = data[1]
                self.price_cache[pair] = {
                    'price': Decimal(ticker_data['c'][0]),
                    'volume': Decimal(ticker_data['v'][1]),
                    'timestamp': datetime.now()
                }
                
                # Check for triggered orders
                await self._check_triggered_orders(pair)
                
            elif channel_name == "trade":
                trade_data = data[1]
                await self._process_trade_data(pair, trade_data)
                
        except Exception as e:
            print(f"Error processing WebSocket data: {str(e)}")

    async def place_order(self, pair: str, order_type: str, side: str, 
                         volume: Decimal, price: Optional[Decimal] = None,
                         leverage: int = 1) -> dict:
        """Place a new order"""
        if leverage > self.max_leverage:
            raise ValueError(f"Leverage {leverage} exceeds maximum allowed {self.max_leverage}")
            
        data = {
            'pair': pair,
            'type': side,
            'ordertype': order_type,
            'volume': str(volume),
            'leverage': str(leverage)
        }
        
        if price and order_type == 'limit':
            data['price'] = str(price)
            
        # Add stop loss and take profit
        if side == 'buy':
            stop_loss = price * (1 - self.stop_loss_pct)
            take_profit = price * (1 + self.take_profit_pct)
        else:
            stop_loss = price * (1 + self.stop_loss_pct)
            take_profit = price * (1 - self.take_profit_pct)
            
        data['close[ordertype]'] = 'stop-loss-limit'
        data['close[price]'] = str(stop_loss)
        data['close[price2]'] = str(take_profit)
        
        result = await self._private_request('AddOrder', data)
        
        # Track the order
        order_id = result['txid'][0]
        self.active_trades[order_id] = {
            'pair': pair,
            'type': order_type,
            'side': side,
            'volume': volume,
            'price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now()
        }
        
        return result

    async def get_balance(self) -> dict:
        """Get account balance"""
        return await self._private_request('Balance')

    async def get_open_positions(self) -> dict:
        """Get open positions"""
        return await self._private_request('OpenPositions')

    async def calculate_optimal_position_size(self, pair: str, risk_per_trade: Decimal) -> Decimal:
        """Calculate optimal position size based on risk management"""
        try:
            balance = await self.get_balance()
            total_equity = sum(Decimal(val) for val in balance.values())
            
            # Limit position size
            max_position = total_equity * self.max_position_size
            risk_based_size = (total_equity * risk_per_trade) / self.stop_loss_pct
            
            return min(max_position, risk_based_size)
            
        except Exception as e:
            print(f"Error calculating position size: {str(e)}")
            raise

    async def analyze_market(self, pair: str, timeframe: int = 60) -> dict:
        """Analyze market conditions using technical indicators"""
        try:
            # Get historical data
            ohlc = await self._private_request('OHLC', {
                'pair': pair,
                'interval': timeframe
            })
            
            df = pd.DataFrame(ohlc[pair], 
                            columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
            
            # Calculate indicators
            df['SMA_20'] = df['close'].rolling(window=20).mean()
            df['SMA_50'] = df['close'].rolling(window=50).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            
            latest = df.iloc[-1]
            
            return {
                'trend': 'bullish' if latest['SMA_20'] > latest['SMA_50'] else 'bearish',
                'rsi': latest['RSI'],
                'macd': latest['MACD'],
                'signal': latest['Signal'],
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"Error analyzing market: {str(e)}")
            raise

    async def execute_strategy(self, pair: str, strategy_config: dict) -> dict:
        """Execute a trading strategy"""
        try:
            # Analyze market
            analysis = await self.analyze_market(pair)
            
            # Get current price
            current_price = self.price_cache.get(pair, {}).get('price')
            if not current_price:
                raise ValueError(f"No price data available for {pair}")
            
            # Strategy logic
            signal = None
            if strategy_config['type'] == 'trend_following':
                if analysis['trend'] == 'bullish' and analysis['rsi'] < 70:
                    signal = 'buy'
                elif analysis['trend'] == 'bearish' and analysis['rsi'] > 30:
                    signal = 'sell'
                    
            elif strategy_config['type'] == 'mean_reversion':
                if analysis['rsi'] < 30:
                    signal = 'buy'
                elif analysis['rsi'] > 70:
                    signal = 'sell'
            
            if signal:
                # Calculate position size
                size = await self.calculate_optimal_position_size(
                    pair, 
                    Decimal(str(strategy_config.get('risk_per_trade', '0.01')))
                )
                
                # Place order
                order = await self.place_order(
                    pair=pair,
                    order_type='market',
                    side=signal,
                    volume=size,
                    leverage=strategy_config.get('leverage', 1)
                )
                
                return {
                    'status': 'success',
                    'action': signal,
                    'order': order,
                    'analysis': analysis
                }
            
            return {
                'status': 'no_action',
                'analysis': analysis
            }
            
        except Exception as e:
            print(f"Error executing strategy: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        self._running = False
        if self.ws:
            await self.ws.close()
        await self.client.aclose()
