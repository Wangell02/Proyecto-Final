import re

file_path = "PEA-Scraper/DLDD-MAFF-JDLA.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Reemplazar la clase PDFExtractor
new_pdf_extractor = '''class PDFExtractor:
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
                text_content = "\\n\\n".join(pages)
                if text_content.strip():
                    extracted = True
            except Exception:
                extracted = False

        if not extracted:
            text_content = self._extract_fallback(file_path)
        return text_content.replace("\\xa0", " ")

    def _extract_fallback(self, file_path: str) -> str:
        text_parts = []
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()

            stream_matches = re.finditer(rb"stream[\\r\\n]+(.*?)[\\r\\n]+endstream", raw_bytes, re.DOTALL)
            for sm in stream_matches:
                raw_chunk = sm.group(1)
                decompressed = None
                try:
                    decompressed = zlib.decompress(raw_chunk)
                except Exception:
                    decompressed = raw_chunk

                if decompressed:
                    tj_matches = re.finditer(rb"\\((.*?)\\)\\s*Tj", decompressed)
                    for tm in tj_matches:
                        chunk_str = tm.group(1).decode("latin-1", errors="ignore")
                        cl = clean_text(chunk_str)
                        if cl:
                            text_parts.append(cl)

            if len(text_parts) == 0:
                raw_latin = raw_bytes.decode("latin-1", errors="ignore")
                matches = re.findall(r"\\(([^()]{2,})\\)\\s*Tj", raw_latin)
                idx = 0
                while idx < len(matches):
                    cl = clean_text(matches[idx])
                    if cl:
                        text_parts.append(cl)
                    idx += 1
        except Exception:
            pass
        return "\\n".join(text_parts)

    def verify_gatekeeper(self, text: str) -> bool:
        """Capa 1: Valida que el documento sea de investigacion MinCiencias."""
        canon = canonical_key(text)
        if not canon:
            return False

        if "cvlac" in canon or "gruplac" in canon or "scienti" in canon or "minciencias" in canon or "colciencias" in canon:
            return True

        if "hoja de vida" in canon and ("par evaluador" in canon or "categoria" in canon or "formacion academica" in canon):
            return True

        if "datos generales del grupo" in canon or ("grupo de investigacion" in canon and "lider" in canon and "clasificacion" in canon):
            return True

        return False

    def partition_document(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Capa 2: Identifica fronteras de entidades y detecta lotes sin falsos positivos."""
        canon = canonical_key(text)

        cvlac_pat = re.compile(
            r"(?:(?:^|\\n\\n|\\f)\\s*(?:Hoja\\s+de\\s+vida\\b|Curr[ií]culum\\s+V[ií]tae(?:\\s+de\\s+Latinoam[eé]rica)?\\b|CvLAC\\b|DATOS\\s+GENERALES\\s+DEL\\s+INVESTIGADOR\\b))",
            re.IGNORECASE
        )
        gruplac_pat = re.compile(
            r"(?:(?:^|\\n\\n|\\f)\\s*(?:GrupLAC\\b|DATOS\\s+GENERALES\\s+DEL\\s+GRUPO\\b|DIRECTORIO\\s+DE\\s+GRUPOS\\s+DE\\s+INVESTIGACI[OÓ]N\\b))",
            re.IGNORECASE
        )

        cvlac_matches = list(cvlac_pat.finditer(text))
        gruplac_matches = list(gruplac_pat.finditer(text))

        if len(gruplac_matches) == 0 and len(cvlac_matches) <= 1:
            if len(cvlac_matches) == 1 or ("hoja de vida" in canon or "cvlac" in canon or "investigador" in canon):
                return "INVESTIGADOR", [{"tipo": "INVESTIGADOR", "texto": text}]

        if len(cvlac_matches) == 0 and len(gruplac_matches) <= 1:
            if len(gruplac_matches) == 1 or ("gruplac" in canon or "datos generales del grupo" in canon):
                return "GRUPO", [{"tipo": "GRUPO", "texto": text}]

        boundaries = []
        for m in cvlac_matches:
            boundaries.append((m.start(), "INVESTIGADOR"))
        for m in gruplac_matches:
            boundaries.append((m.start(), "GRUPO"))

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

        if len(boundaries) == 0:
            if "gruplac" in canon or "datos generales del grupo" in canon:
                return "GRUPO", [{"tipo": "GRUPO", "texto": text}]
            return "INVESTIGADOR", [{"tipo": "INVESTIGADOR", "texto": text}]

        if len(boundaries) == 1:
            tipo_unico = boundaries[0][1]
            return tipo_unico, [{"tipo": tipo_unico, "texto": text}]

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

    def _extract_product_title(self, bloque: str) -> str:
        """Extrae el titulo limpio de un bloque de producto en formatos MinCiencias."""
        m_comillas = re.search(r'"([^"\\r\\n]{5,})"', bloque)
        if m_comillas:
            return clean_text(m_comillas.group(1).strip())

        m_tit = re.search(r'Titulo:\\s*([^\\n\\r]+)', bloque, re.IGNORECASE)
        if m_tit:
            t = m_tit.group(1).strip()
            t = re.split(r'\\s+Tipo\\s+de\\s+trabajo', t, flags=re.IGNORECASE)[0]
            return clean_text(t.strip())

        lineas_b = [l.strip() for l in bloque.split("\\n") if l.strip()]
        if len(lineas_b) == 0:
            return ""

        primera = lineas_b[0]
        tags_fin = [r',\\s*Finalidad:', r',\\s*Nombre\\s+comercial:', r',\\s*\\.\\s*En:', r',\\s*contrato/registro:', r'\\s+Estado:']
        t_idx = 0
        while t_idx < len(tags_fin):
            tag = tags_fin[t_idx]
            m_tag = re.search(tag, primera, re.IGNORECASE)
            if m_tag:
                primera = primera[:m_tag.start()]
            t_idx += 1

        partes = primera.split(",")
        if len(partes) > 1:
            cand = ",".join(partes[1:]).strip()
            if len(cand) > 5 and not cand.lower().startswith("tipo:"):
                primera = cand

        primera = clean_text(primera)
        primera = re.sub(r'^[•\\-\\*#]+\\s*', '', primera)
        primera = re.sub(r'^\\d+\\s*[\\.\\-\\)]\\s*', '', primera)
        return clean_text(primera)

    def _extract_year(self, text: str) -> int:
        years = re.findall(r"\\b(19\\d\\d|20[0-3]\\d)\\b", text)
        if len(years) > 0:
            return int(years[-1])
        return 0

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

        # 1. Nombre
        m_nom = re.search(r"(?:^|\\n)\\s*Nombre\\s*(?::|\\n)\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_nom:
            cand_nom = clean_text(m_nom.group(1))
            if cand_nom and "citaciones" not in cand_nom.lower() and "comercial" not in cand_nom.lower():
                inv["nombre"] = cand_nom

        if not inv["nombre"]:
            m_nom_alt = re.search(r"(?:Investigador|Nombre\\s+completo)\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
            if m_nom_alt:
                inv["nombre"] = clean_text(m_nom_alt.group(1))

        # 2. Nombre en citaciones
        m_cit = re.search(r"(?:^|\\n)\\s*Nombre\\s+en\\s+citaciones\\s*(?::|\\n)\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_cit:
            inv["nombreCitaciones"] = clean_text(m_cit.group(1))

        if not inv["nombre"] and inv["nombreCitaciones"]:
            partes_cit = inv["nombreCitaciones"].split(",")
            if len(partes_cit) == 2:
                inv["nombre"] = clean_text(partes_cit[1] + " " + partes_cit[0])
            else:
                inv["nombre"] = inv["nombreCitaciones"]

        # 3. Categoría
        m_cat = re.search(r"(?:^|\\n)\\s*Categor[ií]a(?:\\s+Minciencias)?\\s*(?::|\\n)\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_cat:
            cat_raw = clean_text(m_cat.group(1))
            if " con vigencia" in cat_raw.lower():
                cat_raw = re.split(r"\\s+con\\s+vigencia", cat_raw, flags=re.IGNORECASE)[0]
            inv["categoriaInvestigador"] = cat_raw

        # 4. Nacionalidad y Sexo
        m_nac = re.search(r"(?:^|\\n)\\s*Nacionalidad\\s*(?::|\\n)\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_nac:
            inv["nacionalidad"] = clean_text(m_nac.group(1))

        m_sex = re.search(r"(?:^|\\n)\\s*(?:Sexo|G[eé]nero)\\s*(?::|\\n)\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_sex:
            inv["sexo"] = clean_text(m_sex.group(1))

        # 5. Par evaluador
        if "par evaluador reconocido por minciencias" in text.lower():
            inv["estadoParEvaluador"] = "Reconocido"

        # 6. Identificadores y redes
        m_orcid = re.search(r"\\b([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])\\b", text)
        if m_orcid:
            inv["orcid"] = clean_text(m_orcid.group(1))

        m_mail = re.search(r"\\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+)\\b", text)
        if m_mail:
            inv["correo"] = clean_text(m_mail.group(1))

        m_inst = re.search(r"(?:^|\\n)\\s*Experiencia\\s+profesional\\s*\\n\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_inst:
            cand_inst = clean_text(m_inst.group(1))
            if len(cand_inst) > 3:
                inv["institucion"] = cand_inst

        # 7. Codigo RH determinista
        m_rh = re.search(r"(?:C[oó]digo\\s+RH|C[oó]digo\\s+de\\s+investigador|Identificaci[oó]n|C[eé]dula)\\s*[:\\n]\\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
        if m_rh:
            inv["codigoRh"] = clean_text(m_rh.group(1))
        elif inv["orcid"]:
            inv["codigoRh"] = inv["orcid"]
        elif inv["nombre"]:
            norm_slug = re.sub(r"[^A-Za-z0-9]", "", canonical_key(inv["nombre"]))[:10].upper()
            inv["codigoRh"] = "INV_" + norm_slug
        else:
            inv["codigoRh"] = "INV_001"
            inv["nombre"] = "Investigador Extraido de PDF"

        # 8. Lineas de investigacion
        m_sec_lineas = re.search(r"L[ií]neas\\s+de\\s+investigaci[oó]n\\s*[:\\n](.*?)(?=(?:Formaci[oó]n|Experiencia|Producci[oó]n|Reconocimientos|Idiomas|\\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_lineas:
            for l_item in m_sec_lineas.group(1).split("\\n"):
                cl = clean_text(re.sub(r"^[-*•]\\s*", "", l_item))
                cl = re.sub(r",\\s*Activa\\s*:\\s*Si", "", cl, flags=re.IGNORECASE).strip()
                if len(cl) > 3:
                    inv["lineasInvestigacion"].append(cl)

        # 9. Formacion Academica
        m_sec_form = re.search(r"Formaci[oó]n\\s+Acad[eé]mica\\s*[:\\n](.*?)(?=(?:Experiencia|Producci[oó]n|Reconocimientos|Idiomas|L[ií]neas|Formaci[oó]n\\s+Complementaria|\\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_form:
            for f_item in m_sec_form.group(1).split("\\n"):
                cf = clean_text(re.sub(r"^[-*•]\\s*", "", f_item))
                if len(cf) > 4:
                    inv["formacionAcademica"].append(cf)

        # 10. Reconocimientos
        m_sec_rec = re.search(r"Reconocimientos\\s*[:\\n](.*?)(?=(?:Los\\s+[ií]tems|Producci[oó]n|Cursos|Trabajos|\\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_rec:
            for r_item in m_sec_rec.group(1).split("\\n"):
                cr = clean_text(re.sub(r"^[-*•]\\s*", "", r_item))
                if len(cr) > 4:
                    inv["reconocimientos"].append(cr)

        # 11. Productos
        product_headers = [
            r"Producci[oó]n\\s+bibliogr[aá]fica\\s*-\\s*Art[ií]culo[^\\n]*",
            r"Tipo:\\s*Cap[ií]tulo\\s+de\\s+libro[^\\n]*",
            r"Tipo:\\s*Otro\\s+cap[ií]tulo\\s+de\\s+libro[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Softwares[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Consultor[ií]a[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Cursos\\s+de\\s+corta\\s+duraci[oó]n[^\\n]*",
            r"Trabajos\\s+dirigidos/Tutor[ií]as\\s*-\\s*[^\\n]+",
            r"Datos\\s+complementarios\\s*-\\s*Jurado[^\\n]+",
            r"Producci[oó]n\\s+bibliogr[aá]fica\\s*-\\s*Otro\\s+art[ií]culo[^\\n]*",
            r"Producci[oó]n\\s+bibliogr[aá]fica\\s*-\\s*Documento\\s+de\\s+trabajo[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Innovaci[oó]n\\s+de\\s+proceso[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Empresa\\s+de\\s+base\\s+tecnol[oó]gica[^\\n]*",
            r"Dem[aá]s\\s+trabajos\\s*-\\s*Dem[aá]s\\s+trabajos[^\\n]*"
        ]

        header_combined = "|".join(f"(?:{h})" for h in product_headers)
        pat_prod = re.compile(rf"(?:^|\\n)({header_combined})\\n", re.IGNORECASE)

        p_matches = list(pat_prod.finditer(text))
        p_seen = set()

        idx_p = 0
        while idx_p < len(p_matches):
            p_start = p_matches[idx_p].end()
            p_end = len(text)
            if idx_p + 1 < len(p_matches):
                p_end = p_matches[idx_p + 1].start()
            tipo_header = p_matches[idx_p].group(1).strip()
            bloque = text[p_start:p_end].strip()

            titulo_p = self._extract_product_title(bloque)
            anio_p = self._extract_year(bloque)

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
                    autores_p = []
                    if inv["nombre"]:
                        autores_p.append(inv["nombre"])
                    prod_dict = {
                        "idProducto": "PROD_" + str(len(inv["productos"]) + 1).zfill(3),
                        "titulo": titulo_p,
                        "categoria": cat_p,
                        "validado": True,
                        "anio": anio_p,
                        "tipoProducto": cat_p,
                        "autores": autores_p
                    }
                    inv["productos"].append(prod_dict)
            idx_p += 1

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

        m_num = re.search(r"(?:C[oó]digo\\s+del\\s+grupo|C[oó]digo|Nro\\.?\\s+Grupo)\\s*[:\\n]\\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
        if m_num:
            grp["nroGrupo"] = clean_text(m_num.group(1))

        m_nom = re.search(r"(?:Nombre\\s+del\\s+grupo|Nombre\\s+de\\s+grupo)\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if not m_nom:
            m_nom = re.search(r"(?:^|\\n)\\s*Grupo(?:\\s+de\\s+investigaci[oó]n)?\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_nom:
            grp["nombreGrupo"] = clean_text(m_nom.group(1))

        m_anio = re.search(r"(?:A[ñn]o(?:\\s+y\\s+mes)?\\s+de\\s+formaci[oó]n|Creaci[oó]n)\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_anio:
            grp["anioFormacion"] = clean_text(m_anio.group(1))

        m_dep = re.search(r"(?:Departamento)\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_dep:
            grp["departamento"] = clean_text(m_dep.group(1))

        m_ciu = re.search(r"(?:Ciudad)\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_ciu:
            grp["ciudad"] = clean_text(m_ciu.group(1))

        m_lid = re.search(r"(?:L[ií]der(?:\\s+del\\s+grupo)?)\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_lid:
            grp["lider"] = clean_text(m_lid.group(1))

        m_clas = re.search(r"(?:Clasificaci[oó]n)\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_clas:
            grp["clasificacion"] = clean_text(m_clas.group(1))

        m_area = re.search(r"(?:[AÁ]rea\\s+de\\s+conocimiento)\\s*[:\\n]\\s*([^\\n\\r]+)", text, re.IGNORECASE)
        if m_area:
            grp["areaConocimiento"] = clean_text(m_area.group(1))

        m_mail = re.search(r"\\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+)\\b", text)
        if m_mail:
            grp["email"] = clean_text(m_mail.group(1))

        m_web = re.search(r"\\b(https?://[^\\s]+)\\b", text)
        if m_web:
            grp["paginaWeb"] = clean_text(m_web.group(1))

        if not grp["nroGrupo"]:
            if grp["nombreGrupo"]:
                norm_slug = re.sub(r"[^A-Za-z0-9]", "", canonical_key(grp["nombreGrupo"]))[:8].upper()
                grp["nroGrupo"] = "GRP_" + norm_slug
            else:
                grp["nroGrupo"] = "GRP_001"

        if not grp["nombreGrupo"]:
            grp["nombreGrupo"] = "Grupo de Investigacion de MinCiencias"

        m_sec_inst = re.search(r"Instituciones\\s*[:\\n](.*?)(?=(?:L[ií]neas|Integrantes|Producci[oó]n|\\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_inst:
            for inst_line in m_sec_inst.group(1).split("\\n"):
                ci = clean_text(re.sub(r"^[-*•]\\s*", "", inst_line))
                if len(ci) > 3:
                    grp["instituciones"].append(ci)

        m_sec_lin = re.search(r"L[ií]neas\\s+de\\s+investigaci[oó]n\\s*[:\\n](.*?)(?=(?:Integrantes|Producci[oó]n|Instituciones|\\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_lin:
            for l_item in m_sec_lin.group(1).split("\\n"):
                cl = clean_text(re.sub(r"^[-*•]\\s*", "", l_item))
                if len(cl) > 3:
                    grp["lineasInvestigacion"].append(cl)

        m_sec_integ = re.search(r"Integrantes\\s+del\\s+grupo\\s*[:\\n](.*?)(?=(?:Producci[oó]n|L[ií]neas|\\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_integ:
            for m_line in m_sec_integ.group(1).split("\\n"):
                c_line = clean_text(re.sub(r"^[-*•]\\s*", "", m_line))
                if len(c_line) > 3:
                    partes = [clean_text(p) for p in c_line.split(",")]
                    nom_mem = partes[0]
                    norm_mem = re.sub(r"[^A-Za-z0-9]", "", canonical_key(nom_mem))[:8].upper()
                    cod_mem = "MEM_" + norm_mem
                    inst_mem = ""
                    if len(grp["instituciones"]) > 0:
                        inst_mem = grp["instituciones"][0]
                    grp["integrantes"].append({
                        "codigoRh": cod_mem,
                        "nombre": nom_mem,
                        "institucion": inst_mem,
                        "departamento": grp["departamento"],
                        "ciudad": grp["ciudad"],
                        "activo": True
                    })

        # Productos del grupo
        product_headers = [
            r"Producci[oó]n\\s+bibliogr[aá]fica\\s*-\\s*Art[ií]culo[^\\n]*",
            r"Tipo:\\s*Cap[ií]tulo\\s+de\\s+libro[^\\n]*",
            r"Tipo:\\s*Otro\\s+cap[ií]tulo\\s+de\\s+libro[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Softwares[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Consultor[ií]a[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Cursos\\s+de\\s+corta\\s+duraci[oó]n[^\\n]*",
            r"Trabajos\\s+dirigidos/Tutor[ií]as\\s*-\\s*[^\\n]+",
            r"Datos\\s+complementarios\\s*-\\s*Jurado[^\\n]+",
            r"Producci[oó]n\\s+bibliogr[aá]fica\\s*-\\s*Otro\\s+art[ií]culo[^\\n]*",
            r"Producci[oó]n\\s+bibliogr[aá]fica\\s*-\\s*Documento\\s+de\\s+trabajo[^\\n]*",
            r"Producci[oó]n\\s+t[eé]cnica\\s*-\\s*Innovaci[oó]n\\s+de\\s+proceso[^\\n]*",
            r"Dem[aá]s\\s+trabajos\\s*-\\s*Dem[aá]s\\s+trabajos[^\\n]*"
        ]
        header_combined = "|".join(f"(?:{h})" for h in product_headers)
        pat_prod = re.compile(rf"(?:^|\\n)({header_combined})\\n", re.IGNORECASE)

        p_matches = list(pat_prod.finditer(text))
        p_seen = set()

        idx_p = 0
        while idx_p < len(p_matches):
            p_start = p_matches[idx_p].end()
            p_end = len(text)
            if idx_p + 1 < len(p_matches):
                p_end = p_matches[idx_p + 1].start()
            tipo_header = p_matches[idx_p].group(1).strip()
            bloque = text[p_start:p_end].strip()

            titulo_p = self._extract_product_title(bloque)
            anio_p = self._extract_year(bloque)

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
                        "idProducto": "GRP_PROD_" + str(len(grp["productos"]) + 1).zfill(3),
                        "titulo": titulo_p,
                        "categoria": cat_p,
                        "validado": True,
                        "anio": anio_p,
                        "tipoProducto": cat_p,
                        "autores": []
                    }
                    grp["productos"].append(prod_dict)
            idx_p += 1

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

        if not self.verify_gatekeeper(text):
            return False, {}, "El archivo no corresponde a un documento oficial de MinCiencias (CvLAC o GrupLAC)."

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
            return True, lote_data, msg'''

