import sys
import os
import re
from typing import Dict, Any, List, Tuple

sys.path.insert(0, "PEA-Scraper")
import fitz

# Importamos utilidades de DLDD-MAFF-JDLA.py
import importlib.util
spec = importlib.util.spec_from_file_location("dldd", "PEA-Scraper/DLDD-MAFF-JDLA.py")
dldd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dldd)

canonical_key = dldd.canonical_key
clean_text = dldd.clean_text


class ImprovedPDFExtractor:
    def __init__(self) -> None:
        self.institutional_markers = [
            "scienti", "minciencias", "colciencias", "cvlac", "gruplac",
            "curriculum vitae", "hoja de vida", "par evaluador reconocido por minciencias",
            "categoria investigador", "datos generales del grupo",
            "lineas de investigacion", "produccion bibliografica"
        ]

    def extract_text(self, file_path: str) -> str:
        text_content = ""
        extracted = False
        if fitz is not None:
            try:
                doc = fitz.open(file_path)
                pages = []
                page_idx = 0
                while page_idx < len(doc):
                    page = doc[page_idx]
                    p_text = page.get_text()
                    if p_text:
                        pages.append(p_text)
                    page_idx += 1
                doc.close()
                text_content = "\n\n".join(pages)
                if text_content.strip():
                    extracted = True
            except Exception:
                extracted = False

        if not extracted:
            text_content = ""
        # Normalizar espacios no separables
        return text_content.replace("\xa0", " ")

    def verify_gatekeeper(self, text: str) -> bool:
        canon = canonical_key(text)
        if not canon:
            return False

        # Si tiene CvLAC, GrupLAC, Minciencias, Colciencias o Scienti
        if "cvlac" in canon or "gruplac" in canon or "scienti" in canon or "minciencias" in canon or "colciencias" in canon:
            return True

        # Marcadores combinados: "hoja de vida" junto con "investigador" o "categoria"
        if "hoja de vida" in canon and ("investigador" in canon or "categoria" in canon or "formacion academica" in canon):
            return True

        if "datos generales del grupo" in canon or ("grupo de investigacion" in canon and "lider" in canon and "clasificacion" in canon):
            return True

        return False

    def partition_document(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Particiona el documento identificando encabezados de primer nivel reales.
        NO busca frases casuales en el texto.
        """
        canon = canonical_key(text)

        # Detectar patrones estrictos de encabezado
        # Encabezado de CvLAC: al inicio de página/documento
        cvlac_pat = re.compile(
            r"(?:(?:^|\n\n|\f)\s*(?:Hoja\s+de\s+vida|Curr[ií]culum\s+V[ií]tae(?:\s+de\s+Latinoam[eé]rica)?|CvLAC\b|DATOS\s+GENERALES\s+DEL\s+INVESTIGADOR\b))",
            re.IGNORECASE
        )

        # Encabezado de GrupLAC: estricto
        gruplac_pat = re.compile(
            r"(?:(?:^|\n\n|\f)\s*(?:GrupLAC\b|DATOS\s+GENERALES\s+DEL\s+GRUPO\b|DIRECTORIO\s+DE\s+GRUPOS\s+DE\s+INVESTIGACI[OÓ]N\b))",
            re.IGNORECASE
        )

        cvlac_matches = list(cvlac_pat.finditer(text))
        gruplac_matches = list(gruplac_pat.finditer(text))

        # Caso más común: Es un solo documento CvLAC de principio a fin
        if len(gruplac_matches) == 0 and len(cvlac_matches) <= 1:
            if len(cvlac_matches) == 1 or ("hoja de vida" in canon or "cvlac" in canon or "investigador" in canon):
                return "INVESTIGADOR", [{"tipo": "INVESTIGADOR", "texto": text}]

        # Caso más común: Es un solo documento GrupLAC de principio a fin
        if len(cvlac_matches) == 0 and len(gruplac_matches) <= 1:
            if len(gruplac_matches) == 1 or ("gruplac" in canon or "datos generales del grupo" in canon):
                return "GRUPO", [{"tipo": "GRUPO", "texto": text}]

        # Lotes compilados: combinar límites ordenados
        boundaries = []
        for m in cvlac_matches:
            boundaries.append((m.start(), "INVESTIGADOR"))
        for m in gruplac_matches:
            boundaries.append((m.start(), "GRUPO"))

        # Ordenar
        i = 0
        while i < len(boundaries):
            j = i + 1
            while j < len(boundaries):
                if boundaries[i][0] > boundaries[j][0]:
                    temp = boundaries[i]
                    boundaries[i] = boundaries[j]
                    boundaries[j] = temp
                j += 1
            i += 1

        # Si no hubo encabezados claros
        if len(boundaries) == 0:
            if "gruplac" in canon or "datos generales del grupo" in canon:
                return "GRUPO", [{"tipo": "GRUPO", "texto": text}]
            return "INVESTIGADOR", [{"tipo": "INVESTIGADOR", "texto": text}]

        if len(boundaries) == 1:
            tipo_unico = boundaries[0][1]
            return tipo_unico, [{"tipo": tipo_unico, "texto": text}]

        # Segmentar lote
        segments = []
        b_idx = 0
        while b_idx < len(boundaries):
            pos_act = boundaries[b_idx][0]
            tipo_act = boundaries[b_idx][1]
            if b_idx + 1 < len(boundaries):
                pos_sig = boundaries[b_idx + 1][0]
                frag = text[pos_act:pos_sig]
            else:
                frag = text[pos_act:]
            if len(frag.strip()) > 50:
                segments.append({"tipo": tipo_act, "texto": frag})
            b_idx += 1

        if len(segments) == 1:
            return segments[0]["tipo"], segments

        return "LOTE", segments

    def parse_investigator(self, text: str) -> Dict[str, Any]:
        inv = {
            "tipo": "INVESTIGADOR",
            "codigoRh": "",
            "nombre": "",
            "correo": "",
            "orcid": "",
            "institucion": "",
            "departamento": "",
            "ciudad": "",
            "categoriaInvestigador": "Sin categoría",
            "perfil": "",
            "nombreCitaciones": "",
            "nacionalidad": "Colombiana",
            "sexo": "",
            "estadoParEvaluador": "",
            "researcherId": "",
            "autorIdScopus": "",
            "googleScholar": "",
            "researchGate": "",
            "academiaEdu": "",
            "mendeley": "",
            "linkedin": "",
            "repositorioInstitucional": "",
            "idiomas": [],
            "areasConocimiento": [],
            "lineasInvestigacion": [],
            "formacionAcademica": [],
            "experienciaProfesional": [],
            "gruposInvestigacion": [],
            "semilleros": [],
            "proyectos": [],
            "reconocimientos": [],
            "productos": [],
            "activo": True
        }

        # 1. Extracción de Nombre (maneja ':' o salto de línea)
        m_nom = re.search(r"(?:^|\n)\s*Nombre\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_nom:
            cand_nom = clean_text(m_nom.group(1))
            if cand_nom and "citaciones" not in cand_nom.lower():
                inv["nombre"] = cand_nom

        if not inv["nombre"]:
            m_nom_alt = re.search(r"(?:Investigador|Nombre\s+completo)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
            if m_nom_alt:
                inv["nombre"] = clean_text(m_nom_alt.group(1))

        # 2. Nombre en citaciones
        m_cit = re.search(r"(?:^|\n)\s*Nombre\s+en\s+citaciones\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_cit:
            inv["nombreCitaciones"] = clean_text(m_cit.group(1))

        # Si aún no tiene nombre pero tiene citaciones: ej "PÉREZ OROZCO, ADITH BISMARCK"
        if not inv["nombre"] and inv["nombreCitaciones"]:
            partes_cit = inv["nombreCitaciones"].split(",")
            if len(partes_cit) == 2:
                inv["nombre"] = clean_text(partes_cit[1] + " " + partes_cit[0])
            else:
                inv["nombre"] = inv["nombreCitaciones"]

        # 3. Categoría
        m_cat = re.search(r"(?:^|\n)\s*Categor[ií]a(?:\s+Minciencias)?\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_cat:
            cat_raw = clean_text(m_cat.group(1))
            # Si tiene "con vigencia hasta...", limpiar si se desea o conservar
            if " con vigencia" in cat_raw.lower():
                cat_raw = re.split(r"\s+con\s+vigencia", cat_raw, flags=re.IGNORECASE)[0]
            inv["categoriaInvestigador"] = cat_raw

        # 4. Nacionalidad y Sexo
        m_nac = re.search(r"(?:^|\n)\s*Nacionalidad\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_nac:
            inv["nacionalidad"] = clean_text(m_nac.group(1))

        m_sex = re.search(r"(?:^|\n)\s*(?:Sexo|G[eé]nero)\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_sex:
            inv["sexo"] = clean_text(m_sex.group(1))

        # 5. Par evaluador
        if "par evaluador reconocido por minciencias" in text.lower():
            inv["estadoParEvaluador"] = "Reconocido"

        # 6. Identificadores
        m_orcid = re.search(r"\b([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])\b", text)
        if m_orcid:
            inv["orcid"] = clean_text(m_orcid.group(1))

        m_mail = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", text)
        if m_mail:
            inv["correo"] = clean_text(m_mail.group(1))

        # Institución de vinculación actual
        m_inst = re.search(r"(?:^|\n)\s*Experiencia\s+profesional\s*\n\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_inst:
            cand_inst = clean_text(m_inst.group(1))
            if len(cand_inst) > 3:
                inv["institucion"] = cand_inst

        # 7. Código RH
        m_rh = re.search(r"(?:C[oó]digo\s+(?:RH|de\s+investigador|investigador)|Identificaci[oó]n|ID)\s*[:\n]\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
        if m_rh:
            inv["codigoRh"] = clean_text(m_rh.group(1))
        elif inv["orcid"]:
            inv["codigoRh"] = inv["orcid"]
        elif inv["nombre"]:
            # Código determinista legible
            norm_slug = re.sub(r"[^A-Za-z0-9]", "", canonical_key(inv["nombre"]))[:10].upper()
            inv["codigoRh"] = "INV_" + norm_slug
        else:
            inv["codigoRh"] = "INV_001"
            inv["nombre"] = "Investigador de MinCiencias"

        # 8. Líneas de investigación
        m_sec_lineas = re.search(r"L[ií]neas\s+de\s+investigaci[oó]n\s*[:\n](.*?)(?=(?:Formaci[oó]n|Experiencia|Producci[oó]n|Reconocimientos|Idiomas|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_lineas:
            for l_item in m_sec_lineas.group(1).split("\n"):
                cl = clean_text(re.sub(r"^[-*•]\s*", "", l_item))
                # Limpiar ", Activa:Si"
                cl = re.sub(r",\s*Activa\s*:\s*Si", "", cl, flags=re.IGNORECASE).strip()
                if len(cl) > 3:
                    inv["lineasInvestigacion"].append(cl)

        # 9. Formación Académica
        m_sec_form = re.search(r"Formaci[oó]n\s+Acad[eé]mica\s*[:\n](.*?)(?=(?:Experiencia|Producci[oó]n|Reconocimientos|Idiomas|L[ií]neas|Formaci[oó]n\s+Complementaria|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_form:
            for f_item in m_sec_form.group(1).split("\n"):
                cf = clean_text(re.sub(r"^[-*•]\s*", "", f_item))
                if len(cf) > 4:
                    inv["formacionAcademica"].append(cf)

        # 10. Reconocimientos
        m_sec_rec = re.search(r"Reconocimientos\s*[:\n](.*?)(?=(?:Los\s+[ií]tems|Producci[oó]n|Cursos|Trabajos|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_rec:
            for r_item in m_sec_rec.group(1).split("\n"):
                cr = clean_text(re.sub(r"^[-*•]\s*", "", r_item))
                if len(cr) > 4:
                    inv["reconocimientos"].append(cr)

        # 11. Productos (Artículos, Capítulos, Softwares, etc.)
        product_headers = [
            r"Producci[oó]n\s+bibliogr[aá]fica\s*-\s*Art[ií]culo[^\n]*",
            r"Tipo:\s*Cap[ií]tulo\s+de\s+libro[^\n]*",
            r"Tipo:\s*Otro\s+cap[ií]tulo\s+de\s+libro[^\n]*",
            r"Producci[oó]n\s+t[eé]cnica\s*-\s*Softwares[^\n]*",
            r"Producci[oó]n\s+t[eé]cnica\s*-\s*Consultor[ií]a[^\n]*",
            r"Producci[oó]n\s+t[eé]cnica\s*-\s*Cursos\s+de\s+corta\s+duraci[oó]n[^\n]*",
            r"Trabajos\s+dirigidos/Tutor[ií]as\s*-\s*[^\n]+",
            r"Datos\s+complementarios\s*-\s*Jurado[^\n]+",
            r"Producci[oó]n\s+bibliogr[aá]fica\s*-\s*Otro\s+art[ií]culo[^\n]*",
            r"Producci[oó]n\s+bibliogr[aá]fica\s*-\s*Documento\s+de\s+trabajo[^\n]*",
            r"Producci[oó]n\s+t[eé]cnica\s*-\s*Innovaci[oó]n\s+de\s+proceso[^\n]*",
            r"Producci[oó]n\s+t[eé]cnica\s*-\s*Empresa\s+de\s+base\s+tecnol[oó]gica[^\n]*",
            r"Dem[aá]s\s+trabajos\s*-\s*Dem[aá]s\s+trabajos[^\n]*"
        ]

        header_combined = "|".join(f"(?:{h})" for h in product_headers)
        pat_prod = re.compile(rf"(?:^|\n)({header_combined})\n", re.IGNORECASE)

        p_matches = list(pat_prod.finditer(text))
        p_seen = set()

        idx_p = 0
        while idx_p < len(p_matches):
            p_start = p_matches[idx_p].end()
            p_end = p_matches[idx_p + 1].start() if idx_p + 1 < len(p_matches) else len(text)
            tipo_header = p_matches[idx_p].group(1).strip()
            bloque = text[p_start:p_end].strip()

            # Extraer titulo
            titulo_p = ""
            m_comillas = re.search(r'"([^"\r\n]{5,})"', bloque)
            if m_comillas:
                titulo_p = m_comillas.group(1).strip()
            else:
                m_tit_lbl = re.search(r'Titulo:\s*([^\n\r]+)', bloque, re.IGNORECASE)
                if m_tit_lbl:
                    titulo_p = m_tit_lbl.group(1).strip()
                else:
                    lineas_b = [l.strip() for l in bloque.split("\n") if l.strip()]
                    if len(lineas_b) > 0:
                        primera = lineas_b[0]
                        partes = primera.split(",")
                        if len(partes) > 1 and len(partes[-1].strip()) > 5 and not partes[-1].strip().lower().startswith("tipo:"):
                            titulo_p = partes[-1].strip()
                        elif len(lineas_b) > 1 and len(lineas_b[1]) > 5:
                            titulo_p = lineas_b[1]
                        else:
                            titulo_p = primera

            # Limpiezas de prefijo
            titulo_p = clean_text(titulo_p)
            titulo_p = re.sub(r'^[•\-\*#]+\s*', '', titulo_p)
            titulo_p = re.sub(r'^\d+\s*[\.\-\)]\s*', '', titulo_p)

            # Extraer año
            anios = re.findall(r'\b(19\d\d|20[0-3]\d)\b', bloque)
            anio_p = 0
            if len(anios) > 0:
                anio_p = int(anios[-1])

            # Categoría
            cat_p = "Artículo"
            t_low = tipo_header.lower()
            if "software" in t_low:
                cat_p = "Software"
            elif "capítulo" in t_low or "capitulo" in t_low or "libro" in t_low:
                cat_p = "Capítulo de libro"
            elif "consultor" in t_low:
                cat_p = "Consultoría"
            elif "tutoria" in t_low or "trabajos dirigidos" in t_low:
                cat_p = "Trabajo dirigido"
            elif "jurado" in t_low:
                cat_p = "Jurado / Evaluación"
            elif "empresa" in t_low:
                cat_p = "Empresa de base tecnológica"

            if len(titulo_p) > 4:
                firma = (canonical_key(titulo_p), anio_p)
                if firma not in p_seen:
                    p_seen.add(firma)
                    prod_dict = {
                        "idProducto": "PROD_" + str(len(inv["productos"]) + 1).zfill(3),
                        "titulo": titulo_p,
                        "categoria": cat_p,
                        "validado": True,
                        "anio": anio_p,
                        "tipoProducto": cat_p,
                        "autores": [inv["nombre"]] if inv["nombre"] else []
                    }
                    inv["productos"].append(prod_dict)
            idx_p += 1

        return inv


# Probar el extractor mejorado
extractor = ImprovedPDFExtractor()
pdf_adith = r"C:\Users\camil\Desktop\Aith Bismarck.pdf"
print("=== PROBANDO ADITH CON EXTRACTOR MEJORADO ===")
text_adith = extractor.extract_text(pdf_adith)
print("Gatekeeper:", extractor.verify_gatekeeper(text_adith))
tipo_part, segs = extractor.partition_document(text_adith)
print("Tipo particionado:", tipo_part, "Total segmentos:", len(segs))
if tipo_part == "INVESTIGADOR":
    inv_data = extractor.parse_investigator(segs[0]["texto"])
    print("Nombre:", inv_data["nombre"])
    print("Codigo:", inv_data["codigoRh"])
    print("Categoria:", inv_data["categoriaInvestigador"])
    print("Nacionalidad:", inv_data["nacionalidad"])
    print("Total productos extraidos:", len(inv_data["productos"]))
    print("Primeros 5 productos:")
    for p in inv_data["productos"][:5]:
        print(f"  [{p['categoria']}] ({p['anio']}) -> {p['titulo'][:50]}")

print("\n=== PROBANDO SOLICITUD DE PERMISOS ===")
pdf_sol = r"C:\Users\camil\Downloads\Solicitud de Permisos.pdf"
text_sol = extractor.extract_text(pdf_sol)
print("Gatekeeper solicitud permiso:", extractor.verify_gatekeeper(text_sol))
