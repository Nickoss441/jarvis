"""Tests for gold trade execution module."""

import pytest
import uuid
from pathlib import Path
from jarvis.tools.gold_trade import (
    GoldTradeSignal,
    GoldTradeExecution,
    GoldTradeDecisionEngine,
    GoldTradeJournal,
    execute_gold_trade_dry_run,
    execute_gold_trade_live,
    execute_gold_trade,
    log_gold_trade_execution,
)


class TestGoldTradeSignal:
    """Test gold trade signal dataclass."""
    
    def test_signal_creation(self):
        """GoldTradeSignal initializes with all fields."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Bullish sentiment",
            news_sentiment=1.5,
            youtube_sentiment=1.2,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        assert signal.action == "BUY"
        assert signal.price == 2050.25
        assert signal.confidence == 0.75
        assert signal.news_sentiment == 1.5
        assert signal.youtube_sentiment == 1.2


class TestGoldTradeExecution:
    """Test gold trade execution record."""
    
    def test_execution_creation(self):
        """GoldTradeExecution initializes with signal."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Bullish",
            news_sentiment=1.5,
            youtube_sentiment=1.2,
            timestamp="2026-04-27T12:00:00Z",
        )
        execution = GoldTradeExecution(
            id="trade-123",
            signal=signal,
            mode="dry_run",
            status="executed",
            fill_price=2050.25,
            fill_quantity=1.0,
        )
        
        assert execution.id == "trade-123"
        assert execution.mode == "dry_run"
        assert execution.fill_price == 2050.25
    
    def test_execution_to_dict(self):
        """Execution serializes to dict."""
        signal = GoldTradeSignal(
            action="SELL",
            price=2050.25,
            quantity=1.0,
            confidence=0.68,
            reason="Bearish",
            news_sentiment=-0.8,
            youtube_sentiment=-1.1,
            timestamp="2026-04-27T12:00:00Z",
        )
        execution = GoldTradeExecution(
            id="trade-456",
            signal=signal,
            mode="dry_run",
            status="executed",
            fill_price=2050.25,
            fill_quantity=1.0,
        )
        
        result = execution.to_dict()
        assert result["id"] == "trade-456"
        assert result["action"] == "SELL"
        assert result["mode"] == "dry_run"
        assert result["news_sentiment"] == -0.8


class TestGoldTradeDecisionEngine:
    """Test trade signal generation logic."""
    
    def test_engine_initialization(self):
        """Decision engine initializes with weights."""
        engine = GoldTradeDecisionEngine(
            news_sentiment_weight=0.5,
            youtube_sentiment_weight=0.3,
            price_momentum_weight=0.2,
            min_confidence=0.7,
        )
        
        assert engine.news_sentiment_weight == 0.5
        assert engine.min_confidence == 0.7
    
    def test_generate_signal_bullish(self):
        """Strong bullish sentiment generates BUY signal."""
        engine = GoldTradeDecisionEngine(min_confidence=0.5)
        signal = engine.generate_signal(
            current_price=2050.25,
            previous_price=2040.0,
            news_sentiment=1.5,
            youtube_sentiment=1.8,
        )
        
        assert signal is not None
        assert signal.action == "BUY"
        assert signal.confidence > 0.5
        assert signal.price == 2050.25
    
    def test_generate_signal_bearish(self):
        """Strong bearish sentiment generates SELL signal."""
        engine = GoldTradeDecisionEngine(min_confidence=0.5)
        signal = engine.generate_signal(
            current_price=2050.25,
            previous_price=2060.0,
            news_sentiment=-1.5,
            youtube_sentiment=-1.8,
        )
        
        assert signal is not None
        assert signal.action == "SELL"
        assert signal.confidence > 0.5
    
    def test_generate_signal_neutral_no_signal(self):
        """Neutral sentiment generates no signal."""
        engine = GoldTradeDecisionEngine(min_confidence=0.6)
        signal = engine.generate_signal(
            current_price=2050.25,
            news_sentiment=0.1,
            youtube_sentiment=-0.2,
        )
        
        assert signal is None
    
    def test_generate_signal_low_confidence_filtered(self):
        """Low confidence signals are filtered."""
        engine = GoldTradeDecisionEngine(min_confidence=0.9)
        signal = engine.generate_signal(
            current_price=2050.25,
            news_sentiment=0.8,
            youtube_sentiment=0.9,
        )
        
        assert signal is None  # Should be filtered due to low confidence
    
    def test_sentiment_clamping(self):
        """Out-of-range sentiment values are clamped."""
        engine = GoldTradeDecisionEngine(min_confidence=0.5)
        signal = engine.generate_signal(
            current_price=2050.25,
            news_sentiment=5.0,  # Out of range
            youtube_sentiment=-5.0,  # Out of range
        )
        
        # Should not raise, values should be clamped to [-2, 2]
        if signal:
            assert -2.0 <= signal.news_sentiment <= 2.0
            assert -2.0 <= signal.youtube_sentiment <= 2.0