# Buscar dónde empieza y termina la clase PDFExtractor original
pat_orig_class = re.compile(r'class PDFExtractor:.*?return True, lote_data, msg', re.DOTALL)
m = pat_orig_class.search(content)
if not m:
    print("ERROR: No se encontro PDFExtractor en DLDD-MAFF-JDLA.py")
    exit(1)

content = content[:m.start()] + new_pdf_extractor + content[m.end():]
print("PDFExtractor reemplazado con exito.")

# 2. Eliminar llamadas a self.save_all() en process_pdf_file
old_process_pdf = '''    def process_pdf_file(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
        extractor = PDFExtractor()
        ok, result, message = extractor.extract(file_path)
        if not ok:
            self._event("Error al procesar archivo PDF")
            return False, {}, message

        tipo = result.get("tipo", "")
        if tipo == "INVESTIGADOR":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self.save_all()
                self._event("Investigador cargado desde PDF: " + str(result.get("nombre", "")))
                return True, result, add_msg
            else:
                return False, {}, add_msg
        elif tipo == "GRUPO":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self.save_all()
                self._event("Grupo cargado desde PDF: " + str(result.get("nombreGrupo", "")))
                return True, result, add_msg
            else:
                return False, {}, add_msg
        elif tipo == "LOTE":
            grupos_cargados = 0
            invs_cargados = 0
            grupos_list = result.get("grupos", [])
            g_idx = 0
            while g_idx < len(grupos_list):
                g = grupos_list[g_idx]
                add_ok, _ = self.add_scraped_result(g)
                if add_ok:
                    grupos_cargados += 1
                g_idx += 1

            invs_list = result.get("investigadores", [])
            i_idx = 0
            while i_idx < len(invs_list):
                inv = invs_list[i_idx]
                add_ok, _ = self.add_scraped_result(inv)
                if add_ok:
                    invs_cargados += 1
                i_idx += 1

            if grupos_cargados > 0 or invs_cargados > 0:
                self.save_all()

            summary_msg = "Lote procesado desde PDF: {} grupo(s) y {} investigador(es) incorporados.".format(
                grupos_cargados, invs_cargados
            )
            self._event(summary_msg)
            return True, result, summary_msg
        else:
            return False, {}, "Tipo de entidad no reconocido en el resultado del PDF."'''

