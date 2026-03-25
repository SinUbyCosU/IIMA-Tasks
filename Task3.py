"""Task 3 · Newspaper ad OCR pipeline.

This script renders each classified-ad PDF page to an image,
feeds it through RapidOCR, and converts the detected text
boxes into consolidated matrimonial ad strings. The final
records are saved as CSV and XLSX files under task 3/output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Literal
from io import BytesIO
import time
import numpy as np
from PIL import Image

import fitz
import pandas as pd
from pypdf import PdfReader
from rapidocr_onnxruntime import RapidOCR

PDF_DIR = Path("task 3/Task 3/ad pdfs")
OUTPUT_DIR = Path("task 3/output")
NOISE_PATTERNS = (
    "Reproduced with permission",
    "The Times of India",
    "Historical Newspapers",
    "Classified Ad",
    "Further reproduction prohibited",
)


@dataclass
class OCRSettings:
    zoom: float = 2.0
    y_tolerance: float = 14.0
    native_min_chars: int = 150
    backend: Literal["paddle", "rapid"] = "rapid"


class TextRecognizer:
    def __init__(self, backend: str) -> None:
        backend = backend.lower()
        if backend == "paddle":
            try:
                from paddleocr import PaddleOCR  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "paddleocr is not installed. Run 'pip install paddleocr' or switch backend to 'rapid'."
                ) from exc
            self.backend = "paddle"
            self.engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        elif backend == "rapid":
            self.backend = "rapid"
            self.engine = RapidOCR()
        else:
            raise ValueError("Unsupported OCR backend")

    def run(self, image_bytes: bytes) -> List[Sequence]:
        if self.backend == "paddle":
            with Image.open(BytesIO(image_bytes)) as img:
                rgb = np.array(img.convert("RGB"))
            # PaddleOCR returns list per page; we need RapidOCR-like tuples
            result = self.engine.ocr(rgb, cls=True)
            formatted: List[Sequence] = []
            for page in result or []:
                for box, (text, score) in page:
                    formatted.append((box, text, score))
            return formatted
        else:
            result, _ = self.engine(image_bytes)
            return result or []


def main() -> None:
    if not PDF_DIR.exists():
        raise FileNotFoundError(f"Expected PDF directory at {PDF_DIR}")

    settings = OCRSettings()
    recognizer = TextRecognizer(settings.backend)
    start_time = time.perf_counter()

    records: List[Dict[str, Optional[str]]] = []
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        print(f"[+] Parsing {pdf_path.name}")
        ad_id = parse_ad_id(pdf_path.stem)
        publication, pub_date, page_label = extract_metadata(pdf_path)
        ads = extract_ads(pdf_path, recognizer, settings)
        if not ads:
            print(f"    [!] No matrimonial content detected in {pdf_path.name}")
        for idx, ad_text in enumerate(ads, start=1):
            record_id = f"{ad_id}-{idx}" if ad_id is not None else f"{pdf_path.stem}-{idx}"
            records.append(
                {
                    "ad_id": record_id,
                    "source_pdf": str(pdf_path),
                    "publication": publication,
                    "publication_date": pub_date,
                    "page": page_label,
                    "ad_text": ad_text,
                }
            )

    if not records:
        raise RuntimeError("No ads were parsed. Please verify the PDF inputs.")

    df = pd.DataFrame(records).sort_values("ad_id")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "task3_ads.csv"
    xlsx_path = OUTPUT_DIR / "task3_ads.xlsx"
    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False)
    print(f"Parsed {len(df)} ads")
    print(f"CSV : {csv_path}")
    print(f"XLSX: {xlsx_path}")
    elapsed = time.perf_counter() - start_time
    print(f"Completed in {elapsed:.1f} seconds")


def extract_ads(pdf_path: Path, recognizer: TextRecognizer, settings: OCRSettings) -> List[str]:
    doc = fitz.open(pdf_path)
    lines: List[str] = []
    for index, page in enumerate(doc, start=1):
        native_text = extract_native_page_text(page)
        if native_text and is_useful_native_text(native_text, settings):
            lines.append(native_text)
            continue

        png_bytes = render_page(page, settings.zoom)
        result = recognizer.run(png_bytes)
        if not result:
            continue
        page_lines = layout_lines(result, settings.y_tolerance)
        for line in page_lines:
            if is_noise(line):
                continue
            lines.append(line)
        print(f"    [OCR] {pdf_path.name} page {index}: {len(page_lines)} lines")
    return segment_ads(lines)


def render_page(page: fitz.Page, zoom: float) -> bytes:
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return pix.tobytes("png")


def layout_lines(result: Sequence[Sequence], y_tol: float) -> List[str]:
    spans: List[Tuple[float, float, str]] = []
    for box, text, score in result:
        if not text.strip():
            continue
        y_center = sum(point[1] for point in box) / len(box)
        x_min = min(point[0] for point in box)
        spans.append((y_center, x_min, text.strip()))

    spans.sort(key=lambda item: (item[0], item[1]))

    grouped: List[Dict[str, object]] = []
    for y, x, text in spans:
        if not grouped or abs(grouped[-1]["y"] - y) > y_tol:
            grouped.append({"y": y, "segments": [(x, text)]})
        else:
            grouped[-1]["segments"].append((x, text))

    lines: List[str] = []
    for group in grouped:
        segments = sorted(group["segments"], key=lambda seg: seg[0])
        raw_line = " ".join(segment[1] for segment in segments)
        lines.append(clean_line(raw_line))
    return [line for line in lines if line]


def clean_line(text: str) -> str:
    normalized = text.replace("\u2019", "'").replace("\u2018", "'")
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = re.sub(r"-\s+(?=[A-Za-z])", "", normalized)
    normalized = re.sub(r"\s+/\s+", "/", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def is_noise(line: str) -> bool:
    return any(pattern.lower() in line.lower() for pattern in NOISE_PATTERNS)


def extract_native_page_text(page: fitz.Page) -> Optional[str]:
    text = page.get_text("text", sort=True)
    if not text:
        return None
    lines = []
    for raw_line in text.splitlines():
        cleaned = clean_line(raw_line)
        if not cleaned or is_noise(cleaned):
            continue
        lines.append(cleaned)
    return " ".join(lines) if lines else None


def is_useful_native_text(text: str, settings: OCRSettings) -> bool:
    if len(text) < settings.native_min_chars:
        return False
    if text.lower().startswith("pg. "):
        return False
    return True


AD_KEYWORDS = (
    "seeks",
    "seeking",
    "alliance",
    "wanted",
    "match",
    "groom",
    "bride",
    "boy",
    "girl",
    "marriage",
    "matrimonial",
    "nm",
    "sm",
    "pqm",
    "handsome",
    "fair",
    "b'tech",
    "b.tech",
    "engineer",
    "mba",
    "doctor",
)


def segment_ads(lines: List[str]) -> List[str]:
    ads: List[str] = []
    current: List[str] = []
    grace = 0

    for raw in lines:
        line = raw.strip()
        if not line:
            if current:
                ads.append(_finalize_ad(current))
                current = []
                grace = 0
            continue

        if _is_ad_line(line):
            current.append(line)
            grace = 2
        elif current and grace > 0:
            current.append(line)
            grace -= 1
        else:
            if current:
                ads.append(_finalize_ad(current))
                current = []
                grace = 0

    if current:
        ads.append(_finalize_ad(current))

    unique_ads = []
    seen = set()
    for ad in ads:
        key = ad.lower()
        if len(ad) < 40 or key in seen:
            continue
        seen.add(key)
        unique_ads.append(ad)
    return unique_ads


def _is_ad_line(line: str) -> bool:
    normalized = line.lower()
    return any(token in normalized for token in AD_KEYWORDS)


def _finalize_ad(chunks: List[str]) -> str:
    text = " ".join(chunks)
    text = re.sub(r"\s+", " ", text)
    text = text.replace(" ,", ",").strip()
    return text


def extract_metadata(pdf_path: Path) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    reader = PdfReader(pdf_path)
    text = " ".join(filter(None, (page.extract_text() for page in reader.pages)))
    publication = "The Times of India" if "Times of India" in text else None
    date_match = re.search(r";\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", text)
    page_match = re.search(r"pg\.\s*([A-Za-z0-9]+)", text)
    date_value = date_match.group(1) if date_match else None
    page_value = page_match.group(1) if page_match else None
    return publication, date_value, page_value


def parse_ad_id(stem: str) -> Optional[int]:
    match = re.search(r"(\d+)", stem)
    return int(match.group(1)) if match else None


if __name__ == "__main__":
    main()
