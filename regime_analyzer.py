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

    close_prices = df['close']

    try:
        log_returns = np.log(close_prices / close_prices.shift(1))
        log_returns = log_returns.replace([np.inf, -np.inf], np.nan).dropna()

        if len(log_returns) < 50:
            logger.warning("صفائی کے بعد GARCH کے لیے ناکافی ڈیٹا۔")
            return "No_Trade_Zone"

        hurst_exponent, _, _ = compute_Hc(close_prices, kind='price', simplified=True)
        
        scaled_returns = log_returns * 100
        model = arch_model(scaled_returns, p=1, q=1, rescale=False) 
        results = model.fit(disp="off")
        
        forecast = results.forecast(horizon=1)
        predicted_volatility = np.sqrt(forecast.variance.iloc[-1, 0]) / 100
        historical_volatility = log_returns.tail(20).std()

        if pd.isna(predicted_volatility) or pd.isna(historical_volatility) or historical_volatility == 0:
             logger.warning("اتار چڑھاؤ کا حساب نہیں لگایا جا سکا، قدریں NaN یا صفر ہیں۔")
             return "No_Trade_Zone"

        logger.info(f"🔬 تشخیصی نتائج: Hurst = {hurst_exponent:.3f}, GARCH Forecast = {predicted_volatility:.4f}, Historical Vol = {historical_volatility:.4f}")

        # --- مرحلہ 6: حالت کی تشخیص (نرم کی گئی حدوں کے ساتھ) ---
        # پہلے: is_trending = hurst_exponent > 0.55
        is_trending = hurst_exponent > 0.52  # تبدیلی: ٹرینڈ کی شرط کو تھوڑا نرم کیا
        
        # پہلے: is_mean_reverting = hurst_exponent < 0.45
        is_mean_reverting = hurst_exponent < 0.48 # تبدیلی: رینج کی شرط کو تھوڑا نرم کیا
        
        is_random = not is_trending and not is_mean_reverting

        is_volatile = predicted_volatility > (historical_volatility * 1.5)
        is_quiet = predicted_volatility < (historical_volatility * 0.75)
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
        logger.error(f"ریجیم تجزیہ میں سنگین خرابی: {e}", exc_info=True)
        return "No_Trade_Zone"
    
