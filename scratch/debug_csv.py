import sys, os
sys.path.insert(0, 'PEA-Scraper')
import importlib
pea = importlib.import_module('DLDD-MAFF-JDLA')

ext = pea.CSVExtractor()
res = ext.read_and_validate_tabular('scratch/csv_tests/1_investigador_valido.csv')
print("res:", res)
