import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, NamedTuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# مقامی امپورٹس
from models import ActiveSignal, CompletedTrade, CachedNews
from schemas import DailyStatsResponse

logger = logging.getLogger(__name__)

class SignalUpdateResult(NamedTuple):
    signal: ActiveSignal
    is_new: bool

def get_all_active_signals_from_db(db: Session) -> List[ActiveSignal]:
    """ڈیٹا بیس سے تمام فعال سگنلز حاصل کرتا ہے۔"""
    try:
        return db.query(ActiveSignal).all()
    except SQLAlchemyError as e:
        logger.error(f"تمام فعال سگنلز حاصل کرنے میں ڈیٹا بیس کی خرابی: {e}", exc_info=True)
        return []

def get_active_signal_by_symbol(db: Session, symbol: str) -> Optional[ActiveSignal]:
    """علامت کی بنیاد پر ایک فعال سگنل حاصل کرتا ہے۔"""
    try:
        return db.query(ActiveSignal).filter(ActiveSignal.symbol == symbol).first()
    except SQLAlchemyError as e:
        logger.error(f"علامت '{symbol}' کے لیے فعال سگنل حاصل کرنے میں خرابی: {e}", exc_info=True)
        return None

def add_or_update_active_signal(db: Session, signal_data: Dict[str, Any]) -> Optional[SignalUpdateResult]:
    """ڈیٹا بیس میں ایک فعال سگنل کو شامل یا اپ ڈیٹ کرتا ہے۔"""
    symbol = signal_data.get("symbol")
    if not symbol:
        logger.error("سگنل ڈیٹا میں 'symbol' غائب ہے۔ سگنل شامل نہیں کیا جا سکتا۔")
        return None
        
    try:
        existing_signal = get_active_signal_by_symbol(db, symbol)

        if existing_signal:
            # موجودہ سگنل کو اپ ڈیٹ کریں
            logger.info(f"موجودہ سگنل {symbol} کو اپ ڈیٹ کیا جا رہا ہے۔")
            for key, value in signal_data.items():
                setattr(existing_signal, key, value)
            existing_signal.is_new = True # ہر اپ ڈیٹ پر اسے نیا سمجھیں تاکہ گریس پیریڈ ملے
            
            db.commit()
            db.refresh(existing_signal)
            return SignalUpdateResult(signal=existing_signal, is_new=False)
        else:
            # نیا سگنل بنائیں
            logger.info(f"نیا سگنل {symbol} بنایا جا رہا ہے۔")
            signal_id = f"{symbol.replace('/', '')}_{signal_data.get('timeframe', '15min')}_{int(datetime.utcnow().timestamp())}"
            
            new_signal = ActiveSignal(
                signal_id=signal_id,
                symbol=symbol,
                timeframe=signal_data.get('timeframe'),
                signal_type=signal_data.get('signal'),
                entry_price=signal_data.get('price'),
                tp_price=signal_data.get('tp'),
                sl_price=signal_data.get('sl'),
                confidence=signal_data.get('confidence'),
                reason=signal_data.get('reason'),
                component_scores=signal_data.get('component_scores'),
                is_new=True
            )
            db.add(new_signal)
            db.commit()
            db.refresh(new_signal)
            return SignalUpdateResult(signal=new_signal, is_new=True)

    except IntegrityError as e:
        logger.error(f"ڈیٹا بیس میں سالمیت کی خلاف ورزی: {e}", exc_info=True)
        db.rollback()
        return None
    except SQLAlchemyError as e:
        logger.error(f"فعال سگنل شامل/اپ ڈیٹ کرنے میں ڈیٹا بیس کی خرابی: {e}", exc_info=True)
        db.rollback()
        return None