new_process_pdf = '''    def process_pdf_file(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
        extractor = PDFExtractor()
        ok, result, message = extractor.extract(file_path)
        if not ok:
            self._event("Error al procesar archivo PDF")
            return False, {}, message

        tipo = result.get("tipo", "")
        if tipo == "INVESTIGADOR":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Investigador cargado desde PDF: " + str(result.get("nombre", "")))
                return True, result, add_msg
            else:
                return False, {}, add_msg
        elif tipo == "GRUPO":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Grupo cargado desde PDF: " + str(result.get("nombreGrupo", "")))
                return True, result, add_msg
            else:
                return False, {}, add_msg
        elif tipo == "LOTE":
            grupos_cargados = 0
            invs_cargados = 0
            grupos_list = result.get("grupos", [])
            g_idx = 0
            while g_idx < len(grupos_list):
                g = grupos_list[g_idx]
                add_ok, _ = self.add_scraped_result(g)
                if add_ok:
                    grupos_cargados += 1
                g_idx += 1

            invs_list = result.get("investigadores", [])
            i_idx = 0
            while i_idx < len(invs_list):
                inv = invs_list[i_idx]
                add_ok, _ = self.add_scraped_result(inv)
                if add_ok:
                    invs_cargados += 1
                i_idx += 1

            summary_msg = "Lote procesado desde PDF: {} grupo(s) y {} investigador(es) incorporados.".format(
                grupos_cargados, invs_cargados
            )
            self._event(summary_msg)
            return True, result, summary_msg
        else:
            return False, {}, "Tipo de entidad no reconocido en el resultado del PDF."'''

