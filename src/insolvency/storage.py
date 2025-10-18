"""Persistenzschicht für Insolvenzfälle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .models import InsolvencyCase


class CaseStorage:
    """Speichert und lädt Insolvenzfälle als JSON-Dateien."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def case_path(self, reference: str) -> Path:
        safe_reference = reference.replace("/", "_").replace(" ", "-")
        return self.directory / f"{safe_reference}.json"

    def save(self, case: InsolvencyCase) -> Path:
        path = self.case_path(case.reference)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(case.summarize(), handle, indent=2, ensure_ascii=False)
        return path

    def load(self, reference: str) -> InsolvencyCase:
        path = self.case_path(reference)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return InsolvencyCase.from_dict(data)

    def list_cases(self) -> List[str]:
        return [path.stem for path in sorted(self.directory.glob("*.json"))]

    def delete(self, reference: str) -> None:
        path = self.case_path(reference)
        if path.exists():
            path.unlink()

    def load_all(self) -> Iterable[InsolvencyCase]:
        for reference in self.list_cases():
            yield self.load(reference)
