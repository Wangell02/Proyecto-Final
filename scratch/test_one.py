import sys, io, csv
sys.path.insert(0, 'PEA-Scraper')
import importlib
pea = importlib.import_module('DLDD-MAFF-JDLA')

file_path = 'scratch/csv_tests/1_investigador_valido.csv'
with open(file_path, 'rb') as f:
    raw = f.read()

text = raw.decode('utf-8-sig')
print("Text:", repr(text))
ext = pea.CSVExtractor()
delimiters = [',', ';']
for d in delimiters:
    try:
        reader = csv.reader(io.StringIO(text), delimiter=d, quotechar='"')
        rows = []
        for r in reader:
            row_clean = [pea.clean_text(cell) for cell in r]
            if any(len(c) > 0 for c in row_clean):
                rows.append(row_clean)
        print("Delim:", d, "rows:", len(rows))
        if len(rows) >= 2:
            header = rows[0]
            print("header:", header, "len:", len(header))
            data_rows = rows[1:]
            consistent_count = 0
            for dr in data_rows:
                if len(dr) == len(header):
                    consistent_count += 1
            print("consistent:", consistent_count)
    except Exception as e:
        print("Exc:", e)

res = ext.read_and_validate_tabular(file_path)
print("Result:", res)
