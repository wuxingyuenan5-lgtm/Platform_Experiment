"""Deterministic adapter inputs for API/SQLite delivery tests, never production data."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.research_data_schemas import (
    AShareIndexHistoryPoint,
    AShareIndexSnapshot,
    AShareMarketTurnoverRow,
    AShareTurnoverStock,
    ShenwanMembership,
    ShortTermEmotionSnapshot,
)

CODES = ["600519", "000858", "300750", "300308", "00700"]
NAMES = ["贵州茅台", "五粮液", "宁德时代", "中际旭创", "腾讯控股"]
TRADE_DATE = date(2026, 9, 7)


class AShareFixtureProvider:
    def __init__(self) -> None:
        self.mode = "ready"
        self.delay = 0.0
        self.calls: dict[str, int] = {}

    async def _check(self, module: str) -> None:
        self.calls[module] = self.calls.get(module, 0) + 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.mode == "error" or (self.mode == "partial" and module == "emotion"):
            raise RuntimeError(f"fixture {module} unavailable")

    @staticmethod
    def history(code: str) -> list[AShareIndexHistoryPoint]:
        dates = [TRADE_DATE - timedelta(days=offset) for offset in range(139, -1, -1)]
        dates = [day for day in dates if day.weekday() < 5]
        factor = 1 + int(code[-1], 16) % 5
        return [
            AShareIndexHistoryPoint(
                observed_at=day,
                close=Decimal(100 + factor * i) / 10,
                turnover_yuan=Decimal("1000000000"),
            )
            for i, day in enumerate(dates)
        ]

    async def index_snapshots(self) -> list[AShareIndexSnapshot]:
        await self._check("indices")
        codes = ["000300", "000852", "399006", "000688", "931071", "931238", "932082", "H30590"]
        names = ["沪深300", "中证1000", "创业板指", "科创50", "AI", "金股", "医药", "机器人"]
        return [
            AShareIndexSnapshot(
                code=code,
                name=names[i],
                source_symbol=code,
                close=Decimal(3000 + i * 100),
                return_1d_pct=Decimal(i - 3),
                return_1w_pct=Decimal(i + 2),
                return_1m_pct=Decimal(i - 1),
                return_ytd_pct=Decimal(i + 12),
                distance_52w_high_pct=Decimal(-8 + i),
                volatility_20_pct=Decimal(20 + i),
                spark=[point.close for point in self.history(code)[-30:]],
                history=self.history(code),
            )
            for i, code in enumerate(codes)
        ]

    async def a_share_spot(self) -> list[AShareTurnoverStock]:
        await self._check("spots")
        return [
            AShareTurnoverStock(
                security_code=code,
                security_name=NAMES[i],
                price=Decimal(100 + i),
                observed_at=datetime(2026, 9, 7, 7, 10, tzinfo=UTC),
                turnover_yuan=Decimal(12 - i) * Decimal("1e9"),
                return_pct=None if self.mode == "missing_value" and i == 2 else Decimal(4 - i * 2),
                turnover_pct=Decimal("2.5"),
                market_cap_yuan=Decimal("500000000000"),
                pe_ttm=Decimal("20"),
                pb=Decimal("3"),
            )
            for i, code in enumerate(CODES[:4])
            if not (self.mode == "partial" and i == 1)
        ]

    async def tracked_stock_spot(self, codes: list[str]) -> list[AShareTurnoverStock]:
        await self._check("supplement")
        return [
            AShareTurnoverStock(
                security_code=code,
                security_name="腾讯控股" if code == "00700" else code,
                currency="HKD" if len(code) == 5 else "CNY",
                price=Decimal("360"),
                turnover_yuan=Decimal("7000000000"),
                return_pct=Decimal("1.1"),
                observed_at=datetime(2026, 9, 7, 8, tzinfo=UTC),
            )
            for code in codes
            if not (self.mode == "partial" and code == "000858")
        ]

    async def stock_daily_histories(
        self, codes: list[str]
    ) -> dict[str, list[AShareIndexHistoryPoint]]:
        await self._check("histories")
        return {
            code: self.history(code)
            for code in codes
            if not (self.mode == "partial" and code == "300750")
        }

    async def shenwan_memberships(self) -> list[ShenwanMembership]:
        await self._check("memberships")
        sectors = [
            ("801102", "通信设备"),
            ("801101", "计算机设备"),
            ("801083", "元件"),
            ("801081", "半导体"),
        ]
        return [
            ShenwanMembership(
                security_code=code,
                sw_l1_code="801080",
                sw_l1_name="电子",
                sw_l2_code=sectors[i][0],
                sw_l2_name=sectors[i][1],
                classification_version="fixture-2026",
                effective_from=date(2026, 1, 1),
            )
            for i, code in enumerate(CODES[:4])
        ]

    async def short_term_emotion(self) -> ShortTermEmotionSnapshot:
        await self._check("emotion")
        return ShortTermEmotionSnapshot(
            limit_up_count=40,
            limit_down_count=5,
            broken_board_count=10,
            highest_board_count=5,
            consecutive_board_count=12,
            seal_rate_pct=Decimal(80),
            break_rate_pct=Decimal(20),
            promotion_rate_pct=Decimal(30),
            ladder=[{"boardCount": "2板", "stockCount": 8}],
            leaders=[
                {
                    "securityCode": "300308",
                    "securityName": "中际旭创",
                    "boardCount": 2,
                    "turnoverYuan": "9000000000",
                }
            ],
            trade_date=TRADE_DATE,
        )

    async def a_share_sector_fund_flow(self) -> list[dict]:
        await self._check("flow")
        return [
            {
                "sectorCode": f"BK{100 + i}",
                "name": name,
                "returnPct": i - 3,
                "netInflowYuan": str((i - 3) * 100000000),
                "inflowYuan": str(max(0, i - 3) * 100000000),
                "outflowYuan": str(max(0, 3 - i) * 100000000),
                "firmCount": 20 + i,
            }
            for i, name in enumerate(
                ["半导体", "光学光电子", "通信设备", "软件开发", "汽车", "有色金属", "医疗", "银行"]
            )
        ]

    async def a_share_market_turnover(self) -> list[AShareMarketTurnoverRow]:
        await self._check("turnover")
        return [
            AShareMarketTurnoverRow(
                security_code=CODES[i] if i < 4 else f"600{i:03}",
                security_name=NAMES[i] if i < 4 else f"样本证券{i}",
                price=Decimal(100 + i),
                return_pct=Decimal(i - 10) / 10,
                turnover_yuan=Decimal(25 - i) * Decimal("1e9"),
                market_cap_yuan=Decimal("500000000000"),
                industry="电子",
            )
            for i in range(20)
        ]
