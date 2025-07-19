from sqlalchemy.orm import Session
from datetime import datetime
import time
import os

from database_config import SessionLocal
from database_crud import get_all_active_trades_from_db, move_trade_to_completed
from utils import fetch_current_price_twelve_data
from key_manager import KeyManager

# KeyManager کو صحیح طریقے سے initialize کریں
api_keys = [
    os.getenv("TWELVE_DATA_API_KEY_1"),
    os.getenv("TWELVE_DATA_API_KEY_2"),
    os.getenv("TWELVE_DATA_API_KEY_3")
]
api_keys = [key for key in api_keys if key]  # Remove None values

key_manager = KeyManager(api_keys) if api_keys else None

def check_feedback_job():
    try:
        print("--- Starting feedback check job ---")
        
        if not key_manager:
            print("--- No API keys available for feedback check ---")
            return
        
        db = SessionLocal()
        
        active_trades = get_all_active_trades_from_db(db)
        
        if not active_trades:
            print("--- No active trades to check ---")
            db.close()
            return
        
        print(f"--- Checking {len(active_trades)} active trades ---")
        
        for trade in active_trades:
            try:
                current_price = fetch_current_price_twelve_data(trade.symbol, key_manager)
                
                if current_price is None:
                    print(f"--- Could not fetch price for {trade.symbol} ---")
                    continue
                
                print(f"--- {trade.symbol}: Current={current_price}, Entry={trade.entry_price}, TP={trade.tp}, SL={trade.sl} ---")
                
                outcome = None
                
                if trade.signal.lower() == "buy":
                    if current_price >= trade.tp:
                        outcome = "tp_hit"
                        print(f"--- BUY TP HIT for {trade.symbol}: {current_price} >= {trade.tp} ---")
                    elif current_price <= trade.sl:
                        outcome = "sl_hit"
                        print(f"--- BUY SL HIT for {trade.symbol}: {current_price} <= {trade.sl} ---")
                
                elif trade.signal.lower() == "sell":
                    if current_price <= trade.tp:
                        outcome = "tp_hit"
                        print(f"--- SELL TP HIT for {trade.symbol}: {current_price} <= {trade.tp} ---")
                    elif current_price >= trade.sl:
                        outcome = "sl_hit"
                        print(f"--- SELL SL HIT for {trade.symbol}: {current_price} >= {trade.sl} ---")
                
                if outcome:
                    move_trade_to_completed(db, trade.id, outcome, current_price)
                    print(f"--- Trade {trade.id} moved to completed with outcome: {outcome} ---")
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"--- ERROR checking trade {trade.id}: {e} ---")
                continue
        
        db.close()
        print("--- Feedback check job completed ---")
        
    except Exception as e:
        print(f"--- ERROR in feedback check job: {e} ---")

def check_single_trade_feedback(trade_id, symbol, signal, entry_price, tp, sl):
    try:
        if not key_manager:
            return None
            
        current_price = fetch_current_price_twelve_data(symbol, key_manager)
        
        if current_price is None:
            return None
        
        outcome = None
        
        if signal.lower() == "buy":
            if current_price >= tp:
                outcome = "tp_hit"
            elif current_price <= sl:
                outcome = "sl_hit"
        
        elif signal.lower() == "sell":
            if current_price <= tp:
                outcome = "tp_hit"
            elif current_price >= sl:
                outcome = "sl_hit"
        
        return {
            "trade_id": trade_id,
            "symbol": symbol,
            "current_price": current_price,
            "outcome": outcome
        }
        
    except Exception as e:
        print(f"--- ERROR in check_single_trade_feedback: {e} ---")
        return None

def get_trade_status(symbol, signal, entry_price, tp, sl):
    try:
        if not key_manager:
            return {"status": "error", "current_price": None}
            
        current_price = fetch_current_price_twelve_data(symbol, key_manager)
        
        if current_price is None:
            return {"status": "unknown", "current_price": None}
        
        if signal.lower() == "buy":
            if current_price >= tp:
                return {"status": "tp_hit", "current_price": current_price}
            elif current_price <= sl:
                return {"status": "sl_hit", "current_price": current_price}
            else:
                pnl_pips = current_price - entry_price
                return {"status": "active", "current_price": current_price, "pnl_pips": pnl_pips}
        
        elif signal.lower() == "sell":
            if current_price <= tp:
                return {"status": "tp_hit", "current_price": current_price}
            elif current_price >= sl:
                return {"status": "sl_hit", "current_price": current_price}
            else:
                pnl_pips = entry_price - current_price
                return {"status": "active", "current_price": current_price, "pnl_pips": pnl_pips}
        
        return {"status": "unknown", "current_price": current_price}
        
    except Exception as e:
        print(f"--- ERROR in get_trade_status: {e} ---")
        return {"status": "error", "current_price": None}
                
