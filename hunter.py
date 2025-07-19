import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional

from key_manager import key_manager
from utils import fetch_current_price_twelve_data, fetch_historical_data_twelve_data, validate_symbol_format
from fusion_engine import generate_signal_with_fusion
from database_crud import save_signal_to_db, get_active_signals_from_db
from signal_tracker import update_active_signals

async def hunt_for_signals_job(db_session_factory):
    """Main job that hunts for trading signals across multiple symbols and timeframes"""
    try:
        print("--- Starting signal hunting job ---")
        
        # Define symbols and timeframes to scan
        symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        timeframes = ["5m", "15m", "1h"]
        
        best_signal = None
        best_confidence = 0.0
        
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    print(f"--- Analyzing {symbol} {timeframe} ---")
                    
                    # Validate symbol
                    if not validate_symbol_format(symbol):
                        print(f"--- Invalid symbol format: {symbol} ---")
                        continue
                    
                    # Fetch current price
                    current_price = fetch_current_price_twelve_data(symbol, key_manager)
                    if not current_price:
                        print(f"--- Could not fetch price for {symbol} ---")
                        continue
                    
                    # Fetch historical data
                    historical_data = fetch_historical_data_twelve_data(symbol, timeframe, key_manager)
                    if not historical_data or len(historical_data) < 20:
                        print(f"--- Insufficient historical data for {symbol} {timeframe} ---")
                        continue
                    
                    # Generate signal using fusion engine
                    signal_result = await generate_signal_with_fusion(
                        symbol=symbol,
                        timeframe=timeframe,
                        current_price=current_price,
                        historical_data=historical_data,
                        key_manager=key_manager
                    )
                    
                    if signal_result and signal_result.get("signal") != "wait":
                        confidence = signal_result.get("confidence", 0.0)
                        
                        # Keep track of the best signal
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_signal = signal_result
                            print(f"--- New best signal: {symbol} {timeframe} with confidence {confidence:.2f} ---")
                    
                    # Small delay to avoid overwhelming the API
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"--- ERROR analyzing {symbol} {timeframe}: {e} ---")
                    continue
        
        # If we found a good signal, save it
        if best_signal and best_confidence > 0.6:  # Only save signals with >60% confidence
            try:
                db = db_session_factory()
                save_signal_to_db(db, best_signal)
                db.close()
                
                # Update active signals tracker
                update_active_signals(best_signal)
                
                print(f"--- Saved best signal: {best_signal['symbol']} {best_signal['signal']} with confidence {best_confidence:.2f} ---")
                
            except Exception as e:
                print(f"--- ERROR saving signal to database: {e} ---")
        
        else:
            print("--- No high-confidence signals found in this scan ---")
        
        print("--- Signal hunting job completed ---")
        
    except Exception as e:
        print(f"--- CRITICAL ERROR in hunt_for_signals_job: {e} ---")

def get_current_best_signal() -> Optional[Dict[str, Any]]:
    """Get the current best active signal"""
    try:
        # Try to load from active signals file
        try:
            with open("active_signals.json", "r") as f:
                signals = json.load(f)
                if signals:
                    return signals[0]  # Return the first (best) signal
        except FileNotFoundError:
            pass
        
        # Fallback: try to get from database
        try:
            from database_config import SessionLocal
            db = SessionLocal()
            signals = get_active_signals_from_db(db)
            db.close()
            
            if signals:
                return signals[0]
        except Exception as e:
            print(f"--- ERROR getting signals from database: {e} ---")
        
        return None
        
    except Exception as e:
        print(f"--- ERROR in get_current_best_signal: {e} ---")
        return None

async def manual_signal_hunt(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    """Manually hunt for a signal for a specific symbol and timeframe"""
    try:
        print(f"--- Manual signal hunt for {symbol} {timeframe} ---")
        
        # Validate symbol
        if not validate_symbol_format(symbol):
            print(f"--- Invalid symbol format: {symbol} ---")
            return None
        
        # Fetch current price
        current_price = fetch_current_price_twelve_data(symbol, key_manager)
        if not current_price:
            print(f"--- Could not fetch price for {symbol} ---")
            return None
        
        # Fetch historical data
        historical_data = fetch_historical_data_twelve_data(symbol, timeframe, key_manager)
        if not historical_data or len(historical_data) < 20:
            print(f"--- Insufficient historical data for {symbol} {timeframe} ---")
            return None
        
        # Generate signal using fusion engine
        signal_result = await generate_signal_with_fusion(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            historical_data=historical_data,
            key_manager=key_manager
        )
        
        return signal_result
        
    except Exception as e:
        print(f"--- ERROR in manual_signal_hunt: {e} ---")
        return None
