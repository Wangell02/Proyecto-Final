import json

# 1. Limpiar investigadores.json
with open("PEA-Scraper/investigadores.json", "r", encoding="utf-8") as f:
    invs = json.load(f)

initial_count = len(invs)
clean_invs = [inv for inv in invs if inv.get("codigoRh") != "PDF_001" and "Investigador Extraido" not in inv.get("nombre", "")]
print(f"investigadores.json: de {initial_count} a {len(clean_invs)}")
with open("PEA-Scraper/investigadores.json", "w", encoding="utf-8") as f:
    json.dump(clean_invs, f, indent=4, ensure_ascii=False)

# 2. Limpiar grupos.json
with open("PEA-Scraper/grupos.json", "r", encoding="utf-8") as f:
    grps = json.load(f)

initial_g_count = len(grps)
clean_grps = [g for g in grps if g.get("nroGrupo") != "GRP_001" and "Extraido de PDF" not in g.get("nombreGrupo", "")]
print(f"grupos.json: de {initial_g_count} a {len(clean_grps)}")
with open("PEA-Scraper/grupos.json", "w", encoding="utf-8") as f:
    json.dump(clean_grps, f, indent=4, ensure_ascii=False)

# 3. Limpiar investigadores.txt
with open("investigadores.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for l in lines:
    if "INVESTIGADOR\tPDF_001" in l or "Investigador Extraido de PDF" in l:
        skip = True
    if skip:
        if "FIN_INVESTIGADOR" in l:
            skip = False
        continue
    new_lines.append(l)

with open("investigadores.txt", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print(f"investigadores.txt limpio: {len(lines)} -> {len(new_lines)} lineas")

# 4. Limpiar grupos.txt
with open("grupos.txt", "r", encoding="utf-8") as f:
    g_lines = f.readlines()

new_glines = []
skip_g = False
for l in g_lines:
    if "GRUPO\tGRP_001" in l or "Grupo de Investigacion Extraido de PDF" in l:
        skip_g = True
    if skip_g:
        if "FIN_GRUPO" in l:
            skip_g = False
        continue
    new_glines.append(l)

with open("grupos.txt", "w", encoding="utf-8") as f:
    f.writelines(new_glines)
print(f"grupos.txt limpio: {len(g_lines)} -> {len(new_glines)} lineas")
