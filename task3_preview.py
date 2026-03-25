from pathlib import Path
from pypdf import PdfReader

root = Path('task 3/Task 3/ad pdfs')
for path in sorted(root.glob('*.pdf'))[:3]:
    reader = PdfReader(path)
    text = ' '.join(filter(None, (page.extract_text() or '' for page in reader.pages)))
    print('=' * 60)
    print(path.name)
    print('chars:', len(text))
    print(text[:800])
