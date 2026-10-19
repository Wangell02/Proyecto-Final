with open("DLDD-MAFF-JDLA.cpp", "r", encoding="utf-8") as f:
    text = f.read()

# 1. En cargarInvestigador:
target1 = """          listasInv.agregar(investigador);
          gestorProductos.consolidar(listasInv, multilistas);
          persistencia.guardarInvestigadores(listasInv);

          gotoxy(15, 15);
          cout << "Investigador cargado correctamente.";"""

# Normalizar saltos de linea
text_norm = text.replace("\r\n", "\n")

target1_norm = """          listasInv.agregar(investigador);
          gestorProductos.consolidar(listasInv, multilistas);
          persistencia.guardarInvestigadores(listasInv);

          gotoxy(15, 15);
          cout << "Investigador cargado correctamente.";"""

rep1 = """          listasInv.agregar(investigador);
          gestorProductos.consolidar(listasInv, multilistas);

          gotoxy(15, 15);
          cout << "Investigador cargado en memoria.";
          gotoxy(15, 16);
          cout << "Para guardar en disco use la opcion 5.";"""

if target1_norm in text_norm:
    text_norm = text_norm.replace(target1_norm, rep1)
    print("cargarInvestigador actualizado.")
else:
    print("Aviso: target1 no encontrado")

# 2. En cargarGrupo:
target2_norm = """          integrantes.clear();
          productos.clear();
          gestorProductos.consolidar(listasInv, multilistas);
          persistencia.guardarGrupos(multilistas);

          gotoxy(15, 15);
          cout << "Grupo cargado correctamente.";"""

rep2 = """          integrantes.clear();
          productos.clear();
          gestorProductos.consolidar(listasInv, multilistas);

          gotoxy(15, 15);
          cout << "Grupo cargado en memoria.";
          gotoxy(15, 16);
          cout << "Para guardar en disco use la opcion 5.";"""

if target2_norm in text_norm:
    text_norm = text_norm.replace(target2_norm, rep2)
    print("cargarGrupo actualizado.")
else:
    print("Aviso: target2 no encontrado")

# Guardar manteniendo CRLF
with open("DLDD-MAFF-JDLA.cpp", "w", encoding="utf-8", newline="\r\n") as f:
    f.write(text_norm)

print("DLDD-MAFF-JDLA.cpp guardado con exito.")
