# filename: app.py (Temporary Version for Cleanup)

# ... (تمام امپورٹس ویسے ہی رہیں گے) ...
from sqlalchemy import desc

# ... (باقی تمام کوڈ ویسا ہی رہے گا) ...

# ★★★ صرف ایک بار چلانے کے لیے عارضی صفائی کا فنکشن ★★★
@app.get("/api/cleanup-duplicates", response_class=JSONResponse)
async def cleanup_duplicate_signals(db: Session = Depends(get_db)):
    """
    ہر علامت کے لیے صرف سب سے نیا فعال سگنل رکھتا ہے اور باقی تمام کو حذف کر دیتا ہے۔
    یہ فنکشن صرف ایک بار چلانے کے لیے ہے۔
    """
    try:
        logger.info("ڈپلیکیٹ فعال سگنلز کی صفائی کا عمل شروع ہو رہا ہے...")
        all_signals = db.query(ActiveSignal).order_by(desc(ActiveSignal.created_at)).all()
        
        kept_signals = {}
        deleted_count = 0

        for signal in all_signals:
            if signal.symbol not in kept_signals:
                kept_signals[signal.symbol] = signal.signal_id
                logger.info(f"[{signal.symbol}] کے لیے سگنل {signal.signal_id} کو رکھا جا رہا ہے۔")
            else:
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


# ... (باقی تمام API روٹس اور app.mount(...) ویسے ہی رہیں گے) ...
