import sys
import os
import io
import json
import tempfile
import urllib.request
import urllib.error

sys.path.insert(0, 'PEA-Scraper')
import importlib
pea = importlib.import_module('DLDD-MAFF-JDLA')

def run_tests():
    print("=" * 60)
    print("ETAPA 2: VERIFICACION COMPLETA DE IMPORTACION CSV")
    print("=" * 60)

    ext = pea.CSVExtractor()
    total_passed = 0
    total_tests = 0

    def assert_test(cond, title, detail=""):
        nonlocal total_passed, total_tests
        total_tests += 1
        if cond:
            total_passed += 1
            print(f"  [PASS] {title}")
        else:
            print(f"  [FAIL] {title}: {detail}")

    # 1. Investigador valido (coma, utf-8)
    ok, data, msg = ext.extract('scratch/csv_tests/1_investigador_valido.csv')
    assert_test(ok and len(data.get('investigadores', [])) == 1, 
                "1. CSV valido de un investigador (coma, utf-8)", msg)

    # 2. Grupo valido con integrantes (punto y coma, utf-8 con BOM)
    ok, data, msg = ext.extract('scratch/csv_tests/2_grupo_integrantes.csv')
    grp_ok = ok and len(data.get('grupos', [])) == 1 and len(data['grupos'][0].get('integrantes', [])) == 2
    assert_test(grp_ok, "2. CSV valido de un grupo con integrantes (punto y coma, UTF-8 BOM)", msg)

    # 3. Productos y metadatos validos (Windows-1252)
    ok, data, msg = ext.extract('scratch/csv_tests/3_productos_win1252.csv')
    prod_ok = ok and len(data.get('grupos', [])) == 1 and len(data['grupos'][0].get('productos', [])) == 2
    assert_test(prod_ok, "3. CSV con productos y metadatos validos (Windows-1252)", msg)

    # 4. Campo entrecomillado con delimitador, comillas escapadas y saltos de linea
    ok, data, msg = ext.extract('scratch/csv_tests/4_comillas_complejas.csv')
    assert_test(ok and len(data.get('grupos', [])) == 1, 
                "4. Campo entrecomillado con delimitador, comillas escapadas y salto de linea", msg)

    # 5. Varias entidades y combinacion grupo/investigador
    ok, data, msg = ext.extract('scratch/csv_tests/12_mixto_lote.csv')
    mixto_ok = ok and len(data.get('investigadores', [])) == 3 and len(data.get('grupos', [])) == 2
    assert_test(mixto_ok, "5. Varias entidades y combinacion de grupo/investigador", msg)

    # 6. CSV generico no MinCiencias (rechazado)
    ok, data, msg = ext.extract('scratch/csv_tests/5_generico_rechazado.csv')
    assert_test(not ok, "6. CSV generico de empleados/clientes rechazado", msg)

    # 7. CSV de peliculas / catalogo comercial rechazado
    ok, data, msg = ext.extract('scratch/csv_tests/6_peliculas_rechazado.csv')
    assert_test(not ok, "7. CSV generico de peliculas/entretenimiento rechazado", msg)

    # 8. Archivo de una sola columna rechazado
    ok, data, msg = ext.extract('scratch/csv_tests/7_una_columna.csv')
    assert_test(not ok, "8. Archivo de una sola columna rechazado", msg)

    # 9. Falso CSV que contiene JSON
    ok, data, msg = ext.extract('scratch/csv_tests/8_falso_json.csv')
    assert_test(not ok, "9. Falso CSV que contiene formato JSON rechazado", msg)

    # 10. Falso CSV que contiene codigo C++ / Python
    ok, data, msg = ext.extract('scratch/csv_tests/9_falso_codigo.csv')
    assert_test(not ok, "10. Falso CSV que contiene codigo fuente rechazado", msg)

    # 11. Archivo vacio
    ok, data, msg = ext.extract('scratch/csv_tests/10_vacio.csv')
    assert_test(not ok, "11. Archivo CSV vacio rechazado", msg)

    # 12. Filas con longitud inconsistente
    ok, data, msg = ext.extract('scratch/csv_tests/11_filas_inconsistentes.csv')
    assert_test(not ok, "12. Filas inconsistentes rechazadas", msg)

    # 13. Productos sin titulo util rechazados o entidades sin identidad suficiente
    tmp_sin_titulo = "scratch/csv_tests/temp_sin_titulo.csv"
    with open(tmp_sin_titulo, "w", encoding="utf-8") as f:
        f.write("codigo_grupo,nombre_grupo,titulo_producto,tipo_producto\n")
        f.write("COL0001,Grupo Alpha,,Articulo\n")
    ok, data, msg = ext.extract(tmp_sin_titulo)
    # Grupo se crea pero producto sin titulo util es descartado
    p_count = len(data.get('grupos', [{}])[0].get('productos', [])) if (ok and data.get('grupos')) else 0
    assert_test(p_count == 0, "13. Producto sin titulo util es descartado/no creado", msg)
    if os.path.exists(tmp_sin_titulo):
        os.remove(tmp_sin_titulo)

    # 14. Gatekeeper rechaza archivo si faltan campos minimos de identidad
    tmp_sin_id = "scratch/csv_tests/temp_sin_id.csv"
    with open(tmp_sin_id, "w", encoding="utf-8") as f:
        f.write("institucion,departamento,ciudad\n")
        f.write("UPC,Cesar,Valledupar\n")
    ok, data, msg = ext.extract(tmp_sin_id)
    assert_test(not ok, "14. Gatekeeper rechaza CSV sin campos de identidad de investigador o grupo", msg)
    if os.path.exists(tmp_sin_id):
        os.remove(tmp_sin_id)

    # 15. Proceso en lote con servicio de aplicacion (ApplicationService)
    svc = pea.ApplicationService()
    # Usamos repositorios temporales para no modificar archivos de persistencia
    svc.investigadores = []
    svc.grupos = []
    
    report = svc.process_csv_files([
        'scratch/csv_tests/1_investigador_valido.csv',
        'scratch/csv_tests/5_generico_rechazado.csv',
        'scratch/csv_tests/2_grupo_integrantes.csv'
    ])
    lote_atomico_ok = (report["total_archivos"] == 3 and 
                       report["archivos_exitosos"] == 2 and 
                       report["archivos_fallidos"] == 1 and
                       report["total_incorporados"] == 2)
    assert_test(lote_atomico_ok, 
                "15. Lote mixto de archivos con ApplicationService (atomico por archivo)", 
                f"report={report}")

    # 16. Deteccion de duplicados en servicio
    ok_dup, _, msg_dup = svc.process_csv_file('scratch/csv_tests/1_investigador_valido.csv')
    assert_test(not ok_dup or "Duplicados omitidos" in msg_dup or "ya se encuentra cargado" in msg_dup,
                "16. Deteccion de entidad duplicada al reinsertar archivo", msg_dup)

    # 17. Serializacion conforme al protocolo estructurado C++
    ok_ser, data_ser, _ = ext.extract('scratch/csv_tests/12_mixto_lote.csv')
    ser_text = pea.serialize_result(data_ser)
    ser_ok = "ESTADO\tOK" in ser_text and "TIPO\tLOTE" in ser_text and "GRUPO\t" in ser_text and "INVESTIGADOR\t" in ser_text
    assert_test(ser_ok, "17. Serializacion estructurada de LOTE para parser C++", ser_text[:120])

    print("=" * 60)
    print(f"RESULTADO: {total_passed} de {total_tests} pruebas superadas.")
    print("=" * 60)
    return total_passed == total_tests

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
