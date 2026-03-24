"""Domainmodelle für Verbraucherinsolvenzverfahren."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class ProcedurePhase(str, Enum):
    """Phasen eines Verbraucherinsolvenzverfahrens."""

    PREPARATION = "Vorbereitung"
    COURT_SUBMISSION = "Antrag beim Gericht"
    TRUSTEE_ASSESSMENT = "Prüfung durch Treuhänder"
    PAYMENT_PLAN = "Abführung der pfändbaren Beträge"
    DISCHARGE = "Restschuldbefreiung"


@dataclass(slots=True)
class Debtor:
    """Informationen zum Schuldner."""

    name: str
    address: str
    birth_date: date
    monthly_net_income: float
    attachable_income: float
    dependents: int = 0

    def __post_init__(self) -> None:
        if self.monthly_net_income < 0:
            raise ValueError("Das Nettoeinkommen darf nicht negativ sein.")
        if self.attachable_income < 0:
            raise ValueError("Das pfändbare Einkommen darf nicht negativ sein.")
        if self.attachable_income > self.monthly_net_income:
            raise ValueError("Pfändbares Einkommen darf das Nettoeinkommen nicht übersteigen.")
        if self.dependents < 0:
            raise ValueError("Unterhaltspflichten dürfen nicht negativ sein.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "address": self.address,
            "birth_date": self.birth_date.isoformat(),
            "monthly_net_income": self.monthly_net_income,
            "attachable_income": self.attachable_income,
            "dependents": self.dependents,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Debtor":
        return cls(
            name=raw["name"],
            address=raw["address"],
            birth_date=date.fromisoformat(raw["birth_date"]),
            monthly_net_income=float(raw["monthly_net_income"]),
            attachable_income=float(raw["attachable_income"]),
            dependents=int(raw.get("dependents", 0)),
        )


@dataclass(slots=True)
class Creditor:
    """Informationen zum Gläubiger."""

    name: str
    reference: str
    contact: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "reference": self.reference, "contact": self.contact}

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Creditor":
        return cls(name=raw["name"], reference=raw["reference"], contact=raw.get("contact"))


@dataclass(slots=True)
class Claim:
    """Forderung eines Gläubigers."""

    creditor: Creditor
    principal: float
    interest_rate: float = 0.0
    priority: int = 3
    created_at: date = field(default_factory=date.today)
    reference: Optional[str] = None

    def __post_init__(self) -> None:
        if self.principal <= 0:
            raise ValueError("Die Forderung muss größer als 0 sein.")
        if self.interest_rate < 0:
            raise ValueError("Der Zinssatz darf nicht negativ sein.")
        if self.priority < 1:
            raise ValueError("Der Rang muss mindestens 1 sein.")

    def outstanding(self, as_of: Optional[date] = None) -> float:
        """Berechnet den offenen Betrag inklusive Zinsen."""

        if self.interest_rate <= 0:
            return round(self.principal, 2)
        as_of = as_of or date.today()
        days = max((as_of - self.created_at).days, 0)
        interest = self.principal * self.interest_rate / 365 * days
        return round(self.principal + interest, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "creditor": self.creditor.to_dict(),
            "principal": self.principal,
            "interest_rate": self.interest_rate,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Claim":
        return cls(
            creditor=Creditor.from_dict(raw["creditor"]),
            principal=float(raw["principal"]),
            interest_rate=float(raw.get("interest_rate", 0.0)),
            priority=int(raw.get("priority", 3)),
            created_at=date.fromisoformat(raw["created_at"]),
            reference=raw.get("reference"),
        )


@dataclass(slots=True)
class PaymentRecord:
    """Protokolliert eine Zahlung in den Plan."""

    amount: float
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Der Zahlungsbetrag muss größer als 0 sein.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": self.amount,
            "executed_at": self.executed_at.isoformat(),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PaymentRecord":
        return cls(
            amount=float(raw["amount"]),
            executed_at=datetime.fromisoformat(raw["executed_at"]),
            note=raw.get("note"),
        )


@dataclass(slots=True)
class PaymentDistribution:
    """Verteilung einer Zahlung auf einzelne Forderungen."""

    claim_reference: str
    creditor_name: str
    amount: float
    remaining: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_reference": self.claim_reference,
            "creditor_name": self.creditor_name,
            "amount": self.amount,
            "remaining": self.remaining,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PaymentDistribution":
        return cls(
            claim_reference=raw["claim_reference"],
            creditor_name=raw["creditor_name"],
            amount=float(raw["amount"]),
            remaining=float(raw["remaining"]),
        )


@dataclass
class InsolvencyCase:
    """Abbildung eines vollständigen Verfahrens."""

    reference: str
    debtor: Debtor
    claims: List[Claim] = field(default_factory=list)
    phase: ProcedurePhase = ProcedurePhase.PREPARATION
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trustee: Optional[str] = None
    court_file_number: Optional[str] = None
    payment_plan_months: int = 36
    payment_records: List[PaymentRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.payment_plan_months <= 0:
            raise ValueError("Die Laufzeit des Zahlungsplans muss größer als 0 sein.")

    def attachable_budget(self) -> float:
        return round(self.debtor.attachable_income, 2)

    def total_claims(self, as_of: Optional[date] = None) -> float:
        return round(sum(claim.outstanding(as_of) for claim in self.claims), 2)

    def total_paid(self) -> float:
        return round(sum(record.amount for record in self.payment_records), 2)

    def remaining_debt(self, as_of: Optional[date] = None) -> float:
        return round(max(self.total_claims(as_of) - self.total_paid(), 0.0), 2)

    def add_claim(self, claim: Claim) -> None:
        claim_reference = claim.reference or claim.creditor.reference
        known_references = {existing.reference or existing.creditor.reference for existing in self.claims}
        if claim_reference in known_references:
            raise ValueError(f"Die Forderung {claim_reference} existiert bereits.")
        self.claims.append(claim)

    def add_payment(self, payment: PaymentRecord) -> None:
        if not self.claims:
            raise ValueError("Es sind keine Forderungen vorhanden.")
        if payment.amount > self.remaining_debt():
            raise ValueError("Die Zahlung übersteigt die offene Gesamtschuld.")
        self.payment_records.append(payment)

    def advance_phase(self, target: ProcedurePhase) -> None:
        phases = list(ProcedurePhase)
        current_index = phases.index(self.phase)
        target_index = phases.index(target)
        if target_index < current_index:
            raise ValueError("Eine Rückstufung der Phase ist nicht zulässig.")
        if target_index - current_index > 1:
            raise ValueError("Phasen müssen der Reihe nach durchlaufen werden.")
        self.phase = target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference": self.reference,
            "phase": self.phase.value,
            "debtor": self.debtor.to_dict(),
            "claims": [claim.to_dict() for claim in self.claims],
            "total_claims": self.total_claims(),
            "total_paid": self.total_paid(),
            "remaining_debt": self.remaining_debt(),
            "created_at": self.created_at.isoformat(),
            "trustee": self.trustee,
            "court_file_number": self.court_file_number,
            "payment_plan_months": self.payment_plan_months,
            "payment_records": [record.to_dict() for record in self.payment_records],
        }

    def summarize(self) -> Dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "InsolvencyCase":
        return cls(
            reference=raw["reference"],
            debtor=Debtor.from_dict(raw["debtor"]),
            claims=[Claim.from_dict(item) for item in raw.get("claims", [])],
            phase=ProcedurePhase(raw.get("phase", ProcedurePhase.PREPARATION.value)),
            created_at=datetime.fromisoformat(raw.get("created_at", datetime.now(timezone.utc).isoformat())),
            trustee=raw.get("trustee"),
            court_file_number=raw.get("court_file_number"),
            payment_plan_months=int(raw.get("payment_plan_months", 36)),
            payment_records=[PaymentRecord.from_dict(item) for item in raw.get("payment_records", [])],
        )


def pro_rata_distribution(
    amount: float,
    claims: Iterable[Claim],
    as_of: Optional[date] = None,
    prior_payments: float = 0.0,
) -> List[PaymentDistribution]:
    """Verteilt einen Zahlbetrag proportional auf die aktuell offene Schuld."""

    claim_list = list(claims)
    balances = [claim.outstanding(as_of) for claim in claim_list]
    total_outstanding = round(sum(balances) - prior_payments, 2)
    if amount <= 0 or total_outstanding <= 0:
        return []

    remaining_pool = min(round(amount, 2), total_outstanding)
    raw_shares = [balance / sum(balances) for balance in balances]
    distributions: List[PaymentDistribution] = []

    allocated = 0.0
    for index, (claim, balance, share_ratio) in enumerate(zip(claim_list, balances, raw_shares)):
        is_last = index == len(claim_list) - 1
        share = round(remaining_pool - allocated, 2) if is_last else round(remaining_pool * share_ratio, 2)
        allocated = round(allocated + share, 2)
        distributions.append(
            PaymentDistribution(
                claim_reference=claim.reference or claim.creditor.reference,
                creditor_name=claim.creditor.name,
                amount=share,
                remaining=round(max(balance - share, 0.0), 2),
            )
        )
    return distributions
