from __future__ import annotations

from decimal import Decimal

from app.bybit_private_stream import BybitPrivateEventParser


def test_parser_accepts_chase_child_prefix_and_stable_execution_identity() -> None:
    parser = BybitPrivateEventParser(
        symbol="XAUTUSDT",
        order_link_prefix="VGP-CHASE",
    )

    events = parser.parse(
        {
            "topic": "execution",
            "data": [
                {
                    "symbol": "XAUTUSDT",
                    "orderLinkId": "VGP-CHASE-2",
                    "orderId": "ORDER-2",
                    "execId": "EXEC-1",
                    "execQty": "0.4",
                    "execPrice": "2500.1",
                    "execTime": "1785000000000",
                },
                {
                    "symbol": "BTCUSDT",
                    "orderLinkId": "VGP-CHASE-2",
                    "orderId": "IGNORED",
                    "execId": "IGNORED",
                    "execQty": "1",
                    "execPrice": "1",
                    "execTime": "1785000000000",
                },
            ],
        }
    )

    assert len(events) == 1
    assert events[0].event_id == "execution:EXEC-1"
    assert events[0].external_order_id == "ORDER-2"
    assert events[0].execution_quantity == Decimal("0.4")
    assert events[0].sequence == 1


def test_parser_ignores_unrelated_order_link_prefix() -> None:
    parser = BybitPrivateEventParser(
        symbol="XAUTUSDT",
        order_link_prefix="VGP-CHASE",
    )

    events = parser.parse(
        {
            "topic": "order",
            "data": [
                {
                    "symbol": "XAUTUSDT",
                    "orderLinkId": "OTHER-ORDER",
                    "orderId": "ORDER-OTHER",
                    "orderStatus": "New",
                    "updatedTime": "1785000000000",
                }
            ],
        }
    )

    assert events == []


def test_parser_maps_order_status_and_composite_identity() -> None:
    parser = BybitPrivateEventParser(
        symbol="XAUTUSDT",
        order_link_prefix="VGP-CHASE",
    )

    events = parser.parse(
        {
            "topic": "order",
            "data": [
                {
                    "symbol": "XAUTUSDT",
                    "orderLinkId": "VGP-CHASE-1",
                    "orderId": "ORDER-1",
                    "orderStatus": "Cancelled",
                    "cumExecQty": "0",
                    "updatedTime": "1785000001000",
                }
            ],
        }
    )

    assert len(events) == 1
    assert events[0].order_status == "canceled"
    assert events[0].event_id == "order:ORDER-1:Cancelled:1785000001000:0"
