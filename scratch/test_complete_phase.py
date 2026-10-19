import sys
import os
import time

sys.path.insert(0, os.path.abspath("PEA-Scraper"))
import importlib.util
spec = importlib.util.spec_from_file_location("dldd", "PEA-Scraper/DLDD-MAFF-JDLA.py")
dldd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dldd)

service = dldd.ApplicationService()

print("=" * 60)
print("VERIFICACION COMPLETA: EXTRACCION DE GRUPOS Y CONTROL DE DUPLICADOS")
print("=" * 60)

# 1. Extractor con Aitice.pdf (GrupLAC)
print("\n[TEST 1] Extraccion de Grupo (GrupLAC Aitice.pdf)...")
pdf_aitice = r"C:\Users\camil\Desktop\Aitice.pdf"
ext = dldd.PDFExtractor()
ok_aitice, res_aitice, msg_aitice = ext.extract(pdf_aitice)
print(f"  Extraccion exitosa: {ok_aitice}")
print(f"  Mensaje: {msg_aitice}")
print(f"  Tipo detectado: {res_aitice.get('tipo')}")
print(f"  Codigo grupo: {res_aitice.get('nroGrupo')}")
print(f"  Nombre grupo: {res_aitice.get('nombreGrupo')}")
print(f"  Lider: {res_aitice.get('lider')}")
print(f"  Anio formacion: {res_aitice.get('anioFormacion')}")
print(f"  Clasificacion: {res_aitice.get('clasificacion')}")
print(f"  Depto / Ciudad: {res_aitice.get('departamento')} / {res_aitice.get('ciudad')}")
print(f"  Total integrantes: {len(res_aitice.get('integrantes', []))}")
print(f"  Total productos: {len(res_aitice.get('productos', []))}")

assert ok_aitice is True, "Aitice.pdf debe extraerse con exito"
assert res_aitice.get("tipo") == "GRUPO", "Aitice.pdf debe clasificarse como GRUPO"
assert res_aitice.get("nombreGrupo") == "AITICE", "El nombre debe ser AITICE"
assert "Armando" in res_aitice.get("lider", ""), "El lider debe ser Armando Javier Lopez Sierra"
assert len(res_aitice.get("integrantes", [])) >= 90, "Debe tener al menos 90 integrantes"
assert len(res_aitice.get("productos", [])) >= 700, "Debe tener al menos 700 productos"
print("  -> TEST 1 PASADO CON EXITO!")

# 2. Extractor con Aith Bismarck.pdf (CvLAC)
print("\n[TEST 2] Extraccion de Investigador (CvLAC Aith Bismarck.pdf)...")
pdf_adith = r"C:\Users\camil\Desktop\Aith Bismarck.pdf"
ok_adith, res_adith, msg_adith = ext.extract(pdf_adith)
print(f"  Extraccion exitosa: {ok_adith}")
print(f"  Tipo detectado: {res_adith.get('tipo')}")
print(f"  Nombre: {res_adith.get('nombre')}")
print(f"  Codigo: {res_adith.get('codigoRh')}")
print(f"  Total productos: {len(res_adith.get('productos', []))}")

assert ok_adith is True, "Aith Bismarck.pdf debe extraerse con exito"
assert res_adith.get("tipo") == "INVESTIGADOR", "Debe clasificarse como INVESTIGADOR"
assert "Adith Bismarck" in res_adith.get("nombre", ""), "El nombre debe contener Adith Bismarck"
assert len(res_adith.get("productos", [])) >= 50, "Debe tener al menos 50 productos"
print("  -> TEST 2 PASADO CON EXITO!")

# 3. Gatekeeper con PDF Invalido
print("\n[TEST 3] Gatekeeper de PDF no perteneciente a MinCiencias...")
pdf_invalido = r"C:\Users\camil\Downloads\Solicitud de Permisos.pdf"
ok_inv, res_inv, msg_inv = ext.extract(pdf_invalido)
print(f"  Aceptado (debe ser False): {ok_inv}")
print(f"  Mensaje de rechazo: {msg_inv}")
assert ok_inv is False, "El PDF ajeno debe ser rechazado"
print("  -> TEST 3 PASADO CON EXITO!")

# 4. Control de Duplicados Multi-Criterio (Web vs PDF)
print("\n[TEST 4] Control de Duplicados Multi-Criterio (Web vs PDF)...")
# Creamos un servicio limpio para prueba aislada
service_test = dldd.ApplicationService()
service_test.investigadores = []
service_test.grupos = []

# Carga web de investigador
inv_web = {
    "tipo": "INVESTIGADOR",
    "codigoRh": "0000799157",  # Codigo numerico web
    "nombre": "Adith Bismarck Pérez Orozco",
    "productos": []
}
add_w1, msg_w1 = service_test.add_scraped_result(inv_web)
print(f"  1. Carga web Adith (RH 0000799157): ok={add_w1}, msg={msg_w1}")
assert add_w1 is True

# Carga posterior desde PDF (codigo sintetico INV_ADITHBISMA)
ok_p1, res_p1, msg_p1 = service_test.process_pdf_file(pdf_adith)
print(f"  2. Carga PDF Adith (mismo nombre, codigo distinto): ok={ok_p1}, msg={msg_p1}")
assert ok_p1 is False, "Debe bloquear la insercion por duplicidad de nombre!"
assert len(service_test.investigadores) == 1, "La lista debe seguir teniendo 1 solo investigador"

# Carga web de grupo
grp_web = {
    "tipo": "GRUPO",
    "nroGrupo": "COL0081234",  # Codigo numerico web
    "nombreGrupo": "AITICE",
    "productos": []
}
add_g1, msg_g1 = service_test.add_scraped_result(grp_web)
print(f"  3. Carga web AITICE (Nro COL0081234): ok={add_g1}, msg={msg_g1}")
assert add_g1 is True

# Carga posterior desde PDF (codigo sintetico GRP_AITICE)
ok_g2, res_g2, msg_g2 = service_test.process_pdf_file(pdf_aitice)
print(f"  4. Carga PDF AITICE (mismo nombre, codigo distinto): ok={ok_g2}, msg={msg_g2}")
assert ok_g2 is False, "Debe bloquear la insercion por duplicidad de nombre de grupo!"
assert len(service_test.grupos) == 1, "La lista debe seguir teniendo 1 solo grupo"
print("  -> TEST 4 PASADO CON EXITO!")

# 5. Sin auto-guardado en disco
print("\n[TEST 5] Verificacion de No Auto-Guardado en Disco...")
mtime_inv_antes = os.path.getmtime("PEA-Scraper/investigadores.json")
mtime_grp_antes = os.path.getmtime("PEA-Scraper/grupos.json")

# Hacemos una operacion de parseo
ext.extract(pdf_aitice)
ext.extract(pdf_adith)
time.sleep(0.1)

mtime_inv_desp = os.path.getmtime("PEA-Scraper/investigadores.json")
mtime_grp_desp = os.path.getmtime("PEA-Scraper/grupos.json")
assert mtime_inv_antes == mtime_inv_desp, "investigadores.json NO debe guardarse automaticamente"
assert mtime_grp_antes == mtime_grp_desp, "grupos.json NO debe guardarse automaticamente"
print("  -> TEST 5 PASADO CON EXITO! Los archivos en disco permanecen intactos.")

print("\n" + "=" * 60)
print("TODAS LAS PRUEBAS DE LA SUITE PASARON AL 100% SATISFACTORIAMENTE!")
print("=" * 60)
