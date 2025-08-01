# filename: hunter.py

import asyncio
import logging
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# 🧠 مقامی ماڈیولز
import database_crud as crud
from utils import fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY
from roster_manager import get_hunting_roster  # ★★★ متحرک جوڑوں کا جدید روسٹر ★★★

logger = logging.getLogger(__name__)
FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]

# ==============================================================================
# ★★★ سگنل شکار کی مرکزی جاب (ہر 3 منٹ بعد متوازی تجزیے کے ساتھ) ★★★
# ==============================================================================
async def hunt_for_signals_job():
    """
    یہ جاب ہر 3 منٹ چلتی ہے، متحرک روسٹر کی بنیاد پر نئے سگنل تلاش کرتی ہے۔
    تمام جوڑوں کا تجزیہ async طور پر کیا جاتا ہے۔
    """
    logger.info("🏹 سگنل شکاری جاب شروع ہو گئی...")

    db = SessionLocal()
    try:
        pairs_to_analyze = get_hunting_roster(db)
        if not pairs_to_analyze:
            logger.warning("⚠️ روسٹر سے کوئی جوڑا نہیں ملا تجزیے کے لیے۔")
            return

        logger.info(f"🔍 {len(pairs_to_analyze)} جوڑوں کا تجزیہ شروع ہو رہا ہے...")
        tasks = [analyze_pair(db, pair) for pair in pairs_to_analyze]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"❌ سگنل شکار جاب میں خرابی: {e}", exc_info=True)
    finally:
        db.close()

# ==============================================================================
# 🔍 انفرادی جوڑے کا تجزیہ
# ==============================================================================
async def analyze_pair(db: Session, pair: str):
    try:
        candles = fetch_twelve_data_ohlc(pair)
        if not candles or len(candles) < 34:
            logger.info(f"⛔ {pair} پر ڈیٹا ناکافی ہے ({len(candles)} candles)۔")
            return

        result = await generate_final_signal(db, pair, candles)

        if result["status"] == "signal":
            logger.info(f"✅ سگنل ملا: {pair} | اعتماد: {result['confidence']:.1f}% | Tier: {result.get('tier')}")
            await send_telegram_alert(result)
            await manager.broadcast(json.dumps(result))
            send_signal_update_alert(result)
        else:
            logger.info(f"❌ {pair} پر سگنل نہیں ملا: {result['reason']}")

    except Exception as e:
        logger.error(f"❌ {pair} پر تجزیہ ناکام: {e}", exc_info=True)
