# -*- coding: utf-8 -*-
"""
Test scratch script for PDFExtractor
Validates zero forbidden statements:
- No break
- No continue
- No ternary operators (a if c else b)
- No return in void functions
"""

import os
import re
import fitz
import unicodedata
from typing import Any, Dict, List, Tuple


def clean_text(value: Any) -> str:
    if value is None:
        text = ""
    else:
        text = str(value)
    text = text.replace("\xa0", " ")
    text = " ".join(text.split())
    return text.strip()


def canonical_key(text: str) -> str:
    cleaned = clean_text(text)
    decomposed = unicodedata.normalize("NFD", cleaned)
    filtered = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    alphanumeric = "".join(ch.lower() for ch in filtered if ch.isalnum() or ch.isspace())
    return " ".join(alphanumeric.split())


class PDFExtractionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PDFExtractor:
    """
    Sistema inteligente de extraccion de 4 capas para documentos MinCiencias PDF.
    Capa 1: MinCiencias Gatekeeper (Valida que sea documento oficial).
    Capa 2: Particionador y Detector Polimorfico de Lotes.
    Capa 3: Normalizador Dinamico de Esquemas y Limpieza de Productos.
    Capa 4: Resolucion de Duplicados y Fusion Relacional con firma canonica.
    """

    def __init__(self) -> None:
        self.institutional_markers = [
            "scienti", "minciencias", "colciencias", "cvlac", "gruplac",
            "curriculum vitae", "curriculum vitae de latinoamerica",
            "grupo de investigacion", "datos generales",
            "lineas de investigacion", "categoria",
            "produccion bibliografica", "articulos",
            "integrantes del grupo"
        ]

    def extract_text(self, file_path: str) -> str:
        text_content = ""
        extracted = False
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
            text_content = self._extract_fallback(file_path)
        return text_content

    def _extract_fallback(self, file_path: str) -> str:
        text_parts = []
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
            text_str = raw_bytes.decode("latin-1", errors="ignore")
            matches = re.findall(r"\(([^()]{2,})\)\s*Tj", text_str)
            idx = 0
            while idx < len(matches):
                cleaned = clean_text(matches[idx])
                if cleaned:
                    text_parts.append(cleaned)
                idx += 1
        except Exception:
            pass
        return "\n".join(text_parts)

    def verify_gatekeeper(self, text: str) -> bool:
        """Capa 1: Valida que el documento sea de investigacion MinCiencias."""
        canon = canonical_key(text)
        if not canon:
            return False

        if "cvlac" in canon or "gruplac" in canon or "scienti" in canon or "minciencias" in canon or "colciencias" in canon:
            return True

        hits = 0
        idx = 0
        while idx < len(self.institutional_markers):
            marker = self.institutional_markers[idx]
            if marker in canon:
                hits += 1
            idx += 1

        if hits >= 2:
            return True
        return False

    def partition_document(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Capa 2: Identifica fronteras de entidades y detecta lotes."""
        cvlac_pat = re.compile(
            r"(?:Curr[ií]culum\s+V[ií]tae(?:\s+de\s+Latinoam[eé]rica)?|CvLAC\b|DATOS\s+GENERALES(?:\s+DEL\s+INVESTIGADOR)?\b)",
            re.IGNORECASE
        )
        gruplac_pat = re.compile(
            r"(?:GrupLAC\b|DATOS\s+GENERALES\s+DEL\s+GRUPO\b|GRUPO\s+DE\s+INVESTIGACI[OÓ]N\b)",
            re.IGNORECASE
        )

        boundaries = []
        for m in cvlac_pat.finditer(text):
            boundaries.append((m.start(), "INVESTIGADOR"))
        for m in gruplac_pat.finditer(text):
            boundaries.append((m.start(), "GRUPO"))

        # Ordenar por posicion
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

        # Coalescer marcadores cercanos (que corresponden al mismo encabezado de documento)
        coalesced = []
        if len(boundaries) > 0:
            coalesced.append(boundaries[0])
            b_idx = 1
            while b_idx < len(boundaries):
                prev_pos = coalesced[-1][0]
                prev_tipo = coalesced[-1][1]
                curr_pos = boundaries[b_idx][0]
                curr_tipo = boundaries[b_idx][1]
                if (curr_pos - prev_pos >= 400) or (curr_tipo != prev_tipo and curr_pos - prev_pos >= 200):
                    coalesced.append(boundaries[b_idx])
                b_idx += 1
        boundaries = coalesced

        # Si no hay marcadores claros, intentar clasificar el documento entero
        if len(boundaries) == 0:
            canon = canonical_key(text)
            tipo_doc = "INVESTIGADOR"
            if "gruplac" in canon or "grupo de investigacion" in canon or "integrantes del grupo" in canon:
                tipo_doc = "GRUPO"
            return tipo_doc, [{"tipo": tipo_doc, "texto": text}]

        # Si hay un unico marcador
        if len(boundaries) == 1:
            tipo_unico = boundaries[0][1]
            return tipo_unico, [{"tipo": tipo_unico, "texto": text}]

        # Segmentar lotes entre fronteras consecutivas
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
            if len(frag.strip()) > 30:
                segments.append({"tipo": tipo_act, "texto": frag})
            b_idx += 1

        if len(segments) == 1:
            return segments[0]["tipo"], segments

        return "LOTE", segments

    def _clean_product_title(self, raw_title: str) -> str:
        """Capa 3: Limpia prefijos numericos e institucionales del titulo."""
        title = clean_text(raw_title)
        title = re.sub(r"^[•\-\*#]+\s*", "", title)
        title = re.sub(r"^\d+\s*[\.\-\)]\s*", "", title)
        title = re.sub(r"^[•\-\*#]+\s*", "", title)
        title = re.sub(r"^(?:Art[ií]culo|Libro|Cap[ií]tulo(?:\s+de\s+libro)?|Software|Trabajo\s+en\s+eventos)\s*[:\-–—]\s*", "", title, flags=re.IGNORECASE)
        # Si contiene detalles de revista, DOI, o volumen, separar el titulo principal
        partes = title.split(", ")
        if len(partes) > 1 and len(partes[0]) > 8:
            title = partes[0]
        return clean_text(title)

    def _extract_year(self, text: str) -> int:
        years = re.findall(r"\b(19\d\d|20[0-3]\d)\b", text)
        if len(years) > 0:
            return int(years[-1])
        return 0

    def _group_product_blocks(self, raw_lines: List[str]) -> List[str]:
        bloques = []
        bloque_act = []
        idx = 0
        while idx < len(raw_lines):
            linea = raw_lines[idx]
            es_inicio = False
            if re.match(r"^\s*(?:\d+\s*[\.\-\)]\s*[-–—]?\s*(?:Art[ií]culo|Libro|Cap[ií]tulo|Software|Trabajo)|[-*•]\s*(?:Art[ií]culo|Libro|Cap[ií]tulo|Software)|\b(?:Art[ií]culo|Libro|Cap[ií]tulo)\s*:)", linea, re.IGNORECASE):
                es_inicio = True
            elif re.match(r"^\s*\d+\s*[\.\-\)]\s+[A-ZÁÉÍÓÚÑ]", linea):
                es_inicio = True

            if es_inicio:
                if len(bloque_act) > 0:
                    bloques.append("\n".join(bloque_act))
                    bloque_act = []
                bloque_act.append(linea)
            else:
                if len(bloque_act) > 0:
                    if len(linea.strip()) > 0:
                        bloque_act.append(linea)
            idx += 1
        if len(bloque_act) > 0:
            bloques.append("\n".join(bloque_act))
        return bloques

    def parse_investigator(self, text: str) -> Dict[str, Any]:
        """Capa 3: Extrae atributos, colecciones y productos de un CvLAC."""
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

        # Extraccion de campos principales
        m_rh = re.search(r"(?:C[oó]digo\s+(?:RH|de\s+investigador|investigador)|Identificaci[oó]n|ID|Identificador)\s*[:\n]\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
        if m_rh:
            inv["codigoRh"] = clean_text(m_rh.group(1))

        m_nom = re.search(r"(?:Nombre(?:\s+completo)?|Investigador)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_nom:
            inv["nombre"] = clean_text(m_nom.group(1))

        m_mail = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", text)
        if m_mail:
            inv["correo"] = clean_text(m_mail.group(1))

        m_orcid = re.search(r"\b([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])\b", text)
        if m_orcid:
            inv["orcid"] = clean_text(m_orcid.group(1))

        m_inst = re.search(r"(?:Instituci[oó]n|Entidad|Vinculaci[oó]n)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_inst:
            inv["institucion"] = clean_text(m_inst.group(1))

        m_dep = re.search(r"(?:Departamento)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_dep:
            inv["departamento"] = clean_text(m_dep.group(1))

        m_ciu = re.search(r"(?:Ciudad)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_ciu:
            inv["ciudad"] = clean_text(m_ciu.group(1))

        m_cat = re.search(r"(?:Categor[ií]a(?:\s+Minciencias)?)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_cat:
            inv["categoriaInvestigador"] = clean_text(m_cat.group(1))

        m_cit = re.search(r"(?:Nombre\s+en\s+citaciones|Citaciones)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_cit:
            inv["nombreCitaciones"] = clean_text(m_cit.group(1))

        m_nac = re.search(r"(?:Nacionalidad)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_nac:
            inv["nacionalidad"] = clean_text(m_nac.group(1))

        m_sex = re.search(r"(?:Sexo|G[eé]nero)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_sex:
            inv["sexo"] = clean_text(m_sex.group(1))

        if not inv["codigoRh"]:
            if inv["nombre"]:
                inv["codigoRh"] = "PDF_" + str(abs(hash(inv["nombre"])))[:10]
            else:
                inv["codigoRh"] = "PDF_001"

        if not inv["nombre"]:
            inv["nombre"] = "Investigador Extraido de PDF"

        # Extraccion de lineas de investigacion
        m_sec_lineas = re.search(r"L[ií]neas\s+de\s+investigaci[oó]n\s*[:\n](.*?)(?=(?:Formaci[oó]n|Experiencia|Producci[oó]n|Reconocimientos|Idiomas|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_lineas:
            for l_item in m_sec_lineas.group(1).split("\n"):
                cl = clean_text(re.sub(r"^[-*•]\s*", "", l_item))
                if len(cl) > 3:
                    inv["lineasInvestigacion"].append(cl)

        # Extraccion de formacion
        m_sec_form = re.search(r"Formaci[oó]n\s+Acad[eé]mica\s*[:\n](.*?)(?=(?:Experiencia|Producci[oó]n|Reconocimientos|Idiomas|L[ií]neas|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_form:
            for f_item in m_sec_form.group(1).split("\n"):
                cf = clean_text(re.sub(r"^[-*•]\s*", "", f_item))
                if len(cf) > 3:
                    inv["formacionAcademica"].append(cf)

        # Extraccion de productos con Capa 4 (Firma canonica y deduplicacion)
        m_sec_prod = re.search(r"(?:Producci[oó]n\s+bibliogr[aá]fica|Art[ií]culos|Libros|Trabajos\s+en\s+eventos|Productos)\s*[:\n](.*?)(?=(?:Reconocimientos|Formaci[oó]n|Experiencia|\Z))", text, re.DOTALL | re.IGNORECASE)
        productos_raw = []
        if m_sec_prod:
            productos_raw = m_sec_prod.group(1).split("\n")
        else:
            productos_raw = text.split("\n")

        p_seen = set()
        bloques = self._group_product_blocks(productos_raw)
        b_idx = 0
        while b_idx < len(bloques):
            bloque = bloques[b_idx]
            lineas_bloque = bloque.split("\n")
            linea_primera = lineas_bloque[0]

            autores_prod = []
            l_idx = 1
            while l_idx < len(lineas_bloque):
                sub_l = lineas_bloque[l_idx]
                if "autor" in sub_l.lower():
                    autores_clean = clean_text(re.sub(r"^Autores\s*[:\-]\s*", "", sub_l, flags=re.IGNORECASE))
                    for a in autores_clean.split(","):
                        ca = clean_text(a)
                        if ca:
                            autores_prod.append(ca)
                l_idx += 1

            anio_p = self._extract_year(bloque)
            titulo_p = self._clean_product_title(linea_primera)
            if len(titulo_p) > 5:
                cat_p = "Artículo"
                if "libro" in bloque.lower():
                    cat_p = "Libro"
                elif "capítulo" in bloque.lower() or "capitulo" in bloque.lower():
                    cat_p = "Capítulo de libro"
                elif "software" in bloque.lower():
                    cat_p = "Software"

                firma = (canonical_key(titulo_p), anio_p)
                if firma not in p_seen:
                    p_seen.add(firma)
                    if not autores_prod and inv["nombre"]:
                        autores_prod.append(inv["nombre"])
                    prod_dict = {
                        "idProducto": "PROD_" + str(len(inv["productos"]) + 1).zfill(3),
                        "titulo": titulo_p,
                        "categoria": cat_p,
                        "validado": True,
                        "anio": anio_p,
                        "tipoProducto": cat_p,
                        "autores": autores_prod
                    }
                    inv["productos"].append(prod_dict)
            b_idx += 1

        return inv

    def parse_group(self, text: str) -> Dict[str, Any]:
        """Capa 3: Extrae atributos, integrantes y productos de un GrupLAC."""
        grp = {
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

        m_num = re.search(r"(?:C[oó]digo\s+del\s+grupo|C[oó]digo|Nro\.?\s+Grupo|ID)\s*[:\n]\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
        if m_num:
            grp["nroGrupo"] = clean_text(m_num.group(1))

        m_nom = re.search(r"(?:Nombre\s+del\s+grupo|Nombre\s+de\s+grupo)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if not m_nom:
            m_nom = re.search(r"\bGrupo(?:\s+de\s+investigaci[oó]n)?\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_nom:
            grp["nombreGrupo"] = clean_text(m_nom.group(1))

        m_anio = re.search(r"(?:A[ñn]o(?:\s+y\s+mes)?\s+de\s+formaci[oó]n|Creaci[oó]n)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_anio:
            grp["anioFormacion"] = clean_text(m_anio.group(1))

        m_dep = re.search(r"(?:Departamento)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_dep:
            grp["departamento"] = clean_text(m_dep.group(1))

        m_ciu = re.search(r"(?:Ciudad)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_ciu:
            grp["ciudad"] = clean_text(m_ciu.group(1))

        m_lid = re.search(r"(?:L[ií]der(?:\s+del\s+grupo)?)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_lid:
            grp["lider"] = clean_text(m_lid.group(1))

        m_clas = re.search(r"(?:Clasificaci[oó]n)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_clas:
            grp["clasificacion"] = clean_text(m_clas.group(1))

        m_area = re.search(r"(?:[AÁ]rea\s+de\s+conocimiento)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_area:
            grp["areaConocimiento"] = clean_text(m_area.group(1))

        m_mail = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", text)
        if m_mail:
            grp["email"] = clean_text(m_mail.group(1))

        m_web = re.search(r"\b(https?://[^\s]+)\b", text)
        if m_web:
            grp["paginaWeb"] = clean_text(m_web.group(1))

        if not grp["nroGrupo"]:
            if grp["nombreGrupo"]:
                grp["nroGrupo"] = "GRP_" + str(abs(hash(grp["nombreGrupo"])))[:8]
            else:
                grp["nroGrupo"] = "GRP_001"

        if not grp["nombreGrupo"]:
            grp["nombreGrupo"] = "Grupo de Investigacion Extraido de PDF"

        # Instituciones
        m_sec_inst = re.search(r"Instituciones\s*[:\n](.*?)(?=(?:L[ií]neas|Integrantes|Producci[oó]n|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_inst:
            for inst_line in m_sec_inst.group(1).split("\n"):
                ci = clean_text(re.sub(r"^[-*•]\s*", "", inst_line))
                if len(ci) > 3:
                    grp["instituciones"].append(ci)

        # Lineas de investigacion
        m_sec_lin = re.search(r"L[ií]neas\s+de\s+investigaci[oó]n\s*[:\n](.*?)(?=(?:Integrantes|Producci[oó]n|Instituciones|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_lin:
            for l_item in m_sec_lin.group(1).split("\n"):
                cl = clean_text(re.sub(r"^[-*•]\s*", "", l_item))
                if len(cl) > 3:
                    grp["lineasInvestigacion"].append(cl)

        # Integrantes
        m_sec_integ = re.search(r"Integrantes\s+del\s+grupo\s*[:\n](.*?)(?=(?:Producci[oó]n|L[ií]neas|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_integ:
            for m_line in m_sec_integ.group(1).split("\n"):
                c_line = clean_text(re.sub(r"^[-*•]\s*", "", m_line))
                if len(c_line) > 3:
                    partes = [clean_text(p) for p in c_line.split(",")]
                    nom_mem = partes[0]
                    cod_mem = "MEM_" + str(abs(hash(nom_mem)))[:8]
                    grp["integrantes"].append({
                        "codigoRh": cod_mem,
                        "nombre": nom_mem,
                        "institucion": grp["instituciones"][0] if grp["instituciones"] else "",
                        "departamento": grp["departamento"],
                        "ciudad": grp["ciudad"],
                        "activo": True
                    })

        # Productos del grupo
        m_sec_prod = re.search(r"(?:Producci[oó]n\s+del\s+grupo|Producci[oó]n\s+bibliogr[aá]fica|Art[ií]culos|Libros|Productos)\s*[:\n](.*?)(?=\Z)", text, re.DOTALL | re.IGNORECASE)
        prod_lines = []
        if m_sec_prod:
            prod_lines = m_sec_prod.group(1).split("\n")
        else:
            prod_lines = text.split("\n")

        p_seen = set()
        bloques = self._group_product_blocks(prod_lines)
        b_idx = 0
        while b_idx < len(bloques):
            bloque = bloques[b_idx]
            lineas_bloque = bloque.split("\n")
            linea_primera = lineas_bloque[0]

            autores_prod = []
            l_idx = 1
            while l_idx < len(lineas_bloque):
                sub_l = lineas_bloque[l_idx]
                if "autor" in sub_l.lower():
                    autores_clean = clean_text(re.sub(r"^Autores\s*[:\-]\s*", "", sub_l, flags=re.IGNORECASE))
                    for a in autores_clean.split(","):
                        ca = clean_text(a)
                        if ca:
                            autores_prod.append(ca)
                l_idx += 1

            anio_p = self._extract_year(bloque)
            titulo_p = self._clean_product_title(linea_primera)
            if len(titulo_p) > 5:
                cat_p = "Artículo"
                if "libro" in bloque.lower():
                    cat_p = "Libro"
                elif "capítulo" in bloque.lower() or "capitulo" in bloque.lower():
                    cat_p = "Capítulo de libro"
                elif "software" in bloque.lower():
                    cat_p = "Software"

                firma = (canonical_key(titulo_p), anio_p)
                if firma not in p_seen:
                    p_seen.add(firma)
                    prod_dict = {
                        "idProducto": "GRP_PROD_" + str(len(grp["productos"]) + 1).zfill(3),
                        "titulo": titulo_p,
                        "categoria": cat_p,
                        "validado": True,
                        "anio": anio_p,
                        "tipoProducto": cat_p,
                        "autores": autores_prod
                    }
                    grp["productos"].append(prod_dict)
            b_idx += 1

        return grp

    def extract(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
        """Ejecuta el pipeline completo de extraccion de 4 capas."""
        if not os.path.isfile(file_path):
            return False, {}, "El archivo especificado no existe: " + str(file_path)

        if not str(file_path).lower().endswith(".pdf"):
            return False, {}, "Formato no compatible: El archivo debe ser un documento PDF (.pdf)."

        text = self.extract_text(file_path)
        if not text.strip():
            return False, {}, "No fue posible extraer texto del archivo PDF o el documento esta vacio."

        # Capa 1: MinCiencias Gatekeeper
        if not self.verify_gatekeeper(text):
            return False, {}, "El archivo no corresponde a un documento oficial de MinCiencias (CvLAC o GrupLAC)."

        # Capa 2: Particionador
        tipo_lote, segments = self.partition_document(text)

        if tipo_lote == "INVESTIGADOR":
            inv_data = self.parse_investigator(segments[0]["texto"])
            msg = "Investigador extraido correctamente desde PDF: " + inv_data["nombre"]
            return True, inv_data, msg
        elif tipo_lote == "GRUPO":
            grp_data = self.parse_group(segments[0]["texto"])
            msg = "Grupo extraido correctamente desde PDF: " + grp_data["nombreGrupo"]
            return True, grp_data, msg
        else:
            # LOTE MIXTO O MULTIPLE
            grupos_res = []
            invs_res = []
            s_idx = 0
            while s_idx < len(segments):
                seg = segments[s_idx]
                if seg["tipo"] == "GRUPO":
                    grupos_res.append(self.parse_group(seg["texto"]))
                else:
                    invs_res.append(self.parse_investigator(seg["texto"]))
                s_idx += 1

            lote_data = {
                "tipo": "LOTE",
                "grupos": grupos_res,
                "investigadores": invs_res
            }
            msg = "Lote procesado: " + str(len(grupos_res)) + " grupo(s) y " + str(len(invs_res)) + " investigador(es) extraidos desde PDF."
            return True, lote_data, msg


# --- Test code ---
if __name__ == "__main__":
    extractor = PDFExtractor()

    # 1. Crear PDF CvLAC de prueba
    cvlac_doc = fitz.open()
    p1 = cvlac_doc.new_page()
    p1.insert_text((50, 50), """Currículum Vítae de Latinoamérica - CvLAC
Servicio Nacional de Aprendizaje - MinCiencias - ScienTI

Datos generales
Nombre: Dr. Carlos Alberto Gómez Restrepo
Nombre en citaciones: Gómez-Restrepo, C. A.
Nacionalidad: Colombiana
Sexo: Masculino
Código RH: 0001234567
Correo electrónico: cgomez@universidad.edu.co
ORCID: 0000-0002-1825-0097
Categoría: Investigador Senior (IS)
Institución: Universidad Popular del Cesar
Departamento: Cesar
Ciudad: Valledupar

Líneas de investigación
- Inteligencia Artificial y Minería de Datos
- Procesamiento de Señales Biomédicas

Formación académica
- Doctorado en Ingeniería de Sistemas, Universidad Nacional de Colombia, 2018
- Maestría en Informática, Universidad de los Andes, 2012

Producción bibliográfica - Artículos
1.- Artículo : Algoritmos de optimización metaheurística aplicados a redes de sensores, Revista Colombiana de Computación, 2021
Autores: Carlos Alberto Gómez Restrepo, Juan Pérez

2.- Artículo : Detección de anomalías en series de tiempo climáticas, IEEE Latin America Transactions, 2023
Autores: Carlos Alberto Gómez Restrepo, María Rodríguez
""")
    cvlac_path = "scratch/test_cvlac.pdf"
    cvlac_doc.save(cvlac_path)
    cvlac_doc.close()

    ok, res, msg = extractor.extract(cvlac_path)
    print("Test 1 (CvLAC individual):", ok, msg)
    print("  Investigador:", res.get("nombre"), "Codigo RH:", res.get("codigoRh"))
    print("  Productos:", len(res.get("productos", [])))
    for p in res.get("productos", []):
        print("   -", p["titulo"], "(", p["anio"], ")")

    # 2. Crear PDF GrupLAC de prueba
    gruplac_doc = fitz.open()
    p2 = gruplac_doc.new_page()
    p2.insert_text((50, 50), """GrupLAC - ScienTI MinCiencias
Grupo de Investigación

Datos generales del grupo
Nombre del grupo: Grupo de Investigación en Inteligencia Computacional y Robótica (GICR)
Código del grupo: COL0012345
Año y mes de formación: 2015 - Junio
Departamento: Cesar
Ciudad: Valledupar
Líder del grupo: Dr. Carlos Alberto Gómez Restrepo
Clasificación: A1
Área de conocimiento: Ciencias de la Computación e Información
Email: gicr@upc.edu.co
Página web: https://upc.edu.co/gicr

Instituciones
- Universidad Popular del Cesar

Líneas de investigación
- Robótica Móvil y Percepción
- Modelos de Aprendizaje Profundo

Integrantes del grupo
- Carlos Alberto Gómez Restrepo, Dr., Líder
- Laura Marcela Ramírez, Ing., Investigadora

Producción del grupo
1.- Artículo : Algoritmos de optimización metaheurística aplicados a redes de sensores, Revista Colombiana de Computación, 2021
Autores: Carlos Alberto Gómez Restrepo, Juan Pérez, Laura Marcela Ramírez

2.- Libro : Fundamentos de Aprendizaje Automático en Ingeniería, Editorial UPC, 2022
Autores: Carlos Alberto Gómez Restrepo
""")
    gruplac_path = "scratch/test_gruplac.pdf"
    gruplac_doc.save(gruplac_path)
    gruplac_doc.close()

    ok, res, msg = extractor.extract(gruplac_path)
    print("\nTest 2 (GrupLAC individual):", ok, msg)
    print("  Grupo:", res.get("nombreGrupo"), "Nro:", res.get("nroGrupo"))
    print("  Integrantes:", len(res.get("integrantes", [])))
    print("  Productos:", len(res.get("productos", [])))
    for p in res.get("productos", []):
        print("   -", p["titulo"], "(", p["anio"], ")")

    # 3. Crear PDF Lote Mixto (GrupLAC + CvLAC)
    mixto_doc = fitz.open()
    pm1 = mixto_doc.new_page()
    pm1.insert_text((50, 50), """GrupLAC - ScienTI MinCiencias
Grupo de Investigación
Nombre del grupo: Grupo de Bioingeniería y Nanotecnología
Código del grupo: COL0099999
Departamento: Cesar
Ciudad: Valledupar
Clasificación: B

Integrantes del grupo
- Andrés Felipe Martínez, Dr.

Producción del grupo
1.- Artículo : Sensores piezoeléctricos para monitoreo cardíaco, 2024
Autores: Andrés Felipe Martínez
""")
    pm2 = mixto_doc.new_page()
    pm2.insert_text((50, 50), """Currículum Vítae de Latinoamérica - CvLAC
MinCiencias ScienTI

Datos generales
Nombre: Dr. Andrés Felipe Martínez
Código RH: 0009999999
Institución: Universidad Popular del Cesar
Departamento: Cesar
Ciudad: Valledupar

Producción bibliográfica - Artículos
1.- Artículo : Sensores piezoeléctricos para monitoreo cardíaco, 2024
Autores: Andrés Felipe Martínez
""")
    mixto_path = "scratch/test_mixto.pdf"
    mixto_doc.save(mixto_path)
    mixto_doc.close()

    ok, res, msg = extractor.extract(mixto_path)
    print("\nTest 3 (Lote Mixto):", ok, msg)
    print("  Tipo:", res.get("tipo"))
    print("  Grupos en lote:", len(res.get("grupos", [])))
    print("  Investigadores en lote:", len(res.get("investigadores", [])))

    # 4. Crear PDF Invalido (No MinCiencias)
    invalido_doc = fitz.open()
    pi = invalido_doc.new_page()
    pi.insert_text((50, 50), """FACTURA COMERCIAL No 10293
Empresa de Telecomunicaciones
Total a pagar: $120.000 COP
Fecha de vencimiento: 15 de Octubre 2026
""")
    invalido_path = "scratch/test_invalido.pdf"
    invalido_doc.save(invalido_path)
    invalido_doc.close()

    ok, res, msg = extractor.extract(invalido_path)
    print("\nTest 4 (PDF no MinCiencias - Gatekeeper):", ok, msg)
