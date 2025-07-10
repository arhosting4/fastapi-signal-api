from datetime import datetime, time

def check_news(symbol: str) -> dict:
    current_utc_time = datetime.utcnow().time()
    risky_hours_utc = [
        (time(12, 0), time(13, 0)), (time(14, 30), time(15, 30)), (time(8, 0), time(9, 0))
    ]
    for start_time, end_time in risky_hours_utc:
        if start_time <= current_utc_time <= end_time:
            return {"impact": "High", "reason": f"Risky hour detected (UTC: {current_utc_time.strftime('%H:%M')})."}
    return {"impact": "Clear", "reason": "No significant news events anticipated."}
