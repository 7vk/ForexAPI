from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base
from datetime import datetime
# Create Base for declarative models
Base = declarative_base()
# Ensure this file can be imported as a module
__all__ = ['ExchangeRate', 'Base']
class ExchangeRate(Base):
    """
    SQLAlchemy ORM model for exchange rates
    
    Attributes:
        id (int): Primary key
        currency_pair (str): Currency pair identifier (e.g., 'GBPINR=X')
        date (str): Date of the exchange rate
        open_rate (float): Opening rate for the day
        high_rate (float): Highest rate for the day
        low_rate (float): Lowest rate for the day
        close_rate (float): Closing rate for the day
        adj_close (float): Adjusted closing rate
        volume (int): Trading volume
        created_at (datetime): Record creation timestamp
    """
    __tablename__ = 'exchange_rates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    currency_pair = Column(String, nullable=False)
    date = Column(String, nullable=False)
    open_rate = Column(Float)
    high_rate = Column(Float)
    low_rate = Column(Float)
    close_rate = Column(Float)
    adj_close = Column(Float)
    volume = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Add unique constraint for currency pair and date combination
    __table_args__ = (
        UniqueConstraint('currency_pair', 'date', name='unique_currency_date'),
    )
    def __repr__(self):
        """String representation of the exchange rate record"""
        return (f"<ExchangeRate("
                f"date={self.date}, "
                f"currency_pair={self.currency_pair}, "
                f"close_rate={self.close_rate})>")