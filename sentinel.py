# filename: sentinel.py
import os
import httpx
import json
from datetime import datetime

MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN")
DATA_DIR = "data"
NEWS_CACHE_FILE = os.path.join(DATA_DIR, "news_cache.json")

# --- اہم ترین تبدیلی: یقینی بنائیں کہ 'data' فولڈر موجود ہے ---
os.makedirs(DATA_DIR, exist_ok=True)

async def update_economic_calendar_cache():
    if not MARKETAUX_API_TOKEN:
        print("--- SENTINEL: Marketaux API token not set. Skipping news update. ---")
        return

    print("--- SENTINEL: Updating economic news cache... ---")
    url = f"https://api.marketaux.com/v1/news/all?filter_entities=true&group=sentiment&api_token={MARKETAUX_API_TOKEN}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        with open(NEWS_CACHE_FILE, "w") as f:
            json.dump(data.get("data", []), f)
        print("--- SENTINEL: News cache updated successfully. ---")
    except Exception as e:
        print(f"--- SENTINEL ERROR: Could not update news cache: {e} ---")

def get_news_analysis_for_symbol(symbol: str):
    try:
        with open(NEWS_CACHE_FILE, "r") as f:
            all_news = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"impact": "Clear", "reason": "News cache is not available."}

    currencies = symbol.replace('/', ',').upper().split(',')
    high_impact_score = 0
    
    for news_item in all_news:
        if any(curr in news_item.get("symbols", []) for curr in currencies):
            if abs(news_item.get("sentiment_score", 0)) > 0.6:
                high_impact_score += 1
    
    if high_impact_score >= 2: return {"impact": "High", "reason": f"High-impact news detected for {symbol}."}
    elif high_impact_score == 1: return {"impact": "Medium", "reason": f"Medium-impact news detected for {symbol}."}
    return {"impact": "Clear", "reason": "No significant news found."}
    
