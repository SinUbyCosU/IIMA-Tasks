# Task 1 · FIBIS Archival Scraper

Automates the download of ten public datasets from https://search.fibis.org/bin/recordslist.php. The job list is hard-coded in `Task1.py` to avoid manual browsing blocks, and each dataset is stored inside a folder whose name exactly matches the dataset title.

## Selected datasets
1. Overseas Births 1852
2. Overseas Births 1853
3. Overseas Births 1854
4. Overseas Deaths 1843
5. Overseas Deaths 1844
6. Overseas Deaths 1845
7. Overseas Marriages 1843
8. Overseas Marriages 1844
9. Overseas Marriages 1845
10. Z Mutiny List 1857

## Running the scraper
1. (Optional) recreate a virtual env and install requirements from `requirements.txt` if available.
2. Execute `python Task1.py` from the repo root.
3. The script skips folders that already contain a CSV file named after the dataset, so reruns are idempotent. Pass `force=True` to `scrape_dataset` inside the script to override.

## Pagination, limits, and errors
- Each dataset page is fetched with a shared `requests.Session`, and `_fetch_with_retries` applies exponential back-off (2s, 4s, 6s) on HTTP failures.
- Pagination follows the `title="Next"` link until it disappears.
- `_extract_primary_table` scores tables by row/column count, drops action columns such as “View”, and keeps the widest grid.
- Empty or failed pages log `[!]` messages; the dataset is skipped but the pipeline continues with the next entry.
- Output folders live under `task 1/` and already contain the ten CSVs required for submission.
