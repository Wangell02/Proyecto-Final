with open("PEA-Scraper/DLDD-MAFF-JDLA.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Localizar def open_large_popup():
start_idx = -1
for i, l in enumerate(lines):
    if "def open_large_popup():" in l:
        start_idx = i
        break

if start_idx == -1:
    print("No se encontro open_large_popup")
    exit(1)

# Buscar 'if not self.stats_selected_items:'
cond_idx = -1
for i in range(start_idx, start_idx + 30):
    if "if not self.stats_selected_items:" in lines[i]:
        cond_idx = i
        break

# Buscar donde termina open_large_popup (linea anterior a 'ttk.Button(filter_frame, text="Aplicar Filtros"')
end_idx = -1
for i in range(cond_idx, len(lines)):
    if 'ttk.Button(filter_frame, text="Aplicar Filtros"' in lines[i]:
        end_idx = i
        break

print(f"open_large_popup de {start_idx} a {end_idx}, cond en {cond_idx}")

# Las lineas desde cond_idx hasta cond_idx + 4 son:
#                 if not self.stats_selected_items:
#                     messagebox.showerror("Error", "Debe seleccionar al menos 1 elemento para generar estadísticas.", parent=self)
#                     return
#
# Queremos que sea:
#                 if not self.stats_selected_items:
#                     messagebox.showerror("Error", "Debe seleccionar al menos 1 elemento para generar estadísticas.", parent=self)
#                 else:
#                     <todo el resto de lineas con 4 espacios mas de indentacion>

# Encontrar la linea de 'return'
ret_idx = -1
for i in range(cond_idx, cond_idx + 5):
    if "return" in lines[i]:
        ret_idx = i
        break

if ret_idx != -1:
    del lines[ret_idx]
    # Ahora insertar '                else:' antes del resto
    lines.insert(cond_idx + 2, "                else:\n")
    # Indentar desde cond_idx + 3 hasta end_idx (ahora +1 por la insercion)
    for j in range(cond_idx + 3, end_idx + 1):
        if lines[j].strip():
            lines[j] = "    " + lines[j]
    with open("PEA-Scraper/DLDD-MAFF-JDLA.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("open_large_popup corregido con exito.")
else:
    print("No se encontro return en open_large_popup.")
