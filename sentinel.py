import os
import httpx
from datetime import datetime, time

MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN")

# --- اہم تبدیلی: یہاں client پیرامیٹر شامل کریں ---
async def check_news(symbol: str, client: httpx.AsyncClient) -> dict:
    """
    Checks for high-impact news events using the Marketaux API.
    """
    # اگر API ٹوکن سیٹ نہیں ہے تو ایک عمومی جواب واپس کریں
    if not MARKETAUX_API_TOKEN:
        print("⚠️ Marketaux API token not set. Skipping news check.")
        return {"impact": "Clear", "reason": "News analysis is disabled."}

    # کرنسی پیئرز سے بنیادی کرنسی نکالیں (مثلاً، EUR/USD -> EUR,USD)
    currencies = symbol.replace('/', ',').split(',')[0:2]
    currency_filter = ",".join(currencies)

    url = f"https://api.marketaux.com/v1/news/all?symbols={currency_filter}&filter_entities=true&group=sentiment&api_token={MARKETAUX_API_TOKEN}"

    try:
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or not data.get("data"):
            return {"impact": "Clear", "reason": "No significant news found."}

        # خبروں کے سینٹیمنٹ کا تجزیہ کریں
        high_impact_score = 0
        for news_item in data["data"]:
            # 'sentiment_score' کی موجودگی کو چیک کریں
            if 'sentiment_score' in news_item:
                # اگر سینٹیمنٹ بہت زیادہ مثبت یا منفی ہے تو اسے ہائی امپیکٹ سمجھیں
                if abs(news_item["sentiment_score"]) > 0.6:
                    high_impact_score += 1
        
        if high_impact_score >= 2: # اگر 2 یا زیادہ ہائی امپیکٹ خبریں ہیں
            return {"impact": "High", "reason": f"High-impact news detected for {currency_filter}."}
        elif high_impact_score == 1:
            return {"impact": "Medium", "reason": f"Medium-impact news detected for {currency_filter}."}
        else:
            return {"impact": "Clear", "reason": "No significant market-moving news found."}

    except httpx.RequestError as e:
        print(f"⚠️ News API request failed: {e}")
        return {"impact": "Clear", "reason": "Could not fetch news data."}
    except Exception as e:
        print(f"⚠️ An unexpected error occurred during news check: {e}")
        return {"impact": "Clear", "reason": "An error occurred during news analysis."}