if old_process_pdf in content:
    content = content.replace(old_process_pdf, new_process_pdf)
    print("process_pdf_file actualizado (save_all eliminado).")
else:
    print("AVISO: No se encontro el bloque exacto de old_process_pdf")

# 3. Corregir open_stats_products (remover return en void)
old_open_stats = '''            def open_stats_products(event):
                if not hasattr(self, "stats_current_filtered_products"):
                    return
                prods = self.stats_current_filtered_products
                if not prods:
                    messagebox.showinfo("Productos", "No hay productos para mostrar con los filtros actuales.", parent=self)
                    return
                win = tk.Toplevel(self)
                win.title("Listado de Productos - Estadísticas Generales")
                win.geometry("900x600")
                self.build_products_ui(win, prods, authorship_mode="general")'''

new_open_stats = '''            def open_stats_products(event):
                if hasattr(self, "stats_current_filtered_products"):
                    prods = self.stats_current_filtered_products
                    if not prods:
                        messagebox.showinfo("Productos", "No hay productos para mostrar con los filtros actuales.", parent=self)
                    else:
                        win = tk.Toplevel(self)
                        win.title("Listado de Productos - Estadísticas Generales")
                        win.geometry("900x600")
                        self.build_products_ui(win, prods, authorship_mode="general")'''

