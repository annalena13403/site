# Verbraucherinsolvenz-Toolkit

Dieses Projekt stellt ein Kommandozeilenwerkzeug zur Abwicklung von Verbraucherinsolvenzverfahren bereit. Es ermöglicht die Erfassung von Schuldner- und Gläubigerdaten, die Verwaltung der Verfahrensphasen sowie die Erstellung eines einfachen Zahlungsplans.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Nutzung

Nach der Installation steht das Kommando `insolvency` (oder alternativ `python -m insolvency`) zur Verfügung.

### Fall anlegen

```bash
insolvency create-case AZ-2024-01 "Max Mustermann" "Musterstraße 1, 12345 Musterstadt" 1980-01-01 2500 400 --dependents 1 --payment-plan-months 36
```

### Forderung hinzufügen

```bash
insolvency add-claim AZ-2024-01 "Bank AG" KRED-1 5000 --interest 0.05
```

### Übersicht anzeigen

```bash
insolvency summary AZ-2024-01
```

### Verfahrensphase wechseln

```bash
insolvency advance AZ-2024-01 PAYMENT_PLAN
```

### Zahlung erfassen

```bash
insolvency record-payment AZ-2024-01 250 --note "Januarrate"
```

### Zahlungsplan generieren

Kompletter Plan:

```bash
insolvency plan AZ-2024-01
```

Nur eine Zusammenfassung:

```bash
insolvency plan AZ-2024-01 --summary
```

### Fälle auflisten

```bash
insolvency list
```

### Fall löschen

```bash
insolvency delete AZ-2024-01
```

Alle Falldaten werden im JSON-Format im Verzeichnis `cases/` gespeichert. Durch Setzen des Schalters `--storage` kann ein anderer Speicherort gewählt werden.
