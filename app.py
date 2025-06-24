# src/app.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from agents.core_controller import generate_final_signal
from agents.telegrambot import send_telegram_signal

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "ScalpMasterAi API is running"}

@app.get("/final-signal/{symbol}")
async def get_signal(symbol: str, tf: str = "1m", closes: str = ""):
    try:
        # Parse closing prices from comma-separated string
        if not closes:
            return {"status": "error", "reason": "Missing 'closes' parameter"}

        close_list = [float(x) for x in closes.split(",") if x.strip()]
        result = generate_final_signal(symbol.upper(), tf, close_list)

        if result["status"] == "ok" and result["signal"] in ["buy", "sell"]:
            send_telegram_signal(
                symbol=symbol.upper(),
                signal=result["signal"],
                price=close_list[-1],
                confidence=result.get("confidence", 0.0),
                tier=result.get("tier", "N/A"),
                reason=result.get("reason", "N/A")
            )

        return result

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "reason": str(e)}
        )
