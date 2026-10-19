import re

with open(r"PEA-Scraper/DLDD-MAFF-JDLA.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update verify_gatekeeper
old_gatekeeper_match = re.search(r'    def verify_gatekeeper\(self, text: str\) -> bool:.*?(?=\n    def partition_document)', content, re.DOTALL)
assert old_gatekeeper_match is not None, "verify_gatekeeper not found!"

new_gatekeeper = '''    def verify_gatekeeper(self, text: str) -> bool:
        """Capa 1: Valida que el documento sea de investigacion MinCiencias."""
        canon = canonical_key(text)
        if not canon:
            return False

        if "cvlac" in canon or "gruplac" in canon or "scienti" in canon or "minciencias" in canon or "colciencias" in canon or "snctei" in canon:
            return True

        if "ano y mes de formacion" in canon or "integrantes del grupo" in canon or "lineas de investigacion declaradas" in canon:
            return True

        if "hoja de vida" in canon and ("par evaluador" in canon or "categoria" in canon or "formacion academica" in canon or "investigador" in canon):
            return True

        if "datos generales del grupo" in canon or ("grupo de investigacion" in canon and "lider" in canon and "clasificacion" in canon):
            return True

        return False
'''
content = content[:old_gatekeeper_match.start()] + new_gatekeeper + content[old_gatekeeper_match.end():]

# 2. Update partition_document
old_partition_match = re.search(r'    def partition_document\(self, text: str\) -> Tuple\[str, List\[Dict\[str, Any\]\]\]:.*?(?=\n    def _extract_product_title)', content, re.DOTALL)
assert old_partition_match is not None, "partition_document not found!"

new_partition = r'''    def partition_document(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Capa 2: Identifica fronteras de entidades y detecta lotes sin falsos positivos."""
        t_low = text.lower()
        canon = canonical_key(text)

        is_grp = False
        if "año y mes de formación" in t_low or "ano y mes de formacion" in t_low:
            is_grp = True
        elif "integrantes del grupo" in t_low and ("horas dedicación" in t_low or "horas dedicacion" in t_low or "vinculación" in t_low or "vinculacion" in t_low):
            is_grp = True
        elif "datos básicos" in t_low and ("líder" in t_low or "lider" in t_low):
            is_grp = True
        elif "gruplac" in t_low or "datos generales del grupo" in t_low:
            is_grp = True
        elif "líneas de investigación declaradas por el grupo" in t_low or "lineas de investigacion declaradas por el grupo" in t_low:
            is_grp = True

        is_cvl = False
        if "hoja de vida" in t_low and ("par evaluador" in t_low or "nombre en citaciones" in t_low or "formación académica" in t_low or "formacion academica" in t_low):
            is_cvl = True
        elif "cvlac" in t_low or "currículum vítae" in t_low or "curriculum vitae" in t_low:
            is_cvl = True
        elif "datos generales del investigador" in t_low:
            is_cvl = True

        if is_grp and not is_cvl:
            return "GRUPO", [{"tipo": "GRUPO", "texto": text}]

        if is_cvl and not is_grp:
            return "INVESTIGADOR", [{"tipo": "INVESTIGADOR", "texto": text}]

        cvlac_pat = re.compile(
            r"(?:(?:^|\n\n|\f)\s*(?:Hoja\s+de\s+vida\b|Curr[ií]culum\s+V[ií]tae(?:\s+de\s+Latinoam[eé]rica)?\b|CvLAC\b|DATOS\s+GENERALES\s+DEL\s+INVESTIGADOR\b))",
            re.IGNORECASE
        )
        gruplac_pat = re.compile(
            r"(?:(?:^|\n\n|\f)\s*(?:GrupLAC\b|DATOS\s+GENERALES\s+DEL\s+GRUPO\b|DIRECTORIO\s+DE\s+GRUPOS\s+DE\s+INVESTIGACI[OÓ]N\b|A[ñn]o\s+y\s+mes\s+de\s+formaci[oó]n))",
            re.IGNORECASE
        )

        cvlac_matches = list(cvlac_pat.finditer(text))
        gruplac_matches = list(gruplac_pat.finditer(text))

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
            if is_grp:
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
'''
content = content[:old_partition_match.start()] + new_partition + content[old_partition_match.end():]

# 3. Update parse_group
old_parse_group_match = re.search(r'    def parse_group\(self, text: str\) -> Dict\[str, Any\]:.*?(?=\n    def extract\()', content, re.DOTALL)
assert old_parse_group_match is not None, "parse_group not matched!"

new_parse_group = r'''    def parse_group(self, text: str) -> Dict[str, Any]:
        """Capa 3: Extrae atributos, integrantes y productos de un GrupLAC."""
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

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        # 1. Nombre del grupo
        m_nom = re.search(r"(?:Nombre\s+del\s+grupo|Nombre\s+de\s+grupo)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_nom:
            grp["nombreGrupo"] = clean_text(m_nom.group(1))
        else:
            found_name = False
            idx_nom = 0
            limit_nom = 10
            if len(lines) < limit_nom:
                limit_nom = len(lines)
            while idx_nom < limit_nom and not found_name:
                l_cur = lines[idx_nom].lower()
                if "datos básicos" in l_cur or "datos basicos" in l_cur or "gruplac" in l_cur:
                    if idx_nom > 0:
                        grp["nombreGrupo"] = clean_text(lines[idx_nom - 1])
                    found_name = True
                idx_nom += 1

        if not grp["nombreGrupo"] and lines:
            grp["nombreGrupo"] = clean_text(lines[0])

        # 2. Codigo del grupo
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

        # 4. Anio y mes
        m_anio = re.search(r"(?:A[ñn]o(?:\s+y\s+mes)?\s+de\s+formaci[oó]n|Creaci[oó]n)\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_anio:
            grp["anioFormacion"] = clean_text(m_anio.group(1))

        # 5. Departamento y ciudad
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

        # 9. Pagina web
        m_web = re.search(r"\b(https?://[^\s]+)\b", text)
        if m_web:
            grp["paginaWeb"] = clean_text(m_web.group(1))

        # 10. Instituciones
        m_sec_inst = re.search(r"Instituciones\s*[:\n](.*?)(?=(?:Plan\s+Estrat[eé]gico|L[ií]neas|Integrantes|PRODUCCI[OÓ]N|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_inst:
            for inst_line in m_sec_inst.group(1).split("\n"):
                ci = clean_text(re.sub(r"^\d+\s*[\.\-]+\s*", "", inst_line))
                ci = re.split(r"\s*-\s*\(Avalado\)", ci, flags=re.IGNORECASE)[0].strip()
                if len(ci) > 3:
                    grp["instituciones"].append(ci)

        # 11. Lineas de investigacion
        m_sec_lin = re.search(r"L[ií]neas\s+de\s+investigaci[oó]n\s*(?:declaradas\s+por\s+el\s+grupo)?\s*[:\n](.*?)(?=(?:Integrantes|Instituciones|Plan\s+Estrat[eé]gico|PRODUCCI[OÓ]N|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_lin:
            for l_item in m_sec_lin.group(1).split("\n"):
                cl = clean_text(re.sub(r"^\d+\s*[\.\-]+\s*", "", l_item))
                if len(cl) > 3:
                    grp["lineasInvestigacion"].append(cl)

        # 12. Integrantes
        pos_integ = text.find("Integrantes del grupo")
        if pos_integ != -1:
            pos_fin_integ = text.find("PRODUCCIÓN DE FORMACIÓN", pos_integ)
            if pos_fin_integ == -1:
                pos_fin_integ = text.find("PRODUCCIÓN BIBLIOGRÁFICA", pos_integ)
            if pos_fin_integ != -1:
                bloque_integ = text[pos_integ:pos_fin_integ]
            else:
                bloque_integ = text[pos_integ:pos_integ + 15000]

            lineas_int = [l.strip() for l in bloque_integ.splitlines() if l.strip()]
            idx_int = 0
            while idx_int < len(lineas_int):
                l_m = lineas_int[idx_int]
                m_item = re.match(r"^\d+\s*[\.\-]+\s*(.+)$", l_m)
                if m_item:
                    nom_mem = clean_text(m_item.group(1))
                    m_inline = re.match(r"^(.+?)\s+(?:Integrante|L[ií]der|Estudiante|Investigador)\s+(\d+)\s+([^\n]+)$", nom_mem, re.IGNORECASE)
                    if m_inline:
                        nom_mem = clean_text(m_inline.group(1))
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
                idx_int += 1

        # 13. Productos del grupo
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
                start_p = p_matches[idx_p].end()
                if idx_p + 1 < len(p_matches):
                    end_p = p_matches[idx_p + 1].start()
                else:
                    end_p = len(bloque_prods)
                blk = bloque_prods[start_p:end_p].strip()
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

        return grp
'''
content = content[:old_parse_group_match.start()] + new_parse_group + content[old_parse_group_match.end():]

# 4. Update ApplicationService with duplicate checkers
old_add_scraped = '''    def add_scraped_result(self, result: Dict[str, Any]) -> Tuple[bool, str]:
        tipo = str(result.get("tipo", "")).casefold()
        if tipo == "investigador":
            key = canonical_key(result.get("codigoRh", ""))
            duplicate = False
            for current in self.investigadores:
                if canonical_key(current.get("codigoRh", "")) == key and key:
                    duplicate = True
            if duplicate:
                return False, "El investigador ya se encuentra cargado."
            self.investigadores.append(result)
            self._event("Investigador cargado desde CvLAC")
            return True, "Investigador cargado correctamente."
        elif tipo == "grupo":
            key = canonical_key(result.get("nroGrupo", ""))
            duplicate = False
            for current in self.grupos:
                if canonical_key(current.get("nroGrupo", "")) == key and key:
                    duplicate = True
            if duplicate:
                return False, "El grupo ya se encuentra cargado."
            self.grupos.append(result)
            self._event("Grupo cargado desde GrupLAC")
            return True, "Grupo cargado correctamente."
        else:
            return False, "El resultado del scraper no tiene un tipo válido."'''

new_add_scraped = '''    def _is_duplicate_investigator(self, inv1: Dict[str, Any], inv2: Dict[str, Any]) -> bool:
        c1 = canonical_key(str(inv1.get("codigoRh", "")))
        c2 = canonical_key(str(inv2.get("codigoRh", "")))
        if c1 and c2 and c1 == c2:
            return True
        n1 = canonical_key(str(inv1.get("nombre", "")))
        n2 = canonical_key(str(inv2.get("nombre", "")))
        if n1 and n2 and len(n1) >= 4 and n1 == n2:
            return True
        o1 = canonical_key(str(inv1.get("orcid", "")))
        o2 = canonical_key(str(inv2.get("orcid", "")))
        if o1 and o2 and len(o1) >= 8 and o1 == o2:
            return True
        e1 = clean_text(str(inv1.get("email", ""))).lower()
        e2 = clean_text(str(inv2.get("email", ""))).lower()
        if e1 and e2 and "@" in e1 and e1 == e2:
            return True
        return False

    def _is_duplicate_group(self, grp1: Dict[str, Any], grp2: Dict[str, Any]) -> bool:
        g1 = canonical_key(str(grp1.get("nroGrupo", "")))
        g2 = canonical_key(str(grp2.get("nroGrupo", "")))
        if g1 and g2 and g1 == g2:
            return True
        n1 = canonical_key(str(grp1.get("nombreGrupo", "")))
        n2 = canonical_key(str(grp2.get("nombreGrupo", "")))
        if n1 and n2 and len(n1) >= 4 and n1 == n2:
            return True
        return False

    def add_scraped_result(self, result: Dict[str, Any]) -> Tuple[bool, str]:
        tipo = str(result.get("tipo", "")).casefold()
        if tipo == "investigador":
            duplicate = False
            for current in self.investigadores:
                if self._is_duplicate_investigator(result, current):
                    duplicate = True
            if duplicate:
                return False, "El investigador ya se encuentra cargado."
            self.investigadores.append(result)
            self._event("Investigador cargado desde CvLAC")
            return True, "Investigador cargado correctamente."
        elif tipo == "grupo":
            duplicate = False
            for current in self.grupos:
                if self._is_duplicate_group(result, current):
                    duplicate = True
            if duplicate:
                return False, "El grupo ya se encuentra cargado."
            self.grupos.append(result)
            self._event("Grupo cargado desde GrupLAC")
            return True, "Grupo cargado correctamente."
        else:
            return False, "El resultado del scraper no tiene un tipo válido."'''

assert old_add_scraped in content, "old_add_scraped not found in content!"
content = content.replace(old_add_scraped, new_add_scraped, 1)

# 5. Update process_pdf_file
old_process_pdf = '''        tipo = result.get("tipo", "")
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
                return False, {}, add_msg'''

new_process_pdf = '''        tipo = result.get("tipo", "")
        if tipo == "INVESTIGADOR":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Investigador cargado desde PDF: " + str(result.get("nombre", "")))
                return True, result, add_msg
            else:
                return False, result, add_msg
        elif tipo == "GRUPO":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Grupo cargado desde PDF: " + str(result.get("nombreGrupo", "")))
                return True, result, add_msg
            else:
                return False, result, add_msg'''

assert old_process_pdf in content, "old_process_pdf not found in content!"
content = content.replace(old_process_pdf, new_process_pdf, 1)

# 6. Update _handle_cargar_archivo so C++ receives extraction payload
old_handle_pdf = '''                if tipo_archivo == "pdf" or ruta.lower().endswith(".pdf"):
                    ok, result, message = self.service.process_pdf_file(ruta)
                    if ok:
                        payload = serialize_result(result)
                    else:
                        payload = serialize_error(message)
                    self._send(200, payload, "text/plain")'''

new_handle_pdf = '''                if tipo_archivo == "pdf" or ruta.lower().endswith(".pdf"):
                    extractor = PDFExtractor()
                    ok, result, message = extractor.extract(ruta)
                    if ok:
                        payload = serialize_result(result)
                    else:
                        payload = serialize_error(message)
                    self._send(200, payload, "text/plain")'''

assert old_handle_pdf in content, "old_handle_pdf not found in content!"
content = content.replace(old_handle_pdf, new_handle_pdf, 1)

# 7. Update status text in do_load_pdf
old_status_else = '''                        else:
                            self.status.set("Error al cargar PDF")'''

new_status_else = '''                        else:
                            self.status.set(message)'''

assert old_status_else in content, "old_status_else not found in content!"
content = content.replace(old_status_else, new_status_else, 1)

with open(r"PEA-Scraper/DLDD-MAFF-JDLA.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Actualización de PEA-Scraper/DLDD-MAFF-JDLA.py completada con éxito!")
