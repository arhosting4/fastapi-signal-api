# filename: hunter.py
import asyncio
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

import config
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal

logger = logging.getLogger(__name__)

async def analyze_pair_timeframe(db: Session, pair: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    ایک دی گئی تجارتی جوڑی کا مخصوص ٹائم فریم پر تجزیہ کرتا ہے اور اگر مل جائے تو ایک درست سگنل واپس کرتا ہے۔
    """
    try:
        candles = await fetch_twelve_data_ohlc(pair, tf, config.CANDLE_COUNT)
        if not candles or len(candles) < 34: # 34 کی ضرورت ہے کیونکہ طویل ترین SMA 30 ہے
            logger.info(f"{pair} ({tf}): تجزیے کے لیے ناکافی کینڈلز ({len(candles) if candles else 0})۔")
            return None

        signal_result = await generate_final_signal(db, pair, candles, tf)

        if signal_result and signal_result.get("status") == "ok":
            return signal_result

    except Exception as e:
        logger.error(f"شکاری کی خرابی {pair} ({tf}) پر کارروائی کرتے ہوئے: {e}", exc_info=True)
    return None

async def hunt_for_signals_job():
    """
    مرکزی آرکیسٹریٹر: جوڑوں کے ذریعے لوپ کرتا ہے اور AI فیوژن کا استعمال کرکے تجارتی سگنل تلاش کرنے کی کوشش کرتا ہے۔
    """
    logger.info("سگنل کی تلاش کا کام چل رہا ہے...")

    active_count = get_active_signals_count()
    if active_count >= config.MAX_ACTIVE_SIGNALS:
        logger.info(f"فعال سگنلز کی زیادہ سے زیادہ حد ({config.MAX_ACTIVE_SIGNALS}) تک پہنچ گئی۔ تلاش روک دی گئی۔")
        return

    pairs = get_available_pairs()
    db = SessionLocal()
    logger.info(f"ان جوڑوں کا تجزیہ کیا جا رہا ہے: {pairs}")

    try:
        for pair in pairs:
            if get_active_signals_count() >= config.MAX_ACTIVE_SIGNALS:
                logger.info("سگنل کی حد تک پہنچ گئی۔ تلاش کا یہ دور ختم کیا جا رہا ہے۔")
                break

            result = await analyze_pair_timeframe(db, pair, config.PRIMARY_TIMEFRAME)

            if result and result.get("confidence", 0) >= config.FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(result)
                await send_telegram_alert(result)
                logger.info(f"کامیابی! {pair} کے لیے سگنل تیار کیا گیا: {result['signal']} ({result['confidence']}%)")

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        
