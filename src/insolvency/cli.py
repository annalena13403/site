"""Kommandozeilenwerkzeug zur Verwaltung von Verbraucherinsolvenzverfahren."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from .models import (
    Claim,
    Creditor,
    Debtor,
    InsolvencyCase,
    PaymentRecord,
    ProcedurePhase,
)
from .planner import PaymentPlanner
from .storage import CaseStorage


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - CLI Eingabevalidierung
        raise argparse.ArgumentTypeError(
            "Datum muss im ISO-Format JJJJ-MM-TT angegeben werden"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verwaltung von Verbraucherinsolvenzverfahren",
    )
    parser.add_argument(
        "--storage",
        type=Path,
        default=Path("cases"),
        help="Ablageort für Falldateien",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    debtor_parser = subparsers.add_parser("create-case", help="Neuen Fall anlegen")
    debtor_parser.add_argument("reference", help="Aktenzeichen des Verfahrens")
    debtor_parser.add_argument("name", help="Name des Schuldners")
    debtor_parser.add_argument("address", help="Adresse des Schuldners")
    debtor_parser.add_argument("birth_date", type=parse_date, help="Geburtsdatum JJJJ-MM-TT")
    debtor_parser.add_argument(
        "monthly_net_income",
        type=float,
        help="Monatliches Nettoeinkommen",
    )
    debtor_parser.add_argument(
        "attachable_income",
        type=float,
        help="Pfändbarer Anteil des Einkommens",
    )
    debtor_parser.add_argument(
        "--dependents",
        type=int,
        default=0,
        help="Unterhaltspflichten",
    )
    debtor_parser.add_argument(
        "--payment-plan-months",
        type=int,
        default=36,
        help="Laufzeit des Zahlungsplans in Monaten",
    )

    claim_parser = subparsers.add_parser("add-claim", help="Forderung hinzufügen")
    claim_parser.add_argument("reference", help="Aktenzeichen des Verfahrens")
    claim_parser.add_argument("creditor", help="Name des Gläubigers")
    claim_parser.add_argument("creditor_reference", help="Aktenzeichen des Gläubigers")
    claim_parser.add_argument("amount", type=float, help="Höhe der Forderung")
    claim_parser.add_argument(
        "--interest",
        type=float,
        default=0.0,
        help="Jährlicher Zinssatz (dezimal)",
    )
    claim_parser.add_argument(
        "--priority",
        type=int,
        default=3,
        help="Rang der Forderung",
    )

    list_parser = subparsers.add_parser("list", help="Alle Fälle anzeigen")

    summary_parser = subparsers.add_parser("summary", help="Fallübersicht ausgeben")
    summary_parser.add_argument("reference", help="Aktenzeichen des Verfahrens")

    phase_parser = subparsers.add_parser("advance", help="Verfahrensphase wechseln")
    phase_parser.add_argument("reference", help="Aktenzeichen des Verfahrens")
    phase_parser.add_argument(
        "phase",
        choices=[phase.name for phase in ProcedurePhase],
        help="Zielphase",
    )

    payment_parser = subparsers.add_parser("record-payment", help="Zahlung protokollieren")
    payment_parser.add_argument("reference", help="Aktenzeichen des Verfahrens")
    payment_parser.add_argument("amount", type=float, help="Zahlungsbetrag")
    payment_parser.add_argument("--note", help="Verwendungszweck")

    plan_parser = subparsers.add_parser("plan", help="Zahlungsplan anzeigen")
    plan_parser.add_argument("reference", help="Aktenzeichen des Verfahrens")
    plan_parser.add_argument(
        "--summary",
        action="store_true",
        help="Nur Zusammenfassung des Plans ausgeben",
    )

    export_parser = subparsers.add_parser(
        "export", help="Fall als JSON-Dokument ausgeben"
    )
    export_parser.add_argument("reference", help="Aktenzeichen des Verfahrens")

    delete_parser = subparsers.add_parser("delete", help="Fall löschen")
    delete_parser.add_argument("reference", help="Aktenzeichen des Verfahrens")

    return parser


def handle_create_case(args: argparse.Namespace, storage: CaseStorage) -> None:
    debtor = Debtor(
        name=args.name,
        address=args.address,
        birth_date=args.birth_date,
        monthly_net_income=args.monthly_net_income,
        attachable_income=args.attachable_income,
        dependents=args.dependents,
    )
    insolvency_case = InsolvencyCase(
        reference=args.reference,
        debtor=debtor,
        payment_plan_months=args.payment_plan_months,
    )
    storage.save(insolvency_case)
    print(f"Fall {args.reference} angelegt.")


def handle_add_claim(args: argparse.Namespace, storage: CaseStorage) -> None:
    insolvency_case = storage.load(args.reference)
    creditor = Creditor(name=args.creditor, reference=args.creditor_reference)
    claim = Claim(
        creditor=creditor,
        principal=args.amount,
        interest_rate=args.interest,
        priority=args.priority,
        reference=args.creditor_reference,
    )
    insolvency_case.add_claim(claim)
    storage.save(insolvency_case)
    print(f"Forderung {args.creditor_reference} hinzugefügt.")


def handle_list(storage: CaseStorage) -> None:
    for reference in storage.list_cases():
        print(reference)


def handle_summary(args: argparse.Namespace, storage: CaseStorage) -> None:
    insolvency_case = storage.load(args.reference)
    print(json.dumps(insolvency_case.summarize(), indent=2, ensure_ascii=False))


def handle_advance(args: argparse.Namespace, storage: CaseStorage) -> None:
    insolvency_case = storage.load(args.reference)
    target_phase = ProcedurePhase[args.phase]
    insolvency_case.advance_phase(target_phase)
    storage.save(insolvency_case)
    print(f"Phase auf {target_phase.value} gewechselt.")


def handle_payment(args: argparse.Namespace, storage: CaseStorage) -> None:
    insolvency_case = storage.load(args.reference)
    payment = PaymentRecord(amount=args.amount, note=args.note)
    insolvency_case.add_payment(payment)
    storage.save(insolvency_case)
    print("Zahlung erfasst.")


def handle_plan(args: argparse.Namespace, storage: CaseStorage) -> None:
    insolvency_case = storage.load(args.reference)
    planner = PaymentPlanner()
    plan = planner.build_plan(insolvency_case)
    if args.summary:
        data: Any = planner.summarize_plan(plan)
    else:
        data = [item.to_dict() for item in plan]
    print(json.dumps(data, indent=2, ensure_ascii=False))


def handle_export(args: argparse.Namespace, storage: CaseStorage) -> None:
    insolvency_case = storage.load(args.reference)
    print(json.dumps(insolvency_case.summarize(), indent=2, ensure_ascii=False))


def handle_delete(args: argparse.Namespace, storage: CaseStorage) -> None:
    storage.delete(args.reference)
    print("Fall gelöscht.")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    storage = CaseStorage(args.storage)

    try:
        if args.command == "create-case":
            handle_create_case(args, storage)
        elif args.command == "add-claim":
            handle_add_claim(args, storage)
        elif args.command == "list":
            handle_list(storage)
        elif args.command == "summary":
            handle_summary(args, storage)
        elif args.command == "advance":
            handle_advance(args, storage)
        elif args.command == "record-payment":
            handle_payment(args, storage)
        elif args.command == "plan":
            handle_plan(args, storage)
        elif args.command == "export":
            handle_export(args, storage)
        elif args.command == "delete":
            handle_delete(args, storage)
        else:  # pragma: no cover - Absicherung gegen neue Commands ohne Handler
            parser.error(f"Unbekanntes Kommando: {args.command}")
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(2, f"Fehler: {exc}\n")


if __name__ == "__main__":  # pragma: no cover - direkter CLI Aufruf
    main()
