import asyncio
import logging
import sys
from backend.main import TradingBot
from pathlib import Path
import json
import signal

# Configuración de logging
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('TradingBotRunner')

class TradingBotRunner:
    def __init__(self):
        self.bot = None
        self.should_stop = False
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """Manejar el apagado graceful del bot"""
        logger.info("Recibida señal de apagado. Deteniendo el bot...")
        self.should_stop = True
        if self.bot:
            self.bot.running = False

    async def start(self):
        """Iniciar el bot con manejo de errores y reintentos"""
        retry_count = 0
        max_retries = 3
        
        while not self.should_stop and retry_count < max_retries:
            try:
                logger.info("Iniciando Trading Bot...")
                self.bot = TradingBot()
                await self.bot.run()
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Error en el bot (intento {retry_count}/{max_retries}): {str(e)}")
                
                if retry_count < max_retries:
                    wait_time = 60 * retry_count  # Espera incremental
                    logger.info(f"Reintentando en {wait_time} segundos...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Número máximo de reintentos alcanzado. Deteniendo el bot.")
                    break
            
            finally:
                if self.bot:
                    # Guardar estado final
                    self.save_final_state()
                    # Cerrar conexiones
                    await self.bot.kraken.close()

    def save_final_state(self):
        """Guardar el estado final del bot"""
        try:
            state = {
                'performance_metrics': {
                    k: str(v) for k, v in self.bot.performance_metrics.items()
                },
                'last_analysis': {
                    pair: {
                        'timestamp': analysis['timestamp'].isoformat(),
                        'data': analysis['data']
                    }
                    for pair, analysis in self.bot.last_analysis.items()
                }
            }
            
            with open('data/bot_state.json', 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.info("Estado del bot guardado correctamente")
            
        except Exception as e:
            logger.error(f"Error guardando estado del bot: {str(e)}")

def main():
    """Punto de entrada principal"""
    try:
        # Crear directorios necesarios
        Path('data').mkdir(exist_ok=True)
        
        # Iniciar el runner
        runner = TradingBotRunner()
        
        # Ejecutar el bot
        asyncio.run(runner.start())
        
    except KeyboardInterrupt:
        logger.info("Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
