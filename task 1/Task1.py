import os
import time
from pathlib import Path
from typing import List, Optional

from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests import Response
from urllib.parse import urljoin

# --- Configuration ---
BASE_URL = "https://search.fibis.org/bin/"
OUTPUT_ROOT = Path.cwd()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_SECONDS = 2

# 10 Explicit datasets to bypass the server's anti-scraping menu blocks
DATASETS = [
    {"name": "Overseas Births 1852", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1249&s_id=791"},
    {"name": "Overseas Births 1853", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1266&s_id=791"},
    {"name": "Overseas Births 1854", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1312&s_id=791"},
    {"name": "Overseas Deaths 1843", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=949&s_id=791"},
    {"name": "Overseas Deaths 1844", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=963&s_id=791"},
    {"name": "Overseas Deaths 1845", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1003&s_id=791"},
    {"name": "Overseas Marriages 1843", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=948&s_id=791"},
    {"name": "Overseas Marriages 1844", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=964&s_id=791"},
    {"name": "Overseas Marriages 1845", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1002&s_id=791"},
    {"name": "Z Mutiny List 1857", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1394&s_id=791"},
]


def _sanitize_name(name: str) -> str:
    return name.replace("/", "-").replace("\\", "-").strip()


def _fetch_with_retries(session: requests.Session, url: str) -> Response:
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            sleep_for = BACKOFF_SECONDS * attempt
            print(f"    [!] Attempt {attempt} failed for {url}: {exc}. Retrying in {sleep_for}s")
            time.sleep(sleep_for)
    assert last_error is not None
    raise last_error


def _extract_primary_table(html: str) -> Optional[pd.DataFrame]:
    try:
        tables: List[pd.DataFrame] = pd.read_html(StringIO(html))
    except ValueError:
        return None

    scored = sorted(
        tables,
        key=lambda df: (df.shape[0], df.shape[1]),
        reverse=True,
    )

    for table in scored:
        table = table.loc[:, ~table.columns.astype(str).str.contains("View|Unnamed", case=False, na=False)]
        if table.shape[1] >= 3:
            return table
    return None


def scrape_dataset(
    dataset_name: str,
    start_url: str,
    output_root: Path = OUTPUT_ROOT,
    *,
    session: Optional[requests.Session] = None,
    force: bool = False,
) -> bool:
    current_url = start_url
    collected: List[pd.DataFrame] = []
    safe_name = _sanitize_name(dataset_name)
    session = session or requests.Session()
    output_dir = output_root / dataset_name
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{safe_name}.csv"

    if file_path.exists() and not force:
        print(f"    [=] Skipping {dataset_name}; existing dataset found at {file_path}")
        return True

    while current_url:
        try:
            response = _fetch_with_retries(session, current_url)
        except requests.RequestException as exc:
            print(f"    [!] Aborting {dataset_name}: {exc}")
            break

        table = _extract_primary_table(response.text)
        if table is None:
            print(f"    [!] No table detected on {current_url}")
            break
        collected.append(table)

        soup = BeautifulSoup(response.text, "html.parser")
        next_tag = soup.find("a", title="Next")
        if next_tag and next_tag.get("href"):
            current_url = urljoin(BASE_URL, next_tag["href"])
            time.sleep(1)
        else:
            current_url = None

    if not collected:
        return False

    final_df = pd.concat(collected, ignore_index=True)
    final_df.dropna(how="all", inplace=True)
    final_df.to_csv(file_path, index=False)
    print(f"    [+] Saved {dataset_name} -> {file_path} ({len(final_df)} rows)")
    return True


def main() -> None:
    print("Starting FIBIS Scraper Pipeline...")
    success_count = 0
    session = requests.Session()

    for dataset in DATASETS:
        name = dataset["name"]
        print(f"\nScraping dataset: {name}")
        if scrape_dataset(name, dataset["url"], session=session, force=False):
            success_count += 1

    print(f"\n✅ Task 1 Complete! Successfully generated {success_count} datasets.")


if __name__ == "__main__":
    main()