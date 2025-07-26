# filename: gold_hunter.py

import asyncio
import logging
from sqlalchemy.orm import Session

# مقامی امپورٹس
from ai_engine_wrapper import process_data_for_ai
from models import SessionLocal

logger = logging.getLogger(__name__)

# کنفیگریشن
GOLD_SYMBOL = "XAU/USD"
GOLD_TIMEFRAME = "15m"

async def hunt_for_gold_signals_job():
    """
    مقررہ وقفوں پر صرف سونے (XAU/USD) کا تجزیہ کرتا ہے۔
    """
    logger.info(f">>> سونے کی تلاش کا کام ({GOLD_SYMBOL}) شروع ہو رہا ہے...")
    
    # ★★★ خودکار اصلاح: غیر ضروری 'db' آرگیومنٹ کو ہٹا دیا گیا ★★★
    # پرانی لائن:
    # await process_data_for_ai(symbol=GOLD_SYMBOL, timeframe=GOLD_TIMEFRAME, source="TwelveData", db=db)
    # نئی اور درست لائن:
    await process_data_for_ai(
        symbol=GOLD_SYMBOL, 
        timeframe=GOLD_TIMEFRAME, 
        source="TwelveData"
    )
    
    logger.info(f">>> سونے کی تلاش کا کام ({GOLD_SYMBOL}) مکمل ہوا۔")
