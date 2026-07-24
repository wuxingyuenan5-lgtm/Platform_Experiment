from app.venue_reconciliation_policy import (
    DifferenceDraft,
    balance_difference_drafts,
    expected_order_status,
    external_order_update_status,
    order_difference_drafts,
    position_difference_drafts,
)


def test_external_order_status_mappings_preserve_update_and_comparison_contracts() -> None:
    assert external_order_update_status("accepted") == "acknowledged"
    assert external_order_update_status("rejected") == "rejected"
    assert external_order_update_status("canceled") == "canceled"
    assert external_order_update_status("unknown") == "result_unknown"
    assert external_order_update_status("filled") is None
    assert expected_order_status("filled") == "filled"
    assert expected_order_status("unexpected") == "result_unknown"


def test_order_difference_drafts_preserve_status_then_quantity_order() -> None:
    drafts = order_difference_drafts(
        order_id="order-1",
        local_status="acknowledged",
        local_fill_quantities=["0.1"],
        external_order={"status": "filled"},
        fills=[{"quantity": "0.2000000000000000000000000001"}],
    )

    assert drafts == [
        DifferenceDraft(
            difference_key="order:order-1:status_mismatch",
            difference_type="status_mismatch",
            entity_type="order",
            local_reference="order-1",
            external_reference=None,
            local_value={"status": "acknowledged"},
            external_value={"status": "filled"},
        ),
        DifferenceDraft(
            difference_key="order:order-1:quantity_mismatch",
            difference_type="quantity_mismatch",
            entity_type="order",
            local_reference="order-1",
            external_reference=None,
            local_value={"filledQuantity": "0.1"},
            external_value={"filledQuantity": "0.2000000000000000000000000001"},
        ),
    ]


def test_order_difference_drafts_return_empty_for_exact_decimal_match() -> None:
    assert order_difference_drafts(
        order_id="order-2",
        local_status="filled",
        local_fill_quantities=["0.1", "0.2000000000000000000000000001"],
        external_order={"status": "filled"},
        fills=[
            {"quantity": "0.1"},
            {"quantity": "0.2000000000000000000000000001"},
        ],
    ) == []


def test_position_difference_drafts_cover_missing_mismatch_and_match() -> None:
    external = {
        "instrumentId": "instrument-1",
        "externalPositionId": "external-position-1",
        "netQuantity": "2.5",
    }
    assert position_difference_drafts(
        account_id="account-1",
        local=None,
        external=external,
        fact_id="fact-1",
    ) == [
        DifferenceDraft(
            difference_key="position:instrument-1:missing_local",
            difference_type="missing_local",
            entity_type="position",
            local_reference=None,
            external_reference="external-position-1",
            local_value={},
            external_value=external,
        )
    ]
    assert position_difference_drafts(
        account_id="account-1",
        local={"net_quantity": "2.4", "average_price": "100"},
        external=external,
        fact_id="fact-1",
    ) == [
        DifferenceDraft(
            difference_key="position:instrument-1:quantity_mismatch",
            difference_type="quantity_mismatch",
            entity_type="position",
            local_reference="account-1:instrument-1",
            external_reference="external-position-1",
            local_value={"netQuantity": "2.4"},
            external_value={"netQuantity": "2.5", "factId": "fact-1"},
        )
    ]
    assert position_difference_drafts(
        account_id="account-1",
        local={"net_quantity": "2.500", "average_price": "100"},
        external=external,
        fact_id="fact-1",
    ) == []


def test_balance_difference_drafts_preserve_precedence_and_values() -> None:
    external = {
        "externalBalanceId": "external-balance-1",
        "currency": "USD",
        "equity": "100.25",
    }
    assert balance_difference_drafts(
        account_id="account-1",
        local=None,
        external=external,
    ) == [
        DifferenceDraft(
            difference_key="balance:USD:missing_local",
            difference_type="missing_local",
            entity_type="balance",
            local_reference="account-1",
            external_reference="external-balance-1",
            local_value={},
            external_value=external,
        )
    ]
    assert balance_difference_drafts(
        account_id="account-1",
        local={"currency": "EUR", "equity": "99"},
        external=external,
    ) == [
        DifferenceDraft(
            difference_key="balance:USD:currency_mismatch",
            difference_type="currency_mismatch",
            entity_type="balance",
            local_reference="account-1",
            external_reference="external-balance-1",
            local_value={"currency": "EUR"},
            external_value={"currency": "USD"},
        )
    ]
    assert balance_difference_drafts(
        account_id="account-1",
        local={"currency": "USD", "equity": "100.2"},
        external=external,
    ) == [
        DifferenceDraft(
            difference_key="balance:USD:quantity_mismatch",
            difference_type="quantity_mismatch",
            entity_type="balance",
            local_reference="account-1",
            external_reference="external-balance-1",
            local_value={"equity": "100.2"},
            external_value={"equity": "100.25"},
        )
    ]
    assert balance_difference_drafts(
        account_id="account-1",
        local={"currency": "USD", "equity": "100.250"},
        external=external,
    ) == []
