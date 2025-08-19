# filename: regime_analyzer.py

import logging
import warnings
import numpy as np
import pandas as pd
from arch import arch_model
from hurst import compute_Hc
from statsmodels.tools.sm_exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=FutureWarning, module='arch')

logger = logging.getLogger(__name__)

def get_market_regime(df: pd.DataFrame) -> str:
    """
    Hurst Exponent اور GARCH ماڈل کا استعمال کرتے ہوئے مارکیٹ کی حالت کا تعین کرتا ہے۔
    """
    if len(df) < 100:
        return "No_Trade_Zone"

    close_prices = df['close'].dropna()
    log_returns = np.log(close_prices / close_prices.shift(1)).dropna()

    if log_returns.empty:
        return "No_Trade_Zone"

    try:
        hurst_exponent, _, _ = compute_Hc(close_prices, kind='price', simplified=True)
        
        # --- ڈیٹا کو بہتر بنانے کے لیے تبدیلی ---
        # DataScaleWarning کو حل کرنے کے لیے ریٹرنز کو 100 سے ضرب دیں
        scaled_returns = log_returns * 100
        
        model = arch_model(scaled_returns, p=1, q=1) 
        results = model.fit(disp="off")
        
        forecast = results.forecast(horizon=1)
        # پیشن گوئی کو واپس اصل اسکیل پر لانے کے لیے 100 سے تقسیم کریں
        predicted_volatility = np.sqrt(forecast.variance.iloc[-1, 0]) / 100
        
        avg_volatility = log_returns.std()

        logger.info(f"🔬 تشخیصی نتائج: Hurst = {hurst_exponent:.3f}, GARCH Forecast = {predicted_volatility:.3f}, Avg Vol = {avg_volatility:.3f}")

        is_trending = hurst_exponent > 0.55
        is_mean_reverting = hurst_exponent < 0.45
        is_random = not is_trending and not is_mean_reverting

        is_volatile = predicted_volatility > (avg_volatility * 1.5)
        is_quiet = predicted_volatility < (avg_volatility * 0.75)
        is_normal_vol = not is_volatile and not is_quiet

        regime = "No_Trade_Zone"
        if is_trending and is_normal_vol:
            regime = "Calm_Trending"
        elif is_trending and is_volatile:
            regime = "Volatile_Trending"
        elif (is_mean_reverting or is_random) and is_quiet:
            regime = "Quiet_Ranging"
        elif (is_mean_reverting or is_random) and is_volatile:
            regime = "Violent_Ranging"
        
        logger.info(f"🎯 تشخیص: {regime}")
        return regime

    except Exception as e:
        logger.error(f"ریجیم تجزیہ میں خرابی: {e}", exc_info=True)
        return "No_Trade_Zone"
        
