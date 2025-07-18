import os
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# --- نیا: کلید مینیجر کو امپورٹ کریں ---
from key_manager import key_manager

NEWS_CACHE_FILE = "data/news_cache.json"
os.makedirs("data", exist_ok=True)

async def update_economic_calendar_cache():
    """
    معاشی کیلنڈر کا ڈیٹا حاصل کرتا ہے، اب API کلید کی گردش کے ساتھ۔
    """
    print("--- SENTINEL: Updating economic calendar cache... ---")
    
    # --- اہم تبدیلی: کلید مینیجر سے کلید حاصل کریں ---
    api_key = key_manager.get_current_key()
    if not api_key:
        print("Sentinel: No available API key.")
        return

    countries = "US,Eurozone,United Kingdom,Germany,Japan,Canada,Australia,China"
    today = datetime.utcnow().strftime('%Y-%m-%d')
    day_after_tomorrow = (datetime.utcnow() + timedelta(days=2)).strftime('%Y-%m-%d')

    url = f"https://api.twelvedata.com/economic_calendar"
    params = {"country": countries, "start_date": today, "end_date": day_after_tomorrow, "apikey": api_key}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=20)
        
        if response.status_code == 429:
            print("Sentinel: API key limit reached. Rotating key.")
            key_manager.rotate_to_next_key()
            # دوبارہ کوشش نہیں کریں گے کیونکہ یہ جاب اہم نہیں اور 12 گھنٹے بعد خود چلے گی
            return

        response.raise_for_status()
        data = response.json()

        upcoming_high_impact_events = []
        if data and "events" in data and data["events"]:
            for event in data["events"]:
                if event.get("importance") == "High":
                    upcoming_high_impact_events.append(event)
        
        with open(NEWS_CACHE_FILE, "w") as f:
            json.dump(upcoming_high_impact_events, f, indent=2)
        
        print(f"--- SENTINEL: Cache updated. Found {len(upcoming_high_impact_events)} high-impact events. ---")

    except Exception as e:
        print(f"⚠️ SENTINEL ERROR: Could not update news cache. Reason: {e}")

# get_news_analysis_for_symbol فنکشن میں کوئی تبدیلی نہیں ہوگی
def get_news_analysis_for_symbol(symbol: str) -> Dict[str, Any]:
    # ... (یہ فنکشن ویسے ہی رہے گا جیسا پچھلے جواب میں تھا) ...
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
            
            if now < event_time < (now + timedelta(minutes=60)):
                event_name = event.get("name")
                time_to_event = round((event_time - now).total_seconds() / 60)
                reason = f"High-impact event '{event_name}' ({event_country}) scheduled in {time_to_event} minutes."
                return {"impact": "High", "reason": reason}

    return {"impact": "Clear", "reason": "No high-impact events for this symbol in the near future."}
    
