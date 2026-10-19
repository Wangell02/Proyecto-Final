import sys
import os
import re

sys.path.insert(0, "PEA-Scraper")
import importlib.util
spec = importlib.util.spec_from_file_location("dldd", "PEA-Scraper/DLDD-MAFF-JDLA.py")
dldd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dldd)

canonical_key = dldd.canonical_key
clean_text = dldd.clean_text
serialize_result = dldd.serialize_result
serialize_error = dldd.serialize_error

from test_improved_extractor import ImprovedPDFExtractor

ext = ImprovedPDFExtractor()
pdf_adith = r"C:\Users\camil\Desktop\Aith Bismarck.pdf"

print("--- PRUEBA 1: PDF ADITH BISMARCK ---")
text = ext.extract_text(pdf_adith)
val = ext.verify_gatekeeper(text)
print("Gatekeeper valido:", val)
tipo, segs = ext.partition_document(text)
print("Tipo:", tipo, "| Total segmentos:", len(segs))
inv = ext.parse_investigator(segs[0]["texto"])
print("Nombre:", inv["nombre"])
print("Categoria:", inv["categoriaInvestigador"])
print("Total productos:", len(inv["productos"]))

tsv = serialize_result(inv)
print("Lineas TSV generadas:", len(tsv.splitlines()))
print("Primeras 10 lineas TSV:")
for l in tsv.splitlines()[:10]:
    print(" ", repr(l))

print("\n--- PRUEBA 2: SOLICITUD DE PERMISO ---")
pdf_sol = r"C:\Users\camil\Downloads\Solicitud de Permisos.pdf"
text_sol = ext.extract_text(pdf_sol)
val_sol = ext.verify_gatekeeper(text_sol)
print("Gatekeeper valido:", val_sol)
if not val_sol:
    err_tsv = serialize_error("El archivo no corresponde a un documento oficial de MinCiencias (CvLAC o GrupLAC).")
    print("TSV de error:")
    print(err_tsv)
