# filename: regime_analyzer.py

import logging
import warnings
import numpy as np
import pandas as pd
from arch import arch_model
from hurst import compute_Hc
from statsmodels.tools.sm_exceptions import ConvergenceWarning

# غیر ضروری انتباہات کو خاموش کریں
warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=FutureWarning, module='arch')
# DataScaleWarning کو بھی خاموش کریں کیونکہ ہم اسے خود ہینڈل کر رہے ہیں
warnings.filterwarnings("ignore", category=UserWarning, module='arch')


logger = logging.getLogger(__name__)

def get_market_regime(df: pd.DataFrame) -> str:
    """
    Hurst Exponent اور GARCH ماڈل کا استعمال کرتے ہوئے مارکیٹ کی حالت کا تعین کرتا ہے۔
    """
    if len(df) < 100:
        return "No_Trade_Zone"

    close_prices = df['close']

    # --- حساب کتاب کا فول پروف طریقہ ---
    try:
        # مرحلہ 1: لاگ ریٹرنز کا حساب لگائیں
        log_returns = np.log(close_prices / close_prices.shift(1))
        
        # مرحلہ 2: حتمی صفائی - NaN اور لامتناہی قدروں کو ہٹائیں
        # یہ سب سے اہم قدم ہے جو ہم پہلے چھوڑ رہے تھے
        log_returns = log_returns.replace([np.inf, -np.inf], np.nan).dropna()

        # اگر صفائی کے بعد ڈیٹا ناکافی ہے، تو باہر نکل جائیں
        if len(log_returns) < 50:
            logger.warning("صفائی کے بعد GARCH کے لیے ناکافی ڈیٹا۔")
            return "No_Trade_Zone"

        # مرحلہ 3: Hurst Exponent کا حساب لگائیں
        hurst_exponent, _, _ = compute_Hc(close_prices, kind='price', simplified=True)
        
        # مرحلہ 4: GARCH ماڈل کے لیے ڈیٹا کو اسکیل کریں
        scaled_returns = log_returns * 100
        
        # مرحلہ 5: GARCH ماڈل کو فٹ کریں
        model = arch_model(scaled_returns, p=1, q=1) 
        results = model.fit(disp="off")
        
        # مرحلہ 6: پیشن گوئی کریں اور اسے واپس اصل اسکیل پر لائیں
        forecast = results.forecast(horizon=1)
        predicted_volatility = np.sqrt(forecast.variance.iloc[-1, 0]) / 100
        
        # مرحلہ 7: اوسط اتار چڑھاؤ کا حساب اصل، صاف شدہ ریٹرنز پر کریں
        avg_volatility = log_returns.std()

        # یقینی بنائیں کہ قدریں صفر نہ ہوں
        if pd.isna(predicted_volatility) or pd.isna(avg_volatility) or avg_volatility == 0:
             logger.warning("اتار چڑھاؤ کا حساب نہیں لگایا جا سکا، قدریں NaN یا صفر ہیں۔")
             return "No_Trade_Zone"

        logger.info(f"🔬 تشخیصی نتائج: Hurst = {hurst_exponent:.3f}, GARCH Forecast = {predicted_volatility:.4f}, Avg Vol = {avg_volatility:.4f}")

        # --- حالت کی تشخیص ---
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
        logger.error(f"ریجیم تجزیہ میں سنگین خرابی: {e}", exc_info=True)
        return "No_Trade_Zone"
        
