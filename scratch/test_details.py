import sys, os, json
sys.path.insert(0, 'PEA-Scraper')
import importlib
pea = importlib.import_module('DLDD-MAFF-JDLA')

ext = pea.CSVExtractor()
ok, data, msg = ext.extract('scratch/csv_tests/2_grupo_integrantes.csv')
print("2_grupo_integrantes.csv data:", json.dumps(data, indent=2, ensure_ascii=False))

ok, data, msg = ext.extract('scratch/csv_tests/3_productos_win1252.csv')
print("3_productos_win1252.csv data:", json.dumps(data, indent=2, ensure_ascii=False))
