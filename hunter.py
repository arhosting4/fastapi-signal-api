import asyncio
import logging
import uuid
from typing import Dict, Any, Optional

from ..utils import get_available_pairs, fetch_twelve_data_ohlc
from . import strategybot, patternai, riskguardian, fusion_engine
from ..database.database_crud import add_active_signal
from ..messenger import send_telegram_alert
from ..database.database_config import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def process_single_pair_timeframe(pair: str, timeframe: str) -> Optional[Dict[str, Any]]:
    """Asynchronously processes a single pair and timeframe to generate a signal."""
    logging.info(f"Processing {pair} on {timeframe}...")
    candles = await fetch_twelve_data_ohlc(pair, timeframe, 200)
    if not candles or len(candles) < 50:
        logging.warning(f"Insufficient data for {pair} on {timeframe}.")
        return None

    core_signal = strategybot.generate_core_signal(candles)
    patterns = patternai.detect_patterns(candles)
    risk = riskguardian.check_risk(candles)
    
    fused_signal = fusion_engine.fuse_signals(core_signal=core_signal, patterns=patterns, risk=risk)

    if fused_signal and fused_signal.get('signal') not in ['hold', 'no_signal']:
        if fused_signal.get('confidence', 0) >= 60:
            logging.info(f"High confidence signal found for {pair} on {timeframe}.")
            final_signal = strategybot.calculate_tp_sl(fused_signal, candles)
            final_signal.update({
                'symbol': pair,
                'timeframe': timeframe,
                'signal_id': str(uuid.uuid4()) # Generate a unique ID for the signal
            })
            return final_signal
    return None

async def hunt_for_signals():
    """Main function to hunt for signals across all pairs and timeframes in parallel."""
    logging.info("Starting new signal hunting cycle...")
    supported_pairs = get_available_pairs()
    timeframes = ["15min", "1h", "4h"]
    
    tasks = [process_single_pair_timeframe(pair, tf) for pair in supported_pairs for tf in timeframes]
    
    logging.info(f"Created {len(tasks)} tasks for parallel execution.")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    logging.info("All tasks executed. Processing results...")
    db_session = SessionLocal()
    try:
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"A task failed during execution: {result}", exc_info=False)
            elif result:
                try:
                    # Prepare data for ActiveSignal model
                    signal_data_for_db = {
                        'signal_id': result['signal_id'],
                        'symbol': result['symbol'],
                        'timeframe': result['timeframe'],
                        'signal_type': result['signal'],
                        'entry_price': result['entry_price'],
                        'tp_price': result['tp_price'],
                        'sl_price': result['sl_price'],
                        'confidence': result['confidence'],
                        'reason': result.get('reason', '')
                    }
                    add_active_signal(db_session, signal_data_for_db)
                    logging.info(f"Signal for {result['symbol']} added to active signals DB.")
                    await send_telegram_alert(result)
                except Exception as e:
                    logging.error(f"Error saving signal or sending alert for {result.get('symbol')}: {e}")
    finally:
        db_session.close()
    logging.info("Signal hunting cycle finished.")
                        
