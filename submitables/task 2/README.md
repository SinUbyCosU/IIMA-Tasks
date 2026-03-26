# Task 2 · PDF-to-dataset Extraction

`Task2.py` converts the sample “History of Services” PDF into structured station records and writes both CSV and XLSX outputs to `task 2/output/`.

## How to rerun
1. Ensure `pdfplumber`, `pandas`, and supporting packages are installed.
2. From the repo root run `python Task2.py`.
3. Inspect the regenerated files in `task 2/output/task2_records.csv` and `task 2/output/task2_records.xlsx`.

## Parsing highlights
- **Header normalization:** Cleans merged words, punctuation glitches, and extracts name, honorific, education, birth/joining/arrival dates, and voted/non-voted flags via targeted regex.
- **Column slicing:** Column boundaries are derived from the table heading so the station/appointment columns stay aligned even when spacing drifts.
- **Repeat values:** Tokens such as “Do.” reuse the previous station or appointment.
- **Multi-line handling:** Continuation lines append to the active row, preserving hyphenated breaks.
- **Date repair:** Two-digit years are expanded relative to a pivot, and ambiguous digits (O/0, I/1) are normalized to ISO `YYYY-MM-DD` strings.

## Assumptions & edge cases
- The provided PDF follows the same template for all pages; radically different layouts get logged and skipped.
- Rows without any text or dates are ignored to avoid headers and separators entering the dataset.
- When a header cannot be parsed confidently, the script logs a warning but continues with the next entry.
