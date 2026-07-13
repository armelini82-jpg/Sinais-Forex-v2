import pytest

from app.services.scan_state_service import ScanRecord, ScanStateService


class TestScanStateService:
    def setup_method(self):
        self.service = ScanStateService()

    @pytest.mark.asyncio
    async def test_record_and_get(self):
        record = ScanRecord(
            symbol="EURUSD",
            timeframe="M15",
            direction="BUY",
            status="DESCARTADO",
            iqs_score=67.5,
            reason="ADX baixo — mercado lateral (5/10)",
            scanned_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        await self.service.record(record)
        fetched = await self.service.get("EURUSD", "M15")
        assert fetched is not None
        assert fetched.iqs_score == 67.5
        assert fetched.status == "DESCARTADO"

    @pytest.mark.asyncio
    async def test_get_all_sorted_by_score_desc(self):
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        await self.service.record(
            ScanRecord("EURUSD", "M15", "BUY", "DESCARTADO", 40.0, "fraco", now)
        )
        await self.service.record(
            ScanRecord("GBPUSD", "M15", "SELL", "PREPARANDO", 85.0, "forte", now)
        )
        results = await self.service.get_all()
        assert results[0].symbol == "GBPUSD"
        assert results[1].symbol == "EURUSD"

    @pytest.mark.asyncio
    async def test_overwrites_previous_record_for_same_pair(self):
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        await self.service.record(
            ScanRecord("EURUSD", "M15", "BUY", "DESCARTADO", 40.0, "primeiro", now)
        )
        await self.service.record(
            ScanRecord("EURUSD", "M15", "BUY", "PREPARANDO", 82.0, "segundo", now)
        )
        results = await self.service.get_all()
        assert len(results) == 1
        assert results[0].iqs_score == 82.0

    @pytest.mark.asyncio
    async def test_get_unknown_pair_returns_none(self):
        result = await self.service.get("XAUUSD", "H1")
        assert result is None
