import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from brokers.kraken import KrakenAPI
import json
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('TradingBot')

class TradingBot:
    def __init__(self):
        self.kraken = KrakenAPI()
        self.active_pairs = ['XBT/USD', 'ETH/USD']
        self.strategies = {}
        self.running = False
        self.last_analysis = {}
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': Decimal('0'),
            'max_drawdown': Decimal('0'),
            'current_drawdown': Decimal('0'),
            'best_trade': Decimal('0'),
            'worst_trade': Decimal('0'),
            'average_profit': Decimal('0')
        }
        
        # Crear directorio para datos
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)

    async def initialize(self):
        """Inicializar el bot y cargar configuraciones"""
        try:
            logger.info("Iniciando Trading Bot...")
            
            # Cargar estrategias predefinidas
            self.strategies = {
                'trend_following': {
                    'type': 'trend_following',
                    'risk_per_trade': '0.01',
                    'leverage': 3,
                    'timeframe': 60,
                    'indicators': {
                        'sma_short': 20,
                        'sma_long': 50,
                        'rsi_period': 14,
                        'rsi_overbought': 70,
                        'rsi_oversold': 30
                    }
                },
                'mean_reversion': {
                    'type': 'mean_reversion',
                    'risk_per_trade': '0.008',
                    'leverage': 2,
                    'timeframe': 30,
                    'indicators': {
                        'bollinger_period': 20,
                        'bollinger_std': 2,
                        'rsi_period': 14
                    }
                },
                'breakout': {
                    'type': 'breakout',
                    'risk_per_trade': '0.012',
                    'leverage': 4,
                    'timeframe': 240,
                    'indicators': {
                        'atr_period': 14,
                        'breakout_period': 20
                    }
                }
            }
            
            # Iniciar WebSocket
            await self.kraken.start_websocket(self.active_pairs)
            
            # Verificar balance inicial
            balance = await self.kraken.get_balance()
            logger.info(f"Balance inicial: {balance}")
            
            # Cargar métricas anteriores si existen
            metrics_file = self.data_dir / 'performance_metrics.json'
            if metrics_file.exists():
                with open(metrics_file) as f:
                    saved_metrics = json.load(f)
                    self.performance_metrics.update({
                        k: Decimal(str(v)) for k, v in saved_metrics.items()
                        if k in self.performance_metrics
                    })
            
            self.running = True
            
        except Exception as e:
            logger.error(f"Error en la inicialización: {str(e)}")
            raise

    async def run_strategy(self, pair: str, strategy_name: str):
        """Ejecutar una estrategia específica"""
        try:
            while self.running:
                strategy_config = self.strategies.get(strategy_name)
                if not strategy_config:
                    raise ValueError(f"Estrategia no encontrada: {strategy_name}")
                
                # Análisis de mercado
                analysis = await self.analyze_market(pair, strategy_config)
                signal = self.generate_signal(analysis, strategy_config)
                
                if signal:
                    # Validar señal con IA
                    if await self.validate_signal_with_ai(pair, signal, analysis):
                        # Calcular tamaño de posición
                        position_size = await self.kraken.calculate_optimal_position_size(
                            pair,
                            Decimal(strategy_config['risk_per_trade'])
                        )
                        
                        # Ejecutar orden
                        order = await self.kraken.place_order(
                            pair=pair,
                            order_type='market',
                            side=signal['direction'],
                            volume=position_size,
                            leverage=strategy_config['leverage']
                        )
                        
                        # Registrar operación
                        await self.record_trade(pair, signal, order, analysis)
                
                # Actualizar análisis
                self.last_analysis[pair] = {
                    'timestamp': datetime.now(),
                    'data': analysis
                }
                
                # Esperar siguiente ciclo
                await asyncio.sleep(strategy_config['timeframe'] * 60)
                
        except Exception as e:
            logger.error(f"Error en estrategia {strategy_name} para {pair}: {str(e)}")
            raise

    async def analyze_market(self, pair: str, strategy_config: dict) -> dict:
        """Análisis técnico avanzado del mercado"""
        try:
            # Obtener datos históricos
            ohlcv = await self.kraken.get_ohlcv(pair, strategy_config['timeframe'])
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            analysis = {
                'timestamp': datetime.now(),
                'indicators': {},
                'patterns': {},
                'volatility': {}
            }
            
            # Calcular indicadores según la estrategia
            if strategy_config['type'] == 'trend_following':
                analysis['indicators'].update(
                    self.calculate_trend_indicators(df, strategy_config['indicators'])
                )
            elif strategy_config['type'] == 'mean_reversion':
                analysis['indicators'].update(
                    self.calculate_mean_reversion_indicators(df, strategy_config['indicators'])
                )
            elif strategy_config['type'] == 'breakout':
                analysis['indicators'].update(
                    self.calculate_breakout_indicators(df, strategy_config['indicators'])
                )
            
            # Análisis de volatilidad
            analysis['volatility'] = self.analyze_volatility(df)
            
            # Patrones de velas
            analysis['patterns'] = self.detect_candlestick_patterns(df)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error en análisis de mercado: {str(e)}")
            raise

    async def validate_signal_with_ai(self, pair: str, signal: dict, analysis: dict) -> bool:
        """Validar señal de trading usando IA"""
        try:
            # Preparar datos para el modelo
            features = self.prepare_features(pair, signal, analysis)
            
            # TODO: Implementar modelo de IA para validación
            # Por ahora, retornamos True como placeholder
            return True
            
        except Exception as e:
            logger.error(f"Error en validación de señal: {str(e)}")
            return False

    async def monitor_performance(self):
        """Monitorear y registrar el rendimiento del bot"""
        try:
            while self.running:
                # Actualizar métricas
                positions = await self.kraken.get_open_positions()
                balance = await self.kraken.get_balance()
                
                # Calcular drawdown actual
                if self.performance_metrics['total_trades'] > 0:
                    current_equity = sum(Decimal(str(v)) for v in balance.values())
                    peak_equity = max(current_equity, self.performance_metrics.get('peak_equity', current_equity))
                    current_drawdown = (peak_equity - current_equity) / peak_equity
                    
                    self.performance_metrics['current_drawdown'] = current_drawdown
                    self.performance_metrics['max_drawdown'] = max(
                        self.performance_metrics['max_drawdown'],
                        current_drawdown
                    )
                
                # Guardar métricas
                metrics_file = self.data_dir / 'performance_metrics.json'
                with open(metrics_file, 'w') as f:
                    json.dump({
                        k: str(v) for k, v in self.performance_metrics.items()
                    }, f, indent=2)
                
                # Log de estado
                logger.info(f"=== Estado del Bot ===")
                logger.info(f"Posiciones abiertas: {len(positions)}")
                logger.info(f"Win Rate: {self.calculate_win_rate():.2f}%")
                logger.info(f"Profit Total: {self.performance_metrics['total_profit']}")
                logger.info(f"Drawdown Actual: {self.performance_metrics['current_drawdown']:.2f}%")
                
                await asyncio.sleep(300)  # Actualizar cada 5 minutos
                
        except Exception as e:
            logger.error(f"Error en monitoreo: {str(e)}")
            raise

    def calculate_win_rate(self) -> float:
        """Calcular win rate"""
        total_trades = self.performance_metrics['total_trades']
        if total_trades == 0:
            return 0.0
        return (self.performance_metrics['winning_trades'] / total_trades) * 100

    async def run(self):
        """Ejecutar el bot"""
        try:
            await self.initialize()
            
            # Crear tareas para cada par y estrategia
            tasks = []
            for pair in self.active_pairs:
                for strategy_name in self.strategies:
                    task = asyncio.create_task(
                        self.run_strategy(pair, strategy_name)
                    )
                    tasks.append(task)
            
            # Agregar tarea de monitoreo
            monitor_task = asyncio.create_task(self.monitor_performance())
            tasks.append(monitor_task)
            
            # Ejecutar todas las tareas
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error en ejecución del bot: {str(e)}")
            raise
        finally:
            self.running = False
            await self.kraken.close()

async def main():
    bot = TradingBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
