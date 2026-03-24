from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from insolvency.cli import main
from insolvency.models import Claim, Creditor, Debtor, InsolvencyCase, PaymentRecord, ProcedurePhase
from insolvency.planner import PaymentPlanner
from insolvency.storage import CaseStorage


def build_case() -> InsolvencyCase:
    debtor = Debtor(
        name="Max Mustermann",
        address="Musterstraße 1",
        birth_date=date(1980, 1, 1),
        monthly_net_income=2500,
        attachable_income=400,
        dependents=1,
    )
    case = InsolvencyCase(
        reference="AZ-1",
        debtor=debtor,
        trustee="Treuhand GmbH",
        court_file_number="12 IK 34/26",
        payment_plan_months=12,
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    case.add_claim(
        Claim(
            creditor=Creditor(name="Bank AG", reference="BANK-1"),
            principal=1000,
            reference="BANK-1",
            created_at=date(2026, 1, 1),
        )
    )
    case.add_claim(
        Claim(
            creditor=Creditor(name="Versandhaus", reference="SHOP-1"),
            principal=500,
            reference="SHOP-1",
            created_at=date(2026, 1, 1),
        )
    )
    return case


def test_storage_roundtrip_preserves_metadata(tmp_path: Path) -> None:
    storage = CaseStorage(tmp_path)
    case = build_case()
    case.phase = ProcedurePhase.COURT_SUBMISSION
    case.add_payment(PaymentRecord(amount=125, note="erste Rate"))

    storage.save(case)
    loaded = storage.load(case.reference)

    assert loaded.created_at == case.created_at
    assert loaded.trustee == "Treuhand GmbH"
    assert loaded.court_file_number == "12 IK 34/26"
    assert loaded.phase == ProcedurePhase.COURT_SUBMISSION
    assert loaded.payment_records[0].amount == 125


def test_payment_plan_stops_when_debt_is_paid() -> None:
    case = build_case()
    planner = PaymentPlanner(today=date(2026, 3, 1))

    plan = planner.build_plan(case)

    assert len(plan) == 4
    assert [item.amount for item in plan] == [400, 400, 400, 300]
    assert plan[-1].remaining_total == 0


def test_duplicate_claim_reference_is_rejected() -> None:
    case = build_case()

    try:
        case.add_claim(
            Claim(
                creditor=Creditor(name="Andere Bank", reference="BANK-1"),
                principal=200,
                reference="BANK-1",
            )
        )
    except ValueError as exc:
        assert "existiert bereits" in str(exc)
    else:
        raise AssertionError("duplicate claim should fail")


def test_list_cases_keeps_original_reference(tmp_path: Path) -> None:
    storage = CaseStorage(tmp_path)
    case = build_case()
    case.reference = "AZ 26/1"

    storage.save(case)

    assert storage.list_cases() == ["AZ 26/1"]


def test_cli_returns_readable_error_for_missing_case(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--storage", str(tmp_path), "summary", "UNBEKANNT"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "Kein Fall mit Aktenzeichen" in captured.err