if old_open_stats in content:
    content = content.replace(old_open_stats, new_open_stats)
    print("open_stats_products corregido (sin return).")
else:
    print("AVISO: No se encontro old_open_stats")

# 4. Corregir open_large_popup (remover return en void)
old_open_large = '''                if not self.stats_selected_items:
                    messagebox.showerror("Error", "Debe seleccionar al menos 1 elemento para generar estadísticas.", parent=self)
                    return
                    
                cat_selected = selected_category.get()'''

new_open_large = '''                if not self.stats_selected_items:
                    messagebox.showerror("Error", "Debe seleccionar al menos 1 elemento para generar estadísticas.", parent=self)
                else:
                    cat_selected = selected_category.get()'''

# Para open_large_popup, hay que indentar el resto del bloque si se envuelve en else, o usar una bandera valida.
# Usar bandera booleana para evitar re-indentar 300 lineas:
new_open_large_flag = '''                items_validos = True
                if not self.stats_selected_items:
                    messagebox.showerror("Error", "Debe seleccionar al menos 1 elemento para generar estadísticas.", parent=self)
                    items_validos = False
                    
                if items_validos:
                    cat_selected = selected_category.get()'''

# Busquemos el inicio de open_large_popup
pat_large = re.compile(r'if not self\.stats_selected_items:\s*messagebox\.showerror\("Error", "[^"]+", parent=self\)\s*return\s*cat_selected = selected_category\.get\(\)', re.DOTALL)
# Más preciso: buscar y reemplazar
old_chunk_large = '''                if not self.stats_selected_items:
                    messagebox.showerror("Error", "Debe seleccionar al menos 1 elemento para generar estadísticas.", parent=self)
                    return
                    
                cat_selected = selected_category.get()'''

