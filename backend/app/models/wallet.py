from datetime import datetime
from sqlalchemy import Column, String, DateTime, UUID, Boolean, JSON
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class TrackedWallet(Base):
    __tablename__ = "tracked_wallets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(String(255), unique=True, nullable=False, index=True)
    currency = Column(String(50), nullable=False, index=True)  # BTC, ETH, XMR, etc.
    label = Column(String(255), nullable=True)
    
    # Metadata
    tags = Column(JSON, nullable=True)  # ["ransomware", "mixer", "scam"]
    risk_level = Column(String(50), default="low")  # low, medium, high, critical
    
    # Discovery info
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, nullable=True)
    source_job_id = Column(UUID(as_uuid=True), nullable=True)
    source_url = Column(String(512), nullable=True)
    
    # Monitoring status
    is_watchlist = Column(Boolean, default=False, index=True)
    last_balance_check = Column(DateTime, nullable=True)
    cached_balance = Column(String(100), nullable=True)
    cached_usd_value = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
