"""
MTF Watchlist model for TA-DSS.

Stores the list of trading pairs scanned by the MTF opportunity scanner.
Pairs are persisted in SQLite so the watchlist survives restarts.

Usage:
    from src.models.mtf_watchlist_model import get_watchlist, create_mtf_watchlist_table
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

DEFAULT_WATCHLIST = ["BTC/USDT", "ETH/USDT", "XAU/USD", "XAG/USD"]


class MTFWatchlistItem(Base):
    """
    A single pair in the MTF scanner watchlist.

    Table: mtf_watchlist
    """

    __tablename__ = "mtf_watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String, unique=True, nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(String, nullable=True)

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "notes": self.notes,
        }


def get_watchlist(db: Session) -> list[str]:
    """
    Return the current watchlist pair symbols.

    Seeds DEFAULT_WATCHLIST into the DB on first call (empty table).

    Args:
        db: SQLAlchemy session.

    Returns:
        Ordered list of pair symbols.
    """
    items = db.query(MTFWatchlistItem).order_by(MTFWatchlistItem.added_at).all()
    if not items:
        for pair in DEFAULT_WATCHLIST:
            db.add(MTFWatchlistItem(pair=pair, added_at=datetime.utcnow()))
        db.commit()
        return list(DEFAULT_WATCHLIST)
    return [item.pair for item in items]


def create_mtf_watchlist_table(engine) -> None:
    """Create the mtf_watchlist table if it does not exist."""
    MTFWatchlistItem.metadata.create_all(bind=engine, checkfirst=True)
