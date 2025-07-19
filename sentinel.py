import os
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any

# .env فائل سے ماحول کے متغیرات لوڈ کریں
from dotenv import load_dotenv
load_dotenv()

# --- درست امپورٹ لائن ---
# ہم یہاں key_manager سے کچھ بھی امپورٹ نہیں کر رہے کیونکہ اس کی ضرورت نہیں
# Marketaux کی اپنی کلید ہے

MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN")

# خبروں کے ڈیٹا کو کیشے کرنے کے لیے تاکہ بار بار API کال نہ ہو
news_cache: Dict[str, Any] = {
    "data": None,
    "timestamp": None
}
CACHE_DURATION = timedelta(minutes=30) # 30 منٹ کے لیے کیشے کریں

async def update_news_cache():
    """
    Marketaux API سے خبروں کا ڈیٹا حاصل کرکے کیشے کو اپ ڈیٹ کرتا ہے۔
    """
    global news_cache
    if not MARKETAUX_API_TOKEN:
        print("⚠️ Marketaux API token not set. Skipping news check.")
        news_cache["data"] = {} # کیشے کو خالی کریں
        return

    print("Updating news cache from Marketaux API...")
    url = f"https://api.marketaux.com/v1/news/all?filter_entities=true&group=sentiment&api_token={MARKETAUX_API_TOKEN}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # صرف اہم کرنسیوں کی خبروں کو محفوظ کریں
        processed_news = {}
        if data and "data" in data:
            for item in data["data"]:
                # 'entities' کی موجودگی کو چیک کریں
                if 'entities' in item:
                    for entity in item['entities']:
                        # 'symbol' کی موجودگی کو چیک کریں
                        if 'symbol' in entity:
                            symbol = entity["symbol"]
                            # صرف اہم کرنسیوں کو شامل کریں
                            if any(curr in symbol for curr in ["USD", "EUR", "GBP", "JPY", "XAU"]):
                                if symbol not in processed_news:
                                    processed_news[symbol] = []
                                processed_news[symbol].append(item.get('sentiment_score', 0.0))
        
        news_cache["data"] = processed_news
        news_cache["timestamp"] = datetime.utcnow()
        print("✅ News cache updated successfully.")

    except Exception as e:
        print(f"❌ Failed to update news cache: {e}")
        # ناکامی کی صورت میں کیشے کو خالی کریں
        news_cache["data"] = {}


def get_news_analysis_for_symbol(symbol: str) -> Dict[str, str]:
    """
    کیشے سے کسی مخصوص علامت کے لیے خبروں کا تجزیہ واپس کرتا ہے۔
    """
    if not news_cache["data"]:
        return {"impact": "Clear", "reason": "News data is not available."}

    # علامت سے بنیادی کرنسیوں کو نکالیں (مثلاً XAU/USD -> XAU, USD)
    currencies = symbol.upper().split('/')
    
    high_impact_score = 0
    for currency in currencies:
        # کیشے میں کرنسی کی خبروں کو تلاش کریں
        if currency in news_cache["data"]:
            for sentiment_score in news_cache["data"][currency]:
                if abs(sentiment_score) > 0.6: # اگر سینٹیمنٹ بہت مضبوط ہے
                    high_impact_score += 1

    if high_impact_score >= 2:
        return {"impact": "High", "reason": f"High-impact news detected for {symbol}."}
    elif high_impact_score == 1:
        return {"impact": "Medium", "reason": f"Medium-impact news detected for {symbol}."}
    
    return {"impact": "Clear", "reason": "No significant market-moving news found."}

