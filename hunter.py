# filename: hunter.py

import asyncio
import logging
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

import database_crud as crud
from utils import fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY
from roster_manager import get_hunting_roster

logger = logging.getLogger(__name__)
FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]

async def hunt_for_signals_job():
    logger.info("🏹 Signal hunting job started...")
    db = SessionLocal()
    try:
        pairs_to_analyze = get_hunting_roster(db)
        if not pairs_to_analyze:
            logger.warning("No pairs found to analyze.")
            return

        logger.info(f"🔍 Analyzing {len(pairs_to_analyze)} pairs...")
        tasks = [analyze_pair(db, pair) for pair in pairs_to_analyze]
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error in signal hunting job: {e}", exc_info=True)
    finally:
        db.close()

async def analyze_pair(db: Session, pair: str):
    try:
        candles = fetch_twelve_data_ohlc(pair)
        if not candles or len(candles) < 34:
            logger.info(f"Insufficient data for {pair}: {len(candles)} candles.")
            return

        result = await generate_final_signal(db, pair, candles)

        if result["status"] == "signal":
            logger.info(f"✅ Signal detected: {pair} | Confidence: {result['confidence']:.1f}% | Tier: {result.get('tier')}")
            await send_telegram_alert(result)
            await manager.broadcast(json.dumps(result))
            send_signal_update_alert(result)
        else:
            logger.info(f"❌ No signal for {pair}: {result['reason']}")
    except Exception as e:
        logger.error(f"Error analyzing {pair}: {e}", exc_info=True)
