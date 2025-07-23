from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, UniqueConstraint, func
from ...database_config import Base # Import Base from the central config file

class CompletedTrade(Base):
    __tablename__ = "completed_trades"
    # ... (all columns remain the same) ...
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    signal_type = Column(String, nullable=False) # 'buy' or 'sell'
    entry_price = Column(Float, nullable=False)
    tp_price = Column(Float, nullable=False)
    sl_price = Column(Float, nullable=False)
    outcome = Column(String, nullable=False) # e.g., 'tp_hit', 'sl_hit', 'expired'
    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=False)


class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"
    # ... (all columns remain the same) ...
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    feedback = Column(String, nullable=False) # 'correct' or 'incorrect'
    created_at = Column(DateTime, server_default=func.now())


class CachedNews(Base):
    __tablename__ = "cached_news"
    # ... (all columns remain the same) ...
    id = Column(Integer, primary_key=True, index=True)
    content = Column(JSON, nullable=False)
    updated_at = Column(DateTime, nullable=False)

# The function to create tables will now be called from the main app.py
# using the engine from database_config.
# ... (other models) ...

class ActiveSignal(Base):
    """
    Represents an active trading signal that is currently being monitored.
    This table provides persistence for signals across application restarts.
    """
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
    
