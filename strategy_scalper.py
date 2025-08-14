import logging
from typing import Any, Dict, Optional

import pandas as pd
import numpy as np # <--- numpy کو شامل کریں

from config import tech_settings
from level_analyzer import find_realistic_tp_sl

logger = logging.getLogger(__name__)

# --- انڈیکیٹرز کا حساب لگانے والے فنکشنز (پہلے سے موجود) ---

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_supertrend(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.DataFrame:
    high, low, close = df['high'], df['low'], df['close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    df['upperband'] = (high + low) / 2 + (multiplier * atr)
    df['lowerband'] = (high + low) / 2 - (multiplier * atr)
    df['in_uptrend'] = True
    for i in range(1, len(df)):
        if close.iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = True
        elif close.iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = False
        else:
            df.loc[df.index[i], 'in_uptrend'] = df['in_uptrend'].iloc[i-1]
        if df['in_uptrend'].iloc[i] and df['lowerband'].iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[df.index[i], 'lowerband'] = df['lowerband'].iloc[i-1]
        if not df['in_uptrend'].iloc[i] and df['upperband'].iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[df.index[i], 'upperband'] = df['upperband'].iloc[i-1]
    return df

# --- ماہرین کے ووٹنگ فنکشنز ---

def get_aggressive_scalper_vote(df: pd.DataFrame) -> (str, int):
    """
    تیز رفتار انڈیکیٹرز کی بنیاد پر ووٹ دیتا ہے۔
    Returns: ('buy', 'sell', or 'neutral'), score
    """
    close = df['close']
    ema_fast = close.ewm(span=tech_settings.EMA_SHORT_PERIOD, adjust=False).mean()
    ema_slow = close.ewm(span=tech_settings.EMA_LONG_PERIOD, adjust=False).mean()
    df_supertrend = calculate_supertrend(df.copy(), tech_settings.SUPERTREND_ATR, tech_settings.SUPERTREND_FACTOR)
    
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_slow = ema_slow.iloc[-1]
    in_uptrend = df_supertrend['in_uptrend'].iloc[-1]

    score = 0
    if last_ema_fast > last_ema_slow: score += 50
    if last_ema_fast < last_ema_slow: score -= 50
    if in_uptrend: score += 50
    if not in_uptrend: score -= 50

    if score >= 100: return "buy", score
    if score <= -100: return "sell", score
    return "neutral", score

def get_cautious_trader_vote(df: pd.DataFrame) -> (str, int):
    """
    لیکویڈیٹی اور والیوم پروفائل کی بنیاد پر ووٹ دیتا ہے۔
    (نوٹ: ابھی کے لیے، ہم RSI کو ایک پلیس ہولڈر کے طور پر استعمال کریں گے۔)
    Returns: ('buy', 'sell', or 'neutral'), score
    """
    # ★★★ پلیس ہولڈر: مستقبل میں یہاں والیوم پروفائل کی منطق آئے گی۔ ★★★
    # ابھی کے لیے، ہم صرف RSI کی انتہائی سطحوں کو دیکھیں گے۔
    rsi = calculate_rsi(df['close'], tech_settings.RSI_PERIOD)
    last_rsi = rsi.iloc[-1]

    if last_rsi < 30: return "buy", 100  # مضبوط ریورسل کا اشارہ
    if last_rsi > 70: return "sell", 100 # مضبوط ریورسل کا اشارہ
    
    # اگر RSI انتہائی سطح پر نہیں ہے، تو یہ محتاط ٹریڈر خاموش رہے گا۔
    return "neutral", 0

# --- مرکزی کمیٹی کا فنکشن ---

def run_trading_committee(df: pd.DataFrame, market_regime: Dict, symbol_personality: Dict) -> Dict[str, Any]:
    """
    تینوں ماہرین کو چلاتا ہے، ووٹ اکٹھا کرتا ہے، اور حتمی فیصلہ کرتا ہے۔
    """
    # مرحلہ 1: رسک مینیجر سے منظوری لینا
    risk_manager_verdict = market_regime.get("regime")
    if risk_manager_verdict == "Kill Zone":
        return {"status": "no-signal", "reason": "Risk Manager Veto: Market is in Kill Zone."}

    # مرحلہ 2: دونوں ٹریڈرز سے ووٹ حاصل کرنا
    scalper_vote, scalper_score = get_aggressive_scalper_vote(df)
    cautious_vote, cautious_score = get_cautious_trader_vote(df)

    logger.info(f"کمیٹی ووٹنگ [{symbol_personality.get('symbol', '')}]: جارحانہ = {scalper_vote} ({scalper_score}), محتاط = {cautious_vote} ({cautious_score})")

    # مرحلہ 3: فیصلہ سازی کا میٹرکس
    final_signal = "neutral"
    signal_grade = "F"
    
    # کیس 1: دونوں متفق ہیں (سب سے مضبوط سگنل)
    if scalper_vote == cautious_vote and scalper_vote != "neutral":
        final_signal = scalper_vote
        signal_grade = "A+"
    # کیس 2: جارحانہ اسکیلپر کو موقع نظر آیا اور محتاط ٹریڈر خاموش ہے
    elif scalper_vote != "neutral" and cautious_vote == "neutral":
        final_signal = scalper_vote
        signal_grade = "A"
    # کیس 3: محتاط ٹریڈر کو موقع نظر آیا اور جارحانہ اسکیلپر خاموش ہے (کم عام، لیکن ممکن)
    elif cautious_vote != "neutral" and scalper_vote == "neutral":
        final_signal = cautious_vote
        signal_grade = "B" # یہ زیادہ محتاط سگنل ہوگا

    # اگر کوئی حتمی سگنل نہیں ہے، تو باہر نکل جائیں
    if final_signal == "neutral":
        return {"status": "no-signal", "reason": "No consensus in the committee."}

    # مرحلہ 4: سگنل کی تفصیلات تیار کرنا
    tp_sl_data = find_realistic_tp_sl(df, final_signal, symbol_personality)
    if not tp_sl_data:
        return {"status": "no-signal", "reason": "Could not calculate realistic TP/SL."}
    
    tp, sl = tp_sl_data
    
    # حتمی اسکور اور دیگر تفصیلات
    total_score = (scalper_score + cautious_score)
    strategy_used = "Trend" if abs(scalper_score) > 0 else "Reversal"
    
    return {
        "status": "ok",
        "signal": final_signal,
        "score": total_score,
        "price": df['close'].iloc[-1],
        "tp": tp,
        "sl": sl,
        "strategy_type": strategy_used,
        "signal_grade": signal_grade, # ★★★ نیا فیلڈ
        "reason": f"{signal_grade}-Grade signal based on {strategy_used} strategy. Scalper: {scalper_vote}, Cautious: {cautious_vote}."
    }

# --- پرانے فنکشن کو نئے سے تبدیل کرنا ---
# generate_adaptive_analysis کو اب run_trading_committee کہا جائے گا
# لہذا، جہاں بھی generate_adaptive_analysis کال ہو رہا تھا، اب run_trading_committee کال ہوگا۔
# ہم نے اس فائل کا نام generate_adaptive_analysis سے بدل کر run_trading_committee کر دیا ہے۔
# اس لیے اب ہم پرانے فنکشن کو حذف کر سکتے ہیں۔
