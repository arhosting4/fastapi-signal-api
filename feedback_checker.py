import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.database.models import SessionLocal, LiveSignal, FeedbackEntry

logger = logging.getLogger(__name__)

def check_active_signals_job():
    """
    Scheduled job to check feedback on active signals.
    Deactivates signals if they've expired or received negative feedback (optional logic).
    """
    logger.info("🔎 Checking active signals and feedback...")

    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()

        # Check signals that have been active more than 3 hours (as an example)
        expiration_time = now - timedelta(hours=3)
        signals_to_expire = db.query(LiveSignal).filter(
            LiveSignal.active == True,
            LiveSignal.created_at < expiration_time
        ).all()

        for signal in signals_to_expire:
            signal.active = False
            logger.info(f"❌ Signal expired: {signal.symbol} ({signal.timeframe})")

        db.commit()

        # Optional: analyze feedback entries
        recent_feedbacks = db.query(FeedbackEntry).filter(
            FeedbackEntry.timestamp >= now - timedelta(hours=6)
        ).all()

        logger.info(f"📝 Recent feedbacks found: {len(recent_feedbacks)}")

    except Exception as e:
        logger.error(f"❌ Error in feedback check job: {e}")
        db.rollback()
    finally:
        db.close()
