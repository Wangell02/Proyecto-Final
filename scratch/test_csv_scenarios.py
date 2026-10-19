import os
import sys

# Import from test_csv_extractor_prototype
from test_csv_extractor_prototype import CSVExtractor

extractor = CSVExtractor()
scratch_dir = "scratch/csv_tests"
os.makedirs(scratch_dir, exist_ok=True)

print("=" * 60)
print("EJECUTANDO BATERIA DE PRUEBAS DE CSVEXTRACTOR")
print("=" * 60)

# 1. Investigador válido (delimitador coma, UTF-8 sin BOM)
f1 = os.path.join(scratch_dir, "1_investigador_valido.csv")
with open(f1, "w", encoding="utf-8") as f:
    f.write("codigo_rh,nombre_investigador,correo,orcid,categoria,institucion,departamento,ciudad\n")
    f.write("0000123456,Carlos Alberto Gómez,carlos.gomez@unicesar.edu.co,0000-0002-1825-0097,Asociado,Universidad Popular del Cesar,Cesar,Valledupar\n")

ok1, res1, msg1 = extractor.extract(f1)
print(f"\n[Test 1] Investigador válido (coma, utf-8): ok={ok1}")
print(f"  Mensaje: {msg1}")
assert ok1 is True
assert len(res1["investigadores"]) == 1
inv = res1["investigadores"][0]
assert inv["codigoRh"] == "0000123456"
assert "Carlos Alberto" in inv["nombre"]
assert inv["categoriaInvestigador"] == "Asociado"
print("  -> PASADO!")

# 2. Grupo válido con integrantes (delimitador punto y coma, UTF-8 con BOM)
f2 = os.path.join(scratch_dir, "2_grupo_integrantes.csv")
with open(f2, "w", encoding="utf-8-sig") as f:
    f.write("codigo_grupo;nombre_grupo;lider;clasificacion;ano_formacion;area_conocimiento;integrante;rol;horas\n")
    f.write("COL0019283;GIEST;Armando Lopez;A;2008;Ingenierías Eléctrica y Electrónica;Norberto Diaz;Investigador;10\n")
    f.write("COL0019283;GIEST;Armando Lopez;A;2008;Ingenierías Eléctrica y Electrónica;Maria Jimenez;Investigador;8\n")

ok2, res2, msg2 = extractor.extract(f2)
print(f"\n[Test 2] Grupo con integrantes (punto y coma, utf-8-sig): ok={ok2}")
print(f"  Mensaje: {msg2}")
assert ok2 is True
assert len(res2["grupos"]) == 1
grp = res2["grupos"][0]
assert grp["nroGrupo"] == "COL0019283"
assert grp["nombreGrupo"] == "GIEST"
assert grp["clasificacion"] == "A"
assert len(grp["integrantes"]) == 2
print("  -> PASADO!")

# 3. Productos y metadatos con comillas y Windows-1252
f3 = os.path.join(scratch_dir, "3_productos_win1252.csv")
with open(f3, "w", encoding="cp1252") as f:
    f.write('cod_grupo,nombre_grupo,titulo_producto,anio,tipo_producto,doi,revista,autores\n')
    f.write('COL0081234,AITICE,"Análisis de Redes Sensoras, IoT y Big Data",2024,Artículo,10.1016/j.iot.2024.100,"IEEE Latin America",Armando Lopez; Carlos Vidal\n')
    f.write('COL0081234,AITICE,"Desarrollo de Software para Agricultura de Precisión",2023,Software,10.1109/soft.2023.01,"Revista Colombiana de Computación",Maria Jimenez\n')

ok3, res3, msg3 = extractor.extract(f3)
print(f"\n[Test 3] Productos con comillas y Windows-1252: ok={ok3}")
print(f"  Mensaje: {msg3}")
assert ok3 is True
assert len(res3["grupos"]) == 1
grp3 = res3["grupos"][0]
assert len(grp3["productos"]) == 2
assert grp3["productos"][0]["titulo"] == "Análisis de Redes Sensoras, IoT y Big Data"
assert grp3["productos"][0]["categoria"] == "Artículo"
assert grp3["productos"][1]["categoria"] == "Software"
print("  -> PASADO!")

# 4. Campo entrecomillado con delimitador, comillas escapadas y salto de línea
f4 = os.path.join(scratch_dir, "4_comillas_complejas.csv")
with open(f4, "w", encoding="utf-8") as f:
    f.write('codigo_grupo;nombre_grupo;titulo_producto;anio;tipo;descripcion\n')
    f.write('GRP_TEST;Grupo de Microelectrónica;"Diseño de un chip ""ASIC"" de bajo consumo; aplicable en IoT";2022;Artículo;"Este proyecto investiga arquitecturas\ncon procesamiento distribuido y bajo consumo."\n')

