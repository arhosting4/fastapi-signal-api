import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# .env فائل سے ماحول کے متغیرات لوڈ کریں
load_dotenv()

# API کلیدوں کو ماحول کے متغیرات سے حاصل کریں
API_KEYS = [
    key.strip() for key in os.getenv("TWELVE_DATA_API_KEYS", "").split(',') if key.strip()
]

# یہ ڈکشنری ہر کلید کی آخری ناکامی کا وقت محفوظ کرے گی
key_limits = {}

print(f"KeyManager: Found {len(API_KEYS)} API keys.")

def get_api_key():
    """
    ایک دستیاب API کلید واپس کرتا ہے جو فی الحال محدود نہیں ہے۔
    """
    now = datetime.utcnow()
    
    # تمام کلیدوں میں سے ایک کو منتخب کرنے کی کوشش کریں
    for key in API_KEYS:
        # اگر کلید محدود ہے، تو چیک کریں کہ کیا ایک منٹ گزر چکا ہے
        if key in key_limits:
            if now - key_limits[key] > timedelta(minutes=1):
                # ایک منٹ گزر چکا ہے، کلید کو دوبارہ قابل استعمال سمجھیں
                key_limits.pop(key)
                print(f"Key ending in ...{key[-4:]} is now available again.")
                return key
        else:
            # اگر کلید محدود نہیں ہے، تو اسے استعمال کریں
            return key
            
    # اگر تمام کلیدیں محدود ہیں اور کسی کا بھی ایک منٹ پورا نہیں ہوا
    print("Warning: All API keys are currently rate-limited.")
    return None

def mark_key_as_limited(key: str):
    """
    ایک کلید کو محدود کے طور پر نشان زد کرتا ہے اور اس کا وقت محفوظ کرتا ہے۔
    """
    now = datetime.utcnow()
    key_limits[key] = now
    print(f"Key ending in ...{key[-4:]} has been marked as rate-limited.")

