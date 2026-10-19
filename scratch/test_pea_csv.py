import sys, os
sys.path.insert(0, 'PEA-Scraper')
import importlib
pea = importlib.import_module('DLDD-MAFF-JDLA')

ext = pea.CSVExtractor()
test_dir = 'scratch/csv_tests'
files = sorted([f for f in os.listdir(test_dir) if f.endswith('.csv')])

print("Running tests on CSV files:")
for fname in files:
    fpath = os.path.join(test_dir, fname)
    ok, data, msg = ext.extract(fpath)
    invs = len(data.get('investigadores', [])) if data else 0
    grps = len(data.get('grupos', [])) if data else 0
    prods = len(data.get('productos', [])) if data else 0
    print(f"[{fname}] ok={ok} invs={invs} grps={grps} prods={prods} msg={msg}")