ok4, res4, msg4 = extractor.extract(f4)
print(f"\n[Test 4] Comillas escapadas y salto de línea en campo: ok={ok4}")
print(f"  Mensaje: {msg4}")
assert ok4 is True
grp4 = res4["grupos"][0]
assert len(grp4["productos"]) == 1
p4 = grp4["productos"][0]
assert 'chip "ASIC" de bajo consumo; aplicable en IoT' in p4["titulo"]
assert "procesamiento distribuido" in p4["descripcion"]
print("  -> PASADO!")

# 5. CSV genérico no MinCiencias (debe ser rechazado)
f5 = os.path.join(scratch_dir, "5_generico_rechazado.csv")
with open(f5, "w", encoding="utf-8") as f:
    f.write("id,nombre_cliente,edad,telefono,ciudad\n")
    f.write("1,Juan Perez,35,3001234567,Bogota\n")
    f.write("2,Ana Maria Torres,28,3109876543,Medellin\n")

ok5, res5, msg5 = extractor.extract(f5)
print(f"\n[Test 5] CSV genérico de clientes (debe ser False): ok={ok5}")
print(f"  Mensaje: {msg5}")
assert ok5 is False
print("  -> PASADO!")

# 6. Películas / lista genérica de títulos y años (debe ser rechazado)
f6 = os.path.join(scratch_dir, "6_peliculas_rechazado.csv")
with open(f6, "w", encoding="utf-8") as f:
    f.write("titulo,ano,director,duracion\n")
    f.write("Inception,2010,Christopher Nolan,148\n")
    f.write("Interstellar,2014,Christopher Nolan,169\n")

ok6, res6, msg6 = extractor.extract(f6)
print(f"\n[Test 6] CSV de películas (debe ser False): ok={ok6}")
print(f"  Mensaje: {msg6}")
assert ok6 is False
print("  -> PASADO!")

# 7. Archivo de una sola columna (debe ser rechazado)
f7 = os.path.join(scratch_dir, "7_una_columna.csv")
with open(f7, "w", encoding="utf-8") as f:
    f.write("investigador\n")
    f.write("Adith Bismarck Pérez Orozco\n")
    f.write("Carlos Vidal Tovar\n")

ok7, res7, msg7 = extractor.extract(f7)
print(f"\n[Test 7] Una sola columna (debe ser False): ok={ok7}")
print(f"  Mensaje: {msg7}")
assert ok7 is False
print("  -> PASADO!")

# 8. Archivo JSON renombrado .csv (debe ser rechazado)
f8 = os.path.join(scratch_dir, "8_falso_json.csv")
with open(f8, "w", encoding="utf-8") as f:
    f.write('{"nombre": "AITICE", "lider": "Armando Lopez", "clasificacion": "B"}\n')

ok8, res8, msg8 = extractor.extract(f8)
print(f"\n[Test 8] Archivo JSON renombrado (debe ser False): ok={ok8}")
print(f"  Mensaje: {msg8}")
assert ok8 is False
print("  -> PASADO!")

# 9. Código C++ renombrado .csv (debe ser rechazado)
f9 = os.path.join(scratch_dir, "9_falso_codigo.csv")
with open(f9, "w", encoding="utf-8") as f:
    f.write('#include <iostream>\nint main() { return 0; }\n')

ok9, res9, msg9 = extractor.extract(f9)
print(f"\n[Test 9] Código fuente renombrado (debe ser False): ok={ok9}")
print(f"  Mensaje: {msg9}")
assert ok9 is False
print("  -> PASADO!")

# 10. Archivo vacío (debe ser rechazado)
f10 = os.path.join(scratch_dir, "10_vacio.csv")
with open(f10, "w", encoding="utf-8") as f:
    f.write('   \n\n  \n')

ok10, res10, msg10 = extractor.extract(f10)
print(f"\n[Test 10] Archivo vacío (debe ser False): ok={ok10}")
print(f"  Mensaje: {msg10}")
assert ok10 is False
print("  -> PASADO!")

# 11. Filas inconsistentes (columnas no alineadas)
f11 = os.path.join(scratch_dir, "11_filas_inconsistentes.csv")
with open(f11, "w", encoding="utf-8") as f:
    f.write("codigorh,nombre,institucion\n")
    f.write("001,Investigador Uno\n")  # Falta columna
    f.write("002,Investigador Dos,UNICESAR,Extra1,Extra2\n")  # Sobran columnas

ok11, res11, msg11 = extractor.extract(f11)
print(f"\n[Test 11] Filas inconsistentes (debe ser False): ok={ok11}")
print(f"  Mensaje: {msg11}")
assert ok11 is False
print("  -> PASADO!")

print("\n" + "=" * 60)
print("TODAS LAS 11 PRUEBAS PASARON SATISFACTORIAMENTE AL 100%!")
print("=" * 60)
