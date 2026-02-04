from __future__ import annotations

import base64
import csv
import io
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from pdf_tools.extraction.schema import TRANSACTION_FIELDS
from pdf_tools.extraction.utils import (
    coalesce,
    detect_currency,
    iter_lines,
    normalize_whitespace,
    parse_amount,
    parse_date,
    parse_date_range,
    split_by_two_spaces,
)


@dataclass
class ExtractionOptions:
    use_pdfplumber: bool = True
    use_camelot: bool = True
    use_tesseract: bool = True
    use_ollama: bool = True
    use_glm_ocr_sdk: bool = False
    ollama_url: str = "http://127.0.0.1:11434/api/chat"
    ollama_model: str = "glm-ocr"
    tesseract_lang: str = "eng+fra"
    tesseract_psm: str = "6"
    camelot_primary_flavor: str = "lattice"
    glm_ocr_config: str = ""


def extract_transactions(
    pdf_paths: Iterable[str],
    output_dir: str,
    combined_csv_path: str | None,
    options: ExtractionOptions,
) -> tuple[list[dict[str, str]], list[str]]:
    all_rows: list[dict[str, str]] = []
    notes: list[str] = []

    for pdf_path in pdf_paths:
        rows, note = extract_from_pdf(pdf_path, options)
        if note:
            notes.append(note)
        if rows:
            all_rows.extend(rows)
        if output_dir:
            per_file_path = Path(output_dir) / (Path(pdf_path).stem + ".csv")
            write_csv(str(per_file_path), rows)

    if combined_csv_path:
        write_csv(combined_csv_path, all_rows)

    return all_rows, notes


def extract_from_pdf(pdf_path: str, options: ExtractionOptions) -> tuple[list[dict[str, str]], str | None]:
    pdf_bytes = load_pdf_bytes(pdf_path)
    text_pages = extract_text_pages(pdf_path)
    full_text = "\n".join(text_pages)
    metadata = extract_statement_metadata(full_text, pdf_path)
    statement_type = detect_statement_type(full_text, pdf_path)

    year_hint = None
    if metadata.get("statement_period_start"):
        try:
            year_hint = int(metadata["statement_period_start"][:4])
        except ValueError:
            year_hint = None

    rows = parse_transactions_by_type(statement_type, text_pages, metadata, pdf_path, year_hint)

    if not rows and options.use_pdfplumber:
        rows = parse_with_pdfplumber(pdf_path, metadata)

    if not rows and options.use_camelot:
        rows = parse_with_camelot(pdf_path, metadata, options)

    if not rows and options.use_tesseract:
        ocr_text = extract_text_with_tesseract(
            pdf_path,
            pdf_bytes,
            options.tesseract_lang,
            options.tesseract_psm,
        )
        if ocr_text:
            ocr_pages = ocr_text.split("\f")
            rows = parse_transactions_by_type(statement_type, ocr_pages, metadata, pdf_path, year_hint)

    if not rows and options.use_glm_ocr_sdk:
        rows = parse_with_glm_ocr_sdk(pdf_path, pdf_bytes, metadata, statement_type, options)
    if not rows and options.use_ollama:
        rows = parse_with_ollama(pdf_path, pdf_bytes, metadata, options)

    if rows:
        rows = [apply_metadata(row, metadata, pdf_path, row.get("source_page")) for row in rows]
    note = None if rows else f"No transactions found in {Path(pdf_path).name}"
    return rows, note


def extract_text_pages(pdf_path: str) -> list[str]:
    try:
        reader = PdfReader(pdf_path)
        return [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, OSError, ValueError):
        return []


