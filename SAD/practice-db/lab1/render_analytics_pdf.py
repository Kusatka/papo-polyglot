"""Растеризация экспортированных Word PDF для постраничной проверки."""
from pathlib import Path
import pymupdf

root = Path(__file__).resolve().parent
for number in [2, 3]:
    out = root.parent.parent / 'tmp' / f'qa-lab{number}'
    out.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(root / f'Отчёт_Лабораторная_{number}.pdf') as doc:
        print(f'lab{number}: {len(doc)} pages')
        for index, page in enumerate(doc, 1):
            page.get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2)).save(out / f'page-{index}.png')
