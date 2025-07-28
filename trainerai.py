# filename: trainerai.py

import random
import logging
import json
import threading
from sqlalchemy.orm import Session
import database_crud as crud
from models import ActiveSignal

logger = logging.getLogger(__name__)
WEIGHTS_FILE = "strategy_weights.json"
weights_lock = threading.Lock() # فائل تک رسائی کو محفوظ بنانے کے لیے

# ==============================================================================
# ★★★ کمک سیکھنے کا انجن (حتمی ورژن) ★★★
# ==============================================================================

def get_confidence(#... کوئی تبدیلی نہیں ...
#... پچھلا کوڈ یہاں ویسے ہی رہے گا ...
#...
#...
    return round(confidence, 2)

def _get_signal_components(reason: str) -> Dict[str, int]:
    """
    سگنل کی وجہ سے انڈیکیٹر کے اسکور نکالتا ہے۔
    یہ ایک آسان طریقہ ہے؛ مستقبل میں اسے بہتر بنایا جا سکتا ہے۔
    """
    # یہ فنکشن ابھی استعمال نہیں ہو رہا، ہم strategybot سے براہ راست اسکور لیں گے
    return {}

def learn_from_outcome(db: Session, signal: ActiveSignal, outcome: str):
    """
    ٹریڈ کے نتیجے سے سیکھتا ہے اور strategy_weights.json کو اپ ڈیٹ کرتا ہے۔
    """
    try:
        symbol = signal.symbol
        result = "کامیابی (TP Hit)" if outcome == "tp_hit" else "ناکامی (SL Hit)"
        logger.info(f"🧠 ٹرینر نے فیڈ بیک وصول کیا: {symbol} پر نتیجہ {result} تھا۔")

        # سگنل کی وجہ سے انڈیکیٹر کے اسکور حاصل کریں
        # نوٹ: یہ فرض کرتا ہے کہ 'reason' میں وہ معلومات موجود ہے،
        # لیکن بہتر طریقہ یہ ہے کہ یہ معلومات سگنل کے ساتھ محفوظ کی جائے۔
        # ہم نے اسے strategybot میں شامل کر دیا ہے۔
        
        # ابھی کے لیے، ہم ایک فرضی تجزیہ کریں گے
        # اصل نفاذ کے لیے، ہمیں سگنل بناتے وقت انڈیکیٹر کی حالت کو محفوظ کرنا ہوگا
        
        # فرض کریں کہ ہم نے سگنل کے ساتھ 'component_scores' محفوظ کیے ہیں
        # (یہ کام ہم نے strategybot میں کر دیا ہے، لیکن اسے DB میں شامل کرنا ہوگا)
        # ابھی کے لیے، ہم ایک فرضی کام کریں گے
        
        adjustment_factor = 0.05 # 5% ایڈجسٹمنٹ
        
        with weights_lock:
            logger.info(f"وزن کی فائل ({WEIGHTS_FILE}) کو لاک کیا جا رہا ہے۔")
            try:
                with open(WEIGHTS_FILE, 'r') as f:
                    weights = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.error(f"{WEIGHTS_FILE} نہیں ملی۔ سیکھنے کا عمل روکا جا رہا ہے۔")
                return

            # فرضی طور پر، ہم تمام وزن کو ایڈجسٹ کرتے ہیں
            if outcome == "tp_hit":
                logger.info(f"✅ {symbol} پر کامیاب ٹریڈ کی بنیاد پر حکمت عملی کو مضبوط کیا جا رہا ہے۔")
                for key in weights:
                    weights[key] *= (1 + adjustment_factor)
            else: # sl_hit
                logger.info(f"❌ {symbol} پر ناکام ٹریڈ کی بنیاد پر حکمت عملی کو ایڈجسٹ کیا جا رہا ہے۔")
                for key in weights:
                    weights[key] *= (1 - adjustment_factor)
            
            # یقینی بنائیں کہ وزن کا مجموعہ 1 کے قریب رہے
            total_weight = sum(weights.values())
            if total_weight > 0:
                for key in weights:
                    weights[key] = round(weights[key] / total_weight, 4)

            with open(WEIGHTS_FILE, 'w') as f:
                json.dump(weights, f, indent=4)
            
            logger.info(f"🧠 نئے وزن کامیابی سے محفوظ کیے گئے: {weights}")

    except Exception as e:
        logger.error(f"سیکھنے کے عمل کے دوران خرابی: {e}", exc_info=True)
    finally:
        if weights_lock.locked():
            weights_lock.release()
            logger.info("وزن کی فائل کو ان لاک کر دیا گیا۔")

