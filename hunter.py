import asyncio
import logging
from typing import List, Dict, Any, Optional

# --- Local Imports ---
from ..utils import get_available_pairs, fetch_twelve_data_ohlc
from ..key_manager import key_manager_instance
from . import strategybot, patternai, riskguardian, fusion_engine, sentinel, supply_demand
from ..database.database_crud import add_active_signal
from ..messenger import send_telegram_alert
from ..database.database_config import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def process_single_pair_timeframe(pair: str, timeframe: str, session) -> Optional[Dict[str, Any]]:
    """
    Asynchronously processes a single pair and timeframe to generate a trading signal.
    This is the core unit of work that will be parallelized.
    """
    logging.info(f"Processing {pair} on {timeframe} timeframe...")
    
    # 1. Fetch Market Data
    candles = await fetch_twelve_data_ohlc(pair, timeframe, 200)
    if not candles or len(candles) < 50: # Ensure enough data for analysis
        logging.warning(f"Insufficient data for {pair} on {timeframe}.")
        return None

    # 2. Run AI Analysis Modules
    # These can also be run in parallel if they are I/O bound
    core_signal = strategybot.generate_core_signal(candles)
    patterns = patternai.detect_patterns(candles)
    risk = riskguardian.check_risk(candles)
    
    # NOTE: Disabling these as per optimization plan, can be re-enabled later.
    # news_analysis = await sentinel.get_news_analysis_for_symbol(pair)
    # market_structure = supply_demand.get_market_structure_analysis(candles)
    
    # 3. Fuse Signals
    # Combine results from various modules into one comprehensive signal
    fused_signal = fusion_engine.fuse_signals(
        core_signal=core_signal,
        patterns=patterns,
        risk=risk,
        # news=news_analysis, # Disabled
        # structure=market_structure # Disabled
    )

    # 4. Process Valid Signal
    if fused_signal and fused_signal.get('signal') not in ['hold', 'no_signal']:
        confidence_threshold = 60  # Configurable: minimum confidence to proceed
        if fused_signal.get('confidence', 0) >= confidence_threshold:
            logging.info(f"High confidence signal found for {pair} on {timeframe}.")
            
            # Calculate TP/SL and add other necessary data
            final_signal = strategybot.calculate_tp_sl(fused_signal, candles)
            final_signal['symbol'] = pair
            final_signal['timeframe'] = timeframe
            
            return final_signal
            
    return None

async def hunt_for_signals():
    """
    Main function to hunt for trading signals across all supported pairs and timeframes in parallel.
    """
    logging.info("Starting new signal hunting cycle...")
    
    # --- Configuration ---
    # These should ideally be moved to a central config file
    supported_pairs = get_available_pairs()
    timeframes = ["15min", "1h", "4h"] # Focus on key timeframes
    
    db_session = SessionLocal()
    
    # Create a list of tasks to run in parallel
    tasks = []
    for pair in supported_pairs:
        for timeframe in timeframes:
            task = process_single_pair_timeframe(pair, timeframe, db_session)
            tasks.append(task)
            
    logging.info(f"Created {len(tasks)} tasks for parallel execution.")
    
    # Execute all tasks concurrently
    # `return_exceptions=True` ensures that one failed task doesn't stop the others.
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    logging.info("All tasks have been executed. Processing results...")
    
    # Process the results
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"A task failed during execution: {result}")
        elif result:
            # A valid signal was found and processed
            try:
                # Add signal to active trades in DB
                add_active_signal(db_session, result)
                logging.info(f"Signal for {result['symbol']} added to active signals.")
                
                # Send Telegram alert
                await send_telegram_alert(result)
                logging.info(f"Telegram alert sent for {result['symbol']}.")
                
            except Exception as e:
                logging.error(f"Error saving signal or sending alert for {result.get('symbol')}: {e}")

    db_session.close()
    logging.info("Signal hunting cycle finished.")

