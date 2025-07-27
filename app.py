# filename: app.py (Temporary Version for Cleanup - CORRECTED)

import asyncio
import logging
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, create_db_and_tables, ActiveSignal

# لاگنگ کی ترتیب
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logger = logging.getLogger(__name__)

# ★★★ FastAPI ایپ کی تعریف یہاں ہونی چاہیے ★★★
app = FastAPI(title="ScalpMaster AI Cleanup Utility")

# DB انحصار
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ★★★ صرف ایک بار چلانے کے لیے عارضی صفائی کا فنکشن ★★★
# یہ ایپ کی تعریف کے بعد ہے، اس لیے یہ کام کرے گا
@app.get("/api/cleanup-duplicates", response_class=JSONResponse)
async def cleanup_duplicate_signals(db: Session = Depends(get_db)):
    """
    ہر علامت کے لیے صرف سب سے نیا فعال سگنل رکھتا ہے اور باقی تمام کو حذف کر دیتا ہے۔
    یہ فنکشن صرف ایک بار چلانے کے لیے ہے۔
    """
    try:
        logger.info("ڈپلیکیٹ فعال سگنلز کی صفائی کا عمل شروع ہو رہا ہے...")
        
        # تمام فعال سگنلز کو حاصل کریں
        all_signals = db.query(ActiveSignal).order_by(desc(ActiveSignal.created_at)).all()
        
        kept_signals = {}
        deleted_count = 0

        # ہر سگنل کو چیک کریں
        for signal in all_signals:
            if signal.symbol not in kept_signals:
                # اگر اس علامت کا کوئی سگنل نہیں رکھا گیا، تو اسے رکھ لیں
                kept_signals[signal.symbol] = signal.signal_id
                logger.info(f"[{signal.symbol}] کے لیے سگنل {signal.signal_id} کو رکھا جا رہا ہے۔")
            else:
                # اگر اس علامت کا سگنل پہلے ہی رکھا جا چکا ہے، تو یہ ڈپلیکیٹ ہے
                db.delete(signal)
                deleted_count += 1
                logger.warning(f"[{signal.symbol}] کے لیے پرانا ڈپلیکیٹ سگنل {signal.signal_id} حذف کیا جا رہا ہے۔")
        
        db.commit()
        message = f"صفائی مکمل ہوئی۔ {deleted_count} ڈپلیکیٹ سگنلز حذف کر دیے گئے۔"
        logger.info(message)
        return {"status": "ok", "message": message}
        
    except Exception as e:
        logger.error(f"صفائی کے عمل میں خرابی: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.get("/")
def read_root():
    return {"message": "Cleanup utility is running. Please navigate to /api/cleanup-duplicates to perform the cleanup."}

