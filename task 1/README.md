# Task 1 · FIBIS Archival Scraper

This folder contains an automated pipeline that downloads 10 publicly-available datasets from the FIBIS archival portal (https://search.fibis.org/bin/recordslist.php). Re-running the workflow is safe and idempotent: datasets that already exist are skipped unless `force=True` is passed explicitly.

## Selected datasets (10)

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

Each dataset is saved inside a folder named exactly like the dataset title, and the CSV file inside uses the same name (e.g., `Overseas Births 1852/Overseas Births 1852.csv`).

## How the scraper works

- **Pagination & traversal:** After loading the dataset landing page, the scraper parses the `title="Next"` link to walk through every page until the link disappears.  
- **Table detection:** `pandas.read_html` (via `Task1._extract_primary_table`) reads all tables, scores them by size, removes utility columns such as *View*, and keeps the widest table as the record grid.  
- **Politeness & retries:** A single `requests.Session` is reused, every page fetch goes through `_fetch_with_retries`, and exponential backoff (2s, 4s, 6s) is applied whenever an HTTP error occurs. A one-second pause is also inserted between paginated requests.  
- **Idempotent outputs:** Before scraping, the pipeline checks whether `<Dataset>/<Dataset>.csv` already exists. If so, it logs a *Skipping* message and continues, so interrupted runs can resume instantly.  
- **Error handling:** Network errors, missing tables, and HTML parsing issues are logged with `[!]` messages. The process then stops for that dataset but continues with the next one.

## Reproducing Task 1

1. Activate the virtual environment (if not already active):
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. Run the production scraper:
   ```powershell
   python Task1.py
   ```
3. (Optional) Re-run or inspect the workflow interactively via the notebook:
   ```text
   notebooks/task1_fibis.ipynb
   ```

> **Next steps:** Please add the two sample PDFs for Task 2 and Task 3 to the workspace (or share their exact paths) so I can implement the PDF-to-dataset extractors. Until those files are available, only Task 1 can be demonstrated end-to-end.
