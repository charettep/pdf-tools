from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

MONTHS_EN = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

MONTHS_FR = {
    "janv": 1,
    "jan": 1,
    "fev": 2,
    "fév": 2,
    "fevr": 2,
    "févr": 2,
    "mar": 3,
    "mars": 3,
    "avr": 4,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juil": 7,
    "juillet": 7,
    "aou": 8,
    "aoû": 8,
    "aout": 8,
    "août": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
    "déc": 12,
}

DATE_PATTERNS = [
    (re.compile(r"^(\d{4}-\d{2}-\d{2})$"), "%Y-%m-%d"),
    (re.compile(r"^(\d{2}-[A-Za-z]{3}-\d{4})$"), "%d-%b-%Y"),
    (re.compile(r"^(\d{2}/\d{2}/\d{4})$"), "%d/%m/%Y"),
]


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def clean_amount(text: str) -> str:
    return text.replace("$", "").replace(",", "").replace(" ", "").replace("–", "-")


def parse_amount(raw: str) -> float | None:
    if not raw:
        return None
    value = clean_amount(raw)
    value = value.replace("(", "-").replace(")", "")
    value = value.replace("+", "")
    try:
        return float(value)
    except ValueError:
        return None


def parse_date(raw: str, year_hint: int | None = None) -> str | None:
    raw = normalize_whitespace(raw)
    for pattern, fmt in DATE_PATTERNS:
        if pattern.match(raw):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                return None

    m = re.match(r"^(\d{1,2})\s+([A-Za-zéûôîàç\.]+)\s+(\d{4})$", raw, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        month_text = m.group(2).strip(".").lower()
        year = int(m.group(3))
        month = MONTHS_EN.get(month_text[:3]) or MONTHS_FR.get(month_text)
        if month:
            return datetime(year, month, day).date().isoformat()

    m = re.match(r"^(\d{1,2})\s+([A-Za-zéûôîàç\.]+)$", raw, re.IGNORECASE)
    if m and year_hint:
        day = int(m.group(1))
        month_text = m.group(2).strip(".").lower()
        month = MONTHS_EN.get(month_text[:3]) or MONTHS_FR.get(month_text)
        if month:
            return datetime(year_hint, month, day).date().isoformat()

    return None


def parse_date_range(raw: str) -> tuple[str | None, str | None]:
    text = normalize_whitespace(raw)
    m = re.search(
        r"(\w+\s+\d{1,2},?\s+\d{4})\s*(?:to|-|—)\s*(\w+\s+\d{1,2},?\s+\d{4})",
        text,
        re.IGNORECASE,
    )
    if m:
        start = parse_date(m.group(1).replace(",", ""))
        end = parse_date(m.group(2).replace(",", ""))
        return start, end

    m = re.search(
        r"(\d{1,2}\s+\w+)\s+(?:to|au)\s+(\d{1,2}\s+\w+)\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if m:
        year = int(m.group(3))
        start = parse_date(f"{m.group(1)} {year}")
        end = parse_date(f"{m.group(2)} {year}")
        return start, end

    m = re.search(r"(\w+\s+\d{1,2})\s*(?:to|au)\s*(\w+\s+\d{1,2})", text, re.IGNORECASE)
    if m:
        start = parse_date(m.group(1))
        end = parse_date(m.group(2))
        return start, end

    return None, None


def detect_currency(text: str) -> str | None:
    if "CAD" in text or "(CAD)" in text:
        return "CAD"
    if "USD" in text or "(USD)" in text:
        return "USD"
    if "$" in text:
        return "CAD"
    return None


def coalesce(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def split_by_two_spaces(line: str) -> list[str]:
    return [chunk for chunk in re.split(r"\s{2,}", line.strip()) if chunk]


def iter_lines(text: str) -> Iterable[str]:
    for line in text.splitlines():
        cleaned = normalize_whitespace(line)
        if cleaned:
            yield cleaned
