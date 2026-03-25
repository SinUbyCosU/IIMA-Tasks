import fitz
import sys

doc = fitz.open(r"task 2/Task 2/task2.pdf")
page_index = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else 7
page = doc.load_page(page_index)
print("page", page_index + 1)
print("-- blocks --")
for block in page.get_text("blocks"):
    x0, y0, x1, y1, text, block_no, block_type = block
    clean = text.strip().replace("\n", " | ")
    if not clean:
        continue
    print(f"block {block_no:02d} ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}): {clean[:200]}")

target_blocks = {6, 8}
print("\n-- spans in target blocks --")
page_dict = page.get_text("dict")
for block in page_dict["blocks"]:
    if block.get("number") not in target_blocks:
        continue
    print(f"block #{block['number']}")
    if "lines" not in block:
        continue
    for line in block["lines"]:
        for span in line["spans"]:
            x0, y0, x1, y1 = span["bbox"]
            text = span["text"].strip()
            if not text:
                continue
            print(f"span ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}): {text}")

words = page.get_text("words")
print("\nSample words (block_no, line_no, text):")
for w in words[:20]:
    x0, y0, x1, y1, text, block_no, line_no, word_no = w
    print(f"block {block_no:02d} line {line_no:02d} word {word_no:02d} @({x0:.1f},{y0:.1f}): {text}")
