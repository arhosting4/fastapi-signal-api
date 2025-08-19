# filename: regime_analyzer.py

import logging
import pandas as pd
from arch import arch_model
from hurst import compute_Hc

logger = logging.getLogger(__name__)

# --- مستقل اقدار اور حدیں (Thresholds) ---
# ان اقدار کو ہم بعد میں ٹیسٹنگ کی بنیاد پر ٹھیک کر سکتے ہیں
HURST_TREND_THRESHOLD = 0.55  # 0.5 سے جتنا اوپر، اتنا مضبوط ٹرینڈ
HURST_RANGE_THRESHOLD = 0.45  # 0.5 سے جتنا نیچے، اتنا مضبوط رینج
GARCH_LOOKBACK_PERIOD = 100   # GARCH ماڈل کے لیے کتنی کینڈلز استعمال کرنی ہیں

def calculate_hurst_exponent(series: pd.Series) -> float:
    """
    دی گئی ٹائم سیریز کے لیے Hurst Exponent کا حساب لگاتا ہے۔
    یہ ہمیں بتاتا ہے کہ آیا سیریز ٹرینڈ کر رہی ہے، رینج کر رہی ہے، یا بے ترتیب ہے۔
    """
    if len(series) < 100:
        logger.warning("Hurst Exponent کے لیے ناکافی ڈیٹا، ڈیفالٹ 0.5۔")
        return 0.5
    
    try:
        # Hc, c, data = compute_Hc(series, kind='price', simplified=True)
        H, _, _ = compute_Hc(series, kind='price', simplified=True)
        return H
    except Exception as e:
        logger.error(f"Hurst Exponent کا حساب لگانے میں خرابی: {e}", exc_info=True)
        return 0.5 # خرابی کی صورت میں بے ترتیب چال فرض کریں

def calculate_garch_volatility_forecast(series: pd.Series) -> float:
    """
    GARCH(1,1) ماڈل کا استعمال کرتے ہوئے اگلے دور کے لیے اتار چڑھاؤ کی پیش گوئی کرتا ہے۔
    """
    if len(series) < GARCH_LOOKBACK_PERIOD:
        logger.warning("GARCH ماڈل کے لیے ناکافی ڈیٹا، ڈیفالٹ 0۔")
        return 0.0
        
    try:
        # قیمت کی تبدیلی (returns) کا حساب لگائیں کیونکہ GARCH ماڈل اس پر بہتر کام کرتا ہے
        returns = 100 * series.pct_change().dropna()
        
        # GARCH(1,1) ماڈل کی وضاحت کریں
        model = arch_model(returns, p=1, q=1, vol='Garch')
        
        # ماڈل کو فٹ کریں، ڈسپلے کو آف رکھیں
        res = model.fit(disp='off')
        
        # اگلے ایک دور کے لیے پیش گوئی کریں
        forecast = res.forecast(horizon=1)
        
        # متوقع ویریئنس (variance) حاصل کریں اور اسے سٹینڈرڈ ڈیوی ایشن (volatility) میں تبدیل کریں
        forecasted_vol = forecast.variance.iloc[-1, 0] ** 0.5
        
        return forecasted_vol
    except Exception as e:
        # اکثر ڈیٹا کم ہونے یا مستحکم نہ ہونے کی وجہ سے خرابی آتی ہے
        logger.warning(f"GARCH ماڈل فٹ کرنے میں خرابی: {e}")
        return 0.0 # خرابی کی صورت میں کوئی اتار چڑھاؤ فرض نہ کریں

def get_market_regime(df: pd.DataFrame) -> str:
    """
    Hurst Exponent اور GARCH کی پیش گوئی کی بنیاد پر مارکیٹ کی موجودہ حالت کا تعین کرتا ہے۔
    یہ ہمارے "ایپیکس پریڈیٹر" انجن کا بنیادی تشخیصی ٹول ہے۔
    """
    logger.info("📈 مارکیٹ کی حالت کی تشخیص شروع کی جا رہی ہے...")
    
    close_prices = df['close']
    
    # مرحلہ 1: مارکیٹ کی چال کی قسم کا تعین کریں (ٹرینڈنگ یا رینجنگ)
    hurst = calculate_hurst_exponent(close_prices)
    is_trending = hurst > HURST_TREND_THRESHOLD
    is_ranging = hurst < HURST_RANGE_THRESHOLD
    
    # مرحلہ 2: متوقع اتار چڑھاؤ کی سطح کا تعین کریں
    garch_forecast = calculate_garch_volatility_forecast(close_prices)
    
    # اتار چڑھاؤ کی اوسط سطح کا حساب لگائیں تاکہ موازنہ کیا جا سکے
    historical_avg_vol = (100 * close_prices.pct_change().dropna()).std()
    is_high_volatility = garch_forecast > historical_avg_vol * 1.2 # اگر متوقع اتار چڑھاؤ اوسط سے 20% زیادہ ہو
    is_low_volatility = garch_forecast < historical_avg_vol * 0.8  # اگر متوقع اتار چڑھاؤ اوسط سے 20% کم ہو

    logger.info(f"🔬 تشخیصی نتائج: Hurst = {hurst:.3f}, GARCH Forecast = {garch_forecast:.3f}, Avg Vol = {historical_avg_vol:.3f}")

    # مرحلہ 3: نتائج کو ملا کر حتمی حالت کا تعین کریں
    if is_trending:
        if is_high_volatility:
            logger.info("🎯 تشخیص: دھماکہ خیز ٹرینڈ (Volatile Trending)")
            return "Volatile_Trending"
        else: # کم یا معمول کا اتار چڑھاؤ
            logger.info("🎯 تشخیص: پرسکون ٹرینڈ (Calm Trending)")
            return "Calm_Trending"
            
    elif is_ranging:
        if is_low_volatility:
            logger.info("🎯 تشخیص: تنگ رینج (Quiet Ranging)")
            return "Quiet_Ranging"
        else: # زیادہ یا معمول کا اتار چڑھاؤ
            logger.info("🎯 تشخیص: وسیع رینج (Violent Ranging)")
            return "Violent_Ranging"
            
    else: # اگر Hurst Exponent درمیان میں ہے (بے ترتیب چال)
        logger.warning("⚠️ تشخیص: ناقابلِ اعتبار حالت (No Trade Zone)")
        return "No_Trade_Zone"

