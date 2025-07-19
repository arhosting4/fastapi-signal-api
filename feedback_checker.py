# filename: feedback_checker.py
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Union

import database_crud as crud
from utils import fetch_current_price_twelve_data

async def check_active_signals_job(db_session_factory):
    db: Session = db_session_factory()
    try:
        active_trades = crud.get_all_active_trades_from_db(db)
        if not active_trades:
            return

        print(f"--- FEEDBACK CHECKER: Found {len(active_trades)} active trades to check. ---")
        async with httpx.AsyncClient() as client:
            for trade in active_trades:
                current_price = await fetch_current_price_twelve_data(trade.symbol, client)
                if current_price is None:
                    continue

                outcome = None
                if trade.signal == "buy":
                    if current_price >= trade.tp: outcome = "tp_hit"
                    elif current_price <= trade.sl: outcome = "sl_hit"
                elif trade.signal == "sell":
                    if current_price <= trade.tp: outcome = "tp_hit"
                    elif current_price >= trade.sl: outcome = "sl_hit"
                
                if outcome:
                    print(f"--- TRADE COMPLETED: {trade.symbol} ({trade.signal}) outcome: {outcome} ---")
                    crud.move_trade_to_completed(db, trade.id, outcome, current_price)

    except Exception as e:
        print(f"--- CRITICAL ERROR in check_active_signals_job: {e} ---")
    finally:
        db.close()
        
