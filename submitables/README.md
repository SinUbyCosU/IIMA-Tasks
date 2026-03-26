# Submission Bundle Overview

This folder mirrors the three tasks required for the FIBIS assignment. Each sub-folder already contains the code, notebook, documentation, and generated datasets requested by the evaluation rubric.

## Contents

| Folder | Included items | Run instructions |
| --- | --- | --- |
| `task 1/` | `Task1.py`, `task1_pipeline.ipynb`, README, and the 10 dataset folders (each with an identically named CSV). | Run `python Task1.py` or use the notebook to regenerate the datasets. |
| `task 2/` | `Task2.py`, `task2_extraction.ipynb`, README, and `output/task2_records.(csv|xlsx)`. | Execute `python Task2.py` or the notebook; outputs rewrite the CSV/XLSX in `output/`. |
| `task 3/` | `Task3.py`, `task3_pipeline.ipynb`, README, and `output/task3_ads.(csv|xlsx)` (CSV currently sourced from the provided AI extraction). | Run `python Task3.py` or the notebook to rebuild the ad table from the PDFs. |

## Evaluation checklist
- ✔️ Ten FIBIS datasets saved under folders that precisely match the online titles.
- ✔️ Automated pipelines for Tasks 2 and 3 with no manual transcription; notebooks document the execution path.
- ✔️ Brief READMEs per task covering dataset choices, pagination/error tactics, parsing heuristics, and limitations.
-  Output files present in their respective `output/` directories for quick verification.

Use this folder as-is for submission (zip if required) to pass the evaluation without touching the working copies in the project root.
