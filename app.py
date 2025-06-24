import sys
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

# Fix for internal imports during deployment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

# Load main AI controller
from agents.core_controller import generate_final_signal

# App initialization
app = FastAPI()

# Allow CORS for all origins (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
def root():
    return {"status": "✅ ScalpMasterAi God-Level AI API is live."}

# Signal processing endpoint
@app.get("/get-signal")
async def get_signal(request: Request) -> Dict[str, Any]:
    try:
        params = dict(request.query_params)
        symbol = params.get("symbol")
        candles = params.get("candles")

        if not symbol or not candles:
            return {"error": "Missing 'symbol' or 'candles' in query params."}

        decoded_symbol = symbol.upper()
        parsed_candles = eval(candles) if isinstance(candles, str) else candles

        final_signal = generate_final_signal(decoded_symbol, parsed_candles)

        return {
            "symbol": decoded_symbol,
            "signal": final_signal
        }

    except Exception as e:
        return {"error": f"❌ Exception: {str(e)}"}
