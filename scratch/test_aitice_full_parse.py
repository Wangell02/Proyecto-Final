import fitz
import re

doc = fitz.open(r"C:\Users\camil\Desktop\Aitice.pdf")
text = "\n".join([p.get_text() for p in doc]).replace("\xa0", " ")

from typing import Dict, Any, List

def clean_text(s: str) -> str:
    if not s:
        return ""
    return " ".join(str(s).split()).strip()

def canonical_key(s: str) -> str:
    if not s:
        return ""
    norm = s.strip().lower()
    for o, d in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n')]:
        norm = norm.replace(o, d)
    return re.sub(r'[^a-z0-9]', '', norm)

# Test parse_group
grp: Dict[str, Any] = {
    "tipo": "GRUPO",
    "nroGrupo": "",
    "nombreGrupo": "",
    "anioFormacion": "",
    "departamento": "",
    "ciudad": "",
    "lider": "",
    "informacionCertificada": "Certificada",
    "paginaWeb": "",
    "email": "",
    "clasificacion": "Reconocido",
    "areaConocimiento": "",
    "programaNacionalCti": "",
    "programaNacionalCtiSecundario": "",
    "planEstrategico": "",
    "estadoArte": "",
    "objetivos": "",
    "retos": "",
    "vision": "",
    "instituciones": [],
    "lineasInvestigacion": [],
    "integrantes": [],
    "productos": []
}

