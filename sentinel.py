import requests
import json
import os
from datetime import datetime, timedelta

NEWS_CACHE_FILE = "data/news_cache.json"
MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

def fetch_market_news():
    try:
        if not MARKETAUX_API_KEY:
            print("--- No MARKETAUX_API_KEY found ---")
            return []
        
        url = "https://api.marketaux.com/v1/news/all"
        params = {
            "api_token": MARKETAUX_API_KEY,
            "symbols": "XAUUSD,EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD",
            "filter_entities": "true",
            "language": "en",
            "limit": 20
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            news_items = []
            
            for article in data.get("data", []):
                news_item = {
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "published_at": article.get("published_at", ""),
                    "source": article.get("source", ""),
                    "entities": article.get("entities", {}),
                    "sentiment": article.get("sentiment", "neutral")
                }
                news_items.append(news_item)
            
            print(f"--- Fetched {len(news_items)} news articles ---")
            return news_items
        
        else:
            print(f"--- Error fetching news: HTTP {response.status_code} ---")
            return []
    
    except Exception as e:
        print(f"--- ERROR in fetch_market_news: {e} ---")
        return []

def save_news_to_cache(news_items):
    try:
        os.makedirs("data", exist_ok=True)
        
        cache_data = {
            "last_updated": datetime.utcnow().isoformat(),
            "news": news_items
        }
        
        with open(NEWS_CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"--- Saved {len(news_items)} news items to cache ---")
        return True
        
    except Exception as e:
        print(f"--- ERROR saving news to cache: {e} ---")
        return False

def get_cached_news():
    try:
        if not os.path.exists(NEWS_CACHE_FILE):
            print("--- No news cache file found ---")
            return []
        
        with open(NEWS_CACHE_FILE, "r") as f:
            cache_data = json.load(f)
        
        news_items = cache_data.get("news", [])
        last_updated = cache_data.get("last_updated", "")
        
        print(f"--- Retrieved {len(news_items)} cached news items (last updated: {last_updated}) ---")
        return news_items
        
    except Exception as e:
        print(f"--- ERROR reading cached news: {e} ---")
        return []

def update_news_cache_job():
    try:
        print("--- Starting news cache update job ---")
        
        news_items = fetch_market_news()
        
        if news_items:
            save_news_to_cache(news_items)
            print("--- News cache update job completed successfully ---")
        else:
            print("--- No news items fetched, keeping existing cache ---")
        
    except Exception as e:
        print(f"--- ERROR in update_news_cache_job: {e} ---")

def is_high_impact_news(news_item):
    try:
        title = news_item.get("title", "").lower()
        description = news_item.get("description", "").lower()
        
        high_impact_keywords = [
            "fed", "federal reserve", "interest rate", "inflation", "gdp",
            "employment", "unemployment", "nonfarm", "cpi", "ppi",
            "fomc", "central bank", "monetary policy", "recession",
            "crisis", "emergency", "breaking", "urgent"
        ]
        
        for keyword in high_impact_keywords:
            if keyword in title or keyword in description:
                return True
        
        return False
        
    except Exception as e:
        print(f"--- ERROR in is_high_impact_news: {e} ---")
        return False

def get_market_sentiment():
    try:
        news_items = get_cached_news()
        
        if not news_items:
            return {"sentiment": "neutral", "confidence": 0.5}
        
        positive_count = 0
        negative_count = 0
        total_count = 0
        
        for news_item in news_items:
            sentiment = news_item.get("sentiment", "neutral")
            
            if sentiment == "positive":
                positive_count += 1
            elif sentiment == "negative":
                negative_count += 1
            
            total_count += 1
        
        if total_count == 0:
            return {"sentiment": "neutral", "confidence": 0.5}
        
        positive_ratio = positive_count / total_count
        negative_ratio = negative_count / total_count
        
        if positive_ratio > negative_ratio:
            sentiment = "positive"
            confidence = positive_ratio
        elif negative_ratio > positive_ratio:
            sentiment = "negative"
            confidence = negative_ratio
        else:
            sentiment = "neutral"
            confidence = 0.5
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "total_count": total_count
        }
        
    except Exception as e:
        print(f"--- ERROR in get_market_sentiment: {e} ---")
        return {"sentiment": "neutral", "confidence": 0.5}

def should_avoid_trading():
    try:
        news_items = get_cached_news()
        
        current_time = datetime.utcnow()
        one_hour_ago = current_time - timedelta(hours=1)
        
        recent_high_impact_count = 0
        
        for news_item in news_items:
            try:
                published_at = datetime.fromisoformat(news_item.get("published_at", "").replace("Z", "+00:00"))
                
                if published_at >= one_hour_ago and is_high_impact_news(news_item):
                    recent_high_impact_count += 1
            
            except Exception:
                continue
        
        avoid_trading = recent_high_impact_count >= 2
        
        print(f"--- Recent high impact news: {recent_high_impact_count}, Avoid trading: {avoid_trading} ---")
        
        return {
            "avoid_trading": avoid_trading,
            "recent_high_impact_count": recent_high_impact_count,
            "reason": f"Found {recent_high_impact_count} high-impact news items in the last hour"
        }
        
    except Exception as e:
        print(f"--- ERROR in should_avoid_trading: {e} ---")
        return {"avoid_trading": False, "recent_high_impact_count": 0, "reason": "Error checking news"}
        
