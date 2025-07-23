from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, func
from ...database_config import Base # Import Base from the central config file

class ActiveSignal(Base):
    """Represents an active trading signal being monitored."""
    __tablename__ = "active_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    tp_price = Column(Float, nullable=False)
    sl_price = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class CompletedTrade(Base):
    """Represents a trade that has been completed (TP/SL hit or expired)."""
    __tablename__ = "completed_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    tp_price = Column(Float, nullable=False)
    sl_price = Column(Float, nullable=False)
    outcome = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=False)

class FeedbackEntry(Base):
    """Stores feedback on signal performance."""
    __tablename__ = "feedback_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    feedback = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class CachedNews(Base):
    """Stores cached news from external sources."""
    __tablename__ = "cached_news"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(JSON, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    
