# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

import config
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal

# لاگر سیٹ اپ
logger = logging.getLogger(__name__)

async def analyze_pair_timeframe(db: Session, pair: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور اگر کوئی درست سگنل ملے تو اسے واپس کرتا ہے۔
    """
    try:
        # --- اہم لاگ: API کال سے پہلے ---
        logger.info(f"[{pair}] کے لیے کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
        candles = await fetch_twelve_data_ohlc(pair, tf, config.CANDLE_COUNT)
        
        if not candles or len(candles) < 34:
            logger.warning(f"[{pair}] کے لیے ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
            return None
        
        # --- اہم لاگ: AI برین کو کال کرنے سے پہلے ---
        logger.info(f"[{pair}] کے لیے AI فیوژن انجن چلایا جا رہا ہے...")
        signal_result = await generate_final_signal(db, pair, candles, tf)

        if signal_result and signal_result.get("status") == "ok":
            return signal_result
        else:
            # --- اہم لاگ: اگر کوئی سگنل نہ ملے ---
            reason = signal_result.get("reason", "کوئی وجہ نہیں بتائی گئی")
            logger.info(f"[{pair}] کے لیے کوئی سگنل نہیں بنا۔ وجہ: {reason}")
            return None

    except Exception as e:
        logger.error(f"[{pair}] ({tf}) پر کارروائی کے دوران خرابی: {e}", exc_info=True)
    return None

async def hunt_for_signals_job():
    """
    اہم آرکیسٹریٹر: یہ پس منظر کا کام سگنل کی تلاش کرتا ہے۔
    """
    # --- اہم لاگ: جاب کے شروع میں ---
    logger.info("=============================================")
    logger.info(">>> سگنل کی تلاش کا کام (Hunt Job) شروع ہو رہا ہے...")
    logger.info("=============================================")

    active_count = get_active_signals_count()
    if active_count >= config.MAX_ACTIVE_SIGNALS:
        logger.info(f"فعال سگنلز کی حد ({active_count}/{config.MAX_ACTIVE_SIGNALS}) پوری ہو چکی ہے۔ تلاش روکی جا رہی ہے۔")
        return

    pairs = get_available_pairs()
    logger.info(f"تجزیہ کے لیے دستیاب جوڑے: {pairs}")
    db = SessionLocal()

    try:
        for pair in pairs:
            result = await analyze_pair_timeframe(db, pair, config.PRIMARY_TIMEFRAME)

            if result and result.get("confidence", 0) >= config.FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(result)
                await send_telegram_alert(result)
                logger.info(f"★★★ نیا سگنل بنا! ★★★ [{result['symbol']}] - {result['signal'].upper()} @ {result['price']} (اعتماد: {result['confidence']}%)")

                active_count += 1
                if active_count >= config.MAX_ACTIVE_SIGNALS:
                    logger.info("سگنل کی حد پوری ہو گئی۔ اس چکر کے لیے تلاش روکی جا رہی ہے۔")
                    break
    
    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        # --- اہم لاگ: جاب کے آخر میں ---
        logger.info(">>> سگنل کی تلاش کا کام (Hunt Job) مکمل ہوا۔")
        logger.info("=============================================\n")
        
