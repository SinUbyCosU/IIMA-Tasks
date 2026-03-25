import pdfplumber

with pdfplumber.open(r"task 2/Task 2/task2.pdf") as pdf:
    page = pdf.pages[49]
    lines = page.extract_text(layout=True).splitlines()
    header = next(line for line in lines if "Station." in line and "Substantive" in line)
    print(header)
    print("".join(str(i//10 % 10) if i % 10 == 0 else " " for i in range(len(header))))
    print("".join(str(i % 10) for i in range(len(header))))
    cols = {
        "station_start": header.index("Station."),
        "substantive_start": header.index("Substantive"),
        "date1_start": header.index("Date."),
        "off_app_start": header.index("Officiating"),
        "date2_start": header.rindex("Date")
    }
    print(cols)
