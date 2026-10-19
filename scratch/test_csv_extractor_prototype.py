import csv
import io
import os
import re
from typing import Dict, Any, List, Tuple, Set

def clean_text(s: Any) -> str:
    if s is None:
        return ""
    return " ".join(str(s).split()).strip()

def canonical_key(s: Any) -> str:
    if not s:
        return ""
    norm = str(s).strip().lower()
    for o, d in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n'), ('ü', 'u')]:
        norm = norm.replace(o, d)
    return re.sub(r'[^a-z0-9]', '', norm)

# Catálogo explícito de alias normalizados
ALIAS_MAP = {
    # Campos de Investigador
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
        "institucionprincipal"
    ],
    "inv_departamento": [
        "departamento", "depto", "departamentoubicacion"
    ],
    "inv_ciudad": [
        "ciudad", "municipio"
    ],
    "inv_categoria": [
        "categoria", "categoriainvestigador", "clasificacioninvestigador", "escalafon",
        "nivelinvestigador", "tipoinvestigador"
    ],
    "inv_perfil": [
        "perfil", "perfilcvlac", "resumenperfil", "descripcionperfil"
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

    # Campos de Grupo
    "grp_nroGrupo": [
        "nrogrupo", "codigogrupo", "idgrupo", "codigogruplac", "gruplac", "idgruplac",
        "codgrupo", "numerogrupo"
    ],
    "grp_nombreGrupo": [
        "nombregrupo", "nombredelgrupo", "grupo", "grupodeinvestigacion"
    ],
    "grp_lider": [
        "lider", "liderdelgrupo", "liderinvestigador", "director", "directordelgrupo"
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
        "areaconocimiento", "areadeconocimiento", "granareadeconocimiento", "granarea", "area"
    ],
    "grp_email": [
        "emailgrupo", "correogrupo"
    ],
    "grp_paginaWeb": [
        "paginaweb", "sitio", "sitioweb", "url", "web"
    ],
    "grp_programaNacionalCti": [
        "programanacionalcti", "programanacional", "programacti"
    ],

    # Campos de Producto
    "prod_titulo": [
        "titulo", "tituloproducto", "titulodelproducto", "nombreproducto", "producto",
        "titulopublicacion", "tituloproyecto", "publicacion", "nombrearticulo", "titulolibro"
    ],
    "prod_anio": [
        "anio", "ano", "aniopublicacion", "anopublicacion", "fechapublicacion", "fecha"
    ],
    "prod_categoria": [
        "categoriaproducto", "tipoproducto", "tipo", "tipologia", "subtipo", "claseproducto"
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
    "prod_descripcion": [
        "descripcion", "resumen", "detalles", "observaciones"
    ],
    "prod_autores": [
        "autores", "autoresproducto", "coautores", "investigadoresparticipantes"
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
    ]
}


class CSVExtractor:
    """
    Pipeline independiente de 4 capas para la importación e ingestión de archivos CSV MinCiencias.
    Capa 1: Lectura, decodificación y consistencia dialectal (coma / punto y coma).
    Capa 2: Gatekeeper semántico y estructural MinCiencias.
    Capa 3: Normalización de alias, mapeo relacional y estructuración.
    Capa 4: Deduplicación, resolución de relaciones y construcción de lote interoperable.
    """

    def __init__(self) -> None:
        self.min_columns = 2

    def read_and_validate_tabular(self, file_path: str) -> Tuple[bool, List[str], List[List[str]], str]:
        """Capa 1: Valida extensión, lee bytes, determina encoding y dialecto tabular consistente."""
        if not file_path.lower().endswith(".csv"):
            return False, [], [], "El archivo no tiene la extensión requerida .csv"

        if not os.path.isfile(file_path):
            return False, [], [], "El archivo no existe o no es accesible: " + str(file_path)

        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
        except Exception as exc:
            return False, [], [], "Error al abrir el archivo: " + str(exc)

        if len(raw_bytes.strip()) == 0:
            return False, [], [], "El archivo CSV está vacío."

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

        stripped = text_content.strip()
        if len(stripped) == 0:
            return False, [], [], "El archivo CSV no contiene texto tras la decodificación."

        # Descartar formatos que no son tabulares aunque tengan extensión .csv
        if stripped.startswith("{") or stripped.startswith("["):
            return False, [], [], "El archivo no es tabular (formato JSON detectado)."

        primera_linea = stripped.splitlines()[0].strip().lower()
        if primera_linea.startswith("<!doctype") or primera_linea.startswith("<html") or primera_linea.startswith("<?xml"):
            return False, [], [], "El archivo no es tabular (código HTML/XML detectado)."

        if primera_linea.startswith("#include") or primera_linea.startswith("import ") or primera_linea.startswith("def ") or primera_linea.startswith("public class"):
            return False, [], [], "El archivo no es tabular (código fuente detectado)."

        if primera_linea.startswith("# ") or primera_linea.startswith("## ") or primera_linea.startswith("```"):
            return False, [], [], "El archivo no es tabular (formato Markdown detectado)."

        # Probar delimitadores admitidos (coma y punto y coma)
        delimiters = [",", ";"]
        candidates = []

        d_idx = 0
        while d_idx < len(delimiters):
            d = delimiters[d_idx]
            try:
                reader = csv.reader(io.StringIO(text_content), delimiter=d, quotechar='"')
                rows = []
                for r in reader:
                    # Limpiar celdas vacias al final
                    row_clean = [clean_text(cell) for cell in r]
                    if any(len(c) > 0 for c in row_clean):
                        rows.append(row_clean)

                if len(rows) >= 2:
                    header = rows[0]
                    num_cols = len(header)
                    if num_cols >= self.min_columns:
                        data_rows = rows[1:]
                        consistent_count = 0
                        row_idx = 0
                        while row_idx < len(data_rows):
                            dr = data_rows[row_idx]
                            # Aceptar si la longitud coincide o difiere solo en trailing vacios
                            if len(dr) == num_cols:
                                consistent_count += 1
                            elif len(dr) > num_cols and all(len(c) == 0 for c in dr[num_cols:]):
                                consistent_count += 1
                            row_idx += 1

                        if consistent_count == len(data_rows):
                            candidates.append({
                                "delimiter": d,
                                "header": header,
                                "rows": data_rows,
                                "cols": num_cols,
                                "count": len(data_rows)
                            })
            except Exception:
                pass
            d_idx += 1

        if len(candidates) == 0:
            return False, [], [], "El archivo no posee una estructura tabular válida con delimitador coma o punto y coma."

        selected = None
        if len(candidates) == 1:
            selected = candidates[0]
        else:
            # Si ambos fueron parseables, seleccionar el que produzca mas columnas o mejor consistencia
            c0 = candidates[0]
            c1 = candidates[1]
            if c0["cols"] > c1["cols"]:
                selected = c0
            elif c1["cols"] > c0["cols"]:
                selected = c1
            else:
                return False, [], [], "No fue posible determinar un delimitador tabular unívoco entre coma y punto y coma."

        final_header = selected["header"]
        final_rows = selected["rows"]

        if len(final_header) < self.min_columns:
            return False, [], [], "El archivo CSV contiene una sola columna; se requiere formato tabular."

        if len(final_rows) == 0:
            return False, [], [], "El archivo CSV no contiene filas de datos."

        return True, final_header, final_rows, "Estructura tabular verificada."

    def map_headers(self, headers: List[str]) -> Dict[int, str]:
        """Capa 3 auxiliar: Mapea cada indice de columna a su rol canónico en el catálogo de alias."""
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

    def verify_gatekeeper(self, headers: List[str], rows: List[List[str]], mapping: Dict[int, str]) -> Tuple[bool, str]:
        """Capa 2: Valida evidencia estructural y semántica de MinCiencias."""
        if len(mapping) == 0:
            return False, "Los encabezados del archivo no contienen ningún campo reconocido del modelo MinCiencias."

        mapped_fields = set(mapping.values())

        # Categorizar campos reconocidos
        inv_fields = set()
        grp_fields = set()
        prod_fields = set()
        mem_fields = set()

        for f in mapped_fields:
            if f.startswith("inv_"):
                inv_fields.add(f)
            elif f.startswith("grp_"):
                grp_fields.add(f)
            elif f.startswith("prod_"):
                prod_fields.add(f)
            elif f.startswith("mem_"):
                mem_fields.add(f)

        # Campos de identidad especifica MinCiencias
        strong_markers = {
            "inv_codigoRh", "inv_orcid", "inv_categoria", "inv_parevaluador",
            "grp_nroGrupo", "grp_clasificacion", "grp_lider", "grp_areaConocimiento",
            "prod_doi", "prod_isbn", "prod_categoria", "prod_revista"
        }
        has_strong_marker = bool(mapped_fields.intersection(strong_markers))

        # Analizar valores en las filas en busca de señales semánticas
        semantic_research_hits = 0
        research_terms = {
            "senior", "asociado", "junior", "emerito", "a1", "reconocido",
            "articulo", "software", "libro", "capitulo", "prototipo", "patente",
            "universidad", "instituto", "colciencias", "minciencias", "snctei",
            "trabajo de grado", "maestria", "doctorado", "ingenieria", "ciencias"
        }

        r_idx = 0
        limit_r = 10
        if len(rows) < limit_r:
            limit_r = len(rows)
        while r_idx < limit_r:
            row = rows[r_idx]
            for cell in row:
                c_norm = canonical_key(cell)
                for term in research_terms:
                    if term in c_norm:
                        semantic_research_hits += 1
                # Detector de formato ORCID
                if re.search(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b", cell):
                    semantic_research_hits += 3
                # Detector de formato DOI
                if re.search(r"\b10\.\d{4,9}/", cell):
                    semantic_research_hits += 3
            r_idx += 1

        is_valid_research = False
        reason = ""

        # Perfil 1: Investigador
        if "inv_nombre" in mapped_fields:
            if "inv_codigoRh" in mapped_fields or "inv_categoria" in mapped_fields or "inv_orcid" in mapped_fields:
                is_valid_research = True
            elif "inv_correo" in mapped_fields and ("inv_institucion" in mapped_fields or "prod_titulo" in mapped_fields):
                is_valid_research = True
            elif has_strong_marker or semantic_research_hits >= 2:
                is_valid_research = True

        # Perfil 2: Grupo
        if "grp_nombreGrupo" in mapped_fields:
            if "grp_nroGrupo" in mapped_fields or "grp_lider" in mapped_fields or "grp_clasificacion" in mapped_fields or "grp_areaConocimiento" in mapped_fields:
                is_valid_research = True
            elif mem_fields or prod_fields or semantic_research_hits >= 2:
                is_valid_research = True

        # Perfil 3: Productos con contexto de Grupo o Investigador
        if "prod_titulo" in mapped_fields:
            if ("grp_nroGrupo" in mapped_fields or "grp_nombreGrupo" in mapped_fields or "inv_codigoRh" in mapped_fields or "inv_nombre" in mapped_fields):
                if has_strong_marker or semantic_research_hits >= 2:
                    is_valid_research = True

        # Perfil 4: Codigo de grupo o de investigador explicito con productos o miembros
        if ("grp_nroGrupo" in mapped_fields or "inv_codigoRh" in mapped_fields) and (prod_fields or mem_fields or semantic_research_hits >= 1):
            is_valid_research = True

        if not is_valid_research:
            return False, "El archivo no contiene suficientes atributos ni señales semánticas específicas de investigación MinCiencias."

        # Comprobar que al menos una fila tenga valores utiles en los campos requeridos
        has_usable_row = False
        r_check = 0
        while r_check < len(rows):
            row = rows[r_check]
            row_dict = {}
            col_i = 0
            while col_i < len(row):
                if col_i in mapping:
                    f_name = mapping[col_i]
                    val = clean_text(row[col_i])
                    if val:
                        row_dict[f_name] = val
                col_i += 1

            if "inv_nombre" in row_dict and len(row_dict["inv_nombre"]) >= 3:
                has_usable_row = True
            if "grp_nombreGrupo" in row_dict and len(row_dict["grp_nombreGrupo"]) >= 2:
                has_usable_row = True
            if "prod_titulo" in row_dict and len(row_dict["prod_titulo"]) >= 3:
                has_usable_row = True
            if "grp_nroGrupo" in row_dict and len(row_dict["grp_nroGrupo"]) >= 2:
                has_usable_row = True
            if "inv_codigoRh" in row_dict and len(row_dict["inv_codigoRh"]) >= 2:
                has_usable_row = True

            r_check += 1

        if not has_usable_row:
            return False, "Las filas de datos no contienen valores válidos en los campos de identidad mínimos requeridos."

        return True, "Validación de Gatekeeper MinCiencias aprobada."

    def normalize_product_category(self, raw_cat: str, titulo: str) -> str:
        """Normaliza la categoría de producto a las categorías estándar de la aplicación."""
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
        """Capa 3 y 4: Normaliza, agrupa por entidad, deduplica internamente y construye el lote estructurado."""
        # Almacenes intermedios agrupados
        grupos_dict: Dict[str, Dict[str, Any]] = {}
        investigadores_dict: Dict[str, Dict[str, Any]] = {}

        # Determinar que perfiles dominan
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
                    cat_val = self.normalize_product_category(r_data.get("prod_categoria", ""), tit)
                    autores_list = []
                    if "prod_autores" in r_data:
                        for aut in re.split(r"[,;]+", r_data["prod_autores"]):
                            c_aut = clean_text(aut)
                            if c_aut:
                                autores_list.append(c_aut)
                    prod_obj = {
                        "idProducto": "",
                        "titulo": tit,
                        "categoria": cat_val,
                        "validado": True,
                        "anio": anio_val,
                        "tipoProducto": cat_val,
                        "subtipo": r_data.get("prod_categoria", ""),
                        "doi": r_data.get("prod_doi", ""),
                        "isbn": r_data.get("prod_isbn", ""),
                        "revista": r_data.get("prod_revista", ""),
                        "editorial": r_data.get("prod_editorial", ""),
                        "descripcion": r_data.get("prod_descripcion", ""),
                        "autores": autores_list
                    }

            # Caso 1: Fila con datos de Grupo
            if has_grp_fields and ("grp_nombreGrupo" in r_data or "grp_nroGrupo" in r_data):
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
                        "informacionCertificada": "Certificada",
                        "paginaWeb": r_data.get("grp_paginaWeb", ""),
                        "email": r_data.get("grp_email", r_data.get("inv_correo", "")),
                        "clasificacion": r_data.get("grp_clasificacion", "Reconocido"),
                        "areaConocimiento": r_data.get("grp_areaConocimiento", ""),
                        "programaNacionalCti": r_data.get("grp_programaNacionalCti", ""),
                        "programaNacionalCtiSecundario": "",
                        "planEstrategico": "",
                        "estadoArte": "",
                        "objetivos": "",
                        "retos": "",
                        "vision": "",
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
                    ("grp_email", "email"), ("grp_paginaWeb", "paginaWeb")
                ]:
                    if not cur_grp.get(g_attr) and m_field in r_data:
                        cur_grp[g_attr] = r_data[m_field]

                if "inv_institucion" in r_data:
                    inst_c = r_data["inv_institucion"]
                    if inst_c and inst_c not in cur_grp["instituciones"]:
                        cur_grp["instituciones"].append(inst_c)

                # Agregar producto al grupo
                if prod_obj:
                    p_sig = (canonical_key(prod_obj["titulo"]), prod_obj["anio"])
                    if p_sig not in cur_grp["_seen_prods"]:
                        cur_grp["_seen_prods"].add(p_sig)
                        prod_copy = dict(prod_obj)
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
                        cur_grp["integrantes"].append({
                            "codigoRh": cod_mem,
                            "nombre": mem_nom,
                            "correo": r_data.get("inv_correo", ""),
                            "institucion": cur_grp["instituciones"][0] if cur_grp["instituciones"] else "",
                            "departamento": cur_grp["departamento"],
                            "ciudad": cur_grp["ciudad"],
                            "categoriaInvestigador": r_data.get("inv_categoria", ""),
                            "activo": True
                        })

            # Caso 2: Fila con datos de Investigador (cuando no es solo integrante de grupo o el archivo es de investigadores)
            if has_inv_fields and ("inv_nombre" in r_data or "inv_codigoRh" in r_data):
                nom_inv = r_data.get("inv_nombre", "")
                cod_inv = r_data.get("inv_codigoRh", "")
                # Asegurar que el nombre no sea el nombre del grupo
                if nom_inv and (not has_grp_fields or nom_inv != r_data.get("grp_nombreGrupo", "")):
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
                            "activo": True,
                            "_seen_prods": set()
                        }

                    cur_inv = investigadores_dict[inv_id_key]

                    # Completar atributos vacios
                    for f_src, a_dest in [
                        ("inv_correo", "correo"), ("inv_orcid", "orcid"), ("inv_institucion", "institucion"),
                        ("inv_departamento", "departamento"), ("inv_ciudad", "ciudad"),
                        ("inv_categoria", "categoriaInvestigador"), ("inv_perfil", "perfil")
                    ]:
                        if not cur_inv.get(a_dest) and f_src in r_data:
                            cur_inv[a_dest] = r_data[f_src]

                    # Asociar nombre de grupo al investigador si viene en la fila
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
                            prod_copy["idProducto"] = "INV_PROD_" + str(len(cur_inv["productos"]) + 1).zfill(3)
                            cur_inv["productos"].append(prod_copy)

            r_idx += 1

        # Limpiar atributos internos auxiliares
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

        result_payload = {
            "tipo": "LOTE",
            "grupos": final_grupos,
            "investigadores": final_invs
        }
        return result_payload

    def extract(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
        """Ejecuta el pipeline completo de 4 capas para un archivo CSV."""
        ok_tab, headers, rows, msg_tab = self.read_and_validate_tabular(file_path)
        if not ok_tab:
            return False, {}, msg_tab

        mapping = self.map_headers(headers)
        ok_gate, msg_gate = self.verify_gatekeeper(headers, rows, mapping)
        if not ok_gate:
            return False, {}, msg_gate

        result = self.normalize_and_extract(headers, rows, mapping)
        total_g = len(result.get("grupos", []))
        total_i = len(result.get("investigadores", []))

        if total_g == 0 and total_i == 0:
            return False, {}, "El archivo fue procesado pero no produjo ninguna entidad válida de MinCiencias."

        msg_success = f"Extracción CSV exitosa: {total_i} investigador(es) y {total_g} grupo(s) procesados."
        return True, result, msg_success

print("CSVExtractor class defined successfully.")