# ★★★ یہ ہے ہمارا حتمی اور فول پروف حل ★★★
def close_and_archive_signal(db: Session, signal_id: str, outcome: str, close_price: float, reason_for_closure: str) -> bool:
    """
    ایک سگنل کو ایک محفوظ، اٹامک ٹرانزیکشن میں بند اور آرکائیو کرتا ہے۔
    """
    signal_to_archive = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
    
    if not signal_to_archive:
        logger.warning(f"بند کرنے کے لیے فعال سگنل {signal_id} نہیں ملا۔ شاید یہ پہلے ہی بند ہو چکا ہے۔")
        return True # اگر سگنل موجود نہیں، تو ہم اسے کامیاب مانیں گے

    logger.info(f"سگنل {signal_id} کو بند اور آرکائیو کیا جا رہا ہے۔ نتیجہ: {outcome}")
    
    try:
        # مرحلہ 1: ایک نیا مکمل شدہ ٹریڈ آبجیکٹ بنائیں
        completed_trade = CompletedTrade(
            signal_id=signal_to_archive.signal_id,
            symbol=signal_to_archive.symbol,
            timeframe=signal_to_archive.timeframe,
            signal_type=signal_to_archive.signal_type,
            entry_price=signal_to_archive.entry_price,
            tp_price=signal_to_archive.tp_price,
            sl_price=signal_to_archive.sl_price,
            close_price=close_price,
            reason_for_closure=reason_for_closure,
            outcome=outcome,
            confidence=signal_to_archive.confidence,
            reason=signal_to_archive.reason,
            created_at=signal_to_archive.created_at,
            closed_at=datetime.utcnow()
        )
        
        # مرحلہ 2: اسے سیشن میں شامل کریں
        db.add(completed_trade)
        
        # مرحلہ 3: پرانے فعال سگنل کو ڈیلیٹ کریں
        db.delete(signal_to_archive)
        
        # مرحلہ 4: تمام تبدیلیوں کو ایک ساتھ محفوظ کریں (اٹامک کمٹ)
        db.commit()
        
        logger.info(f"سگنل {signal_id} کامیابی سے ہسٹری میں منتقل ہو گیا۔")
        return True

    except SQLAlchemyError as e:
        logger.error(f"سگنل {signal_id} کو آرکائیو کرنے میں ڈیٹا بیس کی سنگین خرابی: {e}", exc_info=True)
        # اگر کوئی بھی خرابی ہو تو تمام تبدیلیوں کو واپس لے لیں
        db.rollback()
        return False

def get_completed_trades(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """مکمل شدہ ٹریڈز کی تاریخ حاصل کرتا ہے۔"""
    try:
        trades = db.query(CompletedTrade).order_by(desc(CompletedTrade.closed_at)).limit(limit).all()
        return [trade.as_dict() for trade in trades]
    except SQLAlchemyError as e:
        logger.error(f"مکمل شدہ ٹریڈز حاصل کرنے میں خرابی: {e}", exc_info=True)
        return []

def get_daily_stats(db: Session) -> DailyStatsResponse:
    """روزانہ کے اعداد و شمار حاصل کرتا ہے۔"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        tp_hits = db.query(func.count(CompletedTrade.id)).filter(
            CompletedTrade.outcome == 'tp_hit',
            CompletedTrade.closed_at >= today_start
        ).scalar() or 0
        
        sl_hits = db.query(func.count(CompletedTrade.id)).filter(
            CompletedTrade.outcome == 'sl_hit',
            CompletedTrade.closed_at >= today_start
        ).scalar() or 0
        
        live_signals = db.query(func.count(ActiveSignal.id)).scalar() or 0
        
        total_today = tp_hits + sl_hits
        win_rate = (tp_hits / total_today * 100) if total_today > 0 else 0
        
        return DailyStatsResponse(
            tp_hits_today=tp_hits,
            sl_hits_today=sl_hits,
            live_signals=live_signals,
            win_rate_today=round(win_rate, 2)
        )
    except SQLAlchemyError as e:
        logger.error(f"روزانہ کے اعداد و شمار حاصل کرنے میں خرابی: {e}", exc_info=True)
        return DailyStatsResponse(tp_hits_today=0, sl_hits_today=0, live_signals=0, win_rate_today=0)

def update_news_cache_in_db(db: Session, news_data: Dict[str, Any]) -> None:
    """نیوز کیش کو ڈیٹا بیس میں اپ ڈیٹ کرتا ہے۔"""
    try:
        db.query(CachedNews).delete()
        new_news = CachedNews(content=news_data, updated_at=datetime.utcnow())
        db.add(new_news)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"نیوز کیش اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()

def get_cached_news(db: Session) -> Optional[Dict[str, Any]]:
    """کیش شدہ خبریں ڈیٹا بیس سے حاصل کرتا ہے۔"""
    try:
        news = db.query(CachedNews).order_by(desc(CachedNews.updated_at)).first()
        return news.content if news else None
    except SQLAlchemyError as e:
        logger.error(f"کیش شدہ خبریں بازیافت کرنے میں خرابی: {e}", exc_info=True)
        return None

def get_recent_sl_hits(db: Session, minutes_ago: int) -> List[CompletedTrade]:
    """حالیہ SL ہٹس حاصل کرتا ہے۔"""
    try:
        time_filter = datetime.utcnow() - timedelta(minutes=minutes_ago)
        return db.query(CompletedTrade).filter(
            CompletedTrade.outcome == 'sl_hit',
            CompletedTrade.closed_at >= time_filter
        ).all()
    except SQLAlchemyError as e:
        logger.error(f"حالیہ SL ہٹس حاصل کرنے میں خرابی: {e}", exc_info=True)
        return []
                        
