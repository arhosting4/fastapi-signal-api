# filename: models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# =============================================================================
# 🔑 ActiveSignal Model
# → Jo trades abhi open hain, unka record yahan store hota hai
# =============================================================================
class ActiveSignal(Base):
    __tablename__ = "active_signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)              # e.g., BTCUSDT
    entry_price = Column(Float)                      # Entry value
    signal_type = Column(String)                     # Buy / Sell
    strategy = Column(String)                        # AI bot / strategy name
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# =============================================================================
# 📈 CompletedTrade Model
# → Close ho chuki trades ka data store hota hai
# =============================================================================
class CompletedTrade(Base):
    __tablename__ = "completed_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float)
    status = Column(String)                         # e.g., TP Hit / SL Hit / Manual Close
    pnl = Column(Float)                             # Profit or Loss
    timestamp = Column(DateTime, default=datetime.utcnow)

# =============================================================================
# 💬 FeedbackEntry Model
# → User feedback ya AI recommendation ka record
# =============================================================================
class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer)                    # Link to signal ID
    feedback = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# =============================================================================
# 📰 CachedNews Model
# → Latest financial news cache karne ke liye
# =============================================================================
class CachedNews(Base):
    __tablename__ = "cached_news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    published_at = Column(DateTime, default=datetime.utcnow)
