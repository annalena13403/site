"""Domainmodelle für Verbraucherinsolvenzverfahren."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, Iterable, List, Optional


class ProcedurePhase(str, Enum):
    """Phasen eines Verbraucherinsolvenzverfahrens."""

    PREPARATION = "Vorbereitung"
    COURT_SUBMISSION = "Antrag beim Gericht"
    TRUSTEE_ASSESSMENT = "Prüfung durch Treuhänder"  # § 313 InsO
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

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "address": self.address,
            "birth_date": self.birth_date.isoformat(),
            "monthly_net_income": self.monthly_net_income,
            "attachable_income": self.attachable_income,
            "dependents": self.dependents,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, str]) -> "Debtor":
        return cls(
            name=raw["name"],
            address=raw["address"],
            birth_date=date.fromisoformat(raw["birth_date"]),
            monthly_net_income=float(raw["monthly_net_income"]),
            attachable_income=float(raw["attachable_income"]),
            dependents=int(raw["dependents"]),
        )


@dataclass(slots=True)
class Creditor:
    """Informationen zum Gläubiger."""

    name: str
    reference: str
    contact: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "reference": self.reference, "contact": self.contact}

    @classmethod
    def from_dict(cls, raw: Dict[str, str]) -> "Creditor":
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

    def outstanding(self, as_of: Optional[date] = None) -> float:
        """Berechnet den offenen Betrag inklusive Zinsen."""

        if self.interest_rate <= 0:
            return self.principal
        as_of = as_of or date.today()
        days = (as_of - self.created_at).days
        # einfache Verzinsung für Transparenz
        interest = self.principal * self.interest_rate / 365 * days
        return round(self.principal + interest, 2)

    def to_dict(self) -> Dict[str, object]:
        return {
            "creditor": self.creditor.to_dict(),
            "principal": self.principal,
            "interest_rate": self.interest_rate,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "Claim":
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
    executed_at: datetime = field(default_factory=datetime.utcnow)
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "amount": self.amount,
            "executed_at": self.executed_at.isoformat(),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "PaymentRecord":
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

    def to_dict(self) -> Dict[str, object]:
        return {
            "claim_reference": self.claim_reference,
            "creditor_name": self.creditor_name,
            "amount": self.amount,
            "remaining": self.remaining,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "PaymentDistribution":
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
    created_at: datetime = field(default_factory=datetime.utcnow)
    trustee: Optional[str] = None
    court_file_number: Optional[str] = None
    payment_plan_months: int = 36
    payment_records: List[PaymentRecord] = field(default_factory=list)

    def attachable_budget(self) -> float:
        return self.debtor.attachable_income

    def total_claims(self) -> float:
        return round(sum(claim.outstanding() for claim in self.claims), 2)

    def add_claim(self, claim: Claim) -> None:
        self.claims.append(claim)

    def add_payment(self, payment: PaymentRecord) -> None:
        self.payment_records.append(payment)

    def advance_phase(self, target: ProcedurePhase) -> None:
        phases = list(ProcedurePhase)
        current_index = phases.index(self.phase)
        target_index = phases.index(target)
        if target_index < current_index:
            raise ValueError("Eine Rückstufung der Phase ist nicht zulässig.")
        if target_index - current_index > 1:
            raise ValueError(
                "Phasen müssen der Reihe nach durchlaufen werden."
            )
        self.phase = target

    def summarize(self) -> Dict[str, object]:
        return {
            "reference": self.reference,
            "phase": self.phase.value,
            "debtor": self.debtor.to_dict(),
            "claims": [claim.to_dict() for claim in self.claims],
            "total_claims": self.total_claims(),
            "payment_plan_months": self.payment_plan_months,
            "payment_records": [record.to_dict() for record in self.payment_records],
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "InsolvencyCase":
        return cls(
            reference=raw["reference"],
            debtor=Debtor.from_dict(raw["debtor"]),
            claims=[Claim.from_dict(item) for item in raw.get("claims", [])],
            phase=ProcedurePhase(raw.get("phase", ProcedurePhase.PREPARATION.value)),
            created_at=datetime.fromisoformat(raw.get("created_at", datetime.utcnow().isoformat())),
            trustee=raw.get("trustee"),
            court_file_number=raw.get("court_file_number"),
            payment_plan_months=int(raw.get("payment_plan_months", 36)),
            payment_records=[
                PaymentRecord.from_dict(item) for item in raw.get("payment_records", [])
            ],
        )


def pro_rata_distribution(
    amount: float, claims: Iterable[Claim], as_of: Optional[date] = None
) -> List[PaymentDistribution]:
    """Verteilt einen Zahlbetrag nach § 38 InsO proportional auf die Forderungen."""

    outstanding = [claim.outstanding(as_of) for claim in claims]
    total_outstanding = sum(outstanding)
    distributions: List[PaymentDistribution] = []
    if total_outstanding == 0:
        return distributions

    for claim, total in zip(claims, outstanding):
        share = amount * (total / total_outstanding)
        distributions.append(
            PaymentDistribution(
                claim_reference=claim.reference or claim.creditor.reference,
                creditor_name=claim.creditor.name,
                amount=round(share, 2),
                remaining=round(max(total - share, 0), 2),
            )
        )
    return distributions
