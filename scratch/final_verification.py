import sys
import os
import time

sys.path.insert(0, os.path.abspath("PEA-Scraper"))
import importlib.util
spec = importlib.util.spec_from_file_location("dldd", "PEA-Scraper/DLDD-MAFF-JDLA.py")
dldd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dldd)

service = dldd.ApplicationService()
# Recordar mtime de archivos json
mtime_inv = os.path.getmtime("PEA-Scraper/investigadores.json")
mtime_grp = os.path.getmtime("PEA-Scraper/grupos.json")

print("=== PRUEBA 1: PDF VALIDO (CvLAC Adith Bismarck) ===")
pdf_adith = r"C:\Users\camil\Desktop\Aith Bismarck.pdf"
ok1, res1, msg1 = service.process_pdf_file(pdf_adith)
print("Resultado ok:", ok1)
print("Mensaje:", msg1)
print("Tipo:", res1.get("tipo"))
print("Nombre:", res1.get("nombre"))
print("Codigo:", res1.get("codigoRh"))
print("Categoria:", res1.get("categoriaInvestigador"))
print("Total productos:", len(res1.get("productos", [])))
print("Primeros 3 productos:")
for p in res1.get("productos", [])[:3]:
    print(f"  - [{p.get('categoria')}] ({p.get('anio')}): {p.get('titulo')}")

# Verificar si se modifico el archivo en disco (NO debe haberse guardado)
time.sleep(0.1)
mtime_inv_post1 = os.path.getmtime("PEA-Scraper/investigadores.json")
print("Archivo investigadores.json modificado tras carga PDF?:", mtime_inv != mtime_inv_post1)

print("\n=== PRUEBA 2: PDF INVALIDO (Solicitud de Permiso) ===")
pdf_invalido = r"C:\Users\camil\Downloads\Solicitud de Permisos.pdf"
ok2, res2, msg2 = service.process_pdf_file(pdf_invalido)
print("Resultado ok (debe ser False):", ok2)
print("Mensaje de rechazo:", msg2)

mtime_inv_post2 = os.path.getmtime("PEA-Scraper/investigadores.json")
print("Archivo investigadores.json modificado tras PDF invalido?:", mtime_inv_post1 != mtime_inv_post2)
