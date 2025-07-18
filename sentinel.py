import os
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
NEWS_CACHE_FILE = "data/news_cache.json"

# یقینی بنائیں کہ 'data' ڈائرکٹری موجود ہے
os.makedirs("data", exist_ok=True)

async def update_economic_calendar_cache():
    """
    معاشی کیلنڈر سے آنے والے ہائی امپیکٹ واقعات کو حاصل کرتا ہے اور انہیں کیشے فائل میں محفوظ کرتا ہے۔
    یہ فنکشن دن میں صرف دو بار چلایا جائے گا۔
    """
    print("--- SENTINEL: Updating economic calendar cache... ---")
    if not TWELVE_DATA_API_KEY:
        print("⚠️ Sentinel Warning: TWELVE_DATA_API_KEY not set.")
        return

    # تمام اہم ممالک کا ڈیٹا ایک ساتھ حاصل کریں
    countries = "US,Eurozone,United Kingdom,Germany,Japan,Canada,Australia,China"
    today = datetime.utcnow().strftime('%Y-%m-%d')
    # اگلے 2 دن کا ڈیٹا حاصل کریں تاکہ کوئی چیز مس نہ ہو
    day_after_tomorrow = (datetime.utcnow() + timedelta(days=2)).strftime('%Y-%m-%d')

    url = f"https://api.twelvedata.com/economic_calendar"
    params = {"country": countries, "start_date": today, "end_date": day_after_tomorrow, "apikey": TWELVE_DATA_API_KEY}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        upcoming_high_impact_events = []
        if data and "events" in data and data["events"]:
            for event in data["events"]:
                if event.get("importance") == "High":
                    upcoming_high_impact_events.append(event)
        
        # کیشے فائل میں محفوظ کریں
        with open(NEWS_CACHE_FILE, "w") as f:
            json.dump(upcoming_high_impact_events, f, indent=2)
        
        print(f"--- SENTINEL: Cache updated. Found {len(upcoming_high_impact_events)} high-impact events for the next 48 hours. ---")

    except Exception as e:
        print(f"⚠️ SENTINEL ERROR: Could not update news cache. Reason: {e}")

def get_news_analysis_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    کیشے فائل سے ایک مخصوص علامت کے لیے نیوز کا تجزیہ حاصل کرتا ہے۔ (کوئی API کال نہیں)
    """
    try:
        with open(NEWS_CACHE_FILE, "r") as f:
            all_events = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"impact": "Clear", "reason": "News cache is not available."}

    country_map = {
        "XAU/USD": ["US"],
        "EUR/USD": ["US", "Eurozone", "Germany"],
        "GBP/USD": ["US", "United Kingdom"],
        "BTC/USD": ["US"]
    }
    relevant_countries = country_map.get(symbol, ["US"])
    now = datetime.utcnow()

    for event in all_events:
        event_country = event.get("country")
        if event_country in relevant_countries:
            event_time_str = event.get("date")
            if not event_time_str:
                continue
            
            event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
            
            # اگر واقعہ مستقبل میں ہے اور اگلے 60 منٹ کے اندر ہے
            if now < event_time < (now + timedelta(minutes=60)):
                event_name = event.get("name")
                time_to_event = round((event_time - now).total_seconds() / 60)
                reason = f"High-impact event '{event_name}' ({event_country}) scheduled in {time_to_event} minutes."
                return {"impact": "High", "reason": reason}

    return {"impact": "Clear", "reason": "No high-impact events for this symbol in the near future."}
    
