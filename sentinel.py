import os
import httpx
from datetime import datetime, timedelta

# Marketaux API کی کو انوائرمنٹ سے حاصل کریں
MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN")

async def check_news(symbol: str) -> dict:
    """
    Checks for high-impact news for the given symbol using Marketaux API.
    Returns a dictionary with news impact and a reason.
    """
    # اگر API کی سیٹ نہیں ہے، تو کوئی خبر چیک نہ کریں
    if not MARKETAUX_API_TOKEN:
        return {"impact": "Clear", "reason": "News API key not configured."}

    # API کی درخواست کے لیے پیرامیٹرز
    # ہم پچھلے 12 گھنٹوں کی خبریں چیک کریں گے
    params = {
        'api_token': MARKETAUX_API_TOKEN,
        'symbols': symbol.split('/')[0], # جیسے 'EUR/USD' سے 'EUR' حاصل کریں
        'language': 'en',
        'sort': 'published_on',
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.marketaux.com/v1/news/all", params=params, timeout=10)
        
        response.raise_for_status() # HTTP ایرر کے لیے چیک کریں
        news_data = response.json()

        if "data" in news_data and news_data["data"]:
            for article in news_data["data"]:
                # ہم "sentiment" (جذبات) کو چیک کریں گے
                # Marketaux sentiment کو -1 (منفی) سے +1 (مثبت) کے درمیان درجہ دیتا ہے
                sentiment_score = article.get("sentiment_score", 0)
                
                # اگر کوئی بہت ہی مثبت یا بہت ہی منفی خبر ہے، تو اسے ہائی امپیکٹ سمجھیں
                if abs(sentiment_score) >= 0.75:
                    return {
                        "impact": "High",
                        "reason": f"High-impact news detected: '{article['title']}' (Sentiment: {sentiment_score})"
                    }
        
        # اگر کوئی ہائی امپیکٹ خبر نہیں ملی
        return {"impact": "Clear", "reason": "No high-impact news detected in the last 12 hours."}

    except httpx.RequestError as e:
        print(f"⚠️ News API request failed: {e}")
        return {"impact": "Error", "reason": "Could not connect to the news API."}
    except Exception as e:
        print(f"⚠️ An error occurred while checking news: {e}")
        return {"impact": "Error", "reason": "An unexpected error occurred during news check."}

