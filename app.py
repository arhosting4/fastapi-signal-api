# filename: app.py (Diagnostic & Repair Version)

import asyncio
import logging
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables, ActiveSignal

# لاگنگ کی ترتیب
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI ایپ کی تعریف
app = FastAPI(title="ScalpMaster AI Diagnostic Utility")

# DB انحصار
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ★★★ نیا تشخیصی فنکشن ★★★
@app.get("/api/diagnose", response_class=JSONResponse)
async def diagnose_active_signals(db: Session = Depends(get_db)):
    """ڈیٹا بیس میں موجود فعال سگنلز کی تعداد اور تفصیلات بتاتا ہے۔"""
    try:
        logger.info("تشخیصی عمل شروع ہو رہا ہے...")
        signal_count = db.query(func.count(ActiveSignal.id)).scalar()
        signals_by_symbol = db.query(ActiveSignal.symbol, func.count(ActiveSignal.id)).group_by(ActiveSignal.symbol).all()
        
        report = {
            "total_active_signals": signal_count,
            "signals_per_symbol": {symbol: count for symbol, count in signals_by_symbol}
        }
        logger.info(f"تشخیصی رپورٹ: {report}")
        return {"status": "ok", "diagnostic_report": report}
        
    except Exception as e:
        logger.error(f"تشخیصی عمل میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# ★★★ زیادہ مضبوط اور فول پروف صفائی کا فنکشن ★★★
@app.get("/api/cleanup-duplicates", response_class=JSONResponse)
async def cleanup_duplicate_signals(db: Session = Depends(get_db)):
    """
    ہر علامت کے لیے صرف سب سے نیا فعال سگنل رکھتا ہے اور باقی تمام کو حذف کر دیتا ہے۔
    """
    try:
        logger.info("فول پروف صفائی کا عمل شروع ہو رہا ہے...")
        all_signals = db.query(ActiveSignal).order_by(desc(ActiveSignal.created_at)).all()
        
        kept_signals = {}
        deleted_count = 0

        for signal in all_signals:
            if signal.symbol not in kept_signals:
                kept_signals[signal.symbol] = signal.signal_id
                logger.info(f"رکھا جا رہا ہے: [{signal.symbol}] - {signal.signal_id}")
            else:
                db.delete(signal)
                deleted_count += 1
                logger.warning(f"حذف کیا جا رہا ہے: [{signal.symbol}] - {signal.signal_id}")
        
        if deleted_count > 0:
            logger.info(f"{deleted_count} سگنلز کو حذف کرنے کے لیے نشان زد کیا گیا ہے۔ اب کمیٹ کیا جا رہا ہے...")
            db.flush()  # تبدیلیوں کو فوری طور پر بھیجیں
            db.commit() # تبدیلیوں کو مستقل طور پر محفوظ کریں
            message = f"صفائی مکمل ہوئی۔ {deleted_count} ڈپلیکیٹ سگنلز کامیابی سے حذف کر دیے گئے۔"
        else:
            message = "صفائی کی ضرورت نہیں، کوئی ڈپلیکیٹ سگنل نہیں ملا۔"

        logger.info(message)
        return {"status": "ok", "message": message}
        
    except Exception as e:
        logger.error(f"صفائی کے عمل میں خرابی: {e}", exc_info=True)
        db.rollback() # اگر کوئی خرابی ہو تو واپس پلٹائیں
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.get("/")
def read_root():
    return {"message": "Diagnostic & Repair utility is running."}