def load_pdf_bytes(pdf_path: str) -> bytes | None:
    try:
        with open(pdf_path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def detect_statement_type(text: str, filename: str) -> str:
    name = Path(filename).name.lower()
    text_lower = text.lower()
    if "koho" in text_lower or "koho" in name:
        return "koho"
    if "wealthsimple" in text_lower or "ws-" in name:
        return "wealthsimple"
    if "tangerine" in text_lower and "mastercard" in text_lower:
        return "tangerine_mastercard"
    if "tangerine" in text_lower and "chequing" in text_lower:
        return "tangerine_chequing"
    if "tangerine" in text_lower and "savings" in text_lower:
        return "tangerine_savings"
    if "walmart" in text_lower or "wm-" in name:
        return "walmart_mc"
    if "capital one" in text_lower or "cap-mc" in name:
        return "capital_one"
    if "desjardins" in text_lower:
        return "desjardins"
    if "manulife" in text_lower:
        return "manulife"
    if "banque nationale" in text_lower or "national bank" in text_lower or "nbc-" in name:
        return "nbc"
    return "unknown"


def extract_statement_metadata(text: str, filename: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    lower = text.lower()

    if "tangerine" in lower:
        metadata["institution"] = "Tangerine"
    elif "wealthsimple" in lower:
        metadata["institution"] = "Wealthsimple"
    elif "koho" in lower:
        metadata["institution"] = "KOHO"
    elif "desjardins" in lower:
        metadata["institution"] = "Desjardins"
    elif "manulife" in lower:
        metadata["institution"] = "Manulife"
    elif "walmart" in lower:
        metadata["institution"] = "Walmart"
    elif "banque nationale" in lower or "national bank" in lower:
        metadata["institution"] = "National Bank"
    elif "capital one" in lower:
        metadata["institution"] = "Capital One"

    if "chequing" in lower or "compte bancaire courant" in lower:
        metadata["account_type"] = "chequing"
    elif "savings" in lower or "compte d'epargne" in lower or "compte d’épargne" in lower:
        metadata["account_type"] = "savings"
    elif "mastercard" in lower:
        metadata["account_type"] = "credit_card"
    elif "prepaid" in lower:
        metadata["account_type"] = "prepaid"

    account_match = re.search(r"account number[:\s]+([\dxX*\-\s]+)", text, re.IGNORECASE)
    if account_match:
        metadata["account_number"] = normalize_whitespace(account_match.group(1))
    else:
        account_match = re.search(r"n°\s*(\d+)", text, re.IGNORECASE)
        if account_match:
            metadata["account_number"] = account_match.group(1)

    details_match = re.search(r"The Details\s+-\s+(.+?)\s+-\s+(\d{4,})", text, re.IGNORECASE)
    if details_match:
        metadata["account_name"] = normalize_whitespace(details_match.group(1))
        metadata["account_number"] = metadata.get("account_number", details_match.group(2))

    period_match = re.search(r"Statement period\s+([^\n]+)", text, re.IGNORECASE)
    if period_match:
        start, end = parse_date_range(period_match.group(1))
        if start:
            metadata["statement_period_start"] = start
        if end:
            metadata["statement_period_end"] = end

    if "statement period" not in lower:
        range_match = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+To\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
        if range_match:
            start, end = parse_date_range(range_match.group(0))
            if start:
                metadata["statement_period_start"] = start
            if end:
                metadata["statement_period_end"] = end

    french_range = re.search(r"du\s+([\w\s]+)\s+au\s+([\w\s]+)\s+(\d{4})", text, re.IGNORECASE)
    if french_range:
        start, end = parse_date_range(f"{french_range.group(1)} au {french_range.group(2)} {french_range.group(3)}")
        if start:
            metadata["statement_period_start"] = start
        if end:
            metadata["statement_period_end"] = end

    date_match = re.search(r"Statement date\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text, re.IGNORECASE)
    if date_match:
        metadata["statement_date"] = parse_date(date_match.group(1).replace(",", "")) or ""
    else:
        date_match = re.search(r"Date du relev[ée]\s*:?\s*(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
        if date_match:
            metadata["statement_date"] = parse_date(date_match.group(1)) or ""

    metadata["currency"] = detect_currency(text) or ""
    metadata["source_file"] = Path(filename).name

    return metadata


def apply_metadata(row: dict[str, str], metadata: dict[str, str], source_file: str, source_page: str | None) -> dict[str, str]:
    merged = {field: "" for field in TRANSACTION_FIELDS}
    for key, value in metadata.items():
        if key in merged:
            merged[key] = value
    for key, value in row.items():
        if key in merged and value:
            merged[key] = value
    merged["source_file"] = Path(source_file).name
    if source_page:
        merged["source_page"] = source_page
    return merged


def parse_transactions_by_type(statement_type: str, pages: list[str], metadata: dict[str, str], pdf_path: str, year_hint: int | None) -> list[dict[str, str]]:
    if statement_type == "koho":
        return parse_koho(pages, year_hint)
    if statement_type in {"tangerine_chequing", "tangerine_savings"}:
        return parse_tangerine_deposit_accounts(pages)
    if statement_type == "tangerine_mastercard":
        return parse_tangerine_mastercard(pages)
    if statement_type == "wealthsimple":
        return parse_wealthsimple(pages)
    if statement_type == "walmart_mc":
        return parse_walmart_mastercard(pages, year_hint)
    if statement_type == "capital_one":
        return parse_capital_one(pages, year_hint)
    if statement_type == "desjardins":
        return parse_desjardins(pages, year_hint)
    if statement_type == "manulife":
        return parse_manulife(pages, year_hint)
    return parse_generic_credit_card(pages, metadata, pdf_path)


def parse_koho(pages: list[str], year_hint: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    month_re = re.compile(r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{1,2}\b")
    for page_index, text in enumerate(pages, start=1):
        for line in iter_lines(text):
            if not month_re.match(line):
                continue
            amounts = re.findall(r"\d[\d,]*\.\d{2}", line)
            if len(amounts) < 2:
                continue
            balance = parse_amount(amounts[-1])
            amount = parse_amount(amounts[-2])
            desc_part = line
            for amt in amounts:
                desc_part = desc_part.replace(amt, "", 1)
            desc = normalize_whitespace(desc_part)
            direction = "credit" if "from" in desc.lower() or "load" in desc.lower() else "debit"
            date_tokens = desc.split(" ", 2)
            date_raw = " ".join(date_tokens[:2]) if len(date_tokens) >= 2 else ""
            rows.append(
                {
                    "transaction_date": parse_date(date_raw, year_hint) or "",
                    "description": desc,
                    "amount": f"{amount:.2f}" if amount is not None else "",
                    "amount_direction": direction,
                    "balance": f"{balance:.2f}" if balance is not None else "",
                    "source_page": str(page_index),
                }
            )
    return rows


def parse_wealthsimple(pages: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    line_re = re.compile(
        r"^(\d{4}-\d{2}-\d{2})\s+(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([–\-$\d,\.\s]+)\s+([\-$\d,\.\s]+)$"
    )
    for page_index, text in enumerate(pages, start=1):
        for line in iter_lines(text):
            match = line_re.match(line)
            if not match:
                continue
            txn_date, posted_date, desc, amount_raw, balance_raw = match.groups()
            amount = parse_amount(amount_raw)
            balance = parse_amount(balance_raw)
            direction = "debit" if amount is not None and amount < 0 else "credit"
            rows.append(
                {
                    "transaction_date": txn_date,
                    "posted_date": posted_date,
                    "description": desc,
                    "amount": f"{amount:.2f}" if amount is not None else "",
                    "amount_direction": direction,
                    "balance": f"{balance:.2f}" if balance is not None else "",
                    "source_page": str(page_index),
                }
            )
    return rows


def parse_tangerine_deposit_accounts(pages: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_account_name: str | None = None
    current_account_number: str | None = None

    details_re = re.compile(r"The Details\s+-\s+(.+?)\s+-\s+(\d{4,})", re.IGNORECASE)
    line_re = re.compile(
        r"^(\(?-?[\d,]+\.\d{2}\)?)+\s+(-?[\d,]+\.\d{2})\s+(.+?)\s+(\d{1,2}\s+\w+\s+\d{4})$"
    )

    buffer: list[str] = []
    for page_index, text in enumerate(pages, start=1):
        for line in iter_lines(text):
            detail_match = details_re.search(line)
            if detail_match:
                current_account_name = normalize_whitespace(detail_match.group(1))
                current_account_number = detail_match.group(2)

            if line.endswith("-"):
                buffer.append(line[:-1])
                continue
            if buffer:
                line = " ".join(buffer + [line])
                buffer = []

            match = line_re.match(line)
            if not match:
                continue
            balance_raw, amount_raw, desc, date_raw = match.groups()
            amount = parse_amount(amount_raw)
            balance = parse_amount(balance_raw)
            direction = "debit"
            if re.search(r"deposit|from|interest|reward|credit", desc, re.IGNORECASE):
                direction = "credit"
            if amount is not None and amount < 0:
                direction = "debit"
            rows.append(
                {
                    "account_name": current_account_name or "",
                    "account_number": current_account_number or "",
                    "transaction_date": parse_date(date_raw) or "",
                    "description": desc,
                    "amount": f"{abs(amount):.2f}" if amount is not None else "",
                    "amount_direction": direction,
                    "balance": f"{balance:.2f}" if balance is not None else "",
                    "source_page": str(page_index),
                }
            )
    return rows


def parse_tangerine_mastercard(pages: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for page_index, text in enumerate(pages, start=1):
        for line in iter_lines(text):
            if not re.match(r"^\d{2}-[A-Za-z]{3}-\d{4}\s+\d{2}-[A-Za-z]{3}-\d{4}", line):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            txn_date = parse_date(parts[0]) or ""
            posted_date = parse_date(parts[1]) or ""
            amount_matches = re.findall(r"-?\$?\d[\d,]*\.\d{2}", line)
            if not amount_matches:
                continue
            amount_raw = amount_matches[-2] if len(amount_matches) >= 2 else amount_matches[-1]
            reward_raw = amount_matches[-1] if len(amount_matches) >= 2 else ""
            amount = parse_amount(amount_raw)
            reward = parse_amount(reward_raw) if reward_raw else None
            desc_part = line
            for token in (parts[0], parts[1]):
                desc_part = desc_part.replace(token, "", 1).strip()
            if amount_raw:
                desc_part = desc_part.rsplit(amount_raw, 1)[0].strip()
            if reward_raw and reward_raw in desc_part:
                desc_part = desc_part.rsplit(reward_raw, 1)[0].strip()
            desc_part = desc_part.replace("–", "-")
            category = ""
            desc_tokens = desc_part.split()
            if desc_tokens and re.fullmatch(r"[A-Z]{2,3}", desc_tokens[-1]):
                category = desc_tokens[-1]
                desc_part = " ".join(desc_tokens[:-1]).strip()
            direction = "debit" if amount is not None and amount < 0 else "credit"
            rows.append(
                {
                    "transaction_date": txn_date,
                    "posted_date": posted_date,
                    "description": desc_part,
                    "category": category,
                    "amount": f"{abs(amount):.2f}" if amount is not None else "",
                    "amount_direction": direction,
                    "reward": f"{reward:.2f}" if reward is not None else "",
                    "source_page": str(page_index),
                }
            )
    return rows


def parse_walmart_mastercard(pages: list[str], year_hint: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    line_re = re.compile(
        r"^(\d+)\s+(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+(.+?)\s+(\$?-?\d[\d,]*\.\d{2})$"
    )
    for page_index, text in enumerate(pages, start=1):
        for line in iter_lines(text):
            match = line_re.match(line)
            if not match:
                continue
            _, txn_date_raw, posted_date_raw, desc, amount_raw = match.groups()
            amount = parse_amount(amount_raw)
            direction = "debit" if amount is not None and amount < 0 else "credit"
            rows.append(
                {
                    "transaction_date": parse_date(txn_date_raw, year_hint) or "",
                    "posted_date": parse_date(posted_date_raw, year_hint) or "",
                    "description": desc,
                    "amount": f"{abs(amount):.2f}" if amount is not None else "",
                    "amount_direction": direction,
                    "source_page": str(page_index),
                }
            )
    return rows


def parse_capital_one(pages: list[str], year_hint: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    line_re = re.compile(
        r"^(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+(.+?)\s+(-?\$?\d[\d,]*\.\d{2})$"
    )
    for page_index, text in enumerate(pages, start=1):
        for line in iter_lines(text):
            match = line_re.match(line)
            if not match:
                continue
            txn_date_raw, posted_date_raw, desc, amount_raw = match.groups()
            amount = parse_amount(amount_raw)
            direction = "debit" if amount is not None and amount < 0 else "credit"
            rows.append(
                {
                    "transaction_date": parse_date(txn_date_raw, year_hint) or "",
                    "posted_date": parse_date(posted_date_raw, year_hint) or "",
                    "description": desc,
                    "amount": f"{abs(amount):.2f}" if amount is not None else "",
                    "amount_direction": direction,
                    "source_page": str(page_index),
                }
            )
    return rows


def parse_desjardins(pages: list[str], year_hint: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for page_index, text in enumerate(pages, start=1):
        capture = False
        for line in iter_lines(text):
            if "Date Code Description" in line:
                capture = True
                continue
            if not capture:
                continue
            if line.startswith("SOMMAIRE") or line.startswith("RELEV"):
                capture = False
                continue
            parts = split_by_two_spaces(line)
            if len(parts) < 4:
                continue
            date_raw = parts[0]
            desc = parts[2] if len(parts) >= 3 else ""
            fee = parts[3] if len(parts) >= 4 else ""
            retrait = parts[4] if len(parts) >= 5 else ""
            depot = parts[5] if len(parts) >= 6 else ""
            solde = parts[6] if len(parts) >= 7 else ""
            amount = parse_amount(depot) if depot else parse_amount(retrait)
            direction = "credit" if depot else "debit"
            rows.append(
                {
                    "transaction_date": parse_date(date_raw, year_hint) or "",
                    "description": desc,
                    "fee": fee,
                    "amount": f"{amount:.2f}" if amount is not None else "",
                    "amount_direction": direction,
                    "balance": solde,
                    "source_page": str(page_index),
                }
            )
    return rows


def parse_manulife(pages: list[str], year_hint: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    line_re = re.compile(r"^(\d{1,2}\s+\w+)\s+(.+?)\s+(\d[\d,]*[,\.]\d{2}\s*\$)\s+(\d[\d,]*[,\.]\d{2}\s*\$)\s+(\d[\d,]*[,\.]\d{2}\s*\$)")
    for page_index, text in enumerate(pages, start=1):
        for line in iter_lines(text):
            match = line_re.match(line)
            if not match:
                continue
            date_raw, desc, retrait, depot, solde = match.groups()
            amount = parse_amount(retrait) if retrait else parse_amount(depot)
            direction = "credit" if depot and parse_amount(depot) else "debit"
            rows.append(
                {
                    "transaction_date": parse_date(date_raw, year_hint) or "",
                    "description": desc,
                    "amount": f"{amount:.2f}" if amount is not None else "",
                    "amount_direction": direction,
                    "balance": solde,
                    "source_page": str(page_index),
                }
            )
    return rows


def parse_generic_credit_card(pages: list[str], metadata: dict[str, str], pdf_path: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for page_index, text in enumerate(pages, start=1):
        for line in iter_lines(text):
            match = re.match(
                r"^(\d{2}-[A-Za-z]{3}-\d{4})\s+(\d{2}-[A-Za-z]{3}-\d{4})\s+(.+?)\s+(-?\$?\d[\d,]*\.\d{2})$",
                line,
            )
            if match:
                txn_date_raw, posted_date_raw, desc, amount_raw = match.groups()
                amount = parse_amount(amount_raw)
                direction = "debit" if amount is not None and amount < 0 else "credit"
                rows.append(
                    {
                        "transaction_date": parse_date(txn_date_raw) or "",
                        "posted_date": parse_date(posted_date_raw) or "",
                        "description": desc,
                        "amount": f"{abs(amount):.2f}" if amount is not None else "",
                        "amount_direction": direction,
                        "source_page": str(page_index),
                    }
                )
    return rows


def parse_with_pdfplumber(pdf_path: str, metadata: dict[str, str]) -> list[dict[str, str]]:
    try:
        import pdfplumber
    except Exception:
        return []

    rows: list[dict[str, str]] = []
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "text",
        "min_words_vertical": 3,
        "snap_tolerance": 5,
        "intersection_tolerance": 5,
    }
    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            table_objects = page.find_tables(table_settings)
            tables: list[list[list[str | None]]] = []
            if table_objects:
                for table in table_objects:
                    cropped = page.crop(table.bbox)
                    extracted = cropped.extract_table(table_settings=table_settings)
                    if extracted:
                        tables.append(extracted)
            if not tables:
                tables = page.extract_tables(table_settings=table_settings)
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row or not any(row):
                        continue
                    cells = [normalize_whitespace(cell) if cell else "" for cell in row]
                    if any("Date" in cell and "Description" in cell for cell in cells):
                        continue
                    rows.extend(parse_table_row(cells, page_index))
    return rows


def parse_with_camelot(pdf_path: str, metadata: dict[str, str], options: ExtractionOptions) -> list[dict[str, str]]:
    try:
        import camelot
    except Exception:
        return []

    rows: list[dict[str, str]] = []
    flavors = [options.camelot_primary_flavor, "stream"]
    flavors = [flavor for flavor in flavors if flavor]
    if len(flavors) == 2 and flavors[0] == flavors[1]:
        flavors = [flavors[0]]
    for flavor in flavors:
        try:
            tables = camelot.read_pdf(pdf_path, flavor=flavor, pages="all")
        except Exception:
            continue
        for table in tables:
            data = table.df.values.tolist()
            for row in data:
                if not row:
                    continue
                cells = [normalize_whitespace(cell) if cell else "" for cell in row]
                if any("Date" in cell and "Description" in cell for cell in cells):
                    continue
                rows.extend(parse_table_row(cells, None))
    return rows


def parse_table_row(cells: list[str], page_index: int | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    joined = " ".join(cells)

    if len(cells) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
        amount = parse_amount(cells[-2]) if len(cells) >= 2 else None
        balance = parse_amount(cells[-1]) if len(cells) >= 1 else None
        rows.append(
            {
                "transaction_date": parse_date(cells[0]) or "",
                "posted_date": parse_date(cells[1]) or "",
                "description": " ".join(cells[2:-2]).strip(),
                "amount": f"{abs(amount):.2f}" if amount is not None else "",
                "amount_direction": "debit" if amount is not None and amount < 0 else "credit",
                "balance": f"{balance:.2f}" if balance is not None else "",
                "source_page": str(page_index) if page_index else "",
            }
        )
        return rows

    amount_matches = re.findall(r"-?\$?\d[\d,]*\.\d{2}", joined)
    if amount_matches and len(cells) >= 2:
        amount = parse_amount(amount_matches[0])
        rows.append(
            {
                "description": joined,
                "amount": f"{abs(amount):.2f}" if amount is not None else "",
                "amount_direction": "debit" if amount is not None and amount < 0 else "credit",
                "source_page": str(page_index) if page_index else "",
            }
        )
    return rows


def extract_text_with_tesseract(
    pdf_path: str,
    pdf_bytes: bytes | None,
    lang: str,
    psm: str,
) -> str | None:
    try:
        from pdf2image import convert_from_path
        from pdf2image import convert_from_bytes
        import pytesseract
    except Exception:
        return None

    try:
        if pdf_bytes:
            images = convert_from_bytes(pdf_bytes)
        else:
            images = convert_from_path(pdf_path)
    except Exception:
        return None

    ocr_pages: list[str] = []
    for image in images:
        config = f"--psm {psm}" if psm else ""
        ocr_pages.append(pytesseract.image_to_string(image, lang=lang, config=config))
    return "\f".join(ocr_pages)


def parse_with_ollama(
    pdf_path: str,
    pdf_bytes: bytes | None,
    metadata: dict[str, str],
    options: ExtractionOptions,
) -> list[dict[str, str]]:
    try:
        from pdf2image import convert_from_path
        from pdf2image import convert_from_bytes
    except Exception:
        return []

    try:
        if pdf_bytes:
            images = convert_from_bytes(pdf_bytes)
        else:
            images = convert_from_path(pdf_path)
    except Exception:
        return []

    rows: list[dict[str, str]] = []
    for page_index, image in enumerate(images, start=1):
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        prompt = "Table Recognition:"
        payload = {
            "model": options.ollama_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [encoded],
                }
            ],
            "stream": False,
        }
        response = ollama_post(options.ollama_url, payload)
        if not response:
            continue
        content = extract_ollama_content(response)
        if not content:
            continue
        csv_text = extract_csv_from_response(content)
        if csv_text:
            rows.extend(parse_csv_rows(csv_text, page_index))
            continue
        markdown_rows = parse_markdown_tables(content, page_index)
        if markdown_rows:
            rows.extend(markdown_rows)
    return rows


def parse_with_glm_ocr_sdk(
    pdf_path: str,
    pdf_bytes: bytes | None,
    metadata: dict[str, str],
    statement_type: str,
    options: ExtractionOptions,
) -> list[dict[str, str]]:
    try:
        from pdf2image import convert_from_path, convert_from_bytes
    except Exception:
        return []

    try:
        if pdf_bytes:
            images = convert_from_bytes(pdf_bytes)
        else:
            images = convert_from_path(pdf_path)
    except Exception:
        return []

    import tempfile
    import shutil
    import subprocess

    rows: list[dict[str, str]] = []
    if not shutil.which("glmocr"):
        return rows
    for page_index, image in enumerate(images, start=1):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = os.path.join(tmpdir, f"page-{page_index}.png")
            image.save(image_path, format="PNG")

            cmd = ["glmocr", "parse", image_path, "--output", tmpdir]
            if options.glm_ocr_config:
                cmd.extend(["--config", options.glm_ocr_config])
            try:
                subprocess.run(cmd, check=False, capture_output=True)
            except Exception:
                continue

            md_text = ""
            for name in os.listdir(tmpdir):
                if name.lower().endswith((".md", ".txt")):
                    with open(os.path.join(tmpdir, name), "r", encoding="utf-8") as handle:
                        md_text = handle.read()
                        break

            if not md_text:
                continue

            markdown_rows = parse_markdown_tables(md_text, page_index)
            if markdown_rows:
                rows.extend(markdown_rows)
                continue

            text_pages = [md_text]
            rows.extend(parse_transactions_by_type(statement_type, text_pages, metadata, pdf_path, None))

    return rows


def ollama_post(url: str, payload: dict) -> dict | None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def extract_ollama_content(response: dict) -> str | None:
    if "message" in response and isinstance(response["message"], dict):
        content = response["message"].get("content", "")
    else:
        content = response.get("response", "")
    if not content:
        return None
    content = content.strip()
    if "```" in content:
        content = content.split("```", 2)[1]
        content = content.lstrip()
        first_line, _, rest = content.partition("\n")
        if first_line.strip().lower() in {"csv", "markdown", "md", "text", "table"}:
            content = rest
    return content.strip()


def extract_csv_from_response(content: str) -> str | None:
    if not content:
        return None
    if "|" in content and "\n" in content:
        return None
    if "," not in content:
        return None
    return content.strip()


def parse_csv_rows(csv_text: str, page_index: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        cleaned = {k.strip(): (v.strip() if isinstance(v, str) else "") for k, v in row.items()}
        amount = parse_amount(cleaned.get("amount", ""))
        balance = parse_amount(cleaned.get("balance", ""))
        rows.append(
            {
                "transaction_date": cleaned.get("transaction_date", ""),
                "posted_date": cleaned.get("posted_date", ""),
                "description": cleaned.get("description", ""),
                "category": cleaned.get("category", ""),
                "reward": cleaned.get("reward", ""),
                "amount": f"{abs(amount):.2f}" if amount is not None else "",
                "amount_direction": "debit" if amount is not None and amount < 0 else "credit",
                "balance": f"{balance:.2f}" if balance is not None else "",
                "source_page": str(page_index),
            }
        )
    return rows


def parse_markdown_tables(text: str, page_index: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    table_lines: list[str] = []
    for line in lines:
        if line.startswith("|") and line.endswith("|"):
            table_lines.append(line)
        elif table_lines:
            rows.extend(parse_markdown_table_block(table_lines, page_index))
            table_lines = []
    if table_lines:
        rows.extend(parse_markdown_table_block(table_lines, page_index))
    return rows


def parse_markdown_table_block(lines: list[str], page_index: int) -> list[dict[str, str]]:
    if len(lines) < 2:
        return []
    header = [cell.strip().lower() for cell in lines[0].strip("|").split("|")]
    separator = lines[1]
    if not all("-" in cell for cell in separator.strip("|").split("|")):
        return []
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(header):
            continue
        data = dict(zip(header, cells))
        amount = parse_amount(data.get("amount", "") or data.get("withdrawal", "") or data.get("debit", ""))
        balance = parse_amount(data.get("balance", ""))
        rows.append(
            {
                "transaction_date": data.get("transaction date", "") or data.get("date", ""),
                "posted_date": data.get("posted date", "") or data.get("posting date", ""),
                "description": data.get("description", "") or data.get("transaction", ""),
                "category": data.get("category", ""),
                "reward": data.get("reward", ""),
                "amount": f"{abs(amount):.2f}" if amount is not None else "",
                "amount_direction": "debit" if amount is not None and amount < 0 else "credit",
                "balance": f"{balance:.2f}" if balance is not None else "",
                "source_page": str(page_index),
            }
        )
    return rows


def write_csv(path: str, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRANSACTION_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in TRANSACTION_FIELDS})
