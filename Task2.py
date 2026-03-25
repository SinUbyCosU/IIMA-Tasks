"""Task 2 PDF-to-dataset extractor.

This script reads the historical "History of Services" PDF (Task 2),
converts the officer roster into a structured tabular dataset, and saves
both CSV and XLSX outputs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pdfplumber

PDF_PATH = Path("task 2/Task 2/task2.pdf")
OUTPUT_DIR = Path("task 2/output")

METADATA_FIELDS = [
    "Full Name",
    "Educational Qualification",
    "Honorific/Title",
    "Date of Birth",
    "Date of Joining Service",
    "Date of Arrival",
    "Voted/Non-voted",
    "Domicile",
]
ROW_FIELDS = [
    "Station",
    "Substantive Appointment",
    "Subst. Date",
    "Officiating Appointment",
    "Off. Date",
]
REPEATERS = {"Do", "Do.", "do", "do."}


@dataclass
class ColumnBounds:
    station: Tuple[int, int]
    substantive: Tuple[int, int]
    subst_date: Tuple[int, int]
    off_app: Tuple[int, int]
    off_date: Tuple[int, int]


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Missing PDF at {PDF_PATH}")

    rows = extract_rows(PDF_PATH)
    if not rows:
        raise RuntimeError("Parser returned zero rows; please inspect the PDF layout.")

    df = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "task2_records.csv"
    xlsx_path = OUTPUT_DIR / "task2_records.xlsx"
    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False)
    print(f"Parsed {len(df)} station records")
    print(f"CSV : {csv_path}")
    print(f"XLSX: {xlsx_path}")


def extract_rows(pdf_path: Path) -> List[Dict[str, Optional[str]]]:
    rows: List[Dict[str, Optional[str]]] = []
    column_bounds: Optional[ColumnBounds] = None

    current_officer: Optional[Dict[str, Optional[str]]] = None
    header_buffer: List[str] = []
    collecting_header = False
    table_active = False

    current_row: Optional[Dict[str, Optional[str]]] = None
    last_station = ""
    last_substantive = ""
    last_off = ""

    previous_line = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(layout=True) or ""
            lines = text.splitlines()

            for line in lines:
                raw_line = line.rstrip("\n")
                normalized_line = raw_line.replace("\u2002", " ")

                looks_like_header = ("—" in normalized_line) or ("—" in previous_line) or ("," in normalized_line) or ("," in previous_line)
                if "Joined" in normalized_line and "service" in normalized_line.replace(" ", "") and looks_like_header:
                    if current_row:
                        rows.append(current_row)
                        current_row = None
                    collecting_header = True
                    table_active = False
                    header_buffer = []
                    if previous_line.strip():
                        header_buffer.append(previous_line)
                    header_buffer.append(normalized_line)
                    continue

                if collecting_header:
                    header_buffer.append(normalized_line)
                    if "Domicile" in normalized_line or "Domiciled" in normalized_line or "Station." in normalized_line:
                        try:
                            current_officer = parse_header(" ".join(header_buffer))
                            last_station = ""
                            last_substantive = ""
                            last_off = ""
                        except ValueError as exc:
                            print(f"[!] Skipping malformed header: {exc}")
                            current_officer = None
                            table_active = False
                        collecting_header = False
                    if "Station." in normalized_line:
                        table_active = True
                    continue

                if "Station." in normalized_line and "Substantive" in normalized_line:
                    if column_bounds is None:
                        column_bounds = derive_column_bounds(normalized_line)
                    table_active = True
                    continue

                if not table_active or current_officer is None or column_bounds is None:
                    continue

                segments = slice_columns(normalized_line, column_bounds)
                if not any(segments.values()):
                    continue

                is_new_row = bool(
                    segments["station"].strip() or _has_digits(segments["subst_date"]) or _has_digits(segments["off_date"])
                )

                if is_new_row:
                    if current_row:
                        rows.append(current_row)
                    current_row = {field: current_officer.get(field) for field in METADATA_FIELDS}
                    current_row.update({field: None for field in ROW_FIELDS})

                    station_val = resolve_repeater(clean_cell(segments["station"]), last_station)
                    substantive_val = resolve_repeater(clean_cell(segments["substantive"]), last_substantive)
                    off_val = resolve_repeater(clean_cell(segments["off_app"]), last_off)

                    current_row["Station"] = station_val or last_station or None
                    current_row["Substantive Appointment"] = substantive_val or last_substantive or None
                    current_row["Subst. Date"] = normalize_date(segments["subst_date"], pivot=50)
                    current_row["Officiating Appointment"] = off_val or last_off or None
                    current_row["Off. Date"] = normalize_date(segments["off_date"], pivot=50)

                    if station_val:
                        last_station = station_val
                    if substantive_val:
                        last_substantive = substantive_val
                    if off_val:
                        last_off = off_val
                else:
                    if not current_row:
                        continue
                    if segments["station"].strip():
                        current_row["Station"] = append_fragment(current_row.get("Station"), clean_cell(segments["station"]))
                        last_station = current_row["Station"] or last_station
                    if segments["substantive"].strip():
                        current_row["Substantive Appointment"] = append_fragment(
                            current_row.get("Substantive Appointment"), clean_cell(segments["substantive"])
                        )
                        last_substantive = current_row["Substantive Appointment"] or last_substantive
                    if segments["subst_date"].strip() and not current_row.get("Subst. Date"):
                        current_row["Subst. Date"] = normalize_date(segments["subst_date"], pivot=50)
                    if segments["off_app"].strip():
                        current_row["Officiating Appointment"] = append_fragment(
                            current_row.get("Officiating Appointment"), clean_cell(segments["off_app"])
                        )
                        last_off = current_row["Officiating Appointment"] or last_off
                    if segments["off_date"].strip() and not current_row.get("Off. Date"):
                        current_row["Off. Date"] = normalize_date(segments["off_date"], pivot=50)

                previous_line = normalized_line

    if current_row:
        rows.append(current_row)

    return rows


def derive_column_bounds(header_line: str) -> ColumnBounds:
    station_start = header_line.index("Station.")
    substantive_start = header_line.index("Substantive")
    date1_start = header_line.index("Date.")
    off_app_start = header_line.index("Officiating")
    date2_start = header_line.rindex("Date")

    return ColumnBounds(
        station=(station_start, substantive_start),
        substantive=(substantive_start, date1_start),
        subst_date=(date1_start, off_app_start),
        off_app=(off_app_start, date2_start),
        off_date=(date2_start, len(header_line) + 10),
    )


def slice_columns(line: str, bounds: ColumnBounds) -> Dict[str, str]:
    padded = line.ljust(bounds.off_date[1])
    return {
        "station": padded[bounds.station[0]:bounds.station[1]],
        "substantive": padded[bounds.substantive[0]:bounds.substantive[1]],
        "subst_date": padded[bounds.subst_date[0]:bounds.subst_date[1]],
        "off_app": padded[bounds.off_app[0]:bounds.off_app[1]],
        "off_date": padded[bounds.off_date[0]:bounds.off_date[1]],
    }


def parse_header(blob: str) -> Dict[str, Optional[str]]:
    clean = blob
    clean = re.sub(r"Joined\s*the\s*service", "Joined the service", clean, flags=re.IGNORECASE)
    clean = re.sub(r"Joined\s*theservice", "Joined the service", clean, flags=re.IGNORECASE)
    clean = re.sub(r"Joined\s*th.?service", "Joined the service", clean, flags=re.IGNORECASE)
    clean = clean.replace(".—", "—")
    clean = clean.replace("Born.", "Born ")
    clean = clean.replace("arrvied", "arrived")
    clean = re.sub(r"\bBom\b", "Born", clean)
    clean = clean.replace(";arrived", "; arrived")
    clean = re.sub(r"\s+", " ", clean)
    clean = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", clean)
    clean = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", clean)
    clean = re.sub(r"Bom(?=\s*\d)", "Born", clean)

    def _clip(value: str) -> str:
        parts = re.split(r"(?:[;,]|\(|$)", value, maxsplit=1)
        return parts[0].strip()

    join_match = re.search(
        r"Joined the service\s+(?P<join>.+?)(?=\s*(?:[;,]|arrived|date of|but|Born|\(|$))",
        clean,
        flags=re.IGNORECASE,
    )
    born_match = re.search(r"Born\s+(?P<born>[^.)]+)", clean, flags=re.IGNORECASE)

    if not join_match or not born_match:
        raise ValueError(f"Could not parse header fragment after normalization: {clean!r}")

    prefix = clean[: join_match.start()].strip().rstrip("-—–, .")
    honorific, name_part = extract_honorific(prefix)
    full_name, education = split_name_and_education(name_part)

    between = clean[join_match.end() : born_match.start()]
    arrive_match = re.search(
        r"arrived\s+(?P<arrive>.+?)(?=\s*(?:[;,]|Born|date of|\(|$))",
        between,
        flags=re.IGNORECASE,
    )

    tail = clean[born_match.end() :].strip()
    votes, domicile = extract_parenthetical_fields(tail)

    join_value = _clip(join_match.group("join"))
    arrive_value = _clip(arrive_match.group("arrive")) if arrive_match else None
    born_value = _clip(born_match.group("born"))

    return {
        "Full Name": full_name,
        "Educational Qualification": education or None,
        "Honorific/Title": honorific or None,
        "Date of Birth": normalize_date(born_value, pivot=50, birth=True),
        "Date of Joining Service": normalize_date(join_value, pivot=50),
        "Date of Arrival": normalize_date(arrive_value or "", pivot=50),
        "Voted/Non-voted": votes,
        "Domicile": domicile,
    }


def extract_parenthetical_fields(tail: str) -> Tuple[Optional[str], Optional[str]]:
    parts = re.findall(r"\(([^)]+)\)", tail)
    if not parts:
        return None, None
    votes = parts[0].strip()
    domicile = parts[1].strip() if len(parts) > 1 else None
    return votes or None, domicile or None


def extract_honorific(prefix: str) -> Tuple[Optional[str], str]:
    pattern = re.compile(r"((?:[A-Z]{1,4}\. ?)+)$")
    match = pattern.search(prefix)
    if match:
        honorific = match.group(1).replace(" ", "").strip()
        name_part = prefix[: match.start()].strip().rstrip(",")
        return honorific, name_part
    return None, prefix


def split_name_and_education(pre: str) -> Tuple[str, Optional[str]]:
    tokens = [restore_token(tok) for tok in pre.split(",") if tok.strip()]
    idx = next((i for i, tok in enumerate(tokens) if "." in tok or re.search(r"(Honours|Oxon|Cantab|Allahabad|Punjab|Bombay|Calcutta|Madras)", tok, re.IGNORECASE)), len(tokens))
    name_tokens = tokens[:idx] or tokens
    edu_tokens = tokens[idx:]
    full_name = ", ".join(name_tokens).strip()
    education = ", ".join(edu_tokens).strip()
    return full_name, education or None


def resolve_repeater(value: Optional[str], previous: str) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip("., ")
    if cleaned in REPEATERS:
        return previous or None
    return value.strip() or None


def clean_cell(text: str) -> Optional[str]:
    stripped = text.strip()
    if not stripped:
        return None
    stripped = stripped.replace("..", " ").replace("—", "-")
    stripped = re.sub(r"(?<=\w)-(?=\w)", "", stripped)
    stripped = re.sub(r"\s+", " ", stripped)
    stripped = restore_token(stripped)
    return stripped.strip() or None


def append_fragment(base: Optional[str], addition: Optional[str]) -> Optional[str]:
    if not addition:
        return base
    if not base:
        return addition
    if base.endswith("-"):
        return (base[:-1] + addition.lstrip()) or None
    return (base + " " + addition).strip()


def normalize_date(raw: str, *, pivot: int, birth: bool = False) -> Optional[str]:
    text = raw.strip().replace("*", "-").replace(".", "-").replace(" ", "-")
    text = text.replace("l", "1").replace("I", "1").replace("O", "0")
    text = re.sub(r"[^0-9-]", "", text)
    if not text:
        return None
    parts = [p for p in text.split("-") if p]
    if len(parts) != 3:
        return None
    day, month, year = parts
    if len(year) == 2:
        year_val = int(year)
        century = 1800 if year_val >= pivot else 1900
        if birth and century == 1900 and year_val >= 30:
            century = 1800
        year = f"{century + year_val:04d}"
    day = f"{int(day):02d}"
    month = f"{int(month):02d}"
    return f"{year}-{month}-{day}"


def restore_token(token: str) -> str:
    token = token.strip()
    token = re.sub(r"\.(?=[A-Za-z])", ". ", token)
    token = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", token)
    token = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", token)
    token = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", token)
    token = token.replace("  ", " ")
    return token.strip()


def _has_digits(text: str) -> bool:
    return bool(re.search(r"\d", text))


if __name__ == "__main__":
    main()