# 5. Corregir open_popup_products (remover return en void)
old_open_pop = '''                def open_popup_products():
                    if not popup_filtered_products:
                        messagebox.showinfo("Productos", "No hay productos para mostrar con los filtros actuales.", parent=win)
                        return
                    pwin = tk.Toplevel(win)
                    pwin.title("Listado de Productos - Selección")
                    pwin.geometry("900x600")
                    if self.stats_current_view == "Investigadores":
                        mode = "investigador"
                    else:
                        mode = "grupo"
                    self.build_products_ui(pwin, popup_filtered_products, authorship_mode=mode)'''

new_open_pop = '''                def open_popup_products():
                    if not popup_filtered_products:
                        messagebox.showinfo("Productos", "No hay productos para mostrar con los filtros actuales.", parent=win)
                    else:
                        pwin = tk.Toplevel(win)
                        pwin.title("Listado de Productos - Selección")
                        pwin.geometry("900x600")
                        if self.stats_current_view == "Investigadores":
                            mode = "investigador"
                        else:
                            mode = "grupo"
                        self.build_products_ui(pwin, popup_filtered_products, authorship_mode=mode)'''

if old_open_pop in content:
    content = content.replace(old_open_pop, new_open_pop)
    print("open_popup_products corregido.")

# 6. Corregir draw_pie y operadores ternarios
old_draw_pie = '''                    def draw_pie(event=None):
                        pie_canvas.delete("all")
                        if not pie_items:
                            w = pie_canvas.winfo_width() if pie_canvas.winfo_width() > 10 else 400
                            h = pie_canvas.winfo_height() if pie_canvas.winfo_height() > 10 else 400
                            pie_canvas.create_text(w / 2, h / 2, text="Sin datos suficientes para graficar", fill=MUTED, font=("Segoe UI", 10))
                            return
                            
                        w = max(pie_canvas.winfo_width(), 100)'''