# 1. Nombre grupo
lines = [l.strip() for l in text.splitlines() if l.strip()]
m_nom = re.search(r"(?:Nombre\s+del\s+grupo|Nombre\s+de\s+grupo)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
if m_nom:
    grp["nombreGrupo"] = clean_text(m_nom.group(1))
else:
    for i, l in enumerate(lines[:10]):
        if "datos básicos" in l.lower() or "datos basicos" in l.lower() or "gruplac" in l.lower():
            if i > 0:
                grp["nombreGrupo"] = clean_text(lines[i-1])
            break

if not grp["nombreGrupo"] and lines:
    grp["nombreGrupo"] = clean_text(lines[0])

# 2. Codigo grupo
m_num = re.search(r"(?:C[oó]digo\s+(?:del\s+grupo|GrupLAC|de\s+grupo)|Nro\.?\s+Grupo)\s*[:\n]\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
if m_num:
    grp["nroGrupo"] = clean_text(m_num.group(1))
elif grp["nombreGrupo"]:
    norm_slug = re.sub(r"[^A-Za-z0-9]", "", canonical_key(grp["nombreGrupo"]))[:8].upper()
    grp["nroGrupo"] = "GRP_" + norm_slug
else:
    grp["nroGrupo"] = "GRP_001"

# 3. Lider
m_lid = re.search(r"(?:^|\n)\s*L[ií]der(?:\s+del\s+grupo)?\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
if m_lid:
    grp["lider"] = clean_text(m_lid.group(1))

# 4. Anio
m_anio = re.search(r"(?:A[ñn]o(?:\s+y\s+mes)?\s+de\s+formaci[oó]n|Creaci[oó]n)\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
if m_anio:
    grp["anioFormacion"] = clean_text(m_anio.group(1))

# 5. Depto y ciudad
m_dep = re.search(r"(?:Departamento\s*-\s*Ciudad|Departamento)\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
if m_dep:
    val_dep = clean_text(m_dep.group(1))
    if "-" in val_dep:
        partes = val_dep.split("-")
        grp["departamento"] = clean_text(partes[0])
        grp["ciudad"] = clean_text(partes[1])
    else:
        grp["departamento"] = val_dep

# 6. Clasificacion
m_clas = re.search(r"(?:^|\n)\s*Clasificaci[oó]n\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
if m_clas:
    c_raw = clean_text(m_clas.group(1))
    if " con vigencia" in c_raw.lower():
        c_raw = re.split(r"\s+con\s+vigencia", c_raw, flags=re.IGNORECASE)[0]
    grp["clasificacion"] = clean_text(c_raw)

# 7. Area conocimiento
m_area = re.search(r"(?:^|\n)\s*[AÁ]rea\s+de\s+conocimiento\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
if m_area:
    grp["areaConocimiento"] = clean_text(m_area.group(1))

# 8. Email
m_mail = re.search(r"(?:^|\n)\s*(?:E-mail|Email|Correo)\s*(?::|\n)\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text, re.IGNORECASE)
if m_mail:
    grp["email"] = clean_text(m_mail.group(1))

# 9. Instituciones
m_sec_inst = re.search(r"Instituciones\s*[:\n](.*?)(?=(?:Plan\s+Estrat[eé]gico|L[ií]neas|Integrantes|\Z))", text, re.DOTALL | re.IGNORECASE)
if m_sec_inst:
    for inst_line in m_sec_inst.group(1).split("\n"):
        ci = clean_text(re.sub(r"^\d+\s*[\.\-]+\s*", "", inst_line))
        ci = re.split(r"\s*-\s*\(Avalado\)", ci, flags=re.IGNORECASE)[0].strip()
        if len(ci) > 3:
            grp["instituciones"].append(ci)

# 10. Lineas
m_sec_lin = re.search(r"L[ií]neas\s+de\s+investigaci[oó]n\s*(?:declaradas\s+por\s+el\s+grupo)?\s*[:\n](.*?)(?=(?:Integrantes|Instituciones|PRODUCCI[OÓ]N|\Z))", text, re.DOTALL | re.IGNORECASE)
if m_sec_lin:
    for l_item in m_sec_lin.group(1).split("\n"):
        cl = clean_text(re.sub(r"^\d+\s*[\.\-]+\s*", "", l_item))
        if len(cl) > 3:
            grp["lineasInvestigacion"].append(cl)

# 11. Integrantes
pos_integ = text.find("Integrantes del grupo")
if pos_integ != -1:
    pos_fin_integ = text.find("PRODUCCIÓN DE FORMACIÓN", pos_integ)
    if pos_fin_integ == -1:
        pos_fin_integ = text.find("PRODUCCIÓN BIBLIOGRÁFICA", pos_integ)
    bloque_integ = text[pos_integ:pos_fin_integ if pos_fin_integ != -1 else pos_integ + 15000]
    
    lineas_int = [l.strip() for l in bloque_integ.splitlines() if l.strip()]
    idx = 0
    while idx < len(lineas_int):
        l = lineas_int[idx]
        m_item = re.match(r"^\d+\s*[\.\-]+\s*(.+)$", l)
        if m_item:
            nom_mem = clean_text(m_item.group(1))
            m_inline = re.match(r"^(.+?)\s+(?:Integrante|L[ií]der|Estudiante|Investigador)\s+(\d+)\s+([^\n]+)$", nom_mem, re.IGNORECASE)
            if m_inline:
                nom_mem = clean_text(m_inline.group(1))
            norm_mem = re.sub(r"[^A-Za-z0-9]", "", canonical_key(nom_mem))[:8].upper()
            cod_mem = "MEM_" + norm_mem
            inst_mem = grp["instituciones"][0] if grp["instituciones"] else ""
            grp["integrantes"].append({
                "codigoRh": cod_mem,
                "nombre": nom_mem,
                "institucion": inst_mem,
                "departamento": grp["departamento"],
                "ciudad": grp["ciudad"],
                "activo": True
            })
        idx += 1

# 12. Productos del grupo
pos_prod_ini = -1
for marker in ["PRODUCCIÓN BIBLIOGRÁFICA", "PRODUCCIÓN TÉCNICA", "APROPIACIÓN SOCIAL", "ACTIVIDADES DE FORMACIÓN"]:
    p_pos = text.find(marker)
    if p_pos != -1:
        if pos_prod_ini == -1 or p_pos < pos_prod_ini:
            pos_prod_ini = p_pos

if pos_prod_ini != -1:
    bloque_prods = text[pos_prod_ini:]
    pat_num_prod = re.compile(r"(?:^|\n)\s*(\d+)\s*[\.\-]+\s+", re.MULTILINE)
    p_matches = list(pat_num_prod.finditer(bloque_prods))
    p_seen = set()
    
    idx_p = 0
    while idx_p < len(p_matches):
        start = p_matches[idx_p].end()
        end = len(bloque_prods)
        if idx_p + 1 < len(p_matches):
            end = p_matches[idx_p + 1].start()
        blk = bloque_prods[start:end].strip()
        lineas_blk = [lb.strip() for lb in blk.splitlines() if lb.strip()]
        if len(lineas_blk) > 0:
            primera = lineas_blk[0]
            partes = primera.split(":", 1)
            tipo_cand = "Artículo"
            tit_cand = primera
            if len(partes) == 2:
                tipo_cand = clean_text(partes[0])
                tit_cand = clean_text(partes[1])
            else:
                tit_cand = clean_text(primera)
            
            anios = re.findall(r"\b(19\d\d|20[0-3]\d)\b", blk)
            anio_p = 0
            if len(anios) > 0:
                anio_p = int(anios[-1])
            
            autores = []
            m_aut = re.search(r"Autores\s*:\s*([^\n\r]+)", blk, re.IGNORECASE)
            if m_aut:
                for a in m_aut.group(1).split(","):
                    ca = clean_text(a)
                    if ca:
                        autores.append(ca)
            
            cat_p = "Artículo"
            t_low = tipo_cand.lower()
            if "libro" in t_low and "capítulo" not in t_low and "capitulo" not in t_low:
                cat_p = "Libro"
            elif "capítulo" in t_low or "capitulo" in t_low:
                cat_p = "Capítulo de libro"
            elif "software" in t_low or "computacional" in t_low or "multimedia" in t_low:
                cat_p = "Software"
            elif "informe" in t_low:
                cat_p = "Informe técnico"
            elif "prototipo" in t_low:
                cat_p = "Prototipo"
            elif "innovación" in t_low or "innovacion" in t_low:
                cat_p = "Innovación"
            elif "evento" in t_low or "congreso" in t_low or "simposio" in t_low or "encuentro" in t_low:
                cat_p = "Trabajo en evento"
            elif "consultor" in t_low:
                cat_p = "Consultoría"
            elif "trabajo de grado" in t_low or "tutor" in t_low or "tesis" in t_low or "orientación" in t_low:
                cat_p = "Trabajo dirigido"
            elif "curso" in t_low or "diplomado" in t_low:
                cat_p = "Curso dictado"
            elif "contenido digital" in t_low or "audiovisual" in t_low or "desarrollo web" in t_low:
                cat_p = "Contenido digital"
            
            tit_cand = clean_text(tit_cand)
            if len(tit_cand) > 4:
                firma = (canonical_key(tit_cand), anio_p)
                if firma not in p_seen:
                    p_seen.add(firma)
                    grp["productos"].append({
                        "idProducto": "GRP_PROD_" + str(len(grp["productos"]) + 1).zfill(3),
                        "titulo": tit_cand,
                        "categoria": cat_p,
                        "validado": True,
                        "anio": anio_p,
                        "tipoProducto": cat_p,
                        "autores": autores
                    })
        idx_p += 1

print("=== RESULTADO DEL PARSEO DE GRUPO ===")
print("Tipo:", grp["tipo"])
print("Codigo:", grp["nroGrupo"])
print("Nombre:", grp["nombreGrupo"])
print("Lider:", grp["lider"])
print("Anio formacion:", grp["anioFormacion"])
print("Clasificacion:", grp["clasificacion"])
print("Depto:", grp["departamento"], "| Ciudad:", grp["ciudad"])
print("Email:", grp["email"])
print("Total instituciones:", len(grp["instituciones"]))
print("Total lineas investigacion:", len(grp["lineasInvestigacion"]))
print("Total integrantes:", len(grp["integrantes"]))
print("Total productos:", len(grp["productos"]))
print("Muestra 5 productos:")
for p in grp["productos"][:5]:
    print(f"  [{p['categoria']}] ({p['anio']}) -> {p['titulo'][:50]} (Autores: {len(p['autores'])})")
