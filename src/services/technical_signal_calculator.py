"""
Technical Signal Calculator for TA-DSS.

This module calculates technical signals for OHLCV candles and stores them
in the technical_signals table. It is used by MarketDataOrchestrator to
pre-calculate signals when fetching new OHLCV data.

Features:
- Batch calculation for multiple candles
- Version tracking for algorithm changes
- Efficient bulk insert
- Compatible with TechnicalAnalyzer output format

Usage:
    from src.services.technical_signal_calculator import TechnicalSignalCalculator

    calculator = TechnicalSignalCalculator(db)
    
    # Calculate signals for OHLCV DataFrame
    df = fetcher.get_ohlcv('BTC/USDT', 'd1', limit=100)
    calculator.calculate_and_save(df, 'BTC/USDT', 'd1')
    
    # Bulk calculate for multiple pairs
    pairs = [('BTC/USDT', 'd1'), ('ETH/USDT', 'd1')]
    calculator.bulk_calculate(pairs)
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from src.models.technical_signal_model import TechnicalSignal
from src.services.technical_analyzer import TechnicalAnalyzer, SignalState

logger = logging.getLogger(__name__)

# Current calculation algorithm version
# Increment when signal logic changes
CALCULATION_VERSION = '1.0'


class TechnicalSignalCalculator:
    """
    Calculates and stores technical signals for OHLCV candles.

    This class:
    1. Uses TechnicalAnalyzer to calculate indicators
    2. Converts results to TechnicalSignal records
    3. Bulk inserts into technical_signals table
    4. Tracks calculation version for audit trail

    Attributes:
        db: Database session.
        analyzer: TechnicalAnalyzer instance for calculations.
        version: Calculation algorithm version.

    Example:
        calculator = TechnicalSignalCalculator(db)
        df = get_ohlcv('BTC/USDT', 'd1')
        calculator.calculate_and_save(df, 'BTC/USDT', 'd1')
    """

    def __init__(
        self,
        db: Session,
        version: str = CALCULATION_VERSION,
    ):
        """
        Initialize the signal calculator.

        Args:
            db: Database session.
            version: Calculation algorithm version (default: '1.0').
        """
        self.db = db
        self.analyzer = TechnicalAnalyzer()
        self.version = version

    def calculate_and_save(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        limit: Optional[int] = None,
    ) -> int:
        """
        Calculate signals for OHLCV data and save to database.

        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume).
            symbol: Trading pair symbol (e.g., 'BTC/USDT').
            timeframe: Timeframe (e.g., 'd1', 'h1').
            limit: Maximum number of candles to calculate (default: all).

        Returns:
            Number of signals saved.

        Example:
            df = fetcher.get_ohlcv('BTC/USDT', 'd1', limit=100)
            count = calculator.calculate_and_save(df, 'BTC/USDT', 'd1')
            logger.info(f"Saved {count} signals")
        """
        if df.empty:
            logger.warning(f"No data provided for {symbol} {timeframe}")
            return 0

        # Limit candles if specified
        if limit:
            df = df.tail(limit)

        # Calculate indicators
        df_with_indicators = self.analyzer.calculate_indicators(df)

        # Generate signal states for all candles
        signals = []
        for i in range(len(df_with_indicators)):
            try:
                # For historical candles, use data up to that point
                candle_df = df_with_indicators.iloc[:i+1]
                signal_states = self.analyzer.generate_signal_states(candle_df)
                overall, _, counts = self.analyzer.calculate_overall_signal(
                    signal_states,
                    position_type=None  # Not needed for overall calculation
                )

                # Extract values
                values = signal_states.get('values', {})

                # Create TechnicalSignal record
                signal = TechnicalSignal(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=df_with_indicators.index[i].to_pydatetime() if hasattr(df_with_indicators.index[i], 'to_pydatetime') else df_with_indicators.index[i],
                    signal_ma10=signal_states.get('MA10', SignalState.NEUTRAL).value if hasattr(signal_states.get('MA10'), 'value') else str(signal_states.get('MA10', 'NEUTRAL')),
                    signal_ma20=signal_states.get('MA20', SignalState.NEUTRAL).value if hasattr(signal_states.get('MA20'), 'value') else str(signal_states.get('MA20', 'NEUTRAL')),
                    signal_ma50=signal_states.get('MA50', SignalState.NEUTRAL).value if hasattr(signal_states.get('MA50'), 'value') else str(signal_states.get('MA50', 'NEUTRAL')),
                    signal_macd=signal_states.get('MACD', SignalState.NEUTRAL).value if hasattr(signal_states.get('MACD'), 'value') else str(signal_states.get('MACD', 'NEUTRAL')),
                    signal_rsi=signal_states.get('RSI', SignalState.NEUTRAL).value if hasattr(signal_states.get('RSI'), 'value') else str(signal_states.get('RSI', 'NEUTRAL')),
                    signal_ott=signal_states.get('OTT', SignalState.NEUTRAL).value if hasattr(signal_states.get('OTT'), 'value') else str(signal_states.get('OTT', 'NEUTRAL')),
                    signal_overall=overall.value if hasattr(overall, 'value') else str(overall),
                    value_ema10=values.get('EMA_10'),
                    value_ema20=values.get('EMA_20'),
                    value_ema50=values.get('EMA_50'),
                    value_macd_hist=values.get('MACD_hist'),
                    value_rsi=values.get('RSI'),
                    value_ott=values.get('OTT'),
                    value_ott_trend=values.get('OTT_Trend'),
                    value_ott_mt=values.get('OTT_MT'),
                    value_ott_mavg=values.get('OTT_MAvg'),
                    calculated_at=datetime.utcnow(),
                    calculation_version=self.version,
                )
                signals.append(signal)

            except Exception as e:
                logger.error(f"Error calculating signals for {symbol} {timeframe} candle {i}: {e}")
                continue

        if not signals:
            logger.warning(f"No signals calculated for {symbol} {timeframe}")
            return 0

        # Bulk insert with upsert (replace existing)
        saved_count = self._bulk_upsert(signals)

        logger.info(
            f"Saved {saved_count} signals for {symbol} {timeframe} "
            f"(version {self.version})"
        )

        return saved_count

    def calculate_and_save_for_pair(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> int:
        """
        Fetch OHLCV data and calculate signals for a symbol/timeframe pair.

        Convenience method that combines fetching and calculation.

        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
            limit: Number of candles to calculate.

        Returns:
            Number of signals saved.
        """
        from src.data_fetcher import DataFetcher
        from src.models.ohlcv_universal_model import OHLCVUniversal

        try:
            # Fetch OHLCV data from database
            candles = self.db.query(OHLCVUniversal).filter(
                OHLCVUniversal.symbol == symbol,
                OHLCVUniversal.timeframe == timeframe,
            ).order_by(
                OHLCVUniversal.timestamp.desc()
            ).limit(limit).all()

            if not candles:
                logger.warning(f"No OHLCV data for {symbol} {timeframe}")
                return 0

            # Convert to DataFrame
            data = [c.to_dict() for c in candles]
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            df = df.sort_index()
            df.columns = df.columns.str.lower()

            # Calculate and save signals
            return self.calculate_and_save(df, symbol, timeframe, limit=limit)

        except Exception as e:
            logger.error(f"Failed to calculate signals for {symbol} {timeframe}: {e}")
            return 0

    def _bulk_upsert(self, signals: List[TechnicalSignal]) -> int:
        """
        Bulk insert signals with upsert (insert or replace).

        Uses SQLite's INSERT OR REPLACE to handle duplicates.

        Args:
            signals: List of TechnicalSignal records to save.

        Returns:
            Number of records saved.
        """
        if not signals:
            return 0

        try:
            # Group by symbol/timeframe for efficient processing
            for signal in signals:
                # Check if record exists
                existing = self.db.query(TechnicalSignal).filter(
                    TechnicalSignal.symbol == signal.symbol,
                    TechnicalSignal.timeframe == signal.timeframe,
                    TechnicalSignal.timestamp == signal.timestamp,
                ).first()

                if existing:
                    # Update existing record
                    for key, value in signal.to_dict().items():
                        if key != 'id':  # Don't update primary key
                            setattr(existing, key, value)
                else:
                    # Insert new record
                    self.db.add(signal)

            self.db.commit()
            return len(signals)

        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            self.db.rollback()
            return 0

    def bulk_calculate(
        self,
        pairs: List[Tuple[str, str]],
        limit: int = 100,
    ) -> dict:
        """
        Calculate signals for multiple symbol/timeframe pairs.

        Args:
            pairs: List of (symbol, timeframe) tuples.
            limit: Number of candles to calculate per pair.

        Returns:
            Dictionary with results: {'success': n, 'failed': m, 'total': k}

        Example:
            pairs = [
                ('BTC/USDT', 'd1'),
                ('ETH/USDT', 'd1'),
                ('XAU/USD', 'h1'),
            ]
            results = calculator.bulk_calculate(pairs, limit=100)
            # {'success': 3, 'failed': 0, 'total': 3}
        """
        from src.data_fetcher import DataFetcher

        results = {'success': 0, 'failed': 0, 'total': len(pairs)}

        for symbol, timeframe in pairs:
            try:
                # Fetch OHLCV data
                fetcher = DataFetcher(source='ccxt', retry_attempts=2)
                df = fetcher.get_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
                fetcher.close()

                if df is None or df.empty:
                    logger.warning(f"No data for {symbol} {timeframe}")
                    results['failed'] += 1
                    continue

                # Standardize column names
                df.columns = df.columns.str.lower()

                # Calculate and save signals
                count = self.calculate_and_save(df, symbol, timeframe, limit=limit)

                if count > 0:
                    results['success'] += 1
                else:
                    results['failed'] += 1

            except Exception as e:
                logger.error(f"Failed to calculate signals for {symbol} {timeframe}: {e}")
                results['failed'] += 1

        logger.info(
            f"Bulk calculation complete: {results['success']}/{results['total']} successful"
        )

        return results

    def get_latest_signals(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> Optional[pd.DataFrame]:
        """
        Get latest pre-calculated signals from database.

        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
            limit: Number of signals to retrieve.

        Returns:
            DataFrame with signals, or None if not found.

        Example:
            df = calculator.get_latest_signals('BTC/USDT', 'd1', limit=100)
            if df is not None:
                latest_overall = df.iloc[-1]['signal_overall']
        """
        try:
            signals = self.db.query(TechnicalSignal).filter(
                TechnicalSignal.symbol == symbol,
                TechnicalSignal.timeframe == timeframe,
            ).order_by(
                TechnicalSignal.timestamp.desc()
            ).limit(limit).all()

            if not signals:
                return None

            # Convert to DataFrame
            data = [s.to_dict() for s in signals]
            df = pd.DataFrame(data)

            # Sort by timestamp ascending
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            logger.error(f"Failed to get signals for {symbol} {timeframe}: {e}")
            return None

    def get_signals_at_timestamp(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
    ) -> Optional[TechnicalSignal]:
        """
        Get signals for a specific candle timestamp.

        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
            timestamp: Candle timestamp.

        Returns:
            TechnicalSignal record, or None if not found.

        Example:
            signal = calculator.get_signals_at_timestamp(
                'BTC/USDT', 'd1', datetime(2026, 3, 8, 0, 0)
            )
            if signal:
                print(f"Overall: {signal.signal_overall}")
        """
        try:
            signal = self.db.query(TechnicalSignal).filter(
                TechnicalSignal.symbol == symbol,
                TechnicalSignal.timeframe == timeframe,
                TechnicalSignal.timestamp == timestamp,
            ).first()

            return signal

        except Exception as e:
            logger.error(f"Failed to get signal at {timestamp}: {e}")
            return None

    def recalculate_all(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> int:
        """
        Recalculate all signals with current algorithm version.

        This is useful when:
        - Signal logic changes (new version)
        - Bug fix in calculation
        - Backfilling historical data

        Args:
            symbol: Optional symbol filter (recalculate all if None).
            timeframe: Optional timeframe filter.

        Returns:
            Number of signals recalculated.

        Example:
            # Recalculate all signals
            count = calculator.recalculate_all()

            # Recalculate only BTC/USDT
            count = calculator.recalculate_all(symbol='BTC/USDT')
        """
        from src.models.ohlcv_universal_model import OHLCVUniversal

        try:
            # Query OHLCV data
            query = self.db.query(OHLCVUniversal)

            if symbol:
                query = query.filter(OHLCVUniversal.symbol == symbol)
            if timeframe:
                query = query.filter(OHLCVUniversal.timeframe == timeframe)

            ohlcv_data = query.order_by(
                OHLCVUniversal.symbol,
                OHLCVUniversal.timeframe,
                OHLCVUniversal.timestamp,
            ).all()

            if not ohlcv_data:
                logger.warning("No OHLCV data found for recalculation")
                return 0

            # Group by symbol/timeframe
            grouped = {}
            for candle in ohlcv_data:
                key = (candle.symbol, candle.timeframe)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(candle)

            # Recalculate for each group
            total_count = 0
            for (sym, tf), candles in grouped.items():
                # Convert to DataFrame
                data = [c.to_dict() for c in candles]
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)

                # Calculate and save
                count = self.calculate_and_save(df, sym, tf)
                total_count += count

            logger.info(f"Recalculated {total_count} signals (version {self.version})")
            return total_count

        except Exception as e:
            logger.error(f"Recalculation failed: {e}")
            return 0

    def delete_signals(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        before_timestamp: Optional[datetime] = None,
    ) -> int:
        """
        Delete signals from database.

        Args:
            symbol: Optional symbol filter.
            timeframe: Optional timeframe filter.
            before_timestamp: Delete signals before this timestamp.

        Returns:
            Number of records deleted.

        Example:
            # Delete all signals for a pair
            count = calculator.delete_signals(symbol='BTC/USDT')

            # Delete old signals (before 2026-01-01)
            count = calculator.delete_signals(before_timestamp=datetime(2026, 1, 1))
        """
        try:
            query = self.db.query(TechnicalSignal)

            if symbol:
                query = query.filter(TechnicalSignal.symbol == symbol)
            if timeframe:
                query = query.filter(TechnicalSignal.timeframe == timeframe)
            if before_timestamp:
                query = query.filter(TechnicalSignal.timestamp < before_timestamp)

            count = query.delete(synchronize_session=False)
            self.db.commit()

            logger.info(f"Deleted {count} signals")
            return count

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            self.db.rollback()
            return 0
