import os
import sys
import csv
import io
import re
import unicodedata
from typing import Dict, List, Any, Tuple, Optional

def canonical_key(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", str(text).strip().lower())
    without_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    cleaned = re.sub(r"[^a-z0-9]", "", without_accents)
    return cleaned

def clean_text(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", s).strip()

def parse_pipe_list(raw: str) -> List[str]:
    if not raw:
        return []
    raw_clean = clean_text(raw)
    if "|" in raw_clean:
        tokens = raw_clean.split("|")
    elif "\n" in raw_clean:
        tokens = raw_clean.split("\n")
    elif ";" in raw_clean:
        tokens = raw_clean.split(";")
    else:
        tokens = [raw_clean]
    res = []
    for t in tokens:
        c = clean_text(t)
        if c and c not in res:
            res.append(c)
    return res

def parse_languages(raw: str) -> List[str]:
    if not raw:
        return []
    raw_clean = clean_text(raw)
    if "|" in raw_clean:
        parts = [clean_text(p) for p in raw_clean.split("|") if clean_text(p)]
        if len(parts) >= 5 and parts[0].lower() == "idioma" and parts[1].lower() == "habla":
            res = ["Idioma | Habla | Escribe | Lee | Entiende"]
            i = 5
            while i < len(parts):
                chunk = parts[i : i + 5]
                if len(chunk) == 5:
                    res.append("{} | {}".format(chunk[0], " | ".join(chunk[1:])))
                elif len(chunk) > 0:
                    res.append(" | ".join(chunk))
                i += 5
            return res
        else:
            return parts
    return [raw_clean]

ALIAS_MAP = {
    # Metadata
    "tipo_registro": ["tiporegistro", "registro", "tipodeentidad", "entidadtipo"],
    "tipo_detalle": ["tipodetalle", "detalle", "subtipoentidad"],

    # Investigador identity
    "inv_codigoRh": [
        "codigorh", "rh", "idrh", "identificadorrh", "codigocvlac", "cvlac", "idcvlac",
        "codinvestigador", "codigoinvestigador", "idinvestigador", "cedula", "documento"
    ],
    "inv_nombre": [
        "nombre", "nombreinvestigador", "nombrecompleto", "investigador", "autor",
        "nombredelautor", "nombreautor"
    ],
    "inv_correo": [
        "correo", "email", "correoelectronico", "mail", "emailinvestigador", "correoinvestigador"
    ],
    "inv_orcid": [
        "orcid", "idorcid", "codigoorcid", "cuentaorcid"
    ],
    "inv_institucion": [
        "institucion", "entidad", "universidad", "institucionavaladora", "afiliacion",
        "institucionprincipal", "institucioninvestigador"
    ],
    "inv_departamento": [
        "departamento", "depto", "departamentoubicacion", "departamentoinvestigador"
    ],
    "inv_ciudad": [
        "ciudad", "municipio", "ciudadinvestigador"
    ],
    "inv_categoria": [
        "categoria", "categoriainvestigador", "clasificacioninvestigador", "escalafon",
        "nivelinvestigador", "tipoinvestigador"
    ],
    "inv_perfil": [
        "perfil", "perfilcvlac", "resumenperfil", "descripcionperfil", "perfilinvestigador"
    ],
    "inv_nombreCitaciones": [
        "nombrecitaciones", "nombreencitaciones", "citaciones", "firmas"
    ],
    "inv_nacionalidad": [
        "nacionalidad", "paisorigen", "paisdenacimiento", "pais"
    ],
    "inv_sexo": [
        "sexo", "genero"
    ],
    "inv_parevaluador": [
        "parevaluador", "estadoparevaluador", "reconocidoparevaluador"
    ],
    "inv_researcherId": [
        "researcherid", "publons", "idresearcher"
    ],
    "inv_scopus": [
        "autoridscopus", "scopusid", "scopus", "idscopus"
    ],
    "inv_scholar": [
        "googlescholar", "scholar", "perfilscholar"
    ],
    "inv_researchgate": [
        "researchgate", "perfilresearchgate"
    ],
    "inv_academiaEdu": [
        "academiaedu", "academia"
    ],
    "inv_mendeley": [
        "mendeley", "perfilmendeley"
    ],
    "inv_linkedin": [
        "linkedin", "perfillinkedin"
    ],
    "inv_repositorio": [
        "repositorioinstitucional", "repositorio"
    ],
    "inv_idiomas": [
        "idiomas", "idioma", "idiomasinvestigador", "lenguas"
    ],
    "inv_areasConocimiento": [
        "areasconocimientoinvestigador", "areasdeconocimientoinvestigador",
        "areaconocimientoinvestigador", "areasconocimiento"
    ],
    "inv_lineasInvestigacion": [
        "lineasinvestigacioninvestigador", "lineasdeinvestigacioninvestigador",
        "lineasinvestigador", "lineasinvestigacion"
    ],
    "inv_formacionAcademica": [
        "formacionacademica", "formacion", "estudios", "titulos", "educacion"
    ],
    "inv_experienciaProfesional": [
        "experienciaprofesional", "experiencia", "trayectoria", "cargos"
    ],
    "inv_gruposInvestigacion": [
        "gruposinvestigacion", "gruposinvestigador", "gruposasociados"
    ],
    "inv_semilleros": [
        "semilleros", "semillerosinvestigacion"
    ],
    "inv_proyectos": [
        "proyectos", "proyectoscvlac", "proyectosinvestigacion"
    ],
    "inv_reconocimientos": [
        "reconocimientos", "reconocimiento", "distinciones", "premios"
    ],
    "inv_activo": [
        "activo", "estadoactivo", "vigente"
    ],
    "inv_fuente": [
        "fuente", "urlfuente", "enlacefuente"
    ],

    # Campos de Grupo
    "grp_nroGrupo": [
        "nrogrupo", "codigogrupo", "idgrupo", "codigogruplac", "gruplac", "idgruplac",
        "codgrupo", "numerogrupo"
    ],
    "grp_nombreGrupo": [
        "nombregrupo", "nombredelgrupo", "grupo", "grupodeinvestigacion"
    ],
    "grp_lider": [
        "lider", "liderdelgrupo", "liderinvestigador", "director", "directordelgrupo",
        "lidergrupo", "liderdegrupo", "directorgrupo"
    ],
    "grp_clasificacion": [
        "clasificacion", "clasificaciongrupo", "categoriagrupo", "reconocimientominciencias"
    ],
    "grp_anioFormacion": [
        "anioformacion", "anoformacion", "aniodeformacion", "anodeformacion", "aniocreacion",
        "creacion", "fechacreacion"
    ],
    "grp_departamento": [
        "departamentogrupo", "deptogrupo"
    ],
    "grp_ciudad": [
        "ciudadgrupo", "municipiogrupo"
    ],
    "grp_areaConocimiento": [
        "areaconocimiento", "areadeconocimiento", "granareadeconocimiento", "granarea", "area",
        "areaconocimientogrupo", "areasconocimientogrupo"
    ],
    "grp_email": [
        "emailgrupo", "correogrupo"
    ],
    "grp_paginaWeb": [
        "paginaweb", "sitio", "sitioweb", "url", "web", "paginawebgrupo"
    ],
    "grp_programaNacionalCti": [
        "programanacionalcti", "programanacional", "programacti"
    ],
    "grp_programaNacionalCtiSecundario": [
        "programanacionalctisecundario", "programacti2", "programasecundario"
    ],
    "grp_planEstrategico": [
        "planestrategico", "plan"
    ],
    "grp_estadoArte": [
        "estadoarte", "estadodelarte"
    ],
    "grp_objetivos": [
        "objetivos", "objetivogeneral", "objetivosespecificos"
    ],
    "grp_retos": [
        "retos", "desafios"
    ],
    "grp_vision": [
        "vision", "visiondelfuturo"
    ],
    "grp_instituciones": [
        "instituciones", "institucionesavaladoras", "entidadesavaladoras", "avales"
    ],
    "grp_lineasInvestigacion": [
        "lineasinvestigaciongrupo", "lineasdeinvestigaciongrupo", "lineasgrupo"
    ],
    "grp_informacionCertificada": [
        "informacioncertificada", "certificada"
    ],

    # Campos de Integrante
    "mem_nombre": [
        "integrante", "nombreintegrante", "miembro", "nombremiembro", "investigadorintegrante"
    ],
    "mem_codigoRh": [
        "codigointegrante", "rhintegrante", "idintegrante"
    ],
    "mem_rol": [
        "rol", "vinculacion", "rolengrupo", "tipovinculacion"
    ],
    "mem_horas": [
        "horas", "horasdedicacion", "dedicacion"
    ],
    "mem_vinculacion": [
        "iniciofinvinculacion", "periodovinculacion", "fechavinculacion"
    ],
    "mem_correo": [
        "integrantecorreo", "correointegrante"
    ],
    "mem_orcid": [
        "integranteorcid", "orcidintegrante"
    ],
    "mem_institucion": [
        "integranteinstitucion", "institucionintegrante"
    ],
    "mem_departamento": [
        "integrantedepartamento"
    ],
    "mem_ciudad": [
        "integranteciudad"
    ],
    "mem_categoria": [
        "integrantecategoria"
    ],
    "mem_perfil": [
        "integranteperfil"
    ],
    "mem_productos": [
        "integranteproductos"
    ],

    # Campos de Producto
    "prod_id": [
        "idproducto", "idprod", "codigoproducto"
    ],
    "prod_titulo": [
        "titulo", "tituloproducto", "titulodelproducto", "nombreproducto", "producto",
        "titulopublicacion", "tituloproyecto", "publicacion", "nombrearticulo", "titulolibro",
        "productotitulo"
    ],
    "prod_anio": [
        "anio", "ano", "aniopublicacion", "anopublicacion", "fechapublicacion", "fecha",
        "productoanio", "productoano"
    ],
    "prod_categoria": [
        "categoriaproducto", "tipoproducto", "tipo", "tipologia", "subtipo", "claseproducto",
        "productocategoria", "productotipo"
    ],
    "prod_validado": [
        "productovalidado", "validado", "avalado"
    ],
    "prod_subtipo": [
        "productosubtipo", "subtipo"
    ],
    "prod_doi": [
        "doi", "linkdoi", "urldoi"
    ],
    "prod_isbn": [
        "isbn", "issn", "identificadorpublicacion"
    ],
    "prod_revista": [
        "revista", "journal", "publicadoen", "nombrerevista"
    ],
    "prod_editorial": [
        "editorial", "casaeditorial", "editor"
    ],
    "prod_disponibilidad": [
        "disponibilidad"
    ],
    "prod_institucion": [
        "productoinstitucion"
    ],
    "prod_ciudad": [
        "productociudad"
    ],
    "prod_pais": [
        "productopais", "paisproducto"
    ],
    "prod_contrato": [
        "numerocontrato", "contrato", "registro"
    ],
    "prod_descripcion": [
        "descripcion", "resumen", "detalles", "observaciones", "productodescripcion"
    ],
    "prod_palabrasClave": [
        "palabrasclave", "keywords"
    ],
    "prod_areas": [
        "productoareas", "areasproducto"
    ],
    "prod_autores": [
        "autores", "autoresproducto", "coautores", "investigadoresparticipantes",
        "productoautores"
    ]
}


class CSVExtractorTest:
    def __init__(self) -> None:
        self.min_columns = 2

    def read_and_validate_tabular(self, file_path: str) -> Tuple[bool, List[str], List[List[str]], str]:
        if not file_path.lower().endswith(".csv"):
            return False, [], [], "El archivo no tiene la extensión requerida .csv"
        if not os.path.isfile(file_path):
            return False, [], [], "El archivo no existe o no es accesible: " + str(file_path)

        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        text_content = ""
        decode_ok = False
        try:
            text_content = raw_bytes.decode("utf-8-sig")
            decode_ok = True
        except UnicodeDecodeError:
            try:
                text_content = raw_bytes.decode("cp1252")
                decode_ok = True
            except UnicodeDecodeError:
                decode_ok = False

        if not decode_ok:
            return False, [], [], "Error de decodificación: el archivo no es UTF-8 ni Windows-1252 válido."

        delimiters = [",", ";"]
        candidates = []
        for d in delimiters:
            try:
                reader = csv.reader(io.StringIO(text_content), delimiter=d, quotechar='"')
                rows = []
                for r in reader:
                    row_clean = [clean_text(cell) for cell in r]
                    if any(len(c) > 0 for c in row_clean):
                        rows.append(row_clean)
                if len(rows) >= 2:
                    header = rows[0]
                    num_cols = len(header)
                    if num_cols >= self.min_columns:
                        data_rows = rows[1:]
                        consistent_count = 0
                        for dr in data_rows:
                            if len(dr) == num_cols or (len(dr) > num_cols and all(len(c) == 0 for c in dr[num_cols:])):
                                consistent_count += 1
                        if consistent_count == len(data_rows):
                            candidates.append({
                                "delimiter": d,
                                "header": header,
                                "rows": data_rows,
                                "cols": num_cols
                            })
            except Exception:
                pass

        if not candidates:
            return False, [], [], "El archivo no posee una estructura tabular válida."

        selected = candidates[0]
        if len(candidates) > 1:
            if candidates[1]["cols"] > candidates[0]["cols"]:
                selected = candidates[1]

        return True, selected["header"], selected["rows"], "Estructura tabular verificada."

    def map_headers(self, headers: List[str]) -> Dict[int, str]:
        mapping: Dict[int, str] = {}
        idx = 0
        while idx < len(headers):
            h_clean = canonical_key(headers[idx])
            mapped_key = ""
            for target_field, aliases in ALIAS_MAP.items():
                for alias in aliases:
                    if h_clean == alias:
                        mapped_key = target_field
            if mapped_key:
                mapping[idx] = mapped_key
            idx += 1
        return mapping

    def normalize_product_category(self, raw_cat: str, titulo: str) -> str:
        c_low = (raw_cat + " " + titulo).lower()
        if "software" in c_low or "computacional" in c_low or "aplicativo" in c_low:
            return "Software"
        elif "libro" in c_low and "capitulo" not in c_low and "capítulo" not in c_low:
            return "Libro"
        elif "capitulo" in c_low or "capítulo" in c_low:
            return "Capítulo de libro"
        elif "informe" in c_low:
            return "Informe técnico"
        elif "prototipo" in c_low:
            return "Prototipo"
        elif "innovacion" in c_low or "innovación" in c_low:
            return "Innovación"
        elif "evento" in c_low or "congreso" in c_low or "simposio" in c_low or "ponencia" in c_low:
            return "Trabajo en evento"
        elif "consultor" in c_low:
            return "Consultoría"
        elif "trabajo de grado" in c_low or "tesis" in c_low or "tutoria" in c_low or "tutoría" in c_low:
            return "Trabajo dirigido"
        elif "curso" in c_low or "diplomado" in c_low:
            return "Curso dictado"
        elif "contenido digital" in c_low or "audiovisual" in c_low or "desarrollo web" in c_low:
            return "Contenido digital"
        return "Artículo"

    def normalize_and_extract(self, headers: List[str], rows: List[List[str]], mapping: Dict[int, str]) -> Dict[str, Any]:
        grupos_dict: Dict[str, Dict[str, Any]] = {}
        investigadores_dict: Dict[str, Dict[str, Any]] = {}

        has_grp_fields = any(f.startswith("grp_") for f in mapping.values())
        has_inv_fields = any(f.startswith("inv_") for f in mapping.values())
        has_prod_fields = any(f.startswith("prod_") for f in mapping.values())
        has_mem_fields = any(f.startswith("mem_") for f in mapping.values())

        r_idx = 0
        while r_idx < len(rows):
            row = rows[r_idx]
            r_data: Dict[str, str] = {}
            c_idx = 0
            while c_idx < len(row):
                if c_idx in mapping:
                    f_key = mapping[c_idx]
                    val = clean_text(row[c_idx])
                    if val:
                        r_data[f_key] = val
                c_idx += 1

            tipo_reg = r_data.get("tipo_registro", "").upper()

            # Extraer producto de la fila si existe
            prod_obj = None
            if has_prod_fields and "prod_titulo" in r_data:
                tit = r_data["prod_titulo"]
                if len(tit) >= 3:
                    anio_val = 0
                    if "prod_anio" in r_data:
                        anios = re.findall(r"\b(19\d\d|20[0-3]\d)\b", r_data["prod_anio"])
                        if anios:
                            anio_val = int(anios[-1])
                    raw_cat = r_data.get("prod_categoria", r_data.get("prod_tipo", ""))
                    cat_val = self.normalize_product_category(raw_cat, tit)
                    autores_list = []
                    if "prod_autores" in r_data:
                        for aut in re.split(r"[,;]+", r_data["prod_autores"]):
                            c_aut = clean_text(aut)
                            if c_aut:
                                autores_list.append(c_aut)
                    val_validado = False
                    if r_data.get("prod_validado", "").lower() in ["true", "1", "si", "sí"]:
                        val_validado = True

                    prod_obj = {
                        "idProducto": r_data.get("prod_id", ""),
                        "titulo": tit,
                        "categoria": cat_val,
                        "validado": val_validado,
                        "anio": anio_val,
                        "tipoProducto": cat_val,
                        "subtipo": r_data.get("prod_subtipo", raw_cat),
                        "doi": r_data.get("prod_doi", ""),
                        "isbn": r_data.get("prod_isbn", ""),
                        "revista": r_data.get("prod_revista", ""),
                        "editorial": r_data.get("prod_editorial", ""),
                        "disponibilidad": r_data.get("prod_disponibilidad", ""),
                        "institucion": r_data.get("prod_institucion", ""),
                        "ciudad": r_data.get("prod_ciudad", ""),
                        "pais": r_data.get("prod_pais", ""),
                        "numeroContrato": r_data.get("prod_contrato", ""),
                        "descripcion": r_data.get("prod_descripcion", ""),
                        "palabrasClave": r_data.get("prod_palabrasClave", ""),
                        "areas": r_data.get("prod_areas", ""),
                        "autores": autores_list
                    }

            # Caso 1: Fila con datos de Grupo
            es_grupo = False
            if tipo_reg == "GRUPO":
                es_grupo = True
            elif tipo_reg == "" and has_grp_fields and ("grp_nombreGrupo" in r_data or "grp_nroGrupo" in r_data):
                es_grupo = True

            if es_grupo:
                nom_grp = r_data.get("grp_nombreGrupo", "")
                num_grp = r_data.get("grp_nroGrupo", "")
                grp_id_key = num_grp
                if not grp_id_key:
                    grp_id_key = "GRP_" + canonical_key(nom_grp)[:8].upper()

                if grp_id_key not in grupos_dict:
                    if not num_grp:
                        num_grp = grp_id_key
                    if not nom_grp:
                        nom_grp = "Grupo " + num_grp
                    grupos_dict[grp_id_key] = {
                        "tipo": "GRUPO",
                        "nroGrupo": num_grp,
                        "nombreGrupo": nom_grp,
                        "anioFormacion": r_data.get("grp_anioFormacion", ""),
                        "departamento": r_data.get("grp_departamento", r_data.get("inv_departamento", "")),
                        "ciudad": r_data.get("grp_ciudad", r_data.get("inv_ciudad", "")),
                        "lider": r_data.get("grp_lider", ""),
                        "informacionCertificada": r_data.get("grp_informacionCertificada", "Certificada"),
                        "paginaWeb": r_data.get("grp_paginaWeb", ""),
                        "email": r_data.get("grp_email", r_data.get("inv_correo", "")),
                        "clasificacion": r_data.get("grp_clasificacion", "Reconocido"),
                        "areaConocimiento": r_data.get("grp_areaConocimiento", ""),
                        "programaNacionalCti": r_data.get("grp_programaNacionalCti", ""),
                        "programaNacionalCtiSecundario": r_data.get("grp_programaNacionalCtiSecundario", ""),
                        "planEstrategico": r_data.get("grp_planEstrategico", ""),
                        "estadoArte": r_data.get("grp_estadoArte", ""),
                        "objetivos": r_data.get("grp_objetivos", ""),
                        "retos": r_data.get("grp_retos", ""),
                        "vision": r_data.get("grp_vision", ""),
                        "instituciones": [],
                        "lineasInvestigacion": [],
                        "integrantes": [],
                        "productos": [],
                        "_seen_prods": set(),
                        "_seen_mems": set()
                    }

                cur_grp = grupos_dict[grp_id_key]

                # Completar metadatos vacios si la fila actual aporta datos
                for m_field, g_attr in [
                    ("grp_lider", "lider"), ("grp_clasificacion", "clasificacion"),
                    ("grp_anioFormacion", "anioFormacion"), ("grp_areaConocimiento", "areaConocimiento"),
                    ("grp_departamento", "departamento"), ("grp_ciudad", "ciudad"),
                    ("grp_email", "email"), ("grp_paginaWeb", "paginaWeb"),
                    ("grp_programaNacionalCti", "programaNacionalCti"),
                    ("grp_programaNacionalCtiSecundario", "programaNacionalCtiSecundario"),
                    ("grp_planEstrategico", "planEstrategico"), ("grp_estadoArte", "estadoArte"),
                    ("grp_objetivos", "objetivos"), ("grp_retos", "retos"), ("grp_vision", "vision"),
                    ("grp_informacionCertificada", "informacionCertificada")
                ]:
                    if not cur_grp.get(g_attr) and m_field in r_data:
                        cur_grp[g_attr] = r_data[m_field]

                if "grp_instituciones" in r_data:
                    inst_items = parse_pipe_list(r_data["grp_instituciones"])
                    for inst_it in inst_items:
                        if inst_it and inst_it not in cur_grp["instituciones"]:
                            cur_grp["instituciones"].append(inst_it)
                elif "inv_institucion" in r_data:
                    inst_c = r_data["inv_institucion"]
                    if inst_c and inst_c not in cur_grp["instituciones"]:
                        cur_grp["instituciones"].append(inst_c)

                if "grp_lineasInvestigacion" in r_data:
                    lin_items = parse_pipe_list(r_data["grp_lineasInvestigacion"])
                    for lin_it in lin_items:
                        if lin_it and lin_it not in cur_grp["lineasInvestigacion"]:
                            cur_grp["lineasInvestigacion"].append(lin_it)

                # Agregar producto al grupo
                if prod_obj:
                    p_sig = (canonical_key(prod_obj["titulo"]), prod_obj["anio"])
                    if p_sig not in cur_grp["_seen_prods"]:
                        cur_grp["_seen_prods"].add(p_sig)
                        prod_copy = dict(prod_obj)
                        if not prod_copy.get("idProducto"):
                            prod_copy["idProducto"] = "GRP_PROD_" + str(len(cur_grp["productos"]) + 1).zfill(3)
                        cur_grp["productos"].append(prod_copy)

                # Agregar integrante al grupo
                mem_nom = r_data.get("mem_nombre", "")
                if not mem_nom and has_inv_fields and "inv_nombre" in r_data and r_data["inv_nombre"] != cur_grp["nombreGrupo"]:
                    mem_nom = r_data["inv_nombre"]

                if mem_nom and len(mem_nom) >= 3:
                    m_sig = canonical_key(mem_nom)
                    if m_sig not in cur_grp["_seen_mems"]:
                        cur_grp["_seen_mems"].add(m_sig)
                        cod_mem = r_data.get("mem_codigoRh", r_data.get("inv_codigoRh", ""))
                        if not cod_mem:
                            cod_mem = "MEM_" + canonical_key(mem_nom)[:8].upper()
                        inst_mem = r_data.get("mem_institucion", "")
                        if not inst_mem and len(cur_grp["instituciones"]) > 0:
                            inst_mem = cur_grp["instituciones"][0]
                        cur_grp["integrantes"].append({
                            "codigoRh": cod_mem,
                            "nombre": mem_nom,
                            "correo": r_data.get("mem_correo", r_data.get("inv_correo", "")),
                            "orcid": r_data.get("mem_orcid", r_data.get("inv_orcid", "")),
                            "institucion": inst_mem,
                            "departamento": r_data.get("mem_departamento", cur_grp["departamento"]),
                            "ciudad": r_data.get("mem_ciudad", cur_grp["ciudad"]),
                            "categoriaInvestigador": r_data.get("mem_categoria", r_data.get("inv_categoria", "")),
                            "perfil": r_data.get("mem_perfil", ""),
                            "activo": True
                        })

            # Caso 2: Fila con datos de Investigador
            es_inv = False
            if tipo_reg == "INVESTIGADOR":
                es_inv = True
            elif tipo_reg == "" and has_inv_fields and ("inv_nombre" in r_data or "inv_codigoRh" in r_data):
                if not has_grp_fields or r_data.get("inv_nombre", "") != r_data.get("grp_nombreGrupo", ""):
                    es_inv = True

            if es_inv:
                nom_inv = r_data.get("inv_nombre", "")
                cod_inv = r_data.get("inv_codigoRh", "")
                if nom_inv or cod_inv:
                    inv_id_key = cod_inv
                    if not inv_id_key:
                        inv_id_key = "INV_" + canonical_key(nom_inv)[:8].upper()

                    if inv_id_key not in investigadores_dict:
                        if not cod_inv:
                            cod_inv = inv_id_key
                        investigadores_dict[inv_id_key] = {
                            "tipo": "INVESTIGADOR",
                            "codigoRh": cod_inv,
                            "nombre": nom_inv,
                            "correo": r_data.get("inv_correo", ""),
                            "orcid": r_data.get("inv_orcid", ""),
                            "institucion": r_data.get("inv_institucion", ""),
                            "departamento": r_data.get("inv_departamento", ""),
                            "ciudad": r_data.get("inv_ciudad", ""),
                            "categoriaInvestigador": r_data.get("inv_categoria", "Sin categoría"),
                            "perfil": r_data.get("inv_perfil", ""),
                            "nombreCitaciones": r_data.get("inv_nombreCitaciones", ""),
                            "nacionalidad": r_data.get("inv_nacionalidad", "Colombiana"),
                            "sexo": r_data.get("inv_sexo", ""),
                            "estadoParEvaluador": r_data.get("inv_parevaluador", "No"),
                            "researcherId": r_data.get("inv_researcherId", ""),
                            "autorIdScopus": r_data.get("inv_scopus", ""),
                            "googleScholar": r_data.get("inv_scholar", ""),
                            "researchGate": r_data.get("inv_researchgate", ""),
                            "academiaEdu": r_data.get("inv_academiaEdu", ""),
                            "mendeley": r_data.get("inv_mendeley", ""),
                            "linkedin": r_data.get("inv_linkedin", ""),
                            "repositorioInstitucional": r_data.get("inv_repositorio", ""),
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
                            "activo": True,
                            "_seen_prods": set()
                        }

                    cur_inv = investigadores_dict[inv_id_key]

                    # Completar atributos escalares vacios
                    for f_src, a_dest in [
                        ("inv_correo", "correo"), ("inv_orcid", "orcid"), ("inv_institucion", "institucion"),
                        ("inv_departamento", "departamento"), ("inv_ciudad", "ciudad"),
                        ("inv_categoria", "categoriaInvestigador"), ("inv_perfil", "perfil"),
                        ("inv_nombreCitaciones", "nombreCitaciones"), ("inv_nacionalidad", "nacionalidad"),
                        ("inv_sexo", "sexo"), ("inv_parevaluador", "estadoParEvaluador"),
                        ("inv_researcherId", "researcherId"), ("inv_scopus", "autorIdScopus"),
                        ("inv_scholar", "googleScholar"), ("inv_researchgate", "researchGate"),
                        ("inv_academiaEdu", "academiaEdu"), ("inv_mendeley", "mendeley"),
                        ("inv_linkedin", "linkedin"), ("inv_repositorio", "repositorioInstitucional")
                    ]:
                        if not cur_inv.get(a_dest) and f_src in r_data:
                            cur_inv[a_dest] = r_data[f_src]

                    # Completar listas (idiomas, lineas, reconocimientos, formacion, etc.)
                    if "inv_idiomas" in r_data and len(cur_inv["idiomas"]) == 0:
                        cur_inv["idiomas"] = parse_languages(r_data["inv_idiomas"])

                    if "inv_lineasInvestigacion" in r_data:
                        lin_items = parse_pipe_list(r_data["inv_lineasInvestigacion"])
                        for lin_it in lin_items:
                            if lin_it and lin_it not in cur_inv["lineasInvestigacion"]:
                                cur_inv["lineasInvestigacion"].append(lin_it)

                    if "inv_reconocimientos" in r_data:
                        rec_items = parse_pipe_list(r_data["inv_reconocimientos"])
                        for rec_it in rec_items:
                            if rec_it and rec_it not in cur_inv["reconocimientos"]:
                                cur_inv["reconocimientos"].append(rec_it)

                    if "inv_formacionAcademica" in r_data:
                        form_items = parse_pipe_list(r_data["inv_formacionAcademica"])
                        for form_it in form_items:
                            if form_it and form_it not in cur_inv["formacionAcademica"]:
                                cur_inv["formacionAcademica"].append(form_it)

                    if "inv_experienciaProfesional" in r_data:
                        exp_items = parse_pipe_list(r_data["inv_experienciaProfesional"])
                        for exp_it in exp_items:
                            if exp_it and exp_it not in cur_inv["experienciaProfesional"]:
                                cur_inv["experienciaProfesional"].append(exp_it)

                    if "inv_proyectos" in r_data:
                        proy_items = parse_pipe_list(r_data["inv_proyectos"])
                        for proy_it in proy_items:
                            if proy_it and proy_it not in cur_inv["proyectos"]:
                                cur_inv["proyectos"].append(proy_it)

                    if "inv_areasConocimiento" in r_data:
                        area_items = parse_pipe_list(r_data["inv_areasConocimiento"])
                        for area_it in area_items:
                            if area_it and area_it not in cur_inv["areasConocimiento"]:
                                cur_inv["areasConocimiento"].append(area_it)

                    if "grp_nombreGrupo" in r_data:
                        grp_n = r_data["grp_nombreGrupo"]
                        if grp_n and grp_n not in cur_inv["gruposInvestigacion"]:
                            cur_inv["gruposInvestigacion"].append(grp_n)

                    # Agregar producto al investigador
                    if prod_obj:
                        p_sig = (canonical_key(prod_obj["titulo"]), prod_obj["anio"])
                        if p_sig not in cur_inv["_seen_prods"]:
                            cur_inv["_seen_prods"].add(p_sig)
                            prod_copy = dict(prod_obj)
                            if not prod_copy.get("idProducto"):
                                prod_copy["idProducto"] = "INV_PROD_" + str(len(cur_inv["productos"]) + 1).zfill(3)
                            cur_inv["productos"].append(prod_copy)

            r_idx += 1

        final_grupos = []
        for g_k, g_v in grupos_dict.items():
            if "_seen_prods" in g_v:
                del g_v["_seen_prods"]
            if "_seen_mems" in g_v:
                del g_v["_seen_mems"]
            final_grupos.append(g_v)

        final_invs = []
        for i_k, i_v in investigadores_dict.items():
            if "_seen_prods" in i_v:
                del i_v["_seen_prods"]
            final_invs.append(i_v)

        # Devolver entidad individual o lote
        if len(final_grupos) == 0 and len(final_invs) == 1:
            return final_invs[0]
        elif len(final_grupos) == 1 and len(final_invs) == 0:
            return final_grupos[0]
        else:
            return {
                "tipo": "LOTE",
                "grupos": final_grupos,
                "investigadores": final_invs
            }

    def extract(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
        ok_tab, headers, rows, msg_tab = self.read_and_validate_tabular(file_path)
        if not ok_tab:
            return False, {}, msg_tab

        mapping = self.map_headers(headers)
        result = self.normalize_and_extract(headers, rows, mapping)
        t = result.get("tipo", "")
        if t == "INVESTIGADOR":
            msg = f"Extracción CSV exitosa: Investigador {result.get('nombre', '')} ({len(result.get('productos', []))} productos)."
        elif t == "GRUPO":
            msg = f"Extracción CSV exitosa: Grupo {result.get('nombreGrupo', '')} ({len(result.get('integrantes', []))} integrantes, {len(result.get('productos', []))} productos)."
        else:
            msg = f"Extracción CSV exitosa: {len(result.get('investigadores', []))} investigadores y {len(result.get('grupos', []))} grupos."
        return True, result, msg

ext = CSVExtractorTest()
ok1, res1, msg1 = ext.extract("Prueba_CvLAC_Aith_Bismarck.csv")
print("=== PRUEBA CVLAC ===")
print("OK:", ok1)
print("Tipo:", res1.get("tipo"))
print("Nombre:", res1.get("nombre"))
print("Codigo RH:", res1.get("codigoRh"))
print("Institucion:", res1.get("institucion"))
print("Idiomas count:", len(res1.get("idiomas", [])))
print("Idiomas sample:", res1.get("idiomas", [])[:3])
print("Lineas investigacion count:", len(res1.get("lineasInvestigacion", [])))
print("Lineas sample:", res1.get("lineasInvestigacion", [])[:3])
print("Reconocimientos count:", len(res1.get("reconocimientos", [])))
print("Reconocimientos sample:", res1.get("reconocimientos", [])[:2])
print("Formacion academica count:", len(res1.get("formacionAcademica", [])))
print("Experiencia count:", len(res1.get("experienciaProfesional", [])))
print("Proyectos count:", len(res1.get("proyectos", [])))
print("Productos count:", len(res1.get("productos", [])))
if res1.get("productos"):
    print("Primer producto:", res1.get("productos")[0])

print("\n=== PRUEBA GRUPLAC ===")
ok2, res2, msg2 = ext.extract("Prueba_GrupLAC_AITICE.csv")
print("OK:", ok2)
print("Tipo:", res2.get("tipo"))
print("Nombre grupo:", res2.get("nombreGrupo"))
print("Codigo grupo:", res2.get("nroGrupo"))
print("Lider grupo:", res2.get("lider"))
print("Clasificacion:", res2.get("clasificacion"))
print("Instituciones count:", len(res2.get("instituciones", [])))
print("Lineas investigacion count:", len(res2.get("lineasInvestigacion", [])))
print("Lineas sample:", res2.get("lineasInvestigacion", [])[:3])
print("Integrantes count:", len(res2.get("integrantes", [])))
print("Productos count:", len(res2.get("productos", [])))
if res2.get("productos"):
    print("Primer producto:", res2.get("productos")[0])
