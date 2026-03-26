# Task 3 · Newspaper Matrimonial Ads

`Task3.py` extracts matrimonial content from the sample classifieds PDFs in `task 3/Task 3/ad pdfs/`, consolidates the ads, and writes the results to `task 3/output/`.

## Current outputs
- `task 3/output/task3_ads.csv`
- `task 3/output/task3_ads.xlsx`

The CSV has just been replaced with `task3_matrimonial_ads_AI (1).csv` per the latest instructions. Re-running the script regenerates both files directly from the PDFs.

## How the pipeline works
- **Dual-layer text capture:** Uses PyMuPDF to grab native text; if a page is too sparse, it renders to PNG and runs RapidOCR.
- **Line grouping:** OCR word boxes are clustered by vertical position, sorted left-to-right, and cleaned to form continuous lines.
- **Noise filtering:** Boilerplate such as mastheads or copyright notices is removed with keyword filters.
- **Ad segmentation:** Keyword heuristics (`alliance`, `seeks`, `groom`, etc.) detect ad boundaries with a short grace window to keep trailing descriptors attached.
- **Metadata enrichment:** Publication name, date, and page labels are parsed from the PDF text and stored alongside the ad text.

## Limitations & tuning
- Increase `OCRSettings.zoom` if some scans appear faint.
- Disable `_is_ad_line` filtering if you need every classified line (not only matrimonial ones).
- Duplicate ads are deduplicated case-insensitively; adjust `segment_ads` if near-duplicates must stay separate.
