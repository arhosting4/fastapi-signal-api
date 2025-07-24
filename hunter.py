import logging
import asyncio
from datetime import datetime
import uuid

# براہ راست امپورٹس
from database_config import SessionLocal
import utils
import strategybot
import patternai
import riskguardian
import supply_demand
import sentinel
import fusion_engine
import signal_tracker
import messenger

async def hunt_for_signals():
    """
    Main function to orchestrate the signal generation process.
    It fetches market data for various pairs and timeframes,
    and then passes this data to different AI modules for analysis.
    """
    logging.info("Starting signal hunting cycle...")
    pairs = utils.get_available_pairs()
    timeframes = ["15min", "1h", "4h"] # Scalping focused timeframes
    
    for pair in pairs:
        for timeframe in timeframes:
            logging.info(f"Processing {pair} on {timeframe}...")
            
            ohlc_data = await utils.fetch_twelve_data_ohlc(pair, timeframe)
            if not ohlc_data:
                logging.warning(f"Could not fetch OHLC data for {pair} on {timeframe}. Skipping.")
                continue

            # --- AI Module Analysis ---
            core_signal = strategybot.generate_core_signal(ohlc_data)
            patterns = patternai.detect_patterns(ohlc_data)
            risk_assessment = riskguardian.check_risk(ohlc_data)
            market_structure = supply_demand.get_market_structure_analysis(ohlc_data)
            news_analysis = await sentinel.get_news_analysis_for_symbol(pair)

            # --- Signal Fusion ---
            final_signal = fusion_engine.fuse_signals(
                core_signal=core_signal,
                patterns=patterns,
                risk=risk_assessment,
                structure=market_structure,
                news=news_analysis
            )

            # --- Process Valid Signal ---
            if final_signal and final_signal.get("signal") not in ["NEUTRAL", "WAIT"]:
                confidence = final_signal.get("confidence", 0)
                if confidence >= 60: # Confidence threshold
                    signal_id = str(uuid.uuid4())
                    
                    # Calculate TP/SL
                    tp_sl = strategybot.calculate_tp_sl(
                        entry_price=ohlc_data['close'].iloc[-1],
                        signal_type=final_signal["signal"],
                        atr=ohlc_data['ATR'].iloc[-1],
                        atr_multiplier=riskguardian.get_dynamic_atr_multiplier(risk_assessment['status'])
                    )

                    active_signal_data = {
                        "signal_id": signal_id,
                        "symbol": pair,
                        "timeframe": timeframe,
                        "signal_type": final_signal["signal"],
                        "entry_price": ohlc_data['close'].iloc[-1],
                        "confidence": confidence,
                        "reason": final_signal.get("reason", "N/A"),
                        "tp_price": tp_sl['tp'],
                        "sl_price": tp_sl['sl'],
                        "created_at": datetime.utcnow()
                    }
                    
                    # Add to tracker and send alert
                    signal_tracker.add_active_signal(active_signal_data)
                    await messenger.send_telegram_alert(active_signal_data)
                    logging.info(f"SUCCESS: New signal generated and sent for {pair} on {timeframe}.")
                else:
                    logging.info(f"Signal for {pair} on {timeframe} did not meet confidence threshold ({confidence}%).")
            else:
                logging.info(f"No actionable signal found for {pair} on {timeframe}.")
            
            await asyncio.sleep(2) # Rate limiting between API calls

    logging.info("Signal hunting cycle finished.")

