from decimal import Decimal

import pytest

from app.position_math import calculate_position_update


@pytest.mark.parametrize(
    ("old_quantity", "old_average", "signed_fill", "fill_price", "expected"),
    [
        (
            Decimal("0"),
            None,
            Decimal("2"),
            Decimal("100"),
            (Decimal("2"), Decimal("100"), Decimal("0")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("1"),
            Decimal("130"),
            (Decimal("3"), Decimal("110"), Decimal("0")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("-1"),
            Decimal("110"),
            (Decimal("1"), Decimal("100"), Decimal("10")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("-2"),
            Decimal("110"),
            (Decimal("0"), None, Decimal("20")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("-3"),
            Decimal("90"),
            (Decimal("-1"), Decimal("90"), Decimal("-20")),
        ),
        (
            Decimal("0"),
            None,
            Decimal("-2"),
            Decimal("100"),
            (Decimal("-2"), Decimal("100"), Decimal("0")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("-1"),
            Decimal("70"),
            (Decimal("-3"), Decimal("90"), Decimal("0")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("1"),
            Decimal("90"),
            (Decimal("-1"), Decimal("100"), Decimal("10")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("2"),
            Decimal("110"),
            (Decimal("0"), None, Decimal("-20")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("3"),
            Decimal("90"),
            (Decimal("1"), Decimal("90"), Decimal("20")),
        ),
    ],
)
def test_calculate_position_update(
    old_quantity: Decimal,
    old_average: Decimal | None,
    signed_fill: Decimal,
    fill_price: Decimal,
    expected: tuple[Decimal, Decimal | None, Decimal],
) -> None:
    result = calculate_position_update(
        old_quantity=old_quantity,
        old_average=old_average,
        signed_fill=signed_fill,
        fill_price=fill_price,
    )

    assert result == expected