class TestDryRunExecution:
    """Test mock trade execution."""
    
    def test_dry_run_execution(self):
        """Dry-run execution always succeeds."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        execution = execute_gold_trade_dry_run(signal)
        
        assert execution.status == "executed"
        assert execution.mode == "dry_run"
        assert execution.fill_price == signal.price
        assert execution.fill_quantity == signal.quantity
        assert execution.error_message is None
    
    def test_dry_run_execution_buy_signal(self):
        """Dry-run handles BUY signals."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        execution = execute_gold_trade_dry_run(signal)
        assert execution.signal.action == "BUY"
    
    def test_dry_run_execution_sell_signal(self):
        """Dry-run handles SELL signals."""
        signal = GoldTradeSignal(
            action="SELL",
            price=2050.25,
            quantity=2.0,
            confidence=0.65,
            reason="Test",
            news_sentiment=-1.0,
            youtube_sentiment=-1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        execution = execute_gold_trade_dry_run(signal)
        assert execution.signal.action == "SELL"
        assert execution.fill_quantity == 2.0


class TestLiveExecution:
    """Test live trade execution."""
    
    def test_live_without_api_key_raises(self):
        """Live execution without API key raises error."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        with pytest.raises(RuntimeError, match="requires JARVIS_BROKER_API_KEY"):
            execute_gold_trade_live(signal, broker_api_key=None)
    
    def test_live_with_api_key_not_yet_implemented(self):
        """Live execution with API key raises not-implemented error."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        with pytest.raises(RuntimeError, match="not yet implemented"):
            execute_gold_trade_live(signal, broker_api_key="test-key")


class TestUnifiedExecution:
    """Test unified trade execution."""
    
    def test_execute_dry_run_mode(self):
        """Unified executor supports dry_run mode."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        execution = execute_gold_trade(signal, mode="dry_run")
        assert execution.mode == "dry_run"
        assert execution.status == "executed"
    
    def test_execute_invalid_mode_raises(self):
        """Invalid mode raises ValueError."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        with pytest.raises(ValueError, match="Unknown gold trade mode"):
            execute_gold_trade(signal, mode="invalid")
    
    def test_execute_live_without_api_key_raises(self):
        """Live execution without API key raises error."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        
        with pytest.raises(RuntimeError, match="requires JARVIS_BROKER_API_KEY"):
            execute_gold_trade(signal, mode="live", broker_api_key=None)


class TestTradeLogging:
    """Test trade execution logging."""
    
    def test_log_execution_creates_file(self, tmp_path):
        """Logging creates trades log file."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        execution = execute_gold_trade_dry_run(signal)
        
        log_path = tmp_path / "trades.jsonl"
        log_gold_trade_execution(execution, log_path)
        
        assert log_path.exists()
    
    def test_log_execution_appends_record(self, tmp_path):
        """Logging appends records to file."""
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        execution = execute_gold_trade_dry_run(signal)
        
        log_path = tmp_path / "trades.jsonl"
        log_gold_trade_execution(execution, log_path)
        log_gold_trade_execution(execution, log_path)
        
        with log_path.open("r") as f:
            lines = [line.strip() for line in f if line.strip()]
        
        assert len(lines) == 2


class TestGoldTradeJournal:
    """Test trade journal tracking."""
    
    def test_journal_creation(self, tmp_path):
        """Journal initializes with log path."""
        log_path = tmp_path / "trades.jsonl"
        journal = GoldTradeJournal(log_path)
        
        assert journal.trades_log_path == log_path
        assert len(journal.trades) == 0
    
    def test_journal_add_execution(self, tmp_path):
        """Journal adds execution records."""
        log_path = tmp_path / "trades.jsonl"
        journal = GoldTradeJournal(log_path)
        
        signal = GoldTradeSignal(
            action="BUY",
            price=2050.25,
            quantity=1.0,
            confidence=0.75,
            reason="Test",
            news_sentiment=1.0,
            youtube_sentiment=1.0,
            timestamp="2026-04-27T12:00:00Z",
        )
        execution = execute_gold_trade_dry_run(signal)
        
        journal.add_execution(execution)
        
        assert len(journal.trades) == 1
        assert log_path.exists()
    
    def test_journal_performance_summary_empty(self, tmp_path):
        """Empty journal returns zero performance."""
        log_path = tmp_path / "trades.jsonl"
        journal = GoldTradeJournal(log_path)
        
        summary = journal.performance_summary()
        
        assert summary["count"] == 0
        assert summary["buy_count"] == 0
        assert summary["sell_count"] == 0
        assert summary["win_rate"] == 0.0
    
    def test_journal_performance_summary_with_trades(self, tmp_path):
        """Journal calculates performance metrics."""
        log_path = tmp_path / "trades.jsonl"
        journal = GoldTradeJournal(log_path)
        
        # Add multiple trades
        for action in ["BUY", "SELL", "BUY"]:
            signal = GoldTradeSignal(
                action=action,
                price=2050.25,
                quantity=1.0,
                confidence=0.75,
                reason="Test",
                news_sentiment=1.0 if action == "BUY" else -1.0,
                youtube_sentiment=1.0 if action == "BUY" else -1.0,
                timestamp="2026-04-27T12:00:00Z",
            )
            execution = execute_gold_trade_dry_run(signal)
            journal.add_execution(execution)
        
        summary = journal.performance_summary()
        
        assert summary["count"] == 3
        assert summary["buy_count"] == 2
        assert summary["sell_count"] == 1
