import sys
import os
sys.path.insert(0, os.path.abspath("PEA-Scraper"))

# Importamos del archivo DLDD-MAFF-JDLA.py
import importlib.util
spec = importlib.util.spec_from_file_location("dldd", "PEA-Scraper/DLDD-MAFF-JDLA.py")
dldd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dldd)

extractor = dldd.PDFExtractor()

# Diagnóstico de Aith Bismarck.pdf
pdf1 = r"C:\Users\camil\Desktop\Aith Bismarck.pdf"
if os.path.exists(pdf1):
    print("=== PROBANDO ADITH BISMARCK ===")
    text1 = extractor.extract_text(pdf1)
    print("Longitud de texto:", len(text1))
    print("Primeras 500 letras:")
    print(text1[:500])
    gk1 = extractor.verify_gatekeeper(text1)
    print("Gatekeeper paso?:", gk1)
    tipo1, segs1 = extractor.partition_document(text1)
    print("Tipo particionado:", tipo1, "Total segmentos:", len(segs1))
    for i, s in enumerate(segs1):
        print(f"  Segmento {i}: tipo={s['tipo']}, longitud={len(s['texto'])}")
    ok1, res1, msg1 = extractor.extract(pdf1)
    print("Resultado extract:", ok1, msg1)
    print("res1 tipo:", res1.get("tipo"))
    if res1.get("tipo") == "LOTE":
        print("Grupos en lote:", len(res1.get("grupos", [])))
        for g in res1.get("grupos", []):
            print("  Grupo:", g.get("nombreGrupo"), "codigo:", g.get("nroGrupo"))
        print("Invs en lote:", len(res1.get("investigadores", [])))
        for inv in res1.get("investigadores", []):
            print("  Investigador:", inv.get("nombre"), "codigo:", inv.get("codigoRh"))
    elif res1.get("tipo") == "INVESTIGADOR":
        print("Investigador nombre:", res1.get("nombre"), "codigo:", res1.get("codigoRh"))
else:
    print("No se encontro pdf1:", pdf1)

# Diagnostico de Solicitud de Permiso
pdf2_candidates = [
    r"C:\Users\camil\Downloads\Solicitud de Permisos.pdf",
    r"C:\Users\camil\Downloads\Solicitud de Permiso 26.pdf",
    r"C:\Users\camil\Downloads\Solicitud de Permiso 27.pdf",
    r"C:\Users\camil\Downloads\Solicitud de Permiso 28.pdf"
]
for p in pdf2_candidates:
    if os.path.exists(p):
        print("\n=== PROBANDO SOLICITUD DE PERMISO ===", p)
        text2 = extractor.extract_text(p)
        print("Longitud:", len(text2))
        print("Primeras 300 letras:")
        print(text2[:300])
        gk2 = extractor.verify_gatekeeper(text2)
        print("Gatekeeper paso?:", gk2)
        ok2, res2, msg2 = extractor.extract(p)
        print("Resultado extract:", ok2, msg2)
        if ok2:
            print("Tipo:", res2.get("tipo"))
            print("Nombre:", res2.get("nombre", res2.get("nombreGrupo", "")))
        break
