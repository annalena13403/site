"""Erstellt Zahlungspläne für Insolvenzverfahren."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List

from .models import InsolvencyCase, PaymentDistribution, pro_rata_distribution


@dataclass
class PlanItem:
    month_index: int
    due_date: date
    amount: float
    distributions: List[PaymentDistribution]

    def to_dict(self) -> Dict[str, object]:
        return {
            "month_index": self.month_index,
            "due_date": self.due_date.isoformat(),
            "amount": self.amount,
            "distributions": [distribution.to_dict() for distribution in self.distributions],
        }


class PaymentPlanner:
    """Berechnet eine einfache Ratenzahlung über die Planlaufzeit."""

    def __init__(self, today: date | None = None) -> None:
        self.today = today or date.today()

    def build_plan(self, case: InsolvencyCase) -> List[PlanItem]:
        monthly_budget = case.attachable_budget()
        if monthly_budget <= 0:
            raise ValueError("Es ist kein pfändbares Einkommen vorhanden.")

        plan: List[PlanItem] = []
        for month in range(case.payment_plan_months):
            due_date = date(self.today.year, self.today.month, 1)
            due_year = due_date.year + (due_date.month - 1 + month) // 12
            due_month = (due_date.month - 1 + month) % 12 + 1
            due_date = date(due_year, due_month, 1)
            distributions = pro_rata_distribution(monthly_budget, case.claims, due_date)
            plan.append(
                PlanItem(
                    month_index=month + 1,
                    due_date=due_date,
                    amount=monthly_budget,
                    distributions=distributions,
                )
            )
        return plan

    def summarize_plan(self, plan: Iterable[PlanItem]) -> Dict[str, object]:
        plan_list = list(plan)
        total_amount = round(sum(item.amount for item in plan_list), 2)
        distribution_totals: Dict[str, float] = {}
        for item in plan_list:
            for distribution in item.distributions:
                distribution_totals.setdefault(distribution.creditor_name, 0.0)
                distribution_totals[distribution.creditor_name] += distribution.amount
        return {
            "months": len(plan_list),
            "total_amount": round(total_amount, 2),
            "creditors": {
                creditor: round(amount, 2) for creditor, amount in distribution_totals.items()
            },
        }
