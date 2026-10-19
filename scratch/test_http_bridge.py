import sys
import os
import json
import threading
import time
import urllib.request

sys.path.insert(0, 'PEA-Scraper')
import importlib
pea = importlib.import_module('DLDD-MAFF-JDLA')

def test_bridge():
    svc = pea.ApplicationService()
    server = pea.LocalAPIServer(svc, host="127.0.0.1", port=8766) # Use 8766 for isolated test
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(1)

    try:
        url = "http://127.0.0.1:8766/cargar-archivo"
        
        # Test 1: Cargar CSV valido de investigador
        payload = json.dumps({
            "tipoArchivo": "csv",
            "ruta": os.path.abspath("scratch/csv_tests/1_investigador_valido.csv")
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            print("Response 1:", data[:120])
            assert "ESTADO\tOK" in data
            assert "INVESTIGADOR\t0000123456" in data

        # Test 2: Cargar CSV generico rechazado
        payload2 = json.dumps({
            "tipoArchivo": "csv",
            "ruta": os.path.abspath("scratch/csv_tests/5_generico_rechazado.csv")
        }).encode("utf-8")
        req2 = urllib.request.Request(url, data=payload2, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req2) as resp:
            data2 = resp.read().decode("utf-8")
            print("Response 2:", data2[:120])
            assert "ESTADO\tERROR" in data2
            assert "MinCiencias" in data2

        print("ALL HTTP Bridge Tests Passed Successfully!")
    finally:
        server.shutdown()

if __name__ == '__main__':
    test_bridge()
