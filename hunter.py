# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from src.database.models import SessionLocal

logger = logging.getLogger(__name__)

# Smart Hunting Configuration
PRIMARY_TIMEFRAME = "15m"
SCOUTING_THRESHOLD = 55.0
CONFLUENCE_BONUS = 15.0
FINAL_CONFIDENCE_THRESHOLD = 70.0
MAX_ACTIVE_SIGNALS = 5

async def analyze_pair_timeframe(db: Session, pair: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    Analyze a given trading pair on a specified timeframe and return a valid signal if found.
    """
    try:
        candles = await fetch_twelve_data_ohlc(pair, tf, 100)
        if not candles or len(candles) < 34:
            return None

        signal_result = await generate_final_signal(db, pair, candles, tf)

        if signal_result and signal_result.get("status") == "ok":
            return signal_result

    except Exception as e:
        logger.error(f"Hunter error processing {pair} ({tf}): {e}")
    return None

async def hunt_for_signals_job():
    """
    Main orchestrator: loops through pairs and tries to find trade signals using AI fusion.
    """
    logger.info("Running signal hunting job...")

    active_count = get_active_signals_count()
    if active_count >= MAX_ACTIVE_SIGNALS:
        logger.info("Max active signals already reached.")
        return

    pairs = get_available_pairs()
    db = SessionLocal()

    try:
        for pair in pairs:
            result = await analyze_pair_timeframe(db, pair, PRIMARY_TIMEFRAME)

            if result and result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(result)
                await send_telegram_alert(result)
                logger.info(f"Signal generated for {pair}: {result['signal']} ({result['confidence']}%)")

                active_count += 1
                if active_count >= MAX_ACTIVE_SIGNALS:
                    logger.info("Signal limit reached. Halting hunting.")
                    break

    except Exception as e:
        logger.error(f"Fatal error in signal hunting job: {e}", exc_info=True)
    finally:
        db.close()
