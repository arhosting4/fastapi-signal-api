# filename: hunter.py

import asyncio
import logging
from sqlalchemy.orm import Session
from models import SessionLocal
from roster_manager import get_hunting_roster
from utils import fetch_twelve_data_ohlc
from fusion_engine import run_full_pipeline

logger = logging.getLogger(__name__)

async def process_symbol(db: Session, symbol: str):
    """
    ایک symbol پر مکمل سگنلنگ/analysis pipeline cycle مکمل کرے۔
    """
    try:
        df_candles = await fetch_twelve_data_ohlc(symbol)
        if not df_candles or len(df_candles) < 34:
            logger.warning(f"[{symbol}] کیلئے ڈیٹا ناکافی؛ skip کیا گیا۔")
            return
        import pandas as pd
        df = pd.DataFrame([candle.model_dump() for candle in df_candles])
        await run_full_pipeline(db, symbol, df)
    except Exception as e:
        logger.error(f"[{symbol}] hunter pipeline error: {e}", exc_info=True)

async def run_hunter_engine():
    """
    مرکزی hunting engine — ہر فعال trading pair پر signal making pipeline async چلاتا ہے۔
    """
    logger.info("🔍 Hunter job cycle start — شکار کے لئے نشانات دیکھ رہا ہے...")
    db = SessionLocal()
    try:
        hunting_roster = get_hunting_roster(db)
        logger.info(f"Hunter roster: {hunting_roster}")
        tasks = [process_symbol(db, symbol) for symbol in hunting_roster]
        if tasks:
            await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Hunter engine major error: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_hunter_engine())
    
