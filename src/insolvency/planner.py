"""Erstellt Zahlungspläne für Insolvenzverfahren."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List

from .models import InsolvencyCase, PaymentDistribution, pro_rata_distribution


@dataclass
class PlanItem:
    month_index: int
    due_date: date
    amount: float
    distributions: List[PaymentDistribution]
    remaining_total: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "month_index": self.month_index,
            "due_date": self.due_date.isoformat(),
            "amount": self.amount,
            "remaining_total": self.remaining_total,
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
        if not case.claims:
            raise ValueError("Es sind keine Forderungen vorhanden.")

        plan: List[PlanItem] = []
        paid_so_far = case.total_paid()
        remaining_total = case.remaining_debt(self.today)

        for month in range(case.payment_plan_months):
            if remaining_total <= 0:
                break
            due_date = date(self.today.year, self.today.month, 1)
            due_year = due_date.year + (due_date.month - 1 + month) // 12
            due_month = (due_date.month - 1 + month) % 12 + 1
            due_date = date(due_year, due_month, 1)
            installment = round(min(monthly_budget, remaining_total), 2)
            distributions = pro_rata_distribution(
                installment,
                case.claims,
                as_of=due_date,
                prior_payments=paid_so_far,
            )
            remaining_total = round(max(remaining_total - installment, 0.0), 2)
            paid_so_far = round(paid_so_far + installment, 2)
            plan.append(
                PlanItem(
                    month_index=month + 1,
                    due_date=due_date,
                    amount=installment,
                    distributions=distributions,
                    remaining_total=remaining_total,
                )
            )
        return plan

    def summarize_plan(self, plan: Iterable[PlanItem]) -> Dict[str, Any]:
        plan_list = list(plan)
        total_amount = round(sum(item.amount for item in plan_list), 2)
        distribution_totals: Dict[str, float] = {}
        for item in plan_list:
            for distribution in item.distributions:
                distribution_totals.setdefault(distribution.creditor_name, 0.0)
                distribution_totals[distribution.creditor_name] += distribution.amount
        return {
            "months": len(plan_list),
            "total_amount": total_amount,
            "remaining_total": plan_list[-1].remaining_total if plan_list else 0.0,
            "creditors": {
                creditor: round(amount, 2) for creditor, amount in distribution_totals.items()
            },
        }
