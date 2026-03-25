import pdfplumber

with pdfplumber.open(r"task 2/Task 2/task2.pdf") as pdf:
    page = pdf.pages[7]
    lines = page.extract_text(layout=True).splitlines()
    for idx, line in enumerate(lines):
        if "service" in line:
            snippet = lines[idx:idx+5]
            print("-- snippet --")
            print("\n".join(snippet))
