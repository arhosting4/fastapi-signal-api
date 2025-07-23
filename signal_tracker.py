# filename: signal_tracker.py

import random
from datetime import datetime

# Dummy signal data for demo; replace with real model integration later
def get_all_signals():
    example_signals = [
        {
            "symbol": "EUR/USD",
            "timeframe": "5m",
            "confidence": round(random.uniform(75.0, 99.0), 2),
            "direction": random.choice(["BUY", "SELL"]),
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "symbol": "BTC/USD",
            "timeframe": "15m",
            "confidence": round(random.uniform(70.0, 95.0), 2),
            "direction": random.choice(["BUY", "SELL"]),
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "symbol": "XAU/USD",
            "timeframe": "1h",
            "confidence": round(random.uniform(80.0, 98.0), 2),
            "direction": random.choice(["BUY", "SELL"]),
            "timestamp": datetime.utcnow().isoformat()
        },
    ]

    # Simulate signal filtering based on confidence threshold
    high_confidence_signals = [s for s in example_signals if s["confidence"] >= 80.0]
    return high_confidence_signals