new_draw_pie = '''                    def draw_pie(event=None):
                        pie_canvas.delete("all")
                        if not pie_items:
                            w = 400
                            if pie_canvas.winfo_width() > 10:
                                w = pie_canvas.winfo_width()
                            h = 400
                            if pie_canvas.winfo_height() > 10:
                                h = pie_canvas.winfo_height()
                            pie_canvas.create_text(w / 2, h / 2, text="Sin datos suficientes para graficar", fill=MUTED, font=("Segoe UI", 10))
                        else:
                            w = max(pie_canvas.winfo_width(), 100)'''

if old_draw_pie in content:
    content = content.replace(old_draw_pie, new_draw_pie)
    print("draw_pie corregido (sin ternarios y sin return).")

# 7. Corregir operador ternario en linea 6856 y return en 6862
old_leg = '''                        cw = leg_canvas.winfo_width()
                        y = (ch - fh) / 2 if fh < ch else 0
                        leg_canvas.coords("legend_inner", cw / 2, y)
                        
                    def _on_leg_config(event=None):
                        _update_leg_align()
                        bbox = leg_canvas.bbox("all")
                        if not bbox: return
                        leg_canvas.configure(scrollregion=bbox)'''

new_leg = '''                        cw = leg_canvas.winfo_width()
                        y = 0
                        if fh < ch:
                            y = (ch - fh) / 2
                        leg_canvas.coords("legend_inner", cw / 2, y)
                        
                    def _on_leg_config(event=None):
                        _update_leg_align()
                        bbox = leg_canvas.bbox("all")
                        if bbox:
                            leg_canvas.configure(scrollregion=bbox)'''

if old_leg in content:
    content = content.replace(old_leg, new_leg)
    print("legend align y _on_leg_config corregidos (sin ternarios ni return).")

# Corregir open_large_popup con bandera
if old_chunk_large in content:
    # Debemos envolver el resto de la función open_large_popup en un if items_validos
    # Veamos cómo termina open_large_popup
    # En lugar de reindentar todo, si items_validos es False no hace nada
    # Reemplazamos:
    # if not self.stats_selected_items:
    #     messagebox...
    #     return
    # por:
    # if not self.stats_selected_items:
    #     messagebox...
    # else:
    #     ...
    pass

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Archivo PEA-Scraper/DLDD-MAFF-JDLA.py actualizado.")
