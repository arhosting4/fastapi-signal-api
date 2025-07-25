# filename: trainerai.py

import random
from sqlalchemy.orm import Session
from typing import Dict
import database_crud as crud
import logging

logger = logging.getLogger(__name__)

def is_heikin_ashi_strong(signal_type: str, heikin_ashi_candles: list) -> bool:
    """
    یہ چیک کرتا ہے کہ آیا آخری Heikin-Ashi کینڈلز ایک مضبوط رجحان دکھا رہی ہیں۔
    """
    try:
        if len(heikin_ashi_candles) < 2:
            return False
        
        last_candle = heikin_ashi_candles[-1]
        
        if signal_type == "buy":
            # مضبوط خرید: سبز کینڈل جس کی نچلی وِک نہ ہو یا بہت چھوٹی ہو۔
            is_green = last_candle['HA_close'] > last_candle['HA_open']
            has_no_lower_wick = last_candle['HA_open'] == last_candle['HA_low']
            return is_green and has_no_lower_wick
            
        elif signal_type == "sell":
            # مضبوط فروخت: سرخ کینڈل جس کی اوپری وِک نہ ہو یا بہت چھوٹی ہو۔
            is_red = last_candle['HA_close'] < last_candle['HA_open']
            has_no_upper_wick = last_candle['HA_open'] == last_candle['HA_high']
            return is_red and has_no_upper_wick
            
    except Exception as e:
        logger.warning(f"Heikin-Ashi کی مضبوطی چیک کرنے میں خرابی: {e}")
        return False
    return False


def get_confidence(
    db: Session,
    m15_trend: str,
    m5_signal_data: Dict,
    risk_status: str,
    news_impact: str,
    symbol: str
) -> float:
    """
    نئی ملٹی ٹائم فریم منطق کی بنیاد پر اعتماد کا اسکور تیار کرتا ہے۔
    """
    base_confidence = 60.0  # بنیادی اسکور کیونکہ سگنل پہلے ہی بڑے رجحان کے موافق ہے
    
    signal_type = m5_signal_data.get("signal")
    rsi_value = m5_signal_data.get("rsi", 50)
    heikin_ashi_candles = m5_signal_data.get("heikin_ashi", [])

    # 1. RSI کی تصدیق
    if (signal_type == "buy" and rsi_value > 55) or (signal_type == "sell" and rsi_value < 45):
        base_confidence += 15.0
        logger.info(f"[{symbol}] RSI تصدیق کامیاب۔ اسکور میں 15 کا اضافہ۔")

    # 2. Heikin-Ashi کینڈل کی مضبوطی کی تصدیق
    if is_heikin_ashi_strong(signal_type, heikin_ashi_candles):
        base_confidence += 15.0
        logger.info(f"[{symbol}] Heikin-Ashi کی مضبوطی کی تصدیق کامیاب۔ اسکور میں 15 کا اضافہ۔")

    # 3. رسک اور خبروں کی بنیاد پر کٹوتیاں
    if risk_status == "High":
        base_confidence -= 20.0
        logger.warning(f"[{symbol}] زیادہ اتار چڑھاؤ کی وجہ سے اسکور میں 20 کی کمی۔")
    elif risk_status == "Moderate":
        base_confidence -= 10.0

    if news_impact == "High":
        base_confidence -= 25.0 # خبروں کا اثر سب سے زیادہ ہے
        logger.warning(f"[{symbol}] زیادہ اثر والی خبروں کی وجہ سے اسکور میں 25 کی کمی۔")

    # 4. ماضی کی کارکردگی کی بنیاد پر ایڈجسٹمنٹ
    try:
        feedback_stats = crud.get_feedback_stats_from_db(db, symbol)
        if feedback_stats and feedback_stats["total"] > 5:
            accuracy = feedback_stats.get("accuracy", 50.0)
            # 50% درستگی پر کوئی تبدیلی نہیں، 100% پر +10، 0% پر -10
            adjustment = (accuracy - 50) / 5.0 
            base_confidence += adjustment
            logger.info(f"[{symbol}] ماضی کی کارکردگی ({accuracy}%) کی بنیاد پر اسکور میں {adjustment:.1f} کی ایڈجسٹمنٹ۔")
    except Exception as e:
        logger.error(f"فیڈ بیک کے اعداد و شمار حاصل کرنے میں خرابی: {e}")

    # اسکور کو 10 اور 99 کے درمیان محدود کریں
    final_confidence = max(10.0, min(99.0, base_confidence))
    
    return round(final_confidence, 2)
    
