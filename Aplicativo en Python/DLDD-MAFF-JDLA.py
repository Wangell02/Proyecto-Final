# -*- coding: utf-8 -*-
"""
PROYECTO PEA-i (Programa Estadistico UPC) - Modulo Scraper Unificado
====================================================================
Este archivo consolida todos los modulos del aplicativo PEA-Scraper en un
unico codigo fuente independiente:
  1. Utilidades y configuracion de rutas.
  2. Modelos de datos (Investigador, Grupo, Producto).
  3. Protocolo de interoperabilidad estructurado para C++.
  4. Persistencia en archivos JSON.
  5. Motor de scraping nativo para CvLAC y GrupLAC (Minciencias).
  6. Capa de servicios y logica de negocio.
  7. Servidor API local HTTP (127.0.0.1:8765) para puente con C++.
  8. Interfaz grafica moderna Tkinter con visualizador de cubo y reportes.
"""

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime
import codecs
import copy
import csv
from html import unescape
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Iterable, List, Optional, Tuple
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
import webbrowser
import zlib
try:
    import fitz
except ImportError:
    fitz = None



# =========================================================================
# UTILIDADES Y CONFIGURACION DEL SISTEMA
# =========================================================================

def application_root() -> Path:
    return Path(__file__).resolve().parent


def data_directory() -> Path:
    if getattr(sys, "frozen", False):
        target = Path(sys.executable).resolve().parent
    else:
        target = application_root()

    target.mkdir(parents=True, exist_ok=True)
    return target


def resource_path(*parts: str) -> Path:
    root = application_root()
    result = root
    for part in parts:
        result = result / part
    return result


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        valid = parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        valid = False
    return valid


def validar_url_minciencias(tipo: str, raw_url: str) -> Tuple[bool, str, str]:
    """
    Valida y normaliza URLs para la carga de datos de Minciencias (CvLAC y GrupLAC).
    Retorna: (es_valido, url_normalizada, mensaje_error).
    """
    url = str(raw_url or "").strip()
    if not url:
        return False, "", "Debe ingresar una URL para procesar la carga."

    norm_url = url
    if not (norm_url.startswith("http://") or norm_url.startswith("https://")):
        norm_url = "https://" + norm_url

    parsed = urlparse(norm_url)
    domain = (parsed.netloc or "").lower().split(":")[0]

    # 1. Validación general: dominio oficial scienti.minciencias.gov.co
    if domain != "scienti.minciencias.gov.co":
        return (
            False,
            norm_url,
            "URL inválida: El enlace debe pertenecer al dominio oficial 'scienti.minciencias.gov.co'."
        )

    # 2. Validación según tipo de entidad
    tipo_norm = str(tipo or "").strip().casefold()
    url_lower = norm_url.lower()

    if tipo_norm == "investigador":
        if "/gruplac" in url_lower:
            return (
                False,
                norm_url,
                "Incompatibilidad de tipo: La URL ingresada corresponde a un grupo (GrupLAC) y no a un investigador (CvLAC). "
                "Seleccione la opción 'Grupo · GrupLAC' si desea registrar este grupo."
            )
        if "/cvlac" not in url_lower:
            return (
                False,
                norm_url,
                "URL de investigador inválida: El enlace debe corresponder a un perfil CvLAC (debe contener '/cvlac')."
            )

    elif tipo_norm == "grupo":
        if "/cvlac" in url_lower:
            return (
                False,
                norm_url,
                "Incompatibilidad de tipo: La URL ingresada corresponde a un investigador (CvLAC) y no a un grupo (GrupLAC). "
                "Seleccione la opción 'Investigador · CvLAC' si desea registrar este investigador."
            )
        if "/gruplac" not in url_lower:
            return (
                False,
                norm_url,
                "URL de grupo inválida: El enlace debe corresponder a un grupo GrupLAC (debe contener '/gruplac')."
            )

    else:
        return False, norm_url, f"Tipo de entidad no reconocido: '{tipo}'."

    return True, norm_url, ""


def normalize_whitespace(text: str) -> str:
    if text is None:
        value = ""
    else:
        value = str(text)
    value = value.replace("\xa0", " ")
    value = value.replace("\r", "\n")
    value = re.sub(r"[\t ]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    lines = [line.strip() for line in value.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def unique_preserve(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        item = normalize_whitespace(value)
        key = item.casefold()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def safe_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError, TypeError):
        return default


def save_json_file(path: Path, data: Any) -> bool:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        ok = True
    except (OSError, TypeError, ValueError):
        ok = False
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass
    return ok


def txt_safe(value: Any) -> str:
    if value is None:
        text = ""
    else:
        text = str(value)
    text = text.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    return normalize_whitespace(text)


def canonical_key(text: str) -> str:
    val = ""
    if text is not None:
        val = str(text)
    val = val.replace("\xa0", " ")
    val = " ".join(val.split()).strip()
    decomposed = unicodedata.normalize("NFD", val)
    filtered = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    alphanumeric = "".join(ch.lower() for ch in filtered if ch.isalnum() or ch.isspace())
    return " ".join(alphanumeric.split())


# =========================================================================
# MODELOS DE DATOS
# =========================================================================

def clean_text(value: Any) -> str:
    if value is None:
        text = ""
    else:
        text = str(value)
    text = text.replace("\xa0", " ")
    text = " ".join(text.split())
    return text.strip()


def unique_strings(values: List[Any]) -> List[str]:
    output: List[str] = []
    seen = set()
    for value in values:
        item = clean_text(value)
        key = item.casefold()
        if item and key not in seen:
            output.append(item)
            seen.add(key)
    return output


@dataclass
class ProductoInvestigacion:
    idProducto: str = ""
    titulo: str = ""
    categoria: str = ""
    validado: bool = False
    anio: int = 0
    tipoProducto: str = ""
    subtipo: str = ""
    doi: str = ""
    isbn: str = ""
    revista: str = ""
    editorial: str = ""
    disponibilidad: str = ""
    institucion: str = ""
    ciudad: str = ""
    pais: str = ""
    numeroContrato: str = ""
    descripcion: str = ""
    palabrasClave: str = ""
    areas: str = ""
    autores: List[str] = field(default_factory=list)

    def normalizar(self) -> None:
        self.idProducto = clean_text(self.idProducto)
        self.titulo = clean_text(self.titulo)
        self.categoria = clean_text(self.categoria)
        self.tipoProducto = clean_text(self.tipoProducto)
        self.subtipo = clean_text(self.subtipo)
        self.doi = clean_text(self.doi)
        self.isbn = clean_text(self.isbn)
        self.revista = clean_text(self.revista)
        self.editorial = clean_text(self.editorial)
        self.disponibilidad = clean_text(self.disponibilidad)
        self.institucion = clean_text(self.institucion)
        self.ciudad = clean_text(self.ciudad)
        self.pais = clean_text(self.pais)
        self.numeroContrato = clean_text(self.numeroContrato)
        self.descripcion = clean_text(self.descripcion)
        self.palabrasClave = clean_text(self.palabrasClave)
        self.areas = clean_text(self.areas)
        normalized_year = 0
        try:
            normalized_year = int(self.anio)
        except (TypeError, ValueError):
            normalized_year = 0
        self.anio = normalized_year
        self.autores = unique_strings(self.autores)

    def to_dict(self) -> Dict[str, Any]:
        self.normalizar()
        return asdict(self)


@dataclass
class Investigador:
    codigoRh: str = ""
    nombre: str = ""
    correo: str = ""
    orcid: str = ""
    institucion: str = ""
    departamento: str = ""
    ciudad: str = ""
    categoriaInvestigador: str = ""
    perfil: str = ""
    nombreCitaciones: str = ""
    nacionalidad: str = ""
    sexo: str = ""
    estadoParEvaluador: str = ""
    researcherId: str = ""
    autorIdScopus: str = ""
    googleScholar: str = ""
    researchGate: str = ""
    academiaEdu: str = ""
    mendeley: str = ""
    linkedin: str = ""
    repositorioInstitucional: str = ""
    idiomas: List[str] = field(default_factory=list)
    areasConocimiento: List[str] = field(default_factory=list)
    lineasInvestigacion: List[str] = field(default_factory=list)
    formacionAcademica: List[str] = field(default_factory=list)
    experienciaProfesional: List[str] = field(default_factory=list)
    gruposInvestigacion: List[str] = field(default_factory=list)
    semilleros: List[str] = field(default_factory=list)
    proyectos: List[str] = field(default_factory=list)
    reconocimientos: List[str] = field(default_factory=list)
    productos: List[Dict[str, Any]] = field(default_factory=list)
    activo: bool = True

    def normalizar(self) -> None:
        text_fields = [
            "codigoRh", "nombre", "correo", "orcid", "institucion",
            "departamento", "ciudad", "categoriaInvestigador", "perfil",
            "nombreCitaciones", "nacionalidad", "sexo", "estadoParEvaluador",
            "researcherId", "autorIdScopus", "googleScholar", "researchGate",
            "academiaEdu", "mendeley", "linkedin", "repositorioInstitucional"
        ]
        for field_name in text_fields:
            setattr(self, field_name, clean_text(getattr(self, field_name)))
        list_fields = [
            "idiomas", "areasConocimiento", "lineasInvestigacion", "formacionAcademica",
            "experienciaProfesional", "gruposInvestigacion", "semilleros", "proyectos",
            "reconocimientos"
        ]
        for field_name in list_fields:
            setattr(self, field_name, unique_strings(getattr(self, field_name)))
        normalized_products: List[Dict[str, Any]] = []
        for product in self.productos:
            if isinstance(product, dict):
                item = product
            else:
                item = {}
            product_model = ProductoInvestigacion(**{k: item.get(k, v) for k, v in ProductoInvestigacion().__dict__.items()})
            product_model.normalizar()
            normalized_products.append(product_model.to_dict())
        self.productos = normalized_products
        self.activo = bool(self.activo)

    def to_dict(self) -> Dict[str, Any]:
        self.normalizar()
        return asdict(self)


@dataclass
class GrupoInvestigacion:
    nroGrupo: str = ""
    nombreGrupo: str = ""
    anioFormacion: str = ""
    departamento: str = ""
    ciudad: str = ""
    lider: str = ""
    informacionCertificada: str = ""
    paginaWeb: str = ""
    email: str = ""
    clasificacion: str = ""
    areaConocimiento: str = ""
    programaNacionalCti: str = ""
    programaNacionalCtiSecundario: str = ""
    planEstrategico: str = ""
    estadoArte: str = ""
    objetivos: str = ""
    retos: str = ""
    vision: str = ""
    instituciones: List[str] = field(default_factory=list)
    lineasInvestigacion: List[str] = field(default_factory=list)
    integrantes: List[Dict[str, Any]] = field(default_factory=list)
    productos: List[Dict[str, Any]] = field(default_factory=list)

    def normalizar(self) -> None:
        text_fields = [
            "nroGrupo", "nombreGrupo", "anioFormacion", "departamento", "ciudad", "lider",
            "informacionCertificada", "paginaWeb", "email", "clasificacion", "areaConocimiento",
            "programaNacionalCti", "programaNacionalCtiSecundario", "planEstrategico", "estadoArte",
            "objetivos", "retos", "vision"
        ]
        for field_name in text_fields:
            setattr(self, field_name, clean_text(getattr(self, field_name)))
        self.instituciones = unique_strings(self.instituciones)
        self.lineasInvestigacion = unique_strings(self.lineasInvestigacion)
        normalized_members: List[Dict[str, Any]] = []
        for member in self.integrantes:
            if isinstance(member, dict):
                item = member
            else:
                item = {}
            member_model = Investigador(**{k: item.get(k, v) for k, v in Investigador().__dict__.items()})
            member_model.normalizar()
            normalized_member = member_model.to_dict()
            for extra_key in ("vinculacion", "horasDedicacion", "inicioFinVinculacion"):
                if extra_key in item:
                    normalized_member[extra_key] = clean_text(item.get(extra_key, ""))
            normalized_members.append(normalized_member)
        self.integrantes = normalized_members
        normalized_products: List[Dict[str, Any]] = []
        for product in self.productos:
            if isinstance(product, dict):
                item = product
            else:
                item = {}
            product_model = ProductoInvestigacion(**{k: item.get(k, v) for k, v in ProductoInvestigacion().__dict__.items()})
            product_model.normalizar()
            normalized_products.append(product_model.to_dict())
        self.productos = normalized_products

    def to_dict(self) -> Dict[str, Any]:
        self.normalizar()
        return asdict(self)


# =========================================================================
# PROTOCOLO DE INTEROPERABILIDAD C++ / TXT
# =========================================================================

def _bool_text(value: Any) -> str:
    if bool(value):
        text = "1"
    else:
        text = "0"
    return text


def _product_line(prefix: str, product: Dict[str, Any]) -> str:
    fields = [
        prefix,
        product.get("idProducto", ""),
        product.get("titulo", ""),
        product.get("categoria", ""),
        _bool_text(product.get("validado", False)),
        product.get("anio", 0),
        product.get("tipoProducto", ""),
        product.get("subtipo", ""),
        product.get("doi", ""),
        product.get("isbn", ""),
        product.get("revista", ""),
        product.get("editorial", ""),
        product.get("disponibilidad", ""),
        product.get("institucion", ""),
        product.get("ciudad", ""),
        product.get("pais", ""),
        product.get("numeroContrato", ""),
        product.get("descripcion", "")
    ]
    return "\t".join(txt_safe(value) for value in fields)


def _write_list(lines: List[str], tag: str, values: List[Any]) -> None:
    for value in values:
        lines.append("{}\t{}".format(tag, txt_safe(value)))


def _write_product(lines: List[str], prefix: str, product: Dict[str, Any]) -> None:
    lines.append(_product_line(prefix, product))
    authors = product.get("autores", [])
    if not isinstance(authors, list):
        authors = []
    _write_list(lines, "AUTOR", authors)
    lines.append("PRODUCTO_FIN")


def serialize_result(result: Dict[str, Any]) -> str:
    lines: List[str] = ["ESTADO\tOK"]
    tipo = txt_safe(result.get("tipo", "")).upper()
    if not tipo:
        if "nroGrupo" in result:
            tipo = "GRUPO"
        elif "codigoRh" in result:
            tipo = "INVESTIGADOR"

    lines.append("TIPO\t{}".format(tipo))

    def escribir_producto(prefix: str, product: Dict[str, Any]) -> None:
        campos = [
            prefix, product.get("idProducto", ""), product.get("titulo", ""), product.get("categoria", ""),
            _bool_text(product.get("validado", False)), product.get("anio", 0), product.get("tipoProducto", ""),
            product.get("subtipo", ""), product.get("doi", ""), product.get("isbn", ""), product.get("revista", ""),
            product.get("editorial", ""), product.get("disponibilidad", ""), product.get("institucion", ""),
            product.get("ciudad", ""), product.get("pais", ""), product.get("numeroContrato", ""),
            product.get("descripcion", ""), product.get("palabrasClave", ""), product.get("areas", "")
        ]
        lines.append("\t".join(txt_safe(v) for v in campos))
        autores = product.get("autores", [])
        if not isinstance(autores, list):
            autores = []
        _write_list(lines, "AUTOR", autores)
        lines.append("PRODUCTO_FIN")

    def escribir_campos(obj: Dict[str, Any], campos: List[Any]) -> None:
        for tag, key in campos:
            lines.append("{}\t{}".format(tag, txt_safe(obj.get(key, ""))))

    if tipo == "GRUPO":
        lines.append("GRUPO\t{}\t{}".format(txt_safe(result.get("nroGrupo", "")), txt_safe(result.get("nombreGrupo", ""))))

        escribir_campos(result, [
            ("ANIO_FORMACION", "anioFormacion"), ("DEPARTAMENTO", "departamento"), ("CIUDAD", "ciudad"),
            ("LIDER", "lider"), ("INFORMACION_CERTIFICADA", "informacionCertificada"), ("PAGINA_WEB", "paginaWeb"),
            ("EMAIL", "email"), ("CLASIFICACION", "clasificacion"), ("AREA_CONOCIMIENTO", "areaConocimiento"),
            ("PROGRAMA_NACIONAL_CTI", "programaNacionalCti"), ("PROGRAMA_NACIONAL_CTI_SECUNDARIO", "programaNacionalCtiSecundario"),
            ("PLAN_ESTRATEGICO", "planEstrategico"), ("ESTADO_ARTE", "estadoArte"), ("OBJETIVOS", "objetivos"),
            ("RETOS", "retos"), ("VISION", "vision")
        ])

        _write_list(lines, "INSTITUCION", result.get("instituciones", []))
        _write_list(lines, "LINEA_INVESTIGACION", result.get("lineasInvestigacion", []))

        for member in result.get("integrantes", []):
            lines.append("INTEGRANTE\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                txt_safe(member.get("codigoRh", "")), txt_safe(member.get("nombre", "")), txt_safe(member.get("correo", "")),
                txt_safe(member.get("orcid", "")), txt_safe(member.get("institucion", "")), txt_safe(member.get("departamento", "")),
                txt_safe(member.get("ciudad", "")), txt_safe(member.get("categoriaInvestigador", "")),
                txt_safe(member.get("perfil", "")), _bool_text(member.get("activo", True))
            ))

            escribir_campos(member, [
                ("INTEGRANTE_NOMBRE_CITACIONES", "nombreCitaciones"), ("INTEGRANTE_NACIONALIDAD", "nacionalidad"),
                ("INTEGRANTE_SEXO", "sexo"), ("INTEGRANTE_ESTADO_PAR_EVALUADOR", "estadoParEvaluador"),
                ("INTEGRANTE_RESEARCHER_ID", "researcherId"), ("INTEGRANTE_AUTOR_ID_SCOPUS", "autorIdScopus"),
                ("INTEGRANTE_GOOGLE_SCHOLAR", "googleScholar"), ("INTEGRANTE_RESEARCHGATE", "researchGate"),
                ("INTEGRANTE_ACADEMIA_EDU", "academiaEdu"), ("INTEGRANTE_MENDELEY", "mendeley"),
                ("INTEGRANTE_LINKEDIN", "linkedin"), ("INTEGRANTE_REPOSITORIO_INSTITUCIONAL", "repositorioInstitucional")
            ])

            _write_list(lines, "INTEGRANTE_IDIOMA", member.get("idiomas", []))
            _write_list(lines, "INTEGRANTE_AREA", member.get("areasConocimiento", []))
            _write_list(lines, "INTEGRANTE_LINEA", member.get("lineasInvestigacion", []))
            _write_list(lines, "INTEGRANTE_FORMACION", member.get("formacionAcademica", []))
            _write_list(lines, "INTEGRANTE_EXPERIENCIA", member.get("experienciaProfesional", []))
            _write_list(lines, "INTEGRANTE_GRUPO", member.get("gruposInvestigacion", []))
            _write_list(lines, "INTEGRANTE_SEMILLERO", member.get("semilleros", []))
            _write_list(lines, "INTEGRANTE_PROYECTO", member.get("proyectos", []))
            _write_list(lines, "INTEGRANTE_RECONOCIMIENTO", member.get("reconocimientos", []))

            for product in member.get("productos", []):
                escribir_producto("INTEGRANTE_PRODUCTO", product)

            lines.append("FIN_INTEGRANTE")

        for product in result.get("productos", []):
            escribir_producto("PRODUCTO", product)

        lines.append("FIN_GRUPO")

    elif tipo == "INVESTIGADOR":
        lines.append("INVESTIGADOR\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
            txt_safe(result.get("codigoRh", "")), txt_safe(result.get("nombre", "")), txt_safe(result.get("correo", "")),
            txt_safe(result.get("orcid", "")), txt_safe(result.get("institucion", "")), txt_safe(result.get("departamento", "")),
            txt_safe(result.get("ciudad", "")), txt_safe(result.get("categoriaInvestigador", "")),
            txt_safe(result.get("perfil", "")), _bool_text(result.get("activo", True))
        ))

        escribir_campos(result, [
            ("NOMBRE_CITACIONES", "nombreCitaciones"), ("NACIONALIDAD", "nacionalidad"), ("SEXO", "sexo"),
            ("ESTADO_PAR_EVALUADOR", "estadoParEvaluador"), ("RESEARCHER_ID", "researcherId"),
            ("AUTOR_ID_SCOPUS", "autorIdScopus"), ("GOOGLE_SCHOLAR", "googleScholar"),
            ("RESEARCHGATE", "researchGate"), ("ACADEMIA_EDU", "academiaEdu"), ("MENDELEY", "mendeley"),
            ("LINKEDIN", "linkedin"), ("REPOSITORIO_INSTITUCIONAL", "repositorioInstitucional")
        ])

        _write_list(lines, "IDIOMA", result.get("idiomas", []))
        _write_list(lines, "AREA_CONOCIMIENTO", result.get("areasConocimiento", []))
        _write_list(lines, "LINEA_INVESTIGACION", result.get("lineasInvestigacion", []))
        _write_list(lines, "FORMACION", result.get("formacionAcademica", []))
        _write_list(lines, "EXPERIENCIA", result.get("experienciaProfesional", []))
        _write_list(lines, "GRUPO_INVESTIGACION", result.get("gruposInvestigacion", []))
        _write_list(lines, "SEMILLERO", result.get("semilleros", []))
        _write_list(lines, "PROYECTO", result.get("proyectos", []))
        _write_list(lines, "RECONOCIMIENTO", result.get("reconocimientos", []))

        for product in result.get("productos", []):
            escribir_producto("PRODUCTO", product)

        lines.append("FIN_INVESTIGADOR")

    elif tipo == "LOTE":
        grupos = result.get("grupos", [])
        investigadores = result.get("investigadores", [])
        lines.append("TOTAL_GRUPOS\t{}".format(len(grupos)))
        lines.append("TOTAL_INVESTIGADORES\t{}".format(len(investigadores)))

        for g in grupos:
            lines.append("GRUPO\t{}\t{}".format(txt_safe(g.get("nroGrupo", "")), txt_safe(g.get("nombreGrupo", ""))))
            escribir_campos(g, [
                ("ANIO_FORMACION", "anioFormacion"), ("DEPARTAMENTO", "departamento"), ("CIUDAD", "ciudad"),
                ("LIDER", "lider"), ("INFORMACION_CERTIFICADA", "informacionCertificada"), ("PAGINA_WEB", "paginaWeb"),
                ("EMAIL", "email"), ("CLASIFICACION", "clasificacion"), ("AREA_CONOCIMIENTO", "areaConocimiento"),
                ("PROGRAMA_NACIONAL_CTI", "programaNacionalCti"), ("PROGRAMA_NACIONAL_CTI_SECUNDARIO", "programaNacionalCtiSecundario"),
                ("PLAN_ESTRATEGICO", "planEstrategico"), ("ESTADO_ARTE", "estadoArte"), ("OBJETIVOS", "objetivos"),
                ("RETOS", "retos"), ("VISION", "vision")
            ])
            _write_list(lines, "INSTITUCION", g.get("instituciones", []))
            _write_list(lines, "LINEA_INVESTIGACION", g.get("lineasInvestigacion", []))
            for member in g.get("integrantes", []):
                lines.append("INTEGRANTE\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                    txt_safe(member.get("codigoRh", "")), txt_safe(member.get("nombre", "")), txt_safe(member.get("correo", "")),
                    txt_safe(member.get("orcid", "")), txt_safe(member.get("institucion", "")), txt_safe(member.get("departamento", "")),
                    txt_safe(member.get("ciudad", "")), txt_safe(member.get("categoriaInvestigador", "")),
                    txt_safe(member.get("perfil", "")), _bool_text(member.get("activo", True))
                ))
                escribir_campos(member, [
                    ("INTEGRANTE_NOMBRE_CITACIONES", "nombreCitaciones"), ("INTEGRANTE_NACIONALIDAD", "nacionalidad"),
                    ("INTEGRANTE_SEXO", "sexo"), ("INTEGRANTE_ESTADO_PAR_EVALUADOR", "estadoParEvaluador"),
                    ("INTEGRANTE_RESEARCHER_ID", "researcherId"), ("INTEGRANTE_AUTOR_ID_SCOPUS", "autorIdScopus"),
                    ("INTEGRANTE_GOOGLE_SCHOLAR", "googleScholar"), ("INTEGRANTE_RESEARCHGATE", "researchGate"),
                    ("INTEGRANTE_ACADEMIA_EDU", "academiaEdu"), ("INTEGRANTE_MENDELEY", "mendeley"),
                    ("INTEGRANTE_LINKEDIN", "linkedin"), ("INTEGRANTE_REPOSITORIO_INSTITUCIONAL", "repositorioInstitucional")
                ])
                _write_list(lines, "INTEGRANTE_IDIOMA", member.get("idiomas", []))
                _write_list(lines, "INTEGRANTE_AREA", member.get("areasConocimiento", []))
                _write_list(lines, "INTEGRANTE_LINEA", member.get("lineasInvestigacion", []))
                _write_list(lines, "INTEGRANTE_FORMACION", member.get("formacionAcademica", []))
                _write_list(lines, "INTEGRANTE_EXPERIENCIA", member.get("experienciaProfesional", []))
                _write_list(lines, "INTEGRANTE_GRUPO", member.get("gruposInvestigacion", []))
                _write_list(lines, "INTEGRANTE_SEMILLERO", member.get("semilleros", []))
                _write_list(lines, "INTEGRANTE_PROYECTO", member.get("proyectos", []))
                _write_list(lines, "INTEGRANTE_RECONOCIMIENTO", member.get("reconocimientos", []))
                for product in member.get("productos", []):
                    escribir_producto("INTEGRANTE_PRODUCTO", product)
                lines.append("FIN_INTEGRANTE")
            for product in g.get("productos", []):
                escribir_producto("PRODUCTO", product)
            lines.append("FIN_GRUPO")

        for inv in investigadores:
            lines.append("INVESTIGADOR\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                txt_safe(inv.get("codigoRh", "")), txt_safe(inv.get("nombre", "")), txt_safe(inv.get("correo", "")),
                txt_safe(inv.get("orcid", "")), txt_safe(inv.get("institucion", "")), txt_safe(inv.get("departamento", "")),
                txt_safe(inv.get("ciudad", "")), txt_safe(inv.get("categoriaInvestigador", "")),
                txt_safe(inv.get("perfil", "")), _bool_text(inv.get("activo", True))
            ))
            escribir_campos(inv, [
                ("NOMBRE_CITACIONES", "nombreCitaciones"), ("NACIONALIDAD", "nacionalidad"), ("SEXO", "sexo"),
                ("ESTADO_PAR_EVALUADOR", "estadoParEvaluador"), ("RESEARCHER_ID", "researcherId"),
                ("AUTOR_ID_SCOPUS", "autorIdScopus"), ("GOOGLE_SCHOLAR", "googleScholar"),
                ("RESEARCHGATE", "researchGate"), ("ACADEMIA_EDU", "academiaEdu"), ("MENDELEY", "mendeley"),
                ("LINKEDIN", "linkedin"), ("REPOSITORIO_INSTITUCIONAL", "repositorioInstitucional")
            ])
            _write_list(lines, "IDIOMA", inv.get("idiomas", []))
            _write_list(lines, "AREA_CONOCIMIENTO", inv.get("areasConocimiento", []))
            _write_list(lines, "LINEA_INVESTIGACION", inv.get("lineasInvestigacion", []))
            _write_list(lines, "FORMACION", inv.get("formacionAcademica", []))
            _write_list(lines, "EXPERIENCIA", inv.get("experienciaProfesional", []))
            _write_list(lines, "GRUPO_INVESTIGACION", inv.get("gruposInvestigacion", []))
            _write_list(lines, "SEMILLERO", inv.get("semilleros", []))
            _write_list(lines, "PROYECTO", inv.get("proyectos", []))
            _write_list(lines, "RECONOCIMIENTO", inv.get("reconocimientos", []))
            for product in inv.get("productos", []):
                escribir_producto("PRODUCTO", product)
            lines.append("FIN_INVESTIGADOR")

        lines.append("FIN_LOTE")

    else:
        lines[0] = "ESTADO\tERROR"
        lines.append("ERROR\tTipo de resultado desconocido.")

    lines.append("FIN")
    return "\n".join(lines) + "\n"


def serialize_error(message: str) -> str:
    return "ESTADO\tERROR\nERROR\t{}\nFIN\n".format(txt_safe(message))


# =========================================================================
# PERSISTENCIA DE DATOS (JSON)
# =========================================================================

class PersistenceManager:
    def __init__(self) -> None:
        self.directory = data_directory()
        self.investigators_path = self.directory / "investigadores.json"
        self.groups_path = self.directory / "grupos.json"

    def load_all(self) -> Dict[str, Any]:
        investigators = load_json_file(self.investigators_path, [])
        groups = load_json_file(self.groups_path, [])
        if not isinstance(investigators, list):
            investigators = []
        if not isinstance(groups, list):
            groups = []
        return {"investigadores": investigators, "grupos": groups}

    def save_all(self, investigators: List[Dict[str, Any]], groups: List[Dict[str, Any]]) -> bool:
        inv_ok = save_json_file(self.investigators_path, investigators)
        groups_ok = save_json_file(self.groups_path, groups)
        return inv_ok and groups_ok

    def export_json(self, path: Path, data: Any) -> bool:
        return save_json_file(path, data)

    def import_json(self, path: Path) -> Dict[str, Any]:
        data = load_json_file(path, {})
        if isinstance(data, dict):
            result = data
        else:
            result = {"data": data}
        return result


# =========================================================================
# MOTOR DE WEB SCRAPING (CvLAC Y GrupLAC)
# =========================================================================

USER_AGENT = "PEA-Scraper/1.0 (+local academic data tool)"
DEFAULT_TIMEOUT = 30


# -------------------------------------------------------------------------
# DOM minimo, sin dependencias externas
# -------------------------------------------------------------------------

class ParseNode:
    def __init__(self, tag: str = "root", attrs: Optional[Dict[str, str]] = None,
                 parent: Optional["ParseNode"] = None) -> None:
        self.tag = tag
        self.attrs = attrs or {}
        self.parent = parent
        self.children: List[ParseNode] = []
        self.text_parts: List[str] = []
        self.contents: List[Any] = []

    @property
    def text(self) -> str:
        if self.contents:
            parts = [item for item in self.contents if isinstance(item, str)]
            return normalize_whitespace(" ".join(parts))
        return normalize_whitespace(" ".join(self.text_parts))

    def all_text(self) -> str:
        parts: List[str] = []
        if self.contents:
            for item in self.contents:
                if isinstance(item, str):
                    if item:
                        parts.append(item)
                elif isinstance(item, ParseNode):
                    value = item.all_text()
                    if value:
                        parts.append(value)
        else:
            if self.text:
                parts.append(self.text)
            for child in self.children:
                value = child.all_text()
                if value:
                    parts.append(value)
        return normalize_whitespace(" ".join(parts))


class DOMParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = ParseNode()
        self.stack: List[ParseNode] = [self.root]

    @property
    def current(self) -> ParseNode:
        return self.stack[-1]

    @current.setter
    def current(self, node: ParseNode) -> None:
        if self.stack and self.stack[-1] is not node:
            self.stack.append(node)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attributes = {key.lower(): (value or "") for key, value in attrs}
        parent = self.stack[-1]
        node = ParseNode(tag.lower(), attributes, parent)
        parent.children.append(node)
        parent.contents.append(node)
        self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attributes = {key.lower(): (value or "") for key, value in attrs}
        parent = self.stack[-1]
        node = ParseNode(tag.lower(), attributes, parent)
        parent.children.append(node)
        parent.contents.append(node)

    def handle_endtag(self, tag: str) -> None:
        target = tag.lower()
        while len(self.stack) > 1 and self.stack[-1].tag != target:
            self.stack.pop()
        if len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        text = unescape(data)
        if text:
            self.stack[-1].text_parts.append(text)
            self.stack[-1].contents.append(text)



# -------------------------------------------------------------------------
# Normalizacion y navegacion
# -------------------------------------------------------------------------

def _norm_key(text: str) -> str:
    return normalize_whitespace(text).rstrip(":").casefold()


def _find_nodes(node: ParseNode, tag: Optional[str] = None) -> List[ParseNode]:
    result: List[ParseNode] = []
    if tag is None or node.tag == tag:
        result.append(node)
    for child in node.children:
        result.extend(_find_nodes(child, tag))
    return result


def _clean_record(text: str) -> str:
    value = clean_text(text)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _document_blocks(root: ParseNode) -> List[Tuple[str, str, List[str]]]:
    """Convierte el DOM en una secuencia lineal de bloques visibles.

    La pagina de Minciencias mezcla headings, divs y tablas. Por eso no se
    depende de una etiqueta HTML concreta para detectar las secciones.
    """
    result: List[Tuple[str, str, List[str]]] = []
    headings = {"h1", "h2", "h3", "h4", "h5", "h6"}
    block_tags = {
        "p", "div", "section", "article", "header", "footer", "main",
        "dt", "dd", "blockquote", "address"
    }

    def walk(node: ParseNode) -> None:
        if node.tag in headings:
            value = _clean_record(node.all_text())
            if value:
                result.append(("heading", value, []))
        elif node.tag == "li":
            value = _clean_record(node.all_text())
            if value:
                result.append(("item", value, []))
        elif node.tag == "tr":
            def has_nested_table(n: ParseNode) -> bool:
                if n.tag == "table":
                    return True
                return any(has_nested_table(c) for c in n.children)

            if any(has_nested_table(c) for c in node.children):
                for child in node.children:
                    walk(child)
            else:
                cells: List[str] = []
                for child in node.children:
                    if child.tag in ("td", "th"):
                        value = _clean_record(child.all_text())
                        if value:
                            cells.append(value)
                if cells:
                    result.append(("row", " | ".join(cells), cells))
        elif node.tag == "table":
            for child in node.children:
                walk(child)
        elif node.tag in ("ul", "ol"):
            for child in node.children:
                walk(child)
        else:
            is_handled_block = False
            if node.tag in block_tags:
                has_block_child = False
                for child in node.children:
                    if child.tag in headings or child.tag in block_tags or child.tag in {
                        "li", "table", "ul", "ol", "tr"
                    }:
                        has_block_child = True
                value = _clean_record(node.all_text())
                if value and not has_block_child:
                    result.append(("text", value, []))
                    is_handled_block = True
            
            if not is_handled_block:
                for child in node.children:
                    walk(child)

    walk(root)

    # El HTML viejo de Minciencias puede provocar el mismo bloque dos veces.
    unique: List[Tuple[str, str, List[str]]] = []
    seen = set()
    for item in result:
        key = (_norm_key(item[1]), item[0], tuple(_norm_key(v) for v in item[2]))
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def _records(root: ParseNode) -> List[Tuple[str, str, List[str]]]:
    return _document_blocks(root)


def _record_values(root: ParseNode) -> List[str]:
    values: List[str] = []
    for kind, text, cells in _records(root):
        value = _clean_record(text)
        if value:
            values.append(value)
    return values


def _query_parameter(url: str, name: str) -> str:
    try:
        values = parse_qs(urlparse(url).query).get(name, [])
        if values:
            return clean_text(values[0])
    except Exception:
        pass
    return ""


def _looks_generic_navigation(value: str) -> bool:
    normalized = _norm_key(value)
    generic = {
        "gruplác - plataforma scienti - colombia",
        "gruplac - plataforma scienti - colombia",
        "gruplác",
        "gruplac",
        "cvlac - rg",
        "datos generales",
        "buscar",
        "input",
    }
    return normalized in generic


def _find_marker_index(values: List[str], markers: List[str], start: int = 0) -> int:
    targets = [_norm_key(marker) for marker in markers]
    for index in range(start, len(values)):
        value = _norm_key(values[index])
        for target in targets:
            if value == target or value.startswith(target + ":"):
                return index
    return -1


def _slice_by_markers(values: List[str], start_markers: List[str], stop_markers: List[str]) -> List[str]:
    start = _find_marker_index(values, start_markers)
    if start < 0:
        return []
    output: List[str] = []
    index = start + 1
    is_stop = False
    while index < len(values) and not is_stop:
        current = _norm_key(values[index])
        for marker in stop_markers:
            target = _norm_key(marker)
            if current == target or current.startswith(target + ":"):
                is_stop = True
        if not is_stop:
            output.append(values[index])
            index += 1
    return output


def _clean_numbered(value: str) -> str:
    match = re.match(r"^\s*\d+\s*[-.)]+\s*(.+)$", value)
    if match:
        return clean_text(match.group(1))
    return clean_text(value)


def _only_numbered_items(values: List[str]) -> List[str]:
    output: List[str] = []
    for value in values:
        if re.match(r"^\s*\d+\s*[-.)]+\s*.+", value):
            cleaned = _clean_numbered(value)
            if cleaned:
                output.append(cleaned)
    return unique_strings(output)


def _extract_tables(root: ParseNode) -> List[List[List[str]]]:
    tables: List[List[List[str]]] = []
    for table in _find_nodes(root, "table"):
        rows: List[List[str]] = []
        for row in _find_nodes(table, "tr"):
            cells: List[str] = []
            for child in row.children:
                if child.tag in ("td", "th"):
                    value = _clean_record(child.all_text())
                    if value:
                        cells.append(value)
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def _label_value_pairs(root: ParseNode) -> Dict[str, str]:
    labels = {
        "nroGrupo": ["código", "codigo", "código del grupo", "codigo del grupo", "nro grupo", "nro"],
        "nombreGrupo": ["nombre del grupo", "nombre de grupo"],
        "anioFormacion": ["año y mes de formación", "año de formación", "fecha de formación"],
        "departamento": ["departamento - ciudad"],
        "ciudad": ["ciudad"],
        "lider": ["líder", "lider"],
        "informacionCertificada": ["¿la información de este grupo se ha certificado?", "la información de este grupo se ha certificado"],
        "paginaWeb": ["página web", "pagina web"],
        "email": ["e-mail", "email", "correo electrónico", "correo electronico"],
        "clasificacion": ["clasificación", "clasificacion"],
        "areaConocimiento": ["área de conocimiento", "area de conocimiento"],
        "programaNacionalCti": ["programa nacional de ciencia y tecnología", "programa nacional de ciencia y tecnologia"],
        "programaNacionalCtiSecundario": ["programa nacional de ciencia y tecnología (secundario)", "programa nacional de ciencia y tecnologia (secundario)"],
        "planEstrategico": ["plan de trabajo", "plan estratégico", "plan estrategico"],
        "estadoArte": ["estado del arte"],
        "objetivos": ["objetivo principal", "objetivos del grupo", "objetivos"],
        "retos": ["retos"],
        "vision": ["visión", "vision"],
    }
    pairs: Dict[str, str] = {}
    for kind, text, cells in _records(root):
        if kind == "row" and len(cells) >= 2:
            label = _norm_key(cells[0])
            value = clean_text(" ".join(cells[1:]))
            if value:
                for field_name, alternatives in labels.items():
                    matched = False
                    for alternative in alternatives:
                        target = _norm_key(alternative)
                        if label == target:
                            matched = True
                    if matched:
                        pairs[field_name] = value
    return pairs


def _section_items(values: List[str], start_markers: List[str], stop_markers: List[str], numbered_only: bool = False) -> List[str]:
    section = _slice_by_markers(values, start_markers, stop_markers)
    if numbered_only:
        return _only_numbered_items(section)
    output: List[str] = []
    for value in section:
        if value:
            if _norm_key(value) not in {
                "*", "habla escribe lee entiende", "nombre vinculación horas dedicación inicio - fin vinculación"
            }:
                if re.match(r"^\s*\d+\s*[-.)]+\s*.+", value):
                    value = _clean_numbered(value)
                value = re.sub(r"^\*\s*", "", value).strip()
                if value:
                    output.append(value)
    return unique_strings(output)


# -------------------------------------------------------------------------
# Campos simples de investigador
# -------------------------------------------------------------------------

def _extract_investigator_identity(values: List[str], full_text: str = "", root: Optional[ParseNode] = None) -> Dict[str, str]:
    """Extrae la identidad del CvLAC probado sin depender del HTML exacto.

    En la pagina real aparecen consecutivamente:
        Nombre ...
        Nombre en citaciones ...
        Nacionalidad ...
        Sexo ...

    Dependiendo de como Minciencias entregue el HTML, esas etiquetas pueden
    llegar como bloques separados o como un mismo bloque de texto. Por eso se
    prueban ambas representaciones, priorizando la tabla DOM cuando esté disponible.
    """
    result: Dict[str, str] = {}

    if root is not None:
        _stop_search = False
        for t in _find_nodes(root, "table"):
            if not _stop_search:
                h3s = _find_nodes(t, "h3")
                if not h3s:
                    txt = t.all_text().lower()
                    if "nombre" in txt and ("nacionalidad" in txt or "sexo" in txt):
                        for tr in _find_nodes(t, "tr"):
                            tds = _find_nodes(tr, "td")
                            if len(tds) >= 2:
                                k = clean_text(tds[0].all_text()).lower().rstrip(":")
                                v = clean_text(tds[1].all_text())
                                if k == "nombre" and not result.get("nombre"):
                                    result["nombre"] = v
                                elif "nombre en citaciones" in k and not result.get("nombreCitaciones"):
                                    result["nombreCitaciones"] = v
                                elif "nacionalidad" in k and not result.get("nacionalidad"):
                                    result["nacionalidad"] = v
                                elif "sexo" in k and not result.get("sexo"):
                                    result["sexo"] = v
                                elif "categor" in k and not result.get("categoriaInvestigador"):
                                    cat_clean = re.split(r"\s+con\s+vigencia\b", v, flags=re.IGNORECASE)[0].strip()
                                    result["categoriaInvestigador"] = cat_clean
                        _stop_search = True

    candidates: List[str] = []

    for value in values:
        cleaned = clean_text(value)
        if cleaned:
            candidates.append(cleaned)

    if full_text:
        cleaned_full = clean_text(full_text)
        if cleaned_full:
            candidates.append(cleaned_full)

    for value in candidates:
        lowered = value.casefold()
        if lowered.startswith("nombre en citaciones") and not result.get("nombreCitaciones"):
            result["nombreCitaciones"] = clean_text(
                value[len("Nombre en citaciones"):].lstrip(" :|-–—")
            )
        elif lowered.startswith("nombre ") and not any(lowered.startswith(p) for p in [
            "nombre en citaciones", "nombre de la red", "nombre comercial", "nombre del producto",
            "nombre del titular", "nombre de la institución", "nombre de la institucion",
            "nombre del orientado", "nombre del evento"
        ]):
            if not result.get("nombre"):
                result["nombre"] = clean_text(
                    value[len("Nombre"):].lstrip(" :|-–—")
                )
        elif "par evaluador reconocido" in lowered and not result.get("estadoParEvaluador"):
            result["estadoParEvaluador"] = "Par evaluador reconocido por Minciencias."
        elif re.match(r"^categor[ií\ufffd]a\b", lowered) and not result.get("categoriaInvestigador"):
            val = re.sub(r"^categor[ií\ufffd]a(?:\s+investigador)?\s*[:|–—\-]?\s*", "", value, flags=re.IGNORECASE).strip()
            if val:
                result["categoriaInvestigador"] = clean_text(val)
        elif lowered.startswith("nacionalidad") and not result.get("nacionalidad"):
            result["nacionalidad"] = clean_text(
                value[len("Nacionalidad"):].lstrip(" :|-–—")
            )
        elif lowered.startswith("sexo") and not result.get("sexo"):
            val = clean_text(value[len("Sexo"):].lstrip(" :|-–—"))
            if val:
                result["sexo"] = re.split(r"\s+(?:Redes|Identificadores|Formaci)", val, flags=re.IGNORECASE)[0].strip()

    joined = " ".join(candidates)

    # Fallback robusto para cuando los campos vienen dentro de un mismo bloque
    cat_match = re.search(
        r"\bCategor[^\s]{0,8}a\s+(.+?)(?=\s+Nombre\b|\s+Nombre en citaciones\b|\s+Nacionalidad\b|$)",
        joined,
        re.IGNORECASE
    )
    if cat_match and not result.get("categoriaInvestigador"):
        val = clean_text(cat_match.group(1)).lstrip(" :|-–—")
        if val:
            result["categoriaInvestigador"] = val

    name_match = re.search(
        r"\bNombre\s+(.+?)\s+Nombre en citaciones\b",
        joined,
        re.IGNORECASE
    )
    if name_match and not result.get("nombre"):
        name = clean_text(name_match.group(1)).lstrip(" :|-–—")
        if name:
            result["nombre"] = name

    citation_match = re.search(
        r"\bNombre en citaciones\s+(.+?)\s+Nacionalidad\b",
        joined,
        re.IGNORECASE
    )
    if citation_match and not result.get("nombreCitaciones"):
        value = clean_text(citation_match.group(1)).lstrip(" :|-–—")
        if value:
            result["nombreCitaciones"] = value

    nationality_match = re.search(
        r"\bNacionalidad\s+(.+?)\s+Sexo\b",
        joined,
        re.IGNORECASE
    )
    if nationality_match and not result.get("nacionalidad"):
        value = clean_text(nationality_match.group(1)).lstrip(" :|-–—")
        if value:
            result["nacionalidad"] = value

    sex_match = re.search(
        r"\bSexo\s+(.+?)(?=\s+Redes sociales\b|\s+Identificadores\b|\s+Formaci[oó\ufffd]n\b|$)",
        joined,
        re.IGNORECASE
    )
    if sex_match and not result.get("sexo"):
        value = clean_text(sex_match.group(1)).lstrip(" :|-–—")
        if value:
            result["sexo"] = re.split(r"\s+(?:Redes|Identificadores|Formaci)", value, flags=re.IGNORECASE)[0].strip()

    if "par evaluador reconocido" in joined.lower() and not result.get("estadoParEvaluador"):
        result["estadoParEvaluador"] = "Par evaluador reconocido por Minciencias."

    if not result.get("categoriaInvestigador"):
        result["categoriaInvestigador"] = "Sin categoría"

    return result


def _extract_investigator_links(root: ParseNode) -> Dict[str, str]:
    output = {
        "googleScholar": "",
        "researchGate": "",
        "academiaEdu": "",
        "mendeley": "",
        "linkedin": "",
        "repositorioInstitucional": "",
        "researcherId": "",
        "autorIdScopus": "",
        "orcid": "",
    }
    for node in _find_nodes(root, "a"):
        text = _norm_key(node.all_text())
        href = clean_text(node.attrs.get("href", ""))
        if href:
            if "google scholar" in text:
                output["googleScholar"] = href
            elif "researchgate" in text:
                output["researchGate"] = href
            elif "academia" in text:
                output["academiaEdu"] = href
            elif "mendeley" in text or "scopus" in text:
                output["mendeley"] = href
            elif "linkedln" in text or "linkedin" in text:
                output["linkedin"] = href
            elif "repositorios institucionales" in text:
                output["repositorioInstitucional"] = href
            elif "researcherid" in text:
                output["researcherId"] = href
            elif "autor id" in text:
                output["autorIdScopus"] = href
            elif "orcid" in text:
                output["orcid"] = href
    return output


def _extract_languages(values: List[str], root: Optional[ParseNode] = None) -> List[str]:
    # 1. Extracción estructurada y aislada desde el nodo DOM (evita contaminación con otras secciones)
    if root is not None:
        tables = _find_nodes(root, "table")
        target_table = None
        _found_table = False
        for t in tables:
            if not _found_table:
                h3s = _find_nodes(t, "h3")
                if h3s:
                    clean_title = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", h3s[0].all_text().lower()))
                    if "idioma" in clean_title:
                        target_table = t
                        _found_table = True
        if target_table is not None:
            trs = _find_nodes(target_table, "tr")
            result: List[str] = []
            has_header = False
            for tr in trs:
                if not _find_nodes(tr, "h3"):
                    tds = _find_nodes(tr, "td")
                    if tds:
                        cells = [clean_text(td.all_text()) for td in tds]
                        non_empty = [c for c in cells if c]
                        if non_empty:
                            norm_combined = " ".join(non_empty).lower()
                            if "habla" in norm_combined and "escribe" in norm_combined:
                                if not has_header:
                                    result.append("Idioma | Habla | Escribe | Lee | Entiende")
                                    has_header = True
                            else:
                                first_cell = re.sub(r"^[*\s\u2022\ufffd\xa0-]+", "", non_empty[0]).strip()
                                ratings = non_empty[1:]
                                if ratings:
                                    row_str = "{} | {}".format(first_cell, " | ".join(ratings))
                                else:
                                    row_str = first_cell
                                if row_str and row_str not in result:
                                    result.append(row_str)
            if len(result) == 1 and result[0] == "Idioma | Habla | Escribe | Lee | Entiende":
                return []
            if result:
                return result

    # 2. Respaldo por texto plano con delimitadores seguros
    section = _slice_by_markers(values, ["idiomas"], [
        "líneas de investigación", "lineas de investigacion", "reconocimientos",
        "cursos de corta duración", "trabajos dirigidos", "artículos", "articulos",
        "libros", "capítulos", "capitulos", "proyectos", "producción", "produccion",
        "los ítems", "los items", "otra información personal"
    ])
    header = _norm_key("Habla Escribe Lee Entiende")
    result: List[str] = []
    index = 0
    _stop = False
    while index < len(section) and not _stop:
        current = clean_text(section[index])
        if current and _norm_key(current) != header and current != "*":
            norm_cur = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", current.lower()))
            if any(norm_cur.startswith(p) for p in ["lositems", "produccionbiblio", "proyectos", "libros"]):
                _stop = True
            if not _stop:
                advanced = False
                if index + 1 < len(section):
                    ratings = clean_text(section[index + 1])
                    if re.match(r"^(Bueno|Excelente|Regular|Básico|Basico|Malo|Aceptable|Deficiente)(\s+\1){1,3}$", ratings, re.IGNORECASE):
                        result.append("{} | {}".format(current, ratings))
                        index += 2
                        advanced = True
                if not advanced:
                    result.append(current)
                    index += 1
        else:
            index += 1
    return unique_strings(result)



def _extract_investigator_affiliation(values: List[str], full_text: str = "", experience_list: Optional[List[str]] = None) -> Tuple[str, str]:
    """Extrae la institucion y ciudad desde 'Experiencia profesional'.

    CvLAC no muestra un campo simple de 'Institucion' o 'Ciudad' para este
    perfil. La afiliacion aparece dentro de la experiencia profesional.
    Esta función soporta diversas variantes y prioriza la institución activa ('de Actual').
    """
    if experience_list:
        experience = experience_list
    else:
        experience = _section_items(values, ["experiencia profesional"], [
            "actividades de investigación", "áreas de actuación", "áreas de conocimiento", "idiomas"
        ])

    if not experience and full_text:
        combined = clean_text(full_text)
        start_match = re.search(
            r"\bExperiencia profesional\b",
            combined,
            re.IGNORECASE
        )
        end_match = re.search(
            r"\b[AÁaá]reas de actuaci[oó]n\b|\bIdiomas\b",
            combined,
            re.IGNORECASE
        )
        if start_match:
            start = start_match.end()
            if end_match and end_match.start() > start:
                end = end_match.start()
            else:
                end = len(combined)
            chunk = clean_text(combined[start:end])
            if chunk:
                experience = [chunk]

    institution = ""
    city = ""
    pairs: List[Tuple[str, str]] = []

    for index, item in enumerate(experience):
        value = clean_text(item)
        if value:
            # Caso 1: institucion y Dedicacion vienen en el mismo bloque.
            same_block = re.search(
                r"^(.+?)\s+(?:Dedicaci[oó]n\s*:|Octubre\s+de|Enero\s+de|Febrero\s+de|Marzo\s+de|Abril\s+de|Mayo\s+de|Junio\s+de|Julio\s+de|Agosto\s+de|Septiembre\s+de|Noviembre\s+de|Diciembre\s+de)",
                value,
                re.IGNORECASE
            )
            handled = False
            if same_block:
                prefix = clean_text(same_block.group(1)).lstrip("* \u2022-")
                if prefix and len(prefix) > 3:
                    pairs.append((prefix, value))
                    handled = True

            if not handled:
                # Caso 2: institucion y Dedicacion llegan como bloques consecutivos.
                if "dedicación" in value.casefold() and index > 0:
                    previous = clean_text(experience[index - 1]).lstrip("* \u2022-")
                    if previous and "dedicación" not in previous.casefold():
                        pairs.append((previous, value))
                        handled = True

            if not handled:
                # Caso 3: linea de texto de la empresa/universidad
                m_simple = re.search(r"^([A-ZÁÉÍÓÚÑa-záéíóúñ\s\.,'-]+?)(?:\s+Dedicaci[oó]n|\s*-\s*Cargo:|\s+Actividades|$)", value)
                if m_simple:
                    prefix = clean_text(m_simple.group(1)).lstrip("* \u2022-")
                    if prefix and len(prefix) > 4:
                        pairs.append((prefix, value))

    preferred_pair: Optional[Tuple[str, str]] = None

    # Prioridad 1: Empleo actualmente activo con "de Actual" o "Actual"
    _found_pref = False
    for pair in pairs:
        if not _found_pref:
            if "de actual" in pair[1].casefold() or "actual" in pair[1].casefold():
                preferred_pair = pair
                _found_pref = True

    # Prioridad 2: Afiliación que contenga 'Campus <ciudad>'
    if preferred_pair is None:
        _found_pref = False
        for pair in pairs:
            if not _found_pref:
                if re.search(r"\bCampus\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)", pair[0], re.IGNORECASE):
                    preferred_pair = pair
                    _found_pref = True

    # Prioridad 3: Primera experiencia registrada
    if preferred_pair is None and pairs:
        preferred_pair = pairs[0]

    if preferred_pair is not None:
        institution = clean_text(preferred_pair[0])
        campus_match = re.search(
            r"\bCampus\s+([A-Za-zÁÉÍÓÚÑáéíóúñü .'-]+?)(?=\s+Dedicaci[oó]n\b|$)",
            institution,
            re.IGNORECASE
        )
        if campus_match:
            city = clean_text(campus_match.group(1))

        if not city:
            generic_city = re.search(
                r"\b(Valledupar|Bucaramanga|Bogot[aá]|Medell[ií]n|Cali|Barranquilla|Cartagena|Sincelejo|Santa Marta)\b",
                preferred_pair[1],
                re.IGNORECASE
            )
            if generic_city:
                city = clean_text(generic_city.group(1))

    # Respaldo directo para el perfil probado.
    if not institution and full_text:
        match = re.search(
            r"(Universidad De Santander\s*-\s*Campus\s+[A-Za-zÁÉÍÓÚÑáéíóúñü .'-]+)",
            full_text,
            re.IGNORECASE
        )
        if match:
            institution = clean_text(match.group(1))

    if not city and institution:
        campus_match = re.search(
            r"\bCampus\s+([A-Za-zÁÉÍÓÚÑáéíóúñü .'-]+?)(?=\s|$)",
            institution,
            re.IGNORECASE
        )
        if campus_match:
            city = clean_text(campus_match.group(1))

    return institution, city


def _extract_group_name(values: List[str], full_text: str = "", root: Optional[ParseNode] = None) -> str:
    """Extrae el nombre real del grupo alrededor del encabezado 'Datos básicos'."""
    if root:
        for span in _find_nodes(root, "span"):
            cls = span.attrs.get("class", "")
            if cls == "celdaEncabezado" or span.attrs.get("id") == "celdaEncabezado":
                candidate = clean_text(span.text)
                if candidate and "plataforma scienti" not in candidate.casefold():
                    return candidate

    basic_index = _find_marker_index(values, ["datos básicos", "datos basicos"])

    if basic_index > 0:
        _stop = False
        _result = ""
        for index in range(basic_index - 1, max(-1, basic_index - 8), -1):
            if not _stop:
                candidate = clean_text(values[index])
                if candidate and not _looks_generic_navigation(candidate):
                    lowered = _norm_key(candidate)
                    if lowered not in {"gruplác", "gruplac", "gruplác - plataforma scienti - colombia", "gruplac - plataforma scienti - colombia"}:
                        if "plataforma scienti" not in lowered:
                            if lowered not in {"inicio", "buscar", "datos generales"}:
                                _result = candidate
                                _stop = True
        if _result:
            return _result

    joined = "\n".join(clean_text(value) for value in values if clean_text(value))
    match = re.search(
        r"(?:^|\n)\s*([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9&.\- ]{1,80})\s*\n\s*Datos básicos\b",
        joined,
        re.IGNORECASE,
    )
    if match:
        candidate = clean_text(match.group(1))
        if candidate and "plataforma scienti" not in candidate.casefold():
            return candidate

    if full_text:
        compact = clean_text(full_text)
        marker = re.search(r"\bDatos básicos\b", compact, re.IGNORECASE)
        if marker:
            before = compact[:marker.start()].strip()
            tokens = before.split()
            for size in range(1, min(8, len(tokens)) + 1):
                candidate = " ".join(tokens[-size:])
                candidate = clean_text(candidate)
                if re.match(r"^[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9&.\- ]{1,80}$", candidate):
                    if "plataforma scienti" not in candidate.casefold() and candidate.casefold() not in {"gruplác", "gruplac"}:
                        return candidate

    return ""


def _normalize_group_classification(value: str) -> str:
    """Convierte 'B con vigencia...' en la categoria corta 'B'."""
    cleaned = clean_text(value)
    if not cleaned:
        return ""
    match = re.match(r"^([A-Z](?:[0-9])?)\s+(?:con\s+vigencia\b|con\s+vigencia)", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    simple = re.match(r"^([A-Z](?:[0-9])?)$", cleaned, re.IGNORECASE)
    if simple:
        return simple.group(1).upper()
    return cleaned


# -------------------------------------------------------------------------
# Productos GrupLAC
# -------------------------------------------------------------------------

GROUP_PRODUCT_RE = re.compile(
    r"^\s*(\d+)\s*[-.)]+\s*(.+?)\s*:\s*(.+)$",
    re.IGNORECASE,
)

GROUP_PRODUCT_TYPES = [
    "publicado en revista especializada",
    "corto",
    "artículo",
    "articulo",
    "libro resultado de investigación",
    "libros de formación",
    "libros de divulgación",
    "libros de divulgación y/o compilación de divulgación",
    "libro pedagógico y/o de divulgación",
    "otro libro publicado",
    "capítulo de libro",
    "capitulos de libro",
    "manuales y guías especializadas",
    "manuales y guias especializadas",
    "norma",
    "computacional",
    "software",
    "patente",
    "otra publicación divulgativa",
    "otra",
    "informes de investigación",
    "producto tecnológico",
    "desarrollo tecnológico",
]


def _looks_like_group_product_start(value: str) -> bool:
    match = GROUP_PRODUCT_RE.match(value)
    if not match:
        return False
    product_type = clean_text(match.group(2)).casefold()
    for candidate in GROUP_PRODUCT_TYPES:
        if product_type.startswith(candidate):
            return True
    return False


def _extract_group_product(lines: List[str], category: str, index: int) -> Optional[ProductoInvestigacion]:
    if not lines:
        return None
    start = GROUP_PRODUCT_RE.match(lines[0])
    if not start:
        return None

    product_type = clean_text(start.group(2))
    title = clean_text(start.group(3))
    all_text = " ".join(clean_text(line) for line in lines if clean_text(line))

    product = ProductoInvestigacion(
        idProducto="P{}".format(index),
        titulo=title,
        categoria=clean_text(category),
        tipoProducto=product_type,
        subtipo=product_type,
        descripcion=all_text,
    )

    year_match = re.search(r"\b(19|20)\d{2}\b", all_text)
    if year_match:
        product.anio = safe_int(year_match.group(0))

    isbn_match = re.search(r"ISBN:\s*([^,]+)", all_text, re.IGNORECASE)
    if isbn_match:
        product.isbn = clean_text(isbn_match.group(1))

    doi_match = re.search(r"DOI:\s*([^,\s]+(?:\S*://\S+|\S+)?)", all_text, re.IGNORECASE)
    if doi_match:
        product.doi = clean_text(doi_match.group(1))

    for line in lines[1:]:
        clean_line = clean_text(line)
        if "ISSN:" in clean_line.upper():
            before_issn = clean_text(re.split(r"ISSN:", clean_line, maxsplit=1, flags=re.IGNORECASE)[0])
            if "," in before_issn:
                first_part, second_part = before_issn.split(",", 1)
                if re.match(r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñü .'-]+$", first_part.strip()):
                    product.revista = clean_text(second_part)
                else:
                    product.revista = before_issn
            else:
                product.revista = before_issn
        editorial_match = re.search(r"\bEd\.\s*([^,]+)", clean_line, re.IGNORECASE)
        if editorial_match:
            product.editorial = clean_text(editorial_match.group(1))

    availability_match = re.search(r"Disponibilidad:\s*([^,]+)", all_text, re.IGNORECASE)
    if availability_match:
        product.disponibilidad = clean_text(availability_match.group(1))

    institution_match = re.search(r"Institución(?: financiadora)?\s*:\s*([^,]+)", all_text, re.IGNORECASE)
    if institution_match:
        product.institucion = clean_text(institution_match.group(1))

    _found_pais = False
    for line in lines[1:]:
        if not _found_pais:
            country_match = re.match(r"^([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñü .'-]+),", clean_text(line))
            if country_match:
                product.pais = clean_text(country_match.group(1))
                _found_pais = True

    _found_autores = False
    for line in lines:
        if not _found_autores:
            authors_match = re.match(r"^Autores?:\s*(.+)$", clean_text(line), re.IGNORECASE)
            if authors_match:
                product.autores = unique_strings(re.split(r"\s*,\s*", authors_match.group(1)))
                _found_autores = True

    product.normalizar()
    if not product.titulo:
        return None
    return product


def _find_group_products(
    values: List[str],
    codigo_grupo: str = ""
) -> List[ProductoInvestigacion]:
    """Extrae productos de GrupLAC dentro del bloque de produccion del grupo.

    La pagina real muestra cada producto como:
        1.- Tipo de producto : Titulo
        Pais, año, ISBN/ISSN/DOI...
        Autores: ...

    Se limita el escaneo desde 'Integrantes del grupo' hasta 'Semilleros de
    investigación' para no interpretar semilleros, eventos u otras secciones
    posteriores como productos.
    """
    start = _find_marker_index(values, ["integrantes del grupo"])
    if start >= 0:
        scan = values[start + 1:]
    else:
        scan = values

    stop = _find_marker_index(scan, [
        "semilleros de investigación", "semilleros de investigacion"
    ])
    if stop >= 0:
        scan = scan[:stop]

    products: List[ProductoInvestigacion] = []
    pending: List[str] = []
    current_category = ""
    counter = 1
    category_markers = {
        _norm_key("Artículos"): "Artículos",
        _norm_key("Libros publicados"): "Libros publicados",
        _norm_key("Capítulos de libro publicados"): "Capítulos de libro publicados",
        _norm_key("Libros de formación"): "Libros de formación",
        _norm_key("Libros de divulgación y/o Compilación de divulgación"): "Libros de divulgación y/o Compilación de divulgación",
        _norm_key("Manuales y Guías Especializadas"): "Manuales y Guías Especializadas",
        _norm_key("Otra publicación divulgativa"): "Otra publicación divulgativa",
        _norm_key("Otros artículos publicados"): "Otros artículos publicados",
        _norm_key("Informes de investigación"): "Informes de investigación",
        _norm_key("Normas y Regulaciones"): "Normas y Regulaciones",
    }

    # Encabezados que indican que ya no estamos en un bloque de productos.
    non_product_markers = {
        "semilleros de investigación", "semilleros de investigacion",
        "integrantes del grupo", "datos básicos", "datos basicos",
    }

    def flush() -> None:
        nonlocal pending, counter

        if pending:
            product = _extract_group_product(
                pending,
                current_category,
                counter
            )

            if product is not None:
                if codigo_grupo:
                    product.idProducto = "G{}_P{}".format(
                        codigo_grupo,
                        counter
                    )

                products.append(product)
                counter += 1

        pending = []

    for value in scan:
        key = _norm_key(value)
        if key in category_markers:
            flush()
            current_category = category_markers[key]
        elif key in non_product_markers:
            flush()
            current_category = ""
        else:
            # Mientras exista una categoria de produccion, cualquier entrada
            # numerada con formato 'N.- Tipo : Titulo' pertenece a esa categoria.
            if current_category and GROUP_PRODUCT_RE.match(value):
                flush()
                pending = [value]
            elif pending:
                pending.append(value)

    flush()

    unique_products: List[ProductoInvestigacion] = []
    seen = set()
    for product in products:
        key = (clean_text(product.titulo).casefold(), int(product.anio or 0))
        if key not in seen:
            unique_products.append(product)
            seen.add(key)
    return unique_products


# -------------------------------------------------------------------------
# Productos CvLAC
# -------------------------------------------------------------------------

INV_PRODUCTION_START_RE = re.compile(
    r"^(Producci[oó\ufffd]n\s+(?:bibliogr[aá\ufffd]fica|t[eé\ufffd]cnica|en\s+arte)|Apropiaci[oó\ufffd]n\s+social)\s*-\s*(.+)$",
    re.IGNORECASE,
)

INV_PRODUCT_INLINE_RE = re.compile(
    r"^Nombre del producto\s*:\s*(.+?)\s+Tipo de producto\s*:\s*(.+)$",
    re.IGNORECASE,
)

ALL_CVLAC_SECTIONS = {
    "datos generales", "identificación", "identificacion", "redes sociales",
    "identificadores de autor", "formación académica", "formacion academica",
    "formación complementaria", "formacion complementaria", "estancias posdoctorales",
    "experiencia profesional", "otra información personal", "otra informacion personal",
    "áreas de actuación", "areas de actuacion", "idiomas", "líneas de investigación",
    "lineas de investigacion", "asesorías", "asesorias", "cursos de corta duración",
    "cursos de corta duracion", "trabajos dirigidos", "tutorías", "tutorias",
    "trabajos dirigidos/tutorías", "trabajos dirigidos/tutorias",
    "actividades de formación", "actividades formacion", "jurado", "par evaluador",
    "comité", "comite", "apropiación social", "apropiacion social", "edición", "edicion",
    "eventos científicos", "eventos cientificos", "evento científico", "evento cientifico",
    "redes de conocimiento", "producción bibliográfica", "produccion bibliografica",
    "artículos", "articulos", "libros", "capítulos de libro", "capitulos de libro",
    "nota científica", "nota cientifica", "textos en publicaciones no científicas",
    "textos en publicaciones no cientificas", "otra producción bibliográfica",
    "otra produccion bibliografica", "producción técnica", "produccion tecnica",
    "patentes", "secretos empresariales", "software", "softwares", "productos tecnológicos",
    "productos tecnologicos", "procesos o técnicas", "procesos o tecnicas",
    "trabajos técnicos", "trabajos tecnicos", "normas", "normas y regulaciones",
    "otra producción técnica", "otra produccion tecnica", "empresas de base tecnológica",
    "empresas de base tecnologica", "más información", "mas informacion",
    "demás trabajos", "demas trabajos", "proyectos", "producción en arte",
    "produccion en arte", "obras o productos", "registros de acuerdo",
    "industrias creativas", "evento artistico", "talleres", "reconocimientos"
}


def _looks_like_inv_product_text(value: str) -> bool:
    lowered = value.casefold()
    if " en: " in lowered or "nombre del producto" in lowered:
        return True
    if "\"" in value or "“" in value:
        return True
    if INV_PRODUCT_INLINE_RE.match(value):
        return True
    return False


def _extract_unquoted_product_title_and_authors(text: str) -> Tuple[str, List[str]]:
    m_del = re.search(r'(?:,\s*Nombre comercial:|\s*contrato/registro:|\.\s*En:|\s*,\s*(?:19|20)\d{2}\s*[,.])', text)
    if m_del:
        end_pos = m_del.start()
    else:
        end_pos = len(text)
    sub_txt = text[:end_pos].strip()
    m_nc = re.search(r"Nombre comercial:\s*([^,\r\n<]+)", text, re.I)
    if m_nc:
        nc = m_nc.group(1).strip()
    else:
        nc = ""

    parts = [p.strip() for p in sub_txt.split(",") if p.strip()]
    title_words = {
        'sistema', 'desarrollo', 'aplicativo', 'software', 'algoritmo', 'generación', 'generacion', 
        'control', 'herramienta', 'inventario', 'administracion', 'administración', 'ova', 'modelo',
        'red', 'portal', 'análisis', 'analisis', 'diseño', 'diseno', 'reingeniería', 'reingenieria',
        'para', 'del', 'los', 'las', 'con', 'por', 'mediante', 'sobre', 'hacia'
    }
    title_idx = -1
    _found_title = False
    for i, p in enumerate(parts):
        if not _found_title:
            low = p.lower()
            if nc and nc.lower() in low:
                title_idx = i
                _found_title = True
            elif ':' in p or any(tw in low.split() for tw in title_words):
                title_idx = i
                _found_title = True

    if title_idx >= 0:
        authors = parts[:title_idx]
        title = ", ".join(parts[title_idx:])
    else:
        if len(parts) > 1:
            authors = [parts[0]]
            title = ", ".join(parts[1:])
        else:
            authors = []
            if nc:
                title = nc
            else:
                if parts:
                    title = parts[0]
                else:
                    title = text

    return title.strip(" ."), [a.strip() for a in authors if len(a.strip()) > 3]


CVLAC_PRODUCT_ANCHORS = {
    "articulos", "libros", "capitulos", "software", "tecnologicos",
    "patentes", "secretos", "procesos", "trabajos_tec", "normas",
    "otra_prod_tecnica", "otra_prod_biblio", "demas_trabajos", "obras_productos",
    "nota_cientifica", "textos", "consultorias", "cursos", "documentos_trabajo"
}


CVLAC_NON_PRODUCT_KEYWORDS = [
    "formacion", "experiencia", "actuacion", "idioma", "linea",
    "evento", "tutor", "proyecto", "jurado", "comite",
    "asesoria", "redes", "datosgenerales", "otrainfopersonal"
]


def _is_cvlac_product_table(table: ParseNode) -> Tuple[bool, str]:
    # 1. Comprobar si el encabezado de la tabla corresponde expresamente a una sección no de productos
    h3s = _find_nodes(table, "h3")
    if h3s:
        raw_title = h3s[0].all_text()
    else:
        raw_title = ""
    clean = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", raw_title.lower()))
    if any(k in clean for k in CVLAC_NON_PRODUCT_KEYWORDS):
        return False, ""

    # 2. Buscar anchor name dentro de la tabla o en su celda contenedora directa
    anc_name = ""
    for a in _find_nodes(table, "a"):
        if not anc_name and a.attrs.get("name"):
            anc_name = a.attrs.get("name").lower()

    if not anc_name and table.parent:
        for child in table.parent.children:
            if child is not table and not anc_name:
                for a in _find_nodes(child, "a"):
                    if not anc_name and a.attrs.get("name"):
                        anc_name = a.attrs.get("name").lower()

        # Buscar en la fila (tr) inmediatamente anterior si existe
        if not anc_name and table.parent.parent:
            p_tr = table.parent
            while p_tr and p_tr.tag != "tr":
                p_tr = p_tr.parent
            if p_tr and p_tr.parent:
                sibs = p_tr.parent.children
                if p_tr in sibs:
                    idx = sibs.index(p_tr)
                else:
                    idx = -1
                if idx > 0:
                    prev_sib = sibs[idx - 1]
                    for a in _find_nodes(prev_sib, "a"):
                        if not anc_name and a.attrs.get("name"):
                            anc_name = a.attrs.get("name").lower()

    if anc_name in CVLAC_PRODUCT_ANCHORS:
        return True, anc_name

    if not h3s:
        return False, ""

    keywords = [
        "art", "libro", "capitul", "software", "patent", "secreto",
        "proces", "tecnic", "tecnol", "obra", "norma", "nota",
        "consultor", "curso", "trabajo", "texto"
    ]
    if any(k in clean for k in keywords):
        return True, raw_title
    return False, ""


def _map_cvlac_product_category(anc_name: str, raw_title: str) -> str:
    anc = anc_name.lower()
    clean = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", raw_title.lower()))
    if anc == "articulos" or ("art" in clean and "cul" in clean):
        return "Artículos"
    if anc == "libros" or ("libro" in clean and "capit" not in clean):
        return "Libros"
    if anc == "capitulos" or "capit" in clean:
        return "Capítulos de libro"
    if anc == "software" or "software" in clean:
        return "Softwares"
    if anc == "tecnologicos" or "tecnol" in clean:
        return "Productos tecnológicos"
    if anc == "patentes" or "patent" in clean:
        return "Patentes"
    if anc == "secretos" or "secreto" in clean:
        return "Secretos empresariales"
    if anc == "procesos" or "proces" in clean:
        return "Procesos o técnicas"
    if anc == "trabajos_tec" or "trabajostec" in clean:
        return "Trabajos técnicos"
    if anc == "normas" or "norma" in clean:
        return "Normas y Regulaciones"
    if anc == "documentos_trabajo" or ("documento" in clean and "trabajo" in clean):
        return "Documentos de trabajo"
    if anc == "demas_trabajos" or "demastrabajo" in clean:
        return "Demás trabajos"
    if anc == "consultorias" or "consultor" in clean:
        return "Consultorías"
    if anc == "cursos" or "curso" in clean:
        return "Cursos de corta duración"
    if anc == "innovacion" or ("innovacion" in clean and "proceso" in clean):
        return "Innovación de proceso o procedimiento"
    if anc == "empresa" or ("empresa" in clean and "base" in clean):
        return "Empresas de base tecnológica"
    if anc == "textos" or ("texto" in clean and "publicacion" in clean):
        return "Textos en publicaciones no científicas"
    return _clean_record(raw_title)


def _extract_investigator_sections_dom(root: ParseNode) -> Dict[str, List[str]]:
    section_map: Dict[str, List[str]] = {}
    all_tables = _find_nodes(root, "table")
    child_tables = []
    for t in all_tables:
        p = t.parent
        has_table_parent = False
        while p and not has_table_parent:
            if p.tag == "table":
                has_table_parent = True
            if not has_table_parent:
                p = p.parent
        if has_table_parent:
            child_tables.append(t)

    if child_tables:
        tables_to_check = child_tables
    else:
        tables_to_check = all_tables
    for t in tables_to_check:
        h3s = _find_nodes(t, "h3")
        if h3s:
            raw_title = h3s[0].all_text()
            clean_key = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", raw_title.lower()))

            is_p, _ = _is_cvlac_product_table(t)
            if not is_p:
                items = []
                for tr in _find_nodes(t, "tr"):
                    if not _find_nodes(tr, "h3"):
                        txt = _clean_record(tr.all_text())
                        norm_tr = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", txt.lower()))
                        if txt and len(txt) > 2 and not norm_tr.startswith("lositems"):
                            items.append(txt)
                if items:
                    section_map[clean_key] = items
    return section_map


def _extract_investigator_product(lines: List[str], category: str, index: int) -> Optional[ProductoInvestigacion]:
    if not lines:
        return None
    first = clean_text(lines[0])
    inline = INV_PRODUCT_INLINE_RE.match(first)
    subtype = clean_text(category)
    title = ""
    autores: List[str] = []

    if inline:
        title = clean_text(inline.group(1))
        subtype = clean_text(inline.group(2))
    else:
        quoted = re.search(r'["“]([^"”\r\n]+)["”]', first)
        if quoted:
            title = clean_text(quoted.group(1))
            q_start = first.find(quoted.group(0))
            raw_auth = first[:q_start].strip().rstrip(",").strip()
            raw_auth = re.sub(r"^(?:Tipo:\s*[^,]+,\s*|\*\s*)", "", raw_auth, flags=re.IGNORECASE)
            if raw_auth:
                autores = [a.strip() for a in raw_auth.split(",") if a.strip() and len(a.strip()) > 3]
        else:
            unq_title, unq_authors = _extract_unquoted_product_title_and_authors(first)
            title = unq_title
            autores = unq_authors

    # Buscar una linea posterior que contenga un titulo entre comillas si no se encontró
    if not title or len(title) < 3 or title in (".", "-", ":"):
        _found_q = False
        for line in lines[1:]:
            if not _found_q:
                quoted = re.search(r'["“]([^"”\r\n]+)["”]', line)
                if quoted:
                    title = clean_text(quoted.group(1))
                    _found_q = True

    all_text = " ".join(clean_text(line) for line in lines if clean_text(line))

    # Buscar nombre comercial si el titulo no fue claro
    if not title or title in (".", "-", ":", "Contacto:"):
        nc = re.search(r"Nombre comercial:\s*([^,]+)", all_text, re.IGNORECASE)
        if nc and nc.group(1).strip():
            title = clean_text(nc.group(1))

    title = title.rstrip(" .")

    product = ProductoInvestigacion(
        idProducto="P{}".format(index),
        titulo=title,
        categoria=clean_text(category),
        tipoProducto=subtype,
        subtipo=subtype,
        descripcion=all_text,
        autores=autores,
    )

    text_no_ids = re.sub(r"(?:ISSN|ISBN)\s*:\s*[\d-]+", "", all_text, flags=re.IGNORECASE)
    ym = re.search(r"(?:p\.\s*[\d\s-]+|\bEn:\s*[^,]+,\s*|,\s*)(19\d{2}|20\d{2})\s*[,.]", text_no_ids, re.IGNORECASE)
    if not ym:
        after_title = text_no_ids
        if title and title in text_no_ids:
            after_title = text_no_ids.split(title, 1)[-1]
        ym = re.search(r"\b(19\d{2}|20\d{2})\b", after_title)
    if not ym:
        ym = re.search(r"\b(19\d{2}|20\d{2})\b", text_no_ids)

    if ym:
        if ym.lastindex:
            val_year = ym.group(1)
        else:
            val_year = ym.group(0)
        product.anio = safe_int(val_year)

    isbn_match = re.search(r"ISBN:\s*([^,]+)", all_text, re.IGNORECASE)
    if isbn_match:
        product.isbn = clean_text(isbn_match.group(1))

    doi_match = re.search(r"DOI:\s*([^,\s]+(?:\S*://\S+|\S+)?)", all_text, re.IGNORECASE)
    if doi_match:
        product.doi = clean_text(doi_match.group(1))

    for line in lines:
        clean_line = clean_text(line)
        if "ISSN:" in clean_line.upper():
            before_issn = clean_text(re.split(r"ISSN:", clean_line, maxsplit=1, flags=re.IGNORECASE)[0])
            if "," in before_issn:
                first_part, second_part = before_issn.split(",", 1)
                if re.match(r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñü .'-]+$", first_part.strip()):
                    product.revista = clean_text(second_part)
                else:
                    product.revista = before_issn
            else:
                product.revista = before_issn
        editorial_match = re.search(r"\bed:\s*([^,]+)", clean_line, re.IGNORECASE)
        if editorial_match:
            product.editorial = clean_text(editorial_match.group(1))

    _found_country = False
    for line in lines:
        if not _found_country:
            clean_line = clean_text(line)
            country_match = re.search(r"\bEn:\s*([^,]+)", clean_line, re.IGNORECASE)
            if country_match:
                product.pais = clean_text(country_match.group(1))
                _found_country = True
    if not product.pais:
        _found_country2 = False
        for line in lines[1:]:
            if not _found_country2:
                country_match = re.match(r"^([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñü .'-]+),", clean_text(line))
                if country_match:
                    product.pais = clean_text(country_match.group(1))
                    _found_country2 = True

    words_match = re.search(r"Palabras:\s*(.+?)(?=\s+Areas:|\s+Sectores:|$)", all_text, re.IGNORECASE)
    if words_match:
        product.palabrasClave = clean_text(words_match.group(1))

    areas_match = re.search(r"Areas:\s*(.+?)(?=\s+Sectores:|$)", all_text, re.IGNORECASE)
    if areas_match:
        product.areas = clean_text(areas_match.group(1))

    contract_match = re.search(r"contrato/registro:\s*([^,]+)", all_text, re.IGNORECASE)
    if contract_match:
        product.numeroContrato = clean_text(contract_match.group(1))

    # Fallback para autores si no se habían extraído
    if not product.autores:
        _found_auth = False
        for line in lines:
            if not _found_auth:
                explicit_authors = re.match(r"^Autores?:\s*(.+)$", clean_text(line), re.IGNORECASE)
                if explicit_authors:
                    product.autores = unique_strings(re.split(r"\s*,\s*", explicit_authors.group(1)))
                    _found_auth = True

    product.normalizar()
    if not product.titulo:
        return None
    return product


def _find_investigator_products(values: List[str], root: Optional[ParseNode] = None) -> List[ProductoInvestigacion]:
    products: List[ProductoInvestigacion] = []
    seen = set()
    counter = 1

    # 1. Extracción estructurada desde el árbol DOM si está disponible
    if root is not None:
        all_tables = _find_nodes(root, "table")
        child_tables = []
        for t in all_tables:
            p = t.parent
            has_table_parent = False
            while p and not has_table_parent:
                if p.tag == "table":
                    has_table_parent = True
                if not has_table_parent:
                    p = p.parent
            if has_table_parent:
                child_tables.append(t)

        if child_tables:
            tables_to_check = child_tables
        else:
            tables_to_check = all_tables
        for table in tables_to_check:
            is_p, label = _is_cvlac_product_table(table)
            if is_p:
                h3_nodes = _find_nodes(table, "h3")
                if h3_nodes:
                    raw_section_title = h3_nodes[0].all_text()
                else:
                    raw_section_title = label
                section_title = _map_cvlac_product_category(label, raw_section_title)

                bqs = _find_nodes(table, "blockquote")
                for bq in bqs:
                    text = _clean_record(bq.all_text())
                    if text and len(text) >= 4:
                        subtype = section_title
                        validado = False

                        # 1. Comprobar si hay imagen de verificación (chulo.jpg) dentro de bq
                        if any("chulo" in img.attrs.get("src", "").lower() for img in _find_nodes(bq, "img")):
                            validado = True

                        # 2. Comprobar en nodo ancestro directo en la misma fila (p.ej. li)
                        if not validado:
                            p_node = bq.parent
                            while p_node and p_node.tag not in ("tr", "table") and not validado:
                                if any("chulo" in img.attrs.get("src", "").lower() for img in _find_nodes(p_node, "img")):
                                    validado = True
                                if not validado:
                                    p_node = p_node.parent

                        # 3. Subtipo y verificación en fila previa si no tiene su propio blockquote
                        p_td = bq.parent
                        while p_td and p_td.tag not in ("td", "tr", "table"):
                            p_td = p_td.parent
                        if p_td and p_td.parent and p_td.parent.tag == "tr":
                            row = p_td.parent
                            table_rows = [c for c in row.parent.children if c.tag == "tr"]
                            if row in table_rows:
                                idx = table_rows.index(row)
                                if idx > 0:
                                    prev_row = table_rows[idx - 1]
                                    if not _find_nodes(prev_row, "blockquote"):
                                        if any("chulo" in img.attrs.get("src", "").lower() for img in _find_nodes(prev_row, "img")):
                                            validado = True
                                        prev_text = _clean_record(prev_row.all_text())
                                        if any(k in prev_text.lower() for k in ["producción", "produccion", "tipo:"]):
                                            m_sub = re.search(r"((?:Producci[oó]n|Tipo:)[^\r\n<]+)", prev_text, re.IGNORECASE)
                                            if m_sub:
                                                subtype = m_sub.group(1).strip()
                                            else:
                                                subtype = prev_text[:80]

                        # Titulo y autores
                        title = ""
                        autores: List[str] = []
                        m_q = re.search(r'["“]([^"”\r\n]+)["”]', text)
                        if m_q:
                            title = m_q.group(1).strip()
                            q_start = text.find(m_q.group(0))
                            raw_auth = text[:q_start].strip().rstrip(",").strip()
                            raw_auth = re.sub(r"^(?:Tipo:\s*[^,]+,\s*|\*\s*)", "", raw_auth, flags=re.IGNORECASE)
                            if raw_auth:
                                autores = [a.strip() for a in raw_auth.split(",") if a.strip() and len(a.strip()) > 3]
                        else:
                            unq_title, unq_authors = _extract_unquoted_product_title_and_authors(text)
                            title = unq_title
                            autores = unq_authors

                        title = title.rstrip(" .")
                        anio = 0
                        ym = re.search(r"\b(19\d{2}|20\d{2})\b", text)
                        if ym:
                            anio = int(ym.group(1))

                        prod = ProductoInvestigacion(
                            idProducto=f"P{counter}",
                            titulo=title,
                            categoria=section_title,
                            validado=validado,
                            anio=anio,
                            tipoProducto=subtype,
                            subtipo=subtype,
                            descripcion=text,
                            autores=autores,
                        )

                        m_doi = re.search(r"DOI:\s*([^,\s]+)", text, re.IGNORECASE)
                        if m_doi:
                            prod.doi = m_doi.group(1).strip()
                        m_isbn = re.search(r"ISBN:\s*([^,\s]+)", text, re.IGNORECASE)
                        if m_isbn:
                            prod.isbn = m_isbn.group(1).strip()
                        m_issn = re.search(r"ISSN:\s*([^,\s]+)", text, re.IGNORECASE)
                        if m_issn:
                            prod.revista = m_issn.group(1).strip()

                        key = (clean_text(prod.titulo).casefold(), int(prod.anio or 0))
                        if key not in seen and len(prod.titulo) >= 2:
                            seen.add(key)
                            products.append(prod)
                            counter += 1

    # 2. Extraccion secuencial sobre bloques de texto (funciona como fallback)
    if not products:
        pending: List[str] = []
        category = ""
        active_production = False

        def flush() -> None:
            nonlocal pending, counter

            if pending:
                product = _extract_investigator_product(
                    pending,
                    category,
                    counter
                )
                if product is not None:
                    key = (clean_text(product.titulo).casefold(), int(product.anio or 0))
                    if key not in seen and len(product.titulo) >= 2:
                        products.append(product)
                        seen.add(key)
                        counter += 1

            pending = []

        for value in values:
            clean_value = clean_text(value)
            lowered = clean_value.casefold()

            marker = INV_PRODUCTION_START_RE.match(clean_value)
            inline_marker = INV_PRODUCT_INLINE_RE.match(clean_value)

            if marker:
                flush()
                active_production = True
                category = clean_text(marker.group(2))
            elif lowered in {
                "artículos", "capitulos de libro", "capítulos de libro",
                "libros", "nota científica", "textos en publicaciones no científicas",
                "otra producción bibliográfica", "patentes", "software", "softwares",
                "procesos o técnicas", "trabajos técnicos", "normas y regulaciones",
                "consultorías", "cursos de corta duración", "secretos empresariales",
                "documentos de trabajo", "demás trabajos", "empresas de base tecnológica"
            }:
                flush()
                category = clean_value
                active_production = True
            elif inline_marker:
                flush()
                pending = [clean_value]
                active_production = True
            elif active_production and _looks_like_inv_product_text(clean_value):
                flush()
                pending = [clean_value]
            else:
                if pending:
                    pending.append(clean_value)
                if any(sec in lowered for sec in ALL_CVLAC_SECTIONS):
                    flush()
                    active_production = False

        flush()

    return products


# -------------------------------------------------------------------------
# Integrantes GrupLAC
# -------------------------------------------------------------------------

def _extract_group_members(root: ParseNode) -> List[Dict[str, Any]]:
    selected_rows: List[List[str]] = []
    _found_tbl = False
    for table in _extract_tables(root):
        if not _found_tbl:
            header_index = -1
            _found_hdr = False
            for index, row in enumerate(table):
                if not _found_hdr:
                    normalized = [_norm_key(cell) for cell in row]
                    if "nombre" in normalized and ("vinculación" in normalized or "vinculacion" in normalized):
                        header_index = index
                        _found_hdr = True
            if header_index >= 0:
                selected_rows = table[header_index + 1:]
                _found_tbl = True

    members: List[Dict[str, Any]] = []
    for row in selected_rows:
        if row:
            name = _clean_numbered(row[0])
            if name:
                lowered = _norm_key(name)
                if lowered not in {"nombre", "nombre completo"}:
                    if len(row) >= 2:
                        vinc = clean_text(row[1])
                    else:
                        vinc = ""
                    if len(row) >= 3:
                        hd = clean_text(row[2])
                    else:
                        hd = ""
                    if len(row) >= 4:
                        ifv = clean_text(row[3])
                    else:
                        ifv = ""
                    member: Dict[str, Any] = {
                        "codigoRh": "",
                        "nombre": name,
                        "correo": "",
                        "orcid": "",
                        "institucion": "",
                        "departamento": "",
                        "ciudad": "",
                        "categoriaInvestigador": "",
                        "perfil": "",
                        "nombreCitaciones": "",
                        "nacionalidad": "",
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
                        "activo": True,
                        "vinculacion": vinc,
                        "horasDedicacion": hd,
                        "inicioFinVinculacion": ifv,
                    }
                    members.append(member)

    output: List[Dict[str, Any]] = []
    seen = set()
    for member in members:
        key = member["nombre"].casefold()
        if key and key not in seen:
            output.append(member)
            seen.add(key)
    return output


# -------------------------------------------------------------------------
# Errores y scraper publico
# -------------------------------------------------------------------------

class ScraperError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class WebScraper:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self.last_error: Optional[ScraperError] = None

    def _fetch(self, url: str) -> str:
        self.last_error = None
        if not is_valid_url(url):
            raise ScraperError("URL_INVALIDA", "La URL no es válida.")

        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.7",
            },
        )

        raw = b""
        response = None
        encoding = "utf-8"
        try:
            # Minciencias puede presentar el certificado de la cadena SSL
            # como no verificable desde algunas instalaciones de Windows.
            context = ssl._create_unverified_context()
            response = urlopen(request, timeout=self.timeout, context=context)
            status = getattr(response, "status", 200)
            if status >= 400:
                raise ScraperError("HTTP", "La página respondió con un error HTTP {}.".format(status))
            raw = response.read()
            try:
                header_value = response.headers.get_content_charset()
                if header_value:
                    encoding = header_value
            except Exception:
                encoding = "utf-8"
        except HTTPError as exc:
            raise ScraperError("HTTP", "La página respondió con HTTP {}.".format(exc.code))
        except URLError as exc:
            raise ScraperError("CONEXION", "No fue posible conectar con la página: {}".format(exc.reason))
        except TimeoutError:
            raise ScraperError("TIMEOUT", "La conexión superó el tiempo de espera.")
        except OSError as exc:
            raise ScraperError("CONEXION", "No fue posible leer la página: {}".format(exc))
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

        detected_enc = None
        match = re.search(rb'charset=["\']?([\w\-]+)', raw[:4096], re.IGNORECASE)
        if match:
            try:
                candidate = match.group(1).decode("ascii", errors="ignore").lower()
                codecs.lookup(candidate)
                detected_enc = candidate
            except Exception:
                pass

        final_enc = detected_enc or encoding or "utf-8"
        try:
            html = raw.decode(final_enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            html = raw.decode("utf-8", errors="replace")

        if not html.strip():
            raise ScraperError("PAGINA_VACIA", "La página no contiene contenido HTML utilizable.")
        return html

    def _parse(self, html: str) -> DOMParser:
        parser = DOMParser()
        try:
            parser.feed(html)
            parser.close()
        except Exception as exc:
            raise ScraperError("HTML_INVALIDO", "No fue posible interpretar la estructura HTML: {}".format(exc))
        return parser

    def buscar_grupo(self, url: str) -> Dict[str, Any]:
        valido, norm_url, error_msg = validar_url_minciencias("grupo", url)
        if not valido:
            raise ScraperError("URL_INVALIDA", error_msg)
        url = norm_url
        try:
            html = self._fetch(url)
            parser = self._parse(html)
            values = _record_values(parser.root)
            full_text = parser.root.all_text()
            pairs = _label_value_pairs(parser.root)

            group = GrupoInvestigacion()
            for field_name in group.__dict__.keys():
                if field_name in pairs:
                    setattr(group, field_name, pairs[field_name])

            # El numero del grupo viene de la URL; es la fuente mas estable.
            nro = _query_parameter(url, "nro")
            if nro:
                group.nroGrupo = nro
            elif "nroGrupo" in pairs and not group.nroGrupo:
                group.nroGrupo = pairs["nroGrupo"]

            # El nombre aparece inmediatamente antes de 'Datos básicos' en
            # la pagina real de GrupLAC, pero puede estar en una etiqueta HTML
            # distinta. Se usa un extractor especifico para ese encabezado.
            group.nombreGrupo = _extract_group_name(values, full_text, parser.root)

            # Respaldo para variantes donde existe literalmente 'Nombre del grupo'.
            if not group.nombreGrupo:
                if "nombreGrupo" in pairs:
                    group.nombreGrupo = pairs["nombreGrupo"]
                else:
                    _found_n = False
                    for index, value in enumerate(values):
                        if not _found_n:
                            if _norm_key(value) in {"nombre del grupo", "nombre grupo"} and index + 1 < len(values):
                                group.nombreGrupo = clean_text(values[index + 1])
                                _found_n = True

            # Ubicacion exacta del registro 'Departamento - Ciudad'.
            location = pairs.get("departamento", "")
            if location:
                parts = re.split(r"\s+-\s+", location, maxsplit=1)
                if len(parts) == 2:
                    group.departamento = clean_text(parts[0])
                    group.ciudad = clean_text(parts[1])
                else:
                    group.departamento = clean_text(location)

            # Las instituciones se toman solamente de su seccion.
            group.instituciones = _section_items(
                values,
                ["instituciones"],
                ["líneas de investigación declaradas por el grupo", "lineas de investigacion declaradas por el grupo", "integrantes del grupo"],
            )

            # MUY IMPORTANTE: solo se recogen las 9 lineas ubicadas entre el
            # titulo de la seccion y 'Integrantes del grupo'.
            group.lineasInvestigacion = _section_items(
                values,
                ["líneas de investigación declaradas por el grupo", "lineas de investigacion declaradas por el grupo"],
                ["integrantes del grupo"],
                numbered_only=True,
            )

            group.integrantes = _extract_group_members(parser.root)
            group_products = _find_group_products(
                values,
                group.nroGrupo
            )

            group.productos = [
                product.to_dict()
                for product in group_products
            ]

            if group.clasificacion:
                group.clasificacion = _normalize_group_classification(group.clasificacion)

            group.normalizar()
            if not group.nroGrupo and not group.nombreGrupo:
                raise ScraperError(
                    "ESTRUCTURA",
                    "La página no contiene la estructura esperada para un grupo GrupLAC.",
                )

            result = group.to_dict()
            result["tipo"] = "grupo"
            result["fuente"] = url
            return result

        except ScraperError as exc:
            self.last_error = exc
            raise
        except Exception as exc:
            error = ScraperError(
                "PROCESAMIENTO",
                "Ocurrió un error controlado al procesar el grupo: {}".format(exc),
            )
            self.last_error = error
            raise error

    def buscar_investigador(self, url: str) -> Dict[str, Any]:
        valido, norm_url, error_msg = validar_url_minciencias("investigador", url)
        if not valido:
            raise ScraperError("URL_INVALIDA", error_msg)
        url = norm_url
        try:
            html = self._fetch(url)
            parser = self._parse(html)
            values = _record_values(parser.root)
            full_text = parser.root.all_text()

            investigator = Investigador()

            identity = _extract_investigator_identity(values, full_text, parser.root)
            for field_name, value in identity.items():
                if hasattr(investigator, field_name) and value:
                    setattr(investigator, field_name, value)

            # El codigo RH se obtiene directamente del parametro cod_rh.
            rh = _query_parameter(url, "cod_rh")
            if rh:
                investigator.codigoRh = rh

            links = _extract_investigator_links(parser.root)
            for field_name, value in links.items():
                if value and hasattr(investigator, field_name):
                    setattr(investigator, field_name, value)

            dom_sections = _extract_investigator_sections_dom(parser.root)

            def get_dom_sec(keywords: List[str]) -> List[str]:
                for kw in keywords:
                    norm_kw = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", kw.lower()))
                    for k, v in dom_sections.items():
                        if norm_kw in k:
                            return v
                return []

            investigator.formacionAcademica = get_dom_sec(["formación académica", "formacion academica", "formacion"]) or _section_items(
                values,
                ["formación académica", "formacion academica"],
                ["formación complementaria", "formacion complementaria", "experiencia profesional"],
            )
            investigator.experienciaProfesional = get_dom_sec(["experiencia profesional", "experiencia"]) or _section_items(
                values,
                ["experiencia profesional"],
                ["áreas de actuación", "areas de actuación", "otra información personal", "idiomas"],
            )
            investigator.areasConocimiento = get_dom_sec(["áreas de actuación", "areas de actuación", "áreas de conocimiento", "areas de conocimiento"]) or _section_items(
                values,
                ["áreas de actuación", "areas de actuación"],
                ["idiomas", "líneas de investigación", "lineas de investigacion"],
            )
            investigator.idiomas = _extract_languages(values, parser.root)
            investigator.lineasInvestigacion = get_dom_sec(["líneas de investigación", "lineas de investigación", "lineas"]) or _section_items(
                values,
                ["líneas de investigación", "lineas de investigación"],
                ["reconocimientos", "trabajos dirigidos", "asesorías", "artículos", "cursos de corta duración"],
            )
            investigator.reconocimientos = get_dom_sec(["reconocimientos"]) or _section_items(
                values,
                ["reconocimientos"],
                ["cursos de corta duración", "artículos", "capitulos de libro", "capítulos de libro"],
            )
            investigator.gruposInvestigacion = get_dom_sec(["grupos de investigación", "grupos de investigacion", "grupos"]) or _section_items(
                values,
                ["grupos de investigación", "grupos de investigacion"],
                ["semilleros", "proyectos", "reconocimientos"],
            )
            investigator.semilleros = get_dom_sec(["semilleros de investigación", "semilleros de investigacion", "semilleros"]) or _section_items(
                values,
                ["semilleros de investigación", "semilleros de investigacion", "semilleros"],
                ["proyectos", "reconocimientos", "artículos", "capitulos de libro", "capítulos de libro"],
            )
            investigator.proyectos = get_dom_sec(["proyectos de investigación", "proyectos de investigacion", "proyectos"]) or _section_items(
                values,
                ["proyectos de investigación", "proyectos de investigacion", "proyectos"],
                ["artículos", "capitulos de libro", "capítulos de libro", "reconocimientos"],
            )

            # En este CvLAC la afiliacion/campus esta dentro de experiencia
            # profesional, priorizando la institución actualmente activa.
            institution, city = _extract_investigator_affiliation(values, full_text, investigator.experienciaProfesional)
            if not investigator.institucion and institution:
                investigator.institucion = institution
            if not investigator.ciudad and city:
                investigator.ciudad = city

            products = _find_investigator_products(values, parser.root)
            investigator.productos = [product.to_dict() for product in products]

            investigator.normalizar()
            if not investigator.nombre and not investigator.codigoRh:
                raise ScraperError(
                    "ESTRUCTURA",
                    "La página no contiene la estructura esperada para un investigador CvLAC.",
                )

            result = investigator.to_dict()
            result["tipo"] = "investigador"
            result["fuente"] = url
            return result

        except ScraperError as exc:
            self.last_error = exc
            raise
        except Exception as exc:
            error = ScraperError(
                "PROCESAMIENTO",
                "Ocurrió un error controlado al procesar el investigador: {}".format(exc),
            )
            self.last_error = error
            raise error

    def buscar(self, tipo_busqueda: str, url: str) -> Dict[str, Any]:
        normalized = clean_text(tipo_busqueda).casefold()
        valido, norm_url, error_msg = validar_url_minciencias(normalized, url)
        if not valido:
            raise ScraperError("URL_INVALIDA", error_msg)

        if normalized == "grupo":
            return self.buscar_grupo(norm_url)
        if normalized == "investigador":
            return self.buscar_investigador(norm_url)
        raise ScraperError(
            "TIPO_INVALIDO",
            "El tipo de búsqueda debe ser 'grupo' o 'investigador'.",
        )


# =========================================================================
# SISTEMA INTELIGENTE DE EXTRACCION DE ARCHIVOS PDF (4 CAPAS)
# =========================================================================

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
            text_content = self._extract_fallback(file_path)
        return text_content.replace("\xa0", " ")

    def _extract_fallback(self, file_path: str) -> str:
        text_parts = []
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()

            stream_matches = re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, re.DOTALL)
            for sm in stream_matches:
                raw_chunk = sm.group(1)
                decompressed = None
                try:
                    decompressed = zlib.decompress(raw_chunk)
                except Exception:
                    decompressed = raw_chunk

                if decompressed:
                    tj_matches = re.finditer(rb"\((.*?)\)\s*Tj", decompressed)
                    for tm in tj_matches:
                        chunk_str = tm.group(1).decode("latin-1", errors="ignore")
                        cl = clean_text(chunk_str)
                        if cl:
                            text_parts.append(cl)

            if len(text_parts) == 0:
                raw_latin = raw_bytes.decode("latin-1", errors="ignore")
                matches = re.findall(r"\(([^()]{2,})\)\s*Tj", raw_latin)
                idx = 0
                while idx < len(matches):
                    cl = clean_text(matches[idx])
                    if cl:
                        text_parts.append(cl)
                    idx += 1
        except Exception:
            pass
        return "\n".join(text_parts)

    def verify_gatekeeper(self, text: str) -> bool:
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

    def partition_document(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
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

    def _extract_product_title(self, bloque: str) -> str:
        """Extrae el titulo limpio de un bloque de producto en formatos MinCiencias."""
        m_comillas = re.search(r'"([^"\r\n]{5,})"', bloque)
        if m_comillas:
            return clean_text(m_comillas.group(1).strip())

        m_tit = re.search(r'Titulo:\s*([^\n\r]+)', bloque, re.IGNORECASE)
        if m_tit:
            t = m_tit.group(1).strip()
            t = re.split(r'\s+Tipo\s+de\s+trabajo', t, flags=re.IGNORECASE)[0]
            return clean_text(t.strip())

        lineas_b = [l.strip() for l in bloque.split("\n") if l.strip()]
        if len(lineas_b) == 0:
            return ""

        primera = lineas_b[0]
        tags_fin = [r',\s*Finalidad:', r',\s*Nombre\s+comercial:', r',\s*\.\s*En:', r',\s*contrato/registro:', r'\s+Estado:']
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
        primera = re.sub(r'^[•\-\*#]+\s*', '', primera)
        primera = re.sub(r'^\d+\s*[\.\-\)]\s*', '', primera)
        return clean_text(primera)

    def _extract_year(self, text: str) -> int:
        years = re.findall(r"\b(19\d\d|20[0-3]\d)\b", text)
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
        m_nom = re.search(r"(?:^|\n)\s*Nombre\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_nom:
            cand_nom = clean_text(m_nom.group(1))
            if cand_nom and "citaciones" not in cand_nom.lower() and "comercial" not in cand_nom.lower():
                inv["nombre"] = cand_nom

        if not inv["nombre"]:
            m_nom_alt = re.search(r"(?:Investigador|Nombre\s+completo)\s*[:\n]\s*([^\n\r]+)", text, re.IGNORECASE)
            if m_nom_alt:
                inv["nombre"] = clean_text(m_nom_alt.group(1))

        # 2. Nombre en citaciones
        m_cit = re.search(r"(?:^|\n)\s*Nombre\s+en\s+citaciones\s*(?::|\n)\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_cit:
            inv["nombreCitaciones"] = clean_text(m_cit.group(1))

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

        # 6. Identificadores y redes
        m_orcid = re.search(r"\b([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])\b", text)
        if m_orcid:
            inv["orcid"] = clean_text(m_orcid.group(1))

        m_mail = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", text)
        if m_mail:
            inv["correo"] = clean_text(m_mail.group(1))

        m_inst = re.search(r"(?:^|\n)\s*Experiencia\s+profesional\s*\n\s*([^\n\r]+)", text, re.IGNORECASE)
        if m_inst:
            cand_inst = clean_text(m_inst.group(1))
            if len(cand_inst) > 3:
                inv["institucion"] = cand_inst

        # 7. Codigo RH determinista
        m_rh = re.search(r"(?:C[oó]digo\s+RH|C[oó]digo\s+de\s+investigador|Identificaci[oó]n|C[eé]dula)\s*[:\n]\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
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
        m_sec_lineas = re.search(r"L[ií]neas\s+de\s+investigaci[oó]n\s*[:\n](.*?)(?=(?:Formaci[oó]n|Experiencia|Producci[oó]n|Reconocimientos|Idiomas|\Z))", text, re.DOTALL | re.IGNORECASE)
        if m_sec_lineas:
            for l_item in m_sec_lineas.group(1).split("\n"):
                cl = clean_text(re.sub(r"^[-*•]\s*", "", l_item))
                cl = re.sub(r",\s*Activa\s*:\s*Si", "", cl, flags=re.IGNORECASE).strip()
                if len(cl) > 3:
                    inv["lineasInvestigacion"].append(cl)

        # 9. Formacion Academica
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

        # 11. Productos
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
            return True, lote_data, msg


# =========================================================================
# MOTOR DE EXTRACCION DE ARCHIVOS CSV (4 CAPAS MINCIENCIAS)
# =========================================================================

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


def parse_pipe_list(raw: str) -> List[str]:
    if not raw:
        return []
    raw_clean = clean_text(raw)
    if not raw_clean:
        return []
    tokens: List[str] = []
    if "|" in raw_clean:
        tokens = raw_clean.split("|")
    elif "\n" in raw_clean:
        tokens = raw_clean.split("\n")
    elif ";" in raw_clean:
        tokens = raw_clean.split(";")
    else:
        tokens = [raw_clean]
    res: List[str] = []
    idx = 0
    while idx < len(tokens):
        c = clean_text(tokens[idx])
        if c:
            if c not in res:
                res.append(c)
        idx += 1
    return res


def parse_languages(raw: str) -> List[str]:
    if not raw:
        return []
    raw_clean = clean_text(raw)
    if not raw_clean:
        return []
    if "|" in raw_clean:
        raw_parts = raw_clean.split("|")
        parts: List[str] = []
        p_i = 0
        while p_i < len(raw_parts):
            p_val = clean_text(raw_parts[p_i])
            if p_val:
                parts.append(p_val)
            p_i += 1
        es_tabla = False
        if len(parts) >= 5:
            if parts[0].lower() == "idioma":
                if parts[1].lower() == "habla":
                    es_tabla = True
        if es_tabla:
            res: List[str] = ["Idioma | Habla | Escribe | Lee | Entiende"]
            i = 5
            while i < len(parts):
                chunk = parts[i : i + 5]
                if len(chunk) == 5:
                    fila_str = chunk[0] + " | " + " | ".join(chunk[1:])
                    res.append(fila_str)
                elif len(chunk) > 0:
                    res.append(" | ".join(chunk))
                i += 5
            return res
        else:
            return parts
    return [raw_clean]


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
            # Si ambos fueron parseables, seleccionar el que produzca mas columnas
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
                    autores_list: List[str] = []
                    if "prod_autores" in r_data:
                        aut_parts = re.split(r"[,;]+", r_data["prod_autores"])
                        a_i = 0
                        while a_i < len(aut_parts):
                            c_aut = clean_text(aut_parts[a_i])
                            if c_aut:
                                autores_list.append(c_aut)
                            a_i += 1
                    val_validado = False
                    val_norm = r_data.get("prod_validado", "").lower()
                    if val_norm == "true" or val_norm == "1" or val_norm == "si" or val_norm == "sí":
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
            elif tipo_reg == "":
                if has_grp_fields:
                    if "grp_nombreGrupo" in r_data or "grp_nroGrupo" in r_data:
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
                if not mem_nom:
                    if has_inv_fields:
                        if "inv_nombre" in r_data:
                            if r_data["inv_nombre"] != cur_grp["nombreGrupo"]:
                                mem_nom = r_data["inv_nombre"]

                if mem_nom:
                    if len(mem_nom) >= 3:
                        m_sig = canonical_key(mem_nom)
                        if m_sig not in cur_grp["_seen_mems"]:
                            cur_grp["_seen_mems"].add(m_sig)
                            cod_mem = r_data.get("mem_codigoRh", r_data.get("inv_codigoRh", ""))
                            if not cod_mem:
                                cod_mem = "MEM_" + canonical_key(mem_nom)[:8].upper()
                            inst_mem = r_data.get("mem_institucion", "")
                            if not inst_mem:
                                if len(cur_grp["instituciones"]) > 0:
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
            elif tipo_reg == "":
                if has_inv_fields:
                    if "inv_nombre" in r_data or "inv_codigoRh" in r_data:
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

                    # Completar listas
                    if "inv_idiomas" in r_data:
                        if len(cur_inv["idiomas"]) == 0:
                            cur_inv["idiomas"] = parse_languages(r_data["inv_idiomas"])

                    if "inv_lineasInvestigacion" in r_data:
                        lin_items = parse_pipe_list(r_data["inv_lineasInvestigacion"])
                        for lin_it in lin_items:
                            if lin_it not in cur_inv["lineasInvestigacion"]:
                                cur_inv["lineasInvestigacion"].append(lin_it)

                    if "inv_reconocimientos" in r_data:
                        rec_items = parse_pipe_list(r_data["inv_reconocimientos"])
                        for rec_it in rec_items:
                            if rec_it not in cur_inv["reconocimientos"]:
                                cur_inv["reconocimientos"].append(rec_it)

                    if "inv_formacionAcademica" in r_data:
                        form_items = parse_pipe_list(r_data["inv_formacionAcademica"])
                        for form_it in form_items:
                            if form_it not in cur_inv["formacionAcademica"]:
                                cur_inv["formacionAcademica"].append(form_it)

                    if "inv_experienciaProfesional" in r_data:
                        exp_items = parse_pipe_list(r_data["inv_experienciaProfesional"])
                        for exp_it in exp_items:
                            if exp_it not in cur_inv["experienciaProfesional"]:
                                cur_inv["experienciaProfesional"].append(exp_it)

                    if "inv_proyectos" in r_data:
                        proy_items = parse_pipe_list(r_data["inv_proyectos"])
                        for proy_it in proy_items:
                            if proy_it not in cur_inv["proyectos"]:
                                cur_inv["proyectos"].append(proy_it)

                    if "inv_areasConocimiento" in r_data:
                        area_items = parse_pipe_list(r_data["inv_areasConocimiento"])
                        for area_it in area_items:
                            if area_it not in cur_inv["areasConocimiento"]:
                                cur_inv["areasConocimiento"].append(area_it)

                    if "grp_nombreGrupo" in r_data:
                        grp_n = r_data["grp_nombreGrupo"]
                        if grp_n:
                            if grp_n not in cur_inv["gruposInvestigacion"]:
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

        # Limpiar atributos internos auxiliares
        final_grupos: List[Dict[str, Any]] = []
        for g_k, g_v in grupos_dict.items():
            if "_seen_prods" in g_v:
                del g_v["_seen_prods"]
            if "_seen_mems" in g_v:
                del g_v["_seen_mems"]
            final_grupos.append(g_v)

        final_invs: List[Dict[str, Any]] = []
        for i_k, i_v in investigadores_dict.items():
            if "_seen_prods" in i_v:
                del i_v["_seen_prods"]
            final_invs.append(i_v)

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
        """Ejecuta el pipeline completo de 4 capas para un archivo CSV."""
        ok_tab, headers, rows, msg_tab = self.read_and_validate_tabular(file_path)
        if not ok_tab:
            return False, {}, msg_tab

        mapping = self.map_headers(headers)
        ok_gate, msg_gate = self.verify_gatekeeper(headers, rows, mapping)
        if not ok_gate:
            return False, {}, msg_gate

        result = self.normalize_and_extract(headers, rows, mapping)
        t = result.get("tipo", "")
        if t == "INVESTIGADOR":
            msg = "Extracción CSV exitosa: Investigador " + str(result.get("nombre", "")) + " (" + str(len(result.get("productos", []))) + " productos)."
            return True, result, msg
        elif t == "GRUPO":
            msg = "Extracción CSV exitosa: Grupo " + str(result.get("nombreGrupo", "")) + " (" + str(len(result.get("integrantes", []))) + " integrantes, " + str(len(result.get("productos", []))) + " productos)."
            return True, result, msg
        else:
            total_g = len(result.get("grupos", []))
            total_i = len(result.get("investigadores", []))

            if total_g == 0 and total_i == 0:
                return False, {}, "El archivo fue procesado pero no produjo ninguna entidad válida de MinCiencias."

            msg_success = "Extracción CSV exitosa: " + str(total_i) + " investigador(es) y " + str(total_g) + " grupo(s) procesados."
            return True, result, msg_success


# =========================================================================
# CAPA DE SERVICIOS Y LOGICA DE APLICACION
# =========================================================================

class ApplicationService:
    def __init__(self) -> None:
        self.scraper = WebScraper()
        self.persistence = PersistenceManager()
        stored = self.persistence.load_all()
        self.investigadores: List[Dict[str, Any]] = stored.get("investigadores", [])
        self.grupos: List[Dict[str, Any]] = stored.get("grupos", [])
        self.events: List[Dict[str, str]] = []
        self.last_saved: str = ""

    def _event(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M")
        self.events.insert(0, {"hora": timestamp, "mensaje": message})
        self.events = self.events[:8]

    def save_all(self) -> bool:
        ok = self.persistence.save_all(self.investigadores, self.grupos)
        if ok:
            self.last_saved = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._event("Datos guardados correctamente")
        else:
            self._event("Error al guardar los datos")
        return ok

    def _is_duplicate_investigator(self, inv1: Dict[str, Any], inv2: Dict[str, Any]) -> bool:
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
            return False, "El resultado del scraper no tiene un tipo válido."

    def scrape_and_add(self, tipo: str, url: str) -> Tuple[bool, Dict[str, Any], str]:
        valido, norm_url, error_msg = validar_url_minciencias(tipo, url)
        if not valido:
            self._event("Error de validación de URL")
            return False, {}, error_msg

        try:
            result = self.scraper.buscar(tipo, norm_url)
            added, message = self.add_scraped_result(result)
            return added, result, message
        except ScraperError as exc:
            self._event("Error de scraping: {}".format(exc.code))
            return False, {}, exc.message
        except Exception as exc:
            self._event("Error inesperado de scraping")
            return False, {}, "Error controlado de procesamiento: {}".format(exc)

    def scrape_pure(self, tipo: str, url: str) -> Tuple[bool, Dict[str, Any], str]:
        valido, norm_url, error_msg = validar_url_minciencias(tipo, url)
        if not valido:
            return False, {}, error_msg

        try:
            result = self.scraper.buscar(tipo, norm_url)
            return True, result, "Extracción completada con éxito."
        except ScraperError as exc:
            return False, {}, exc.message
        except Exception as exc:
            return False, {}, "Error controlado de procesamiento: {}".format(exc)

    def toggle_investigator(self, codigo: str) -> bool:
        changed = False
        for investigator in self.investigadores:
            if canonical_key(investigator.get("codigoRh", "")) == canonical_key(codigo):
                investigator["activo"] = not bool(investigator.get("activo", True))
                changed = True
        if changed:
            self._event("Estado de investigador actualizado")
        return changed

    def delete_investigator(self, target_identifier: str) -> bool:
        target_canon = canonical_key(target_identifier)
        remove_idx = -1
        idx = 0
        while idx < len(self.investigadores) and remove_idx == -1:
            inv = self.investigadores[idx]
            rh_canon = canonical_key(str(inv.get("codigoRh", "")))
            nom_canon = canonical_key(str(inv.get("nombre", "")))
            if target_canon and (rh_canon == target_canon or nom_canon == target_canon):
                remove_idx = idx
            idx += 1
        deleted = False
        if remove_idx != -1:
            removed_inv = self.investigadores.pop(remove_idx)
            inv_nom = removed_inv.get("nombre", "Investigador")
            self._event(f"Investigador eliminado: {inv_nom}")
            deleted = True
        return deleted

    def delete_group(self, target_identifier: str) -> bool:
        target_canon = canonical_key(target_identifier)
        remove_idx = -1
        idx = 0
        while idx < len(self.grupos) and remove_idx == -1:
            grp = self.grupos[idx]
            cod_canon = canonical_key(str(grp.get("nroGrupo", "")))
            nom_canon = canonical_key(str(grp.get("nombreGrupo", "")))
            if target_canon and (cod_canon == target_canon or nom_canon == target_canon):
                remove_idx = idx
            idx += 1
        deleted = False
        if remove_idx != -1:
            removed_grp = self.grupos.pop(remove_idx)
            grp_nom = removed_grp.get("nombreGrupo", "Grupo")
            self._event(f"Grupo eliminado: {grp_nom}")
            deleted = True
        return deleted

    def search_investigators(self, text: str) -> List[Dict[str, Any]]:
        query = canonical_key(text)
        result: List[Dict[str, Any]] = []
        for item in self.investigadores:
            haystack = " ".join([
                str(item.get("codigoRh", "")), str(item.get("nombre", "")),
                str(item.get("institucion", "")), str(item.get("categoriaInvestigador", ""))
            ])
            if not query or query in canonical_key(haystack):
                result.append(item)
        return result

    def search_groups(self, text: str) -> List[Dict[str, Any]]:
        query = canonical_key(text)
        result: List[Dict[str, Any]] = []
        for item in self.grupos:
            haystack = " ".join([
                str(item.get("nroGrupo", "")), str(item.get("nombreGrupo", "")),
                str(item.get("ciudad", "")), str(item.get("lider", "")),
                str(item.get("clasificacion", ""))
            ])
            if not query or query in canonical_key(haystack):
                result.append(item)
        return result

    def statistics(self) -> Dict[str, Any]:
        investigator_count = len(self.investigadores)
        active_count = sum(1 for item in self.investigadores if bool(item.get("activo", True)))
        group_count = len(self.grupos)
        products: List[Dict[str, Any]] = []
        categories: Dict[str, int] = {}
        years: Dict[str, int] = {}
        for investigator in self.investigadores:
            for product in investigator.get("productos", []):
                products.append(product)
        for group in self.grupos:
            for product in group.get("productos", []):
                products.append(product)
        unique_products: List[Dict[str, Any]] = []
        seen = set()
        for product in products:
            titulo = str(product.get("titulo", ""))
            anio = str(product.get("anio", 0))
            key = (canonical_key(titulo), anio)
            if titulo and key not in seen:
                unique_products.append(product)
                seen.add(key)
        for product in unique_products:
            category = str(product.get("categoria", "") or product.get("tipoProducto", "") or "Sin categoría").strip()
            year = str(product.get("anio", "") or "Sin año").strip()
            categories[category] = categories.get(category, 0) + 1
            years[year] = years.get(year, 0) + 1
        return {
            "investigadores": investigator_count,
            "investigadores_activos": active_count,
            "grupos": group_count,
            "productos": len(unique_products),
            "categorias": categories,
            "anios": years,
        }

    def dashboard(self) -> Dict[str, Any]:
        stats = self.statistics()
        return {
            "stats": stats,
            "events": list(self.events),
            "last_saved": self.last_saved,
        }

    def process_pdf_file(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
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
                return False, result, add_msg
        elif tipo == "GRUPO":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Grupo cargado desde PDF: " + str(result.get("nombreGrupo", "")))
                return True, result, add_msg
            else:
                return False, result, add_msg
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
            return False, {}, "Tipo de entidad no reconocido en el resultado del PDF."

    def process_csv_file(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
        extractor = CSVExtractor()
        ok, result, message = extractor.extract(file_path)
        if not ok:
            self._event("Error al procesar archivo CSV: " + message)
            return False, {}, message

        tipo = result.get("tipo", "")
        if tipo == "INVESTIGADOR":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Investigador cargado desde CSV: " + str(result.get("nombre", "")))
                return True, result, add_msg
            else:
                return False, result, add_msg
        elif tipo == "GRUPO":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Grupo cargado desde CSV: " + str(result.get("nombreGrupo", "")))
                return True, result, add_msg
            else:
                return False, result, add_msg
        elif tipo == "LOTE":
            grupos_cargados = 0
            grupos_duplicados = 0
            invs_cargados = 0
            invs_duplicados = 0

            grupos_list = result.get("grupos", [])
            g_idx = 0
            while g_idx < len(grupos_list):
                g = grupos_list[g_idx]
                add_ok, _ = self.add_scraped_result(g)
                if add_ok:
                    grupos_cargados += 1
                else:
                    grupos_duplicados += 1
                g_idx += 1

            invs_list = result.get("investigadores", [])
            i_idx = 0
            while i_idx < len(invs_list):
                inv = invs_list[i_idx]
                add_ok, _ = self.add_scraped_result(inv)
                if add_ok:
                    invs_cargados += 1
                else:
                    invs_duplicados += 1
                i_idx += 1

            summary_msg = "Lote CSV procesado: {} grupo(s) y {} investigador(es) incorporados (Duplicados omitidos: {} grupos, {} investigadores).".format(
                grupos_cargados, invs_cargados, grupos_duplicados, invs_duplicados
            )
            self._event(summary_msg)
            return True, result, summary_msg
        else:
            return False, {}, "Tipo de entidad no reconocido en el resultado del CSV."

    def process_csv_files(self, file_paths: List[str]) -> Dict[str, Any]:
        report = {
            "total_archivos": len(file_paths),
            "archivos_exitosos": 0,
            "archivos_fallidos": 0,
            "total_incorporados": 0,
            "total_duplicados": 0,
            "detalles": []
        }

        f_idx = 0
        while f_idx < len(file_paths):
            f_path = file_paths[f_idx]
            ok_f, res_f, msg_f = self.process_csv_file(f_path)
            detalle = {
                "archivo": os.path.basename(f_path),
                "ruta": f_path,
                "exito": ok_f,
                "mensaje": msg_f,
                "incorporados": 0,
                "duplicados": 0,
                "resultado": res_f
            }
            if ok_f:
                report["archivos_exitosos"] += 1
                tipo_f = res_f.get("tipo", "")
                if tipo_f == "INVESTIGADOR" or tipo_f == "GRUPO":
                    detalle["incorporados"] = 1
                    report["total_incorporados"] += 1
                elif tipo_f == "LOTE":
                    n_g = len(res_f.get("grupos", []))
                    n_i = len(res_f.get("investigadores", []))
                    detalle["incorporados"] = n_g + n_i
                    report["total_incorporados"] += n_g + n_i
            else:
                report["archivos_fallidos"] += 1
                if "ya se encuentra cargado" in msg_f.lower():
                    detalle["duplicados"] = 1
                    report["total_duplicados"] += 1

            report["detalles"].append(detalle)
            f_idx += 1

        return report

    def create_investigator(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        codigo = clean_text(str(data.get("codigoRh", "")))
        nombre = clean_text(str(data.get("nombre", "")))
        departamento = clean_text(str(data.get("departamento", "")))
        ciudad = clean_text(str(data.get("ciudad", "")))
        nacionalidad = clean_text(str(data.get("nacionalidad", "")))
        sexo = clean_text(str(data.get("sexo", "")))
        correo = clean_text(str(data.get("correo", "")))
        nombreCitaciones = clean_text(str(data.get("nombreCitaciones", "")))

        if not codigo:
            return False, "El código RH / identificador del investigador es obligatorio."
        if not nombre:
            return False, "El nombre completo del investigador es obligatorio."
        if not departamento:
            return False, "El departamento del investigador es obligatorio."
        if not ciudad:
            return False, "La ciudad del investigador es obligatoria."
        if not nacionalidad:
            return False, "La nacionalidad del investigador es obligatoria."
        if not sexo:
            return False, "El sexo del investigador es obligatorio."
        if not correo:
            return False, "El correo electrónico del investigador es obligatorio."
        if not nombreCitaciones:
            return False, "El nombre en citaciones del investigador es obligatorio."

        duplicate = False
        for current in self.investigadores:
            if self._is_duplicate_investigator(data, current):
                duplicate = True
        if duplicate:
            return False, "Ya existe un investigador registrado con el mismo código, nombre u ORCID."

        new_inv = {
            "codigoRh": codigo,
            "nombre": nombre,
            "correo": correo,
            "orcid": clean_text(str(data.get("orcid", ""))),
            "institucion": clean_text(str(data.get("institucion", ""))),
            "departamento": departamento,
            "ciudad": ciudad,
            "categoriaInvestigador": clean_text(str(data.get("categoriaInvestigador", ""))),
            "perfil": clean_text(str(data.get("perfil", ""))),
            "nombreCitaciones": nombreCitaciones,
            "nacionalidad": nacionalidad,
            "sexo": sexo,
            "estadoParEvaluador": clean_text(str(data.get("estadoParEvaluador", ""))),
            "researcherId": clean_text(str(data.get("researcherId", ""))),
            "autorIdScopus": clean_text(str(data.get("autorIdScopus", ""))),
            "googleScholar": clean_text(str(data.get("googleScholar", ""))),
            "researchGate": clean_text(str(data.get("researchGate", ""))),
            "academiaEdu": clean_text(str(data.get("academiaEdu", ""))),
            "mendeley": clean_text(str(data.get("mendeley", ""))),
            "linkedin": clean_text(str(data.get("linkedin", ""))),
            "repositorioInstitucional": clean_text(str(data.get("repositorioInstitucional", ""))),
            "idiomas": list(data.get("idiomas", [])),
            "areasConocimiento": list(data.get("areasConocimiento", [])),
            "lineasInvestigacion": list(data.get("lineasInvestigacion", [])),
            "formacionAcademica": list(data.get("formacionAcademica", [])),
            "experienciaProfesional": list(data.get("experienciaProfesional", [])),
            "gruposInvestigacion": list(data.get("gruposInvestigacion", [])),
            "semilleros": list(data.get("semilleros", [])),
            "proyectos": list(data.get("proyectos", [])),
            "reconocimientos": list(data.get("reconocimientos", [])),
            "productos": list(data.get("productos", [])),
            "activo": bool(data.get("activo", True)),
            "tipo": "INVESTIGADOR",
            "fuente": "MANUAL"
        }
        self.investigadores.append(new_inv)
        self._event("Investigador agregado manualmente: " + nombre)
        return True, "Investigador registrado exitosamente."

    def create_group(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        nombre = clean_text(str(data.get("nombreGrupo", "")))
        nro = clean_text(str(data.get("nroGrupo", "")))
        lider = clean_text(str(data.get("lider", "")))
        anio = clean_text(str(data.get("anioFormacion", "")))
        depto = clean_text(str(data.get("departamento", "")))
        ciudad = clean_text(str(data.get("ciudad", "")))
        email = clean_text(str(data.get("email", "")))
        instituciones = list(data.get("instituciones", []))
        integrantes = list(data.get("integrantes", []))

        if not nombre:
            return False, "El nombre del grupo es obligatorio."
        if not nro:
            return False, "El código / número del grupo es obligatorio."
        if not lider:
            return False, "El líder del grupo es obligatorio."
        if not anio:
            return False, "El año de formación del grupo es obligatorio."
        if not depto:
            return False, "El departamento del grupo es obligatorio."
        if not ciudad:
            return False, "La ciudad del grupo es obligatoria."
        if not email:
            return False, "El correo electrónico del grupo es obligatorio."
        if len(instituciones) == 0:
            return False, "Debe registrar al menos una institución con su plan estratégico."
        if len(integrantes) < 2:
            return False, "El grupo debe registrar al menos 2 integrantes."

        duplicate = False
        for current in self.grupos:
            if self._is_duplicate_group(data, current):
                duplicate = True
        if duplicate:
            return False, "Ya existe un grupo registrado con el mismo código o nombre."

        new_grp = {
            "nroGrupo": nro,
            "nombreGrupo": nombre,
            "anioFormacion": anio,
            "departamento": depto,
            "ciudad": ciudad,
            "lider": lider,
            "informacionCertificada": clean_text(str(data.get("informacionCertificada", ""))),
            "paginaWeb": clean_text(str(data.get("paginaWeb", ""))),
            "email": email,
            "clasificacion": clean_text(str(data.get("clasificacion", ""))),
            "areaConocimiento": clean_text(str(data.get("areaConocimiento", ""))),
            "programaNacionalCti": clean_text(str(data.get("programaNacionalCti", ""))),
            "programaNacionalCtiSecundario": clean_text(str(data.get("programaNacionalCtiSecundario", ""))),
            "planEstrategico": clean_text(str(data.get("planEstrategico", ""))),
            "estadoArte": clean_text(str(data.get("estadoArte", ""))),
            "objetivos": clean_text(str(data.get("objetivos", ""))),
            "retos": clean_text(str(data.get("retos", ""))),
            "vision": clean_text(str(data.get("vision", ""))),
            "instituciones": instituciones,
            "lineasInvestigacion": list(data.get("lineasInvestigacion", [])),
            "integrantes": integrantes,
            "productos": list(data.get("productos", [])),
            "tipo": "GRUPO",
            "fuente": "MANUAL"
        }
        self.grupos.append(new_grp)
        self._event("Grupo creado manualmente: " + nombre)
        return True, "Grupo registrado exitosamente."

    def update_investigator(self, target_inv: Dict[str, Any], data: Dict[str, Any]) -> Tuple[bool, str]:
        codigo = clean_text(str(data.get("codigoRh", "")))
        nombre = clean_text(str(data.get("nombre", "")))
        departamento = clean_text(str(data.get("departamento", "")))
        ciudad = clean_text(str(data.get("ciudad", "")))
        nacionalidad = clean_text(str(data.get("nacionalidad", "")))
        sexo = clean_text(str(data.get("sexo", "")))
        correo = clean_text(str(data.get("correo", "")))
        nombreCitaciones = clean_text(str(data.get("nombreCitaciones", "")))

        if not codigo:
            return False, "El código RH / identificador del investigador es obligatorio."
        if not nombre:
            return False, "El nombre completo del investigador es obligatorio."
        if not departamento:
            return False, "El departamento del investigador es obligatorio."
        if not ciudad:
            return False, "La ciudad del investigador es obligatoria."
        if not nacionalidad:
            return False, "La nacionalidad del investigador es obligatoria."
        if not sexo:
            return False, "El sexo del investigador es obligatorio."
        if not correo:
            return False, "El correo electrónico del investigador es obligatorio."
        if not nombreCitaciones:
            return False, "El nombre en citaciones del investigador es obligatorio."

        duplicate = False
        for current in self.investigadores:
            if current is not target_inv:
                if self._is_duplicate_investigator(data, current):
                    duplicate = True
        if duplicate:
            return False, "Ya existe otro investigador registrado con el mismo código, nombre u ORCID."

        target_inv["codigoRh"] = codigo
        target_inv["nombre"] = nombre
        target_inv["correo"] = correo
        target_inv["orcid"] = clean_text(str(data.get("orcid", "")))
        target_inv["institucion"] = clean_text(str(data.get("institucion", "")))
        target_inv["departamento"] = departamento
        target_inv["ciudad"] = ciudad
        target_inv["categoriaInvestigador"] = clean_text(str(data.get("categoriaInvestigador", "")))
        target_inv["perfil"] = clean_text(str(data.get("perfil", "")))
        target_inv["nombreCitaciones"] = nombreCitaciones
        target_inv["nacionalidad"] = nacionalidad
        target_inv["sexo"] = sexo
        target_inv["estadoParEvaluador"] = clean_text(str(data.get("estadoParEvaluador", "")))
        target_inv["researcherId"] = clean_text(str(data.get("researcherId", "")))
        target_inv["autorIdScopus"] = clean_text(str(data.get("autorIdScopus", "")))
        target_inv["googleScholar"] = clean_text(str(data.get("googleScholar", "")))
        target_inv["researchGate"] = clean_text(str(data.get("researchGate", "")))
        target_inv["academiaEdu"] = clean_text(str(data.get("academiaEdu", "")))
        target_inv["mendeley"] = clean_text(str(data.get("mendeley", "")))
        target_inv["linkedin"] = clean_text(str(data.get("linkedin", "")))
        target_inv["repositorioInstitucional"] = clean_text(str(data.get("repositorioInstitucional", "")))
        target_inv["idiomas"] = list(data.get("idiomas", []))
        target_inv["areasConocimiento"] = list(data.get("areasConocimiento", []))
        target_inv["lineasInvestigacion"] = list(data.get("lineasInvestigacion", []))
        target_inv["formacionAcademica"] = list(data.get("formacionAcademica", []))
        target_inv["experienciaProfesional"] = list(data.get("experienciaProfesional", []))
        if "gruposInvestigacion" in data:
            target_inv["gruposInvestigacion"] = list(data.get("gruposInvestigacion", []))
        if "semilleros" in data:
            target_inv["semilleros"] = list(data.get("semilleros", []))
        target_inv["proyectos"] = list(data.get("proyectos", []))
        target_inv["reconocimientos"] = list(data.get("reconocimientos", []))
        target_inv["productos"] = list(data.get("productos", []))
        if "activo" in data:
            target_inv["activo"] = bool(data.get("activo", True))

        self._event("Investigador modificado: " + nombre)
        return True, "Investigador actualizado exitosamente."

    def update_group(self, target_grp: Dict[str, Any], data: Dict[str, Any]) -> Tuple[bool, str]:
        nombre = clean_text(str(data.get("nombreGrupo", "")))
        nro = clean_text(str(data.get("nroGrupo", "")))
        lider = clean_text(str(data.get("lider", "")))
        anio = clean_text(str(data.get("anioFormacion", "")))
        depto = clean_text(str(data.get("departamento", "")))
        ciudad = clean_text(str(data.get("ciudad", "")))
        email = clean_text(str(data.get("email", "")))
        instituciones = list(data.get("instituciones", []))
        integrantes = list(data.get("integrantes", []))

        if not nombre:
            return False, "El nombre del grupo es obligatorio."
        if not nro:
            return False, "El código / número del grupo es obligatorio."
        if not lider:
            return False, "El líder del grupo es obligatorio."
        if not anio:
            return False, "El año de formación del grupo es obligatorio."
        if not depto:
            return False, "El departamento del grupo es obligatorio."
        if not ciudad:
            return False, "La ciudad del grupo es obligatoria."
        if not email:
            return False, "El correo electrónico del grupo es obligatorio."
        if len(instituciones) == 0:
            return False, "Debe registrar al menos una institución con su plan estratégico."
        if len(integrantes) < 2:
            return False, "El grupo debe registrar al menos 2 integrantes."

        duplicate = False
        for current in self.grupos:
            if current is not target_grp:
                if self._is_duplicate_group(data, current):
                    duplicate = True
        if duplicate:
            return False, "Ya existe otro grupo registrado con el mismo código o nombre."

        target_grp["nroGrupo"] = nro
        target_grp["nombreGrupo"] = nombre
        target_grp["anioFormacion"] = anio
        target_grp["departamento"] = depto
        target_grp["ciudad"] = ciudad
        target_grp["lider"] = lider
        target_grp["informacionCertificada"] = clean_text(str(data.get("informacionCertificada", "")))
        target_grp["paginaWeb"] = clean_text(str(data.get("paginaWeb", "")))
        target_grp["email"] = email
        target_grp["clasificacion"] = clean_text(str(data.get("clasificacion", "")))
        target_grp["areaConocimiento"] = clean_text(str(data.get("areaConocimiento", "")))
        target_grp["programaNacionalCti"] = clean_text(str(data.get("programaNacionalCti", "")))
        target_grp["programaNacionalCtiSecundario"] = clean_text(str(data.get("programaNacionalCtiSecundario", "")))
        target_grp["planEstrategico"] = clean_text(str(data.get("planEstrategico", "")))
        target_grp["estadoArte"] = clean_text(str(data.get("estadoArte", "")))
        target_grp["objetivos"] = clean_text(str(data.get("objetivos", "")))
        target_grp["retos"] = clean_text(str(data.get("retos", "")))
        if "vision" in data:
            target_grp["vision"] = clean_text(str(data.get("vision", "")))
        target_grp["instituciones"] = instituciones
        target_grp["lineasInvestigacion"] = list(data.get("lineasInvestigacion", []))
        target_grp["integrantes"] = integrantes
        target_grp["productos"] = list(data.get("productos", []))

        self._event("Grupo modificado: " + nombre)
        return True, "Grupo actualizado exitosamente."


# =========================================================================
# SERVIDOR API LOCAL (PUENTE HTTP 127.0.0.1:8765)
# =========================================================================

HOST = "127.0.0.1"
PORT = 8765


class PEARequestHandler(BaseHTTPRequestHandler):
    service: ApplicationService = None  # type: ignore

    def _send(self, status: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/health":
            self._send(200, json.dumps({"status": "ok", "service": "PEA-Scraper"}, ensure_ascii=False), "application/json")
        else:
            self._send(404, json.dumps({"status": "error", "message": "Ruta no encontrada."}, ensure_ascii=False), "application/json")

    def do_POST(self) -> None:
        route = self.path.split("?", 1)[0]
        if route == "/scraping":
            self._handle_scraping()
        elif route == "/cargar-archivo":
            self._handle_cargar_archivo()
        else:
            self._send(404, serialize_error("Ruta no encontrada."), "text/plain")

    def _handle_cargar_archivo(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(content_length)
        request = None
        request_error = ""
        try:
            request = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            request_error = "El cuerpo de la solicitud no contiene JSON válido."
        if request_error:
            self._send(200, serialize_error(request_error), "text/plain")
        elif not isinstance(request, dict):
            self._send(200, serialize_error("La solicitud JSON debe ser un objeto."), "text/plain")
        else:
            ruta = str(request.get("ruta", "")).strip()
            tipo_archivo = str(request.get("tipoArchivo", "")).strip().lower()
            if not ruta:
                self._send(200, serialize_error("Debe proporcionar la ruta del archivo."), "text/plain")
            elif not os.path.isfile(ruta):
                self._send(200, serialize_error("El archivo especificado no existe o no es accesible: " + ruta), "text/plain")
            else:
                if tipo_archivo == "pdf" or ruta.lower().endswith(".pdf"):
                    extractor = PDFExtractor()
                    ok, result, message = extractor.extract(ruta)
                    if ok:
                        payload = serialize_result(result)
                    else:
                        payload = serialize_error(message)
                    self._send(200, payload, "text/plain")
                elif tipo_archivo == "csv" or ruta.lower().endswith(".csv"):
                    extractor_csv = CSVExtractor()
                    ok, result, message = extractor_csv.extract(ruta)
                    if ok:
                        payload = serialize_result(result)
                    else:
                        payload = serialize_error(message)
                    self._send(200, payload, "text/plain")
                else:
                    self._send(200, serialize_error("Tipo de archivo no soportado en esta etapa."), "text/plain")

    def _handle_scraping(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(content_length)
        request = None
        request_error = ""
        try:
            request = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            request_error = "El cuerpo de la solicitud no contiene JSON válido."
        if request_error:
            self._send(200, serialize_error(request_error), "text/plain")
        elif not isinstance(request, dict):
            self._send(200, serialize_error("La solicitud JSON debe ser un objeto."), "text/plain")
        else:
            tipo = request.get("tipoBusqueda", "")
            url = request.get("url", "")
            valid = isinstance(tipo, str) and isinstance(url, str) and bool(tipo.strip()) and bool(url.strip())
            if not valid:
                self._send(200, serialize_error("La solicitud debe incluir tipoBusqueda y url."), "text/plain")
            else:
                ok, result, message = self.service.scrape_pure(tipo, url)
                if ok:
                    payload = serialize_result(result)
                else:
                    payload = serialize_error(message)
                self._send(200, payload, "text/plain")

    def log_message(self, format: str, *args: Any) -> None:
        pass


class LocalAPIServer:
    def __init__(self, service: ApplicationService, host: str = HOST, port: int = PORT) -> None:
        self.service = service
        self.server = ThreadingHTTPServer((host, port), PEARequestHandler)
        self.server.RequestHandlerClass.service = service

    def serve_forever(self) -> None:
        self.server.serve_forever()

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()


# =========================================================================
# INTERFAZ GRAFICA DE USUARIO (TKINTER / MODO CUBO)
# =========================================================================

BG = "#f4f6f8"
PANEL = "#ffffff"
DARK = "#17202a"
MUTED = "#697586"
ACCENT = "#2457a6"
PRIMARY = "#2457a6"
GREEN = "#2f855a"
RED = "#c53030"
BORDER = "#d9dee7"


class CubeView(tk.Frame):
    def __init__(self, master: tk.Misc, on_select, on_exit) -> None:
        super().__init__(master, bg=BG)
        self.on_select = on_select
        self.on_exit = on_exit
        self.faces = [
            ("Inicio", "Dashboard principal"),
            ("Investigadores", "Gestión de investigadores"),
            ("Grupos", "Grupos de Investigación"),
            ("Carga de Datos", "CvLAC y GrupLAC"),
            ("Estadísticas", "Indicadores y gráficos"),
            ("Reportes / Análisis", "Consultas y reportes")
        ]
        self.rotation_x = -0.28
        self.rotation_y = 0.55
        self.scale = 1.0
        self.drag_start: Optional[Tuple[int, int]] = None
        self.click_pos: Optional[Tuple[int, int]] = None
        self.drag_distance: float = 0.0
        self.hovered_face: Optional[int] = None
        self.rendered_faces: List[Tuple[float, int, List[Tuple[float, float]], Tuple[float, float, float, float]]] = []

        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=20, pady=(10, 55))

        self.controls_bar = tk.Frame(self, bg=BG)
        self.controls_bar.place(relx=0.5, rely=0.95, anchor="center")

        self.btn_open_front = ttk.Button(
            self.controls_bar,
            text="Abrir módulo frontal",
            command=self._open_front_face
        )
        self.btn_open_front.pack(side="left", padx=8)

        self.btn_exit = ttk.Button(
            self.controls_bar,
            text="Volver a la interfaz normal (ESC)",
            command=self._handle_exit
        )
        self.btn_exit.pack(side="left", padx=8)

        self.canvas.bind("<Configure>", lambda event: self.draw())
        self.canvas.bind("<ButtonPress-1>", self.begin_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Button-4>", lambda event: self.zoom(1))
        self.canvas.bind("<Button-5>", lambda event: self.zoom(-1))
        self.keys_pressed = set()
        
        self.canvas.bind("<KeyPress-Left>", lambda event: self._on_key_press("Left"))
        self.canvas.bind("<KeyRelease-Left>", lambda event: self._on_key_release("Left"))
        self.canvas.bind("<KeyPress-Right>", lambda event: self._on_key_press("Right"))
        self.canvas.bind("<KeyRelease-Right>", lambda event: self._on_key_release("Right"))
        self.canvas.bind("<KeyPress-Up>", lambda event: self._on_key_press("Up"))
        self.canvas.bind("<KeyRelease-Up>", lambda event: self._on_key_release("Up"))
        self.canvas.bind("<KeyPress-Down>", lambda event: self._on_key_press("Down"))
        self.canvas.bind("<KeyRelease-Down>", lambda event: self._on_key_release("Down"))
        self.canvas.bind("<Return>", lambda event: self._open_front_face())
        
        self.canvas.focus_set()
        self.after(60, self.draw)

    def _on_key_press(self, key: str) -> None:
        if key not in self.keys_pressed:
            self.keys_pressed.add(key)
            if len(self.keys_pressed) == 1:
                self._process_keys()

    def _on_key_release(self, key: str) -> None:
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)

    def _process_keys(self) -> None:
        dyaw = 0.0
        dpitch = 0.0
        if "Left" in self.keys_pressed:
            dyaw += 0.10
        if "Right" in self.keys_pressed:
            dyaw -= 0.10
        if "Up" in self.keys_pressed:
            dpitch -= 0.10
        if "Down" in self.keys_pressed:
            dpitch += 0.10

        if dyaw != 0.0 or dpitch != 0.0:
            self.rotate(dyaw, dpitch)
            self.after(30, self._process_keys)


    def _handle_exit(self) -> None:
        if callable(self.on_exit):
            self.on_exit()

    def _handle_select(self, face_idx: int) -> None:
        if 0 <= face_idx < len(self.faces) and callable(self.on_select):
            self.on_select(self.faces[face_idx][0])

    def _open_front_face(self) -> None:
        if getattr(self, "hovered_face", None) is not None:
            self._handle_select(self.hovered_face)
        else:
            nearest = self._nearest_face()
            if nearest is not None:
                self._handle_select(nearest[0])

    def begin_drag(self, event) -> None:
        self.drag_start = (event.x, event.y)
        self.click_pos = (event.x, event.y)
        self.drag_distance = 0.0

    def drag(self, event) -> None:
        if self.drag_start is not None:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.drag_distance += abs(dx) + abs(dy)
            self.rotate(dx * 0.01, -dy * 0.01)
            self.drag_start = (event.x, event.y)

    def end_drag(self, event) -> None:
        # If total mouse movement was minimal, consider this a face click
        handled = False
        if self.click_pos is not None and self.drag_distance < 10:
            face_idx = self._face_at_point(event.x, event.y)
            if face_idx is not None:
                self._handle_select(face_idx)
                handled = True
        if not handled:
            self.drag_start = None
            self.click_pos = None

    def on_motion(self, event) -> None:
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        if self.drag_start is None:
            face_idx = self._face_at_point(event.x, event.y)
            if face_idx != self.hovered_face:
                self.hovered_face = face_idx
                if face_idx is not None:
                    self.canvas.config(cursor="hand2")
                else:
                    self.canvas.config(cursor="")
                self.draw()

    def on_leave(self, event) -> None:
        self.last_mouse_x = None
        self.last_mouse_y = None
        if self.hovered_face is not None:
            self.hovered_face = None
            self.canvas.config(cursor="")
            self.draw()

    def wheel(self, event) -> None:
        if event.delta > 0:
            direction = 1
        else:
            direction = -1
        self.zoom(direction)

    def zoom(self, direction: int) -> None:
        self.scale += 0.08 * direction
        if self.scale < 0.7:
            self.scale = 0.7
        if self.scale > 1.35:
            self.scale = 1.35
        self.draw()

    def rotate(self, dyaw: float, dpitch: float) -> None:
        if math.cos(self.rotation_x) < 0:
            dyaw = -dyaw
        self.rotation_y += dyaw
        self.rotation_x += dpitch
        self.draw()

    @staticmethod
    def _point_in_polygon(x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
        n = len(poly)
        inside = False
        p1x, p1y = poly[0]
        for i in range(1, n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def _face_at_point(self, x: float, y: float) -> Optional[int]:
        # Iterate in reverse Painter's order (closest faces tested first)
        for avg_z, index, polygon, _ in reversed(self.rendered_faces):
            if avg_z > -0.05 and self._point_in_polygon(x, y, polygon):
                return index
        return None

    def _nearest_face(self):
        face_defs = [
            (0, [(0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, -0.5, 0.5)]),
            (1, [(0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5)]),
            (2, [(-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5)]),
            (3, [(0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5)]),
            (4, [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (-0.5, -0.5, -0.5)]),
            (5, [(-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5)])
        ]
        best = None
        for index, vertices in face_defs:
            rotated = [self._rotate_point(v) for v in vertices]
            z = sum(point[2] for point in rotated) / 4.0
            if best is None or z > best[1]:
                best = (index, z)
        return best

    def _rotate_point(self, point: Tuple[float, float, float]) -> Tuple[float, float, float]:
        x, y, z = point
        cy = math.cos(self.rotation_y)
        sy = math.sin(self.rotation_y)
        x1 = x * cy + z * sy
        z1 = -x * sy + z * cy
        cx = math.cos(self.rotation_x)
        sx = math.sin(self.rotation_x)
        y2 = y * cx - z1 * sx
        z2 = y * sx + z1 * cx
        return x1, y2, z2

    def _project(self, point: Tuple[float, float, float], width: int, height: int) -> Tuple[float, float, float]:
        x, y, z = self._rotate_point(point)
        focal = 3.2
        depth = focal / max(0.7, focal - z)
        screen_x = width / 2 + x * 310 * depth * self.scale
        screen_y = height / 2 + y * 310 * depth * self.scale
        return screen_x, screen_y, z

    def draw(self) -> None:
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 520)
        self.canvas.delete("all")
        face_defs = [
            (0, [(0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, -0.5, 0.5)]),
            (1, [(0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5)]),
            (2, [(-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5)]),
            (3, [(0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5)]),
            (4, [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (-0.5, -0.5, -0.5)]),
            (5, [(-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5)])
        ]
        render: List[Tuple[float, int, List[Tuple[float, float]], Tuple[float, float, float, float]]] = []
        palette = ["#d7e7ff", "#dce9dc", "#f4e4c6", "#eadcf7", "#f1d9df", "#d9edef"]
        hover_palette = ["#bcd7ff", "#c7e3c7", "#f6dcab", "#dfcbf5", "#f0c2cd", "#c5e6e8"]
        for index, vertices in face_defs:
            projected = [self._project(vertex, width, height) for vertex in vertices]
            avg_z = sum(point[2] for point in projected) / 4.0
            polygon = [(point[0], point[1]) for point in projected]
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            center = (sum(xs) / 4.0, sum(ys) / 4.0)
            render.append((avg_z, index, polygon, (center[0], center[1], sum(xs) / 4.0, sum(ys) / 4.0)))
        render.sort(key=lambda item: item[0])
        self.rendered_faces = render

        if getattr(self, "last_mouse_x", None) is not None and getattr(self, "last_mouse_y", None) is not None:
            if getattr(self, "drag_start", None) is None:
                new_hover = self._face_at_point(self.last_mouse_x, self.last_mouse_y)
                if new_hover != getattr(self, "hovered_face", None):
                    self.hovered_face = new_hover
                    if self.hovered_face is not None:
                        self.canvas.config(cursor="hand2")
                    else:
                        self.canvas.config(cursor="")

        for avg_z, index, polygon, center_info in render:
            is_hovered = (index == self.hovered_face)
            if is_hovered:
                fill_color = hover_palette[index]
            else:
                fill_color = palette[index]
            if is_hovered:
                outline_color = PRIMARY
            else:
                outline_color = "#5b6573"
            if is_hovered:
                outline_width = 3
            else:
                outline_width = 2
            self.canvas.create_polygon(polygon, fill=fill_color, outline=outline_color, width=outline_width)
            if avg_z > -0.05:
                center_x, center_y, _, _ = center_info
                title, subtitle = self.faces[index]
                if is_hovered:
                    text_color = PRIMARY
                else:
                    text_color = DARK
                self.canvas.create_text(center_x, center_y - 12, text=title, fill=text_color, font=("Segoe UI", 18, "bold"))
                self.canvas.create_text(center_x, center_y + 16, text=subtitle, fill=MUTED, font=("Segoe UI", 9))

        nearest = self._nearest_face()
        if getattr(self, "hovered_face", None) is not None:
            hov_title, hov_sub = self.faces[self.hovered_face]
            top_heading = f"▶ Clic para abrir módulo: {hov_title}"
            sub_heading = f"{hov_sub} (haz clic directamente sobre la cara para entrar)"
            head_color = PRIMARY
            if hasattr(self, "btn_open_front"):
                self.btn_open_front.configure(text=f"Abrir módulo: {hov_title}")
        elif nearest is not None:
            front_title, front_sub = self.faces[nearest[0]]
            top_heading = f"Módulo frontal: {front_title}"
            sub_heading = f"{front_sub} · Haz clic en cualquier cara para abrirla · Arrastra para rotar"
            head_color = DARK
            if hasattr(self, "btn_open_front"):
                self.btn_open_front.configure(text=f"Abrir módulo: {front_title}")
        else:
            top_heading = "Navegación 3D de Módulos"
            sub_heading = "Haz clic en cualquier cara para abrirla · Arrastra para rotar · Rueda para zoom"
            head_color = DARK

        self.canvas.create_text(width / 2, 34, text=top_heading, fill=head_color, font=("Segoe UI", 18, "bold"))
        self.canvas.create_text(width / 2, 60, text=sub_heading, fill=MUTED, font=("Segoe UI", 10))


class PEAApp(tk.Tk):
    def __init__(self, service: ApplicationService) -> None:
        super().__init__()
        self.service = service
        self.title("PEA-i Programa Estadístico de Análisis de Investigacion")
        self.geometry("1250x760")
        self.update_idletasks()
        x_pos = (self.winfo_screenwidth() - 1250) // 2
        y_pos = (self.winfo_screenheight() - 760) // 2
        self.geometry(f"1250x760+{x_pos}+{y_pos}")
        self.state('zoomed')
        self.minsize(1050, 680)
        self.configure(bg=BG)
        self.current_view = "Inicio"
        self.previous_view = "Inicio"
        self.view_history: List[str] = []
        self.content: Optional[tk.Frame] = None
        self.status = tk.StringVar(value="Sistema listo")
        self.nav_frame = None
        self.in_cube_mode = False
        self.was_nav_visible_before_cube = False
        self.main_investigator_tree: Optional[ttk.Treeview] = None
        self.main_group_tree: Optional[ttk.Treeview] = None
        self._configure_styles()
        self._build_shell()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Escape>", self.toggle_cube)
        self.bind("<Control-q>", lambda e: self.on_close())
        self.bind("<Control-Q>", lambda e: self.on_close())
        self.show_view("Inicio")

    def on_close(self) -> None:
        self.destroy()
        sys.exit(0)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        style.configure("TLabel", background=BG, foreground=DARK, font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_shell(self) -> None:
        self.top_frame = tk.Frame(self, bg=PANEL, height=68, highlightbackground=BORDER, highlightthickness=1)
        self.top_frame.pack(fill="x")
        self.menu_button = ttk.Button(self.top_frame, text="☰", width=4, command=self.toggle_nav)
        self.menu_button.pack(side="left", padx=14, pady=12)
        self.back_button = ttk.Button(self.top_frame, text="← Regresar", command=self.go_back, state="disabled")
        self.back_button.pack(side="left", padx=(0, 10))
        self.cube_button = ttk.Button(self.top_frame, text="◇ Menú Interactivo (ESC)", command=self.show_cube)
        self.cube_button.pack(side="left", padx=(0, 14))
        self.title_label = tk.Label(self.top_frame, text="PEA-i Programa Estadístico de Análisis de Investigacion", bg=PANEL, fg=DARK, font=("Segoe UI", 15, "bold"))
        self.title_label.pack(side="left")
        self.subtitle_label = tk.Label(self.top_frame, text="Gestión y Análisis de Información de Investigación", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.subtitle_label.pack(side="left", padx=12, pady=(17, 0))
        self.close_button = ttk.Button(self.top_frame, text="⏻ (CTRL + Q)", command=self.on_close)
        self.close_button.pack(side="right", padx=14)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        self.nav_frame = tk.Frame(body, bg="#202a36", width=215)
        self.nav_visible = False
        self._build_nav()
        self.main_frame = tk.Frame(body, bg=BG)
        self.main_frame.pack(side="right", fill="both", expand=True)

        self.bottom_frame = tk.Frame(self, bg=PANEL, height=48, highlightbackground=BORDER, highlightthickness=1)
        self.bottom_frame.pack(fill="x")
        ttk.Button(self.bottom_frame, text="💾 Guardar datos", command=self.save_data).pack(side="left", padx=14, pady=7)
        tk.Label(self.bottom_frame, textvariable=self.status, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=18)

    def _build_nav(self) -> None:
        tk.Label(self.nav_frame, text="MÓDULOS", bg="#202a36", fg="#cfd7e3", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=22, pady=(25, 12))
        options = ["Inicio", "Investigadores", "Grupos", "Carga de Datos", "Estadísticas", "Reportes / Análisis"]
        for option in options:
            button = tk.Button(self.nav_frame, text=option, bg="#202a36", fg="#edf2f7", activebackground="#314154", activeforeground="#ffffff", bd=0, anchor="w", font=("Segoe UI", 10), padx=22, pady=11, command=lambda name=option: self.show_view(name))
            button.pack(fill="x")

    def toggle_nav(self) -> None:
        if not getattr(self, "in_cube_mode", False):
            if self.nav_visible:
                self.nav_frame.pack_forget()
                self.nav_visible = False
            else:
                self.nav_frame.pack(side="left", fill="y", before=self.main_frame)
                self.nav_visible = True

    def clear_content(self) -> None:
        if self.content is not None:
            self.content.destroy()
        self.content = tk.Frame(self.main_frame, bg=BG)
        self.content.pack(fill="both", expand=True, padx=28, pady=24)

    def go_back(self) -> None:
        if len(self.view_history) > 0:
            previous_target = self.view_history.pop()
            self.show_view(previous_target, is_back=True)
        else:
            if getattr(self, "current_view", "Inicio") != "Inicio":
                self.show_view("Inicio", is_back=True)

    def show_view(self, name: str, is_back: bool = False) -> None:
        if getattr(self, "in_cube_mode", False):
            self.in_cube_mode = False
            if hasattr(self, "menu_button") and not self.menu_button.winfo_ismapped():
                self.menu_button.pack(side="left", padx=14, pady=12, before=self.title_label)
            if hasattr(self, "back_button") and not self.back_button.winfo_ismapped():
                self.back_button.pack(side="left", padx=(0, 10), after=self.menu_button)
            if hasattr(self, "cube_button") and not self.cube_button.winfo_ismapped():
                self.cube_button.pack(side="left", padx=(0, 14), after=self.back_button)
            if hasattr(self, "bottom_frame") and not self.bottom_frame.winfo_ismapped():
                self.bottom_frame.pack(fill="x")
            if getattr(self, "was_nav_visible_before_cube", True):
                if not self.nav_visible:
                    self.nav_frame.pack(side="left", fill="y", before=self.main_frame)
                    self.nav_visible = True
            else:
                if self.nav_visible:
                    self.nav_frame.pack_forget()
                    self.nav_visible = False

        if not is_back:
            cur = getattr(self, "current_view", None)
            if cur is not None and cur != name:
                self.view_history.append(cur)

        self.current_view = name
        if hasattr(self, "back_button"):
            if len(self.view_history) > 0:
                self.back_button.configure(state="normal")
            else:
                self.back_button.configure(state="disabled")

        self.clear_content()
        if name == "Inicio":
            self.build_dashboard()
        elif name == "Investigadores":
            self.build_investigators()
        elif name == "Grupos":
            self.build_groups()
        elif name == "Carga de Datos":
            self.build_loading()
        elif name == "Estadísticas":
            self.build_statistics()
        elif name == "Reportes / Análisis":
            self.build_reports()

    def toggle_cube(self, event=None) -> None:
        if event is not None and hasattr(event, 'widget'):
            w_class = getattr(event.widget, 'winfo_class', lambda: '')()
            if w_class in ('TCombobox', 'Combobox', 'Entry', 'TEntry', 'Listbox'):
                return
        if getattr(self, "in_cube_mode", False):
            self.exit_cube()
        else:
            self.show_cube()

    def show_cube(self) -> None:
        if not getattr(self, "in_cube_mode", False):
            self.in_cube_mode = True
            self.previous_view = self.current_view or "Inicio"
            self.was_nav_visible_before_cube = self.nav_visible

            # Hide left navigation module list
            if self.nav_visible:
                self.nav_frame.pack_forget()
                self.nav_visible = False

            # Hide top bar "Modo Cubo" button, back button, and menu button
            if hasattr(self, "cube_button") and self.cube_button.winfo_ismapped():
                self.cube_button.pack_forget()
            if hasattr(self, "back_button") and self.back_button.winfo_ismapped():
                self.back_button.pack_forget()
            if hasattr(self, "menu_button") and self.menu_button.winfo_ismapped():
                self.menu_button.pack_forget()

            # Hide bottom bar for distraction-free 3D cube view
            if hasattr(self, "bottom_frame") and self.bottom_frame.winfo_ismapped():
                self.bottom_frame.pack_forget()

            self.clear_content()
            cube = CubeView(self.content, on_select=self.open_cube_module, on_exit=self.exit_cube)
            cube.pack(fill="both", expand=True)

    def exit_cube(self, target_view: Optional[str] = None) -> None:
        if not getattr(self, "in_cube_mode", False):
            if target_view:
                self.show_view(target_view)
        else:
            self.in_cube_mode = False

            # Restore top bar buttons
            if hasattr(self, "menu_button") and not self.menu_button.winfo_ismapped():
                self.menu_button.pack(side="left", padx=14, pady=12, before=self.title_label)
            if hasattr(self, "back_button") and not self.back_button.winfo_ismapped():
                self.back_button.pack(side="left", padx=(0, 10), after=self.menu_button)
            if hasattr(self, "cube_button") and not self.cube_button.winfo_ismapped():
                self.cube_button.pack(side="left", padx=(0, 14), after=self.back_button)

            # Restore bottom bar
            if hasattr(self, "bottom_frame") and not self.bottom_frame.winfo_ismapped():
                self.bottom_frame.pack(fill="x")

            # Restore left navigation menu only if it was open prior to entering cube mode
            if getattr(self, "was_nav_visible_before_cube", True):
                if not self.nav_visible:
                    self.nav_frame.pack(side="left", fill="y", before=self.main_frame)
                    self.nav_visible = True
            else:
                if self.nav_visible:
                    self.nav_frame.pack_forget()
                    self.nav_visible = False

            dest = target_view or getattr(self, "previous_view", "Inicio") or "Inicio"
            self.show_view(dest)

    def open_cube_module(self, module: str) -> None:
        self.exit_cube(target_view=module)

    def heading(self, title: str, subtitle: str) -> None:
        tk.Label(self.content, text=title, bg=BG, fg=DARK, font=("Segoe UI", 26, "bold")).pack(anchor="w")
        tk.Label(self.content, text=subtitle, bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 18))

    def card(self, parent: tk.Misc, title: str, value: str, note: str = "", command: Optional[Any] = None) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        if command:
            frame.configure(cursor="hand2")
            frame.bind("<Button-1>", lambda e: command())
            
        lbl_title = tk.Label(frame, text=title.upper(), bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        lbl_title.pack(anchor="w", padx=16, pady=(14, 3))
        lbl_val = tk.Label(frame, text=value, bg=PANEL, fg=DARK, font=("Segoe UI", 26, "bold"))
        lbl_val.pack(anchor="w", padx=16)
        
        if note:
            lbl_note = tk.Label(frame, text=note, bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
            lbl_note.pack(anchor="w", padx=16, pady=(1, 14))
        else:
            frame.configure(pady=10)
            lbl_note = None
            
        if command:
            lbl_title.bind("<Button-1>", lambda e: command())
            lbl_val.bind("<Button-1>", lambda e: command())
            if lbl_note:
                lbl_note.bind("<Button-1>", lambda e: command())
                
        return frame

    def build_dashboard(self) -> None:
        self.heading("Dashboard", "Visión general de grupos de investigación e investigadores institucionales")
        stats = self.service.statistics()

        total_inv = stats["investigadores"]
        active_inv = stats["investigadores_activos"]
        if total_inv:
            inv_note = f"{active_inv} activos"
        else:
            inv_note = "registrados"
        total_groups = stats["grupos"]
        total_products = stats["productos"]
        total_members = sum(len(g.get("integrantes", [])) for g in self.service.grupos)
        if total_groups:
            members_note = "en grupos"
        else:
            members_note = "vinculaciones"

        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x")
        kpis = [
            ("Investigadores", str(total_inv), inv_note, lambda: self.show_view("Investigadores")),
            ("Grupos de Investigación", str(total_groups), "unidades cargadas", lambda: self.show_view("Grupos")),
            ("Producción Científica", str(total_products), "productos únicos", None),
            ("Integrantes Vinculados", str(total_members), members_note, None)
        ]
        for index, (title, value, note, cmd) in enumerate(kpis):
            card = self.card(cards, title, value, note, cmd)
            if index == 0:
                left_pad = 0
            else:
                left_pad = 8
            if index == len(kpis) - 1:
                right_pad = 0
            else:
                right_pad = 8
            card.grid(row=0, column=index, sticky="nsew", padx=(left_pad, right_pad))
            cards.grid_columnconfigure(index, weight=1)

        lower = tk.Frame(self.content, bg=BG)
        lower.pack(fill="both", expand=True, pady=18)

        # Panel Izquierdo: Panorama de Grupos de Investigación
        groups_frame = tk.Frame(lower, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        groups_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(groups_frame, text="Grupos de Investigación Registrados", bg=PANEL, fg=DARK, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(16, 2))
        tk.Label(groups_frame, text="Unidades académicas, clasificación Minciencias y líderes", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 10))

        if not self.service.grupos:
            empty_grp = tk.Frame(groups_frame, bg="#fbfcfe", highlightbackground=BORDER, highlightthickness=1)
            empty_grp.pack(fill="both", expand=True, padx=16, pady=12)
            tk.Label(empty_grp, text="No hay grupos de investigación registrados en el sistema.", bg="#fbfcfe", fg=MUTED, font=("Segoe UI", 10)).pack(pady=(35, 6))
            tk.Label(empty_grp, text="Puedes importar grupos y sus integrantes desde el módulo de carga.", bg="#fbfcfe", fg=MUTED, font=("Segoe UI", 9)).pack(pady=(0, 14))
            ttk.Button(empty_grp, text="Ir a Carga de Datos (GrupLAC)", command=lambda: self.show_view("Carga de Datos")).pack(pady=(0, 30))
        else:
            tree_container = tk.Frame(groups_frame, bg=PANEL)
            tree_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

            grp_tree = ttk.Treeview(tree_container, columns=("nombre", "clasif", "lider", "integrantes", "productos"), show="headings", height=7)
            sb = ttk.Scrollbar(tree_container, orient="vertical", command=grp_tree.yview)
            grp_tree.configure(yscrollcommand=sb.set)

            grp_tree.heading("nombre", text="Nombre del Grupo")
            grp_tree.column("nombre", width=220, anchor="w")
            grp_tree.heading("clasif", text="Clasif.")
            grp_tree.column("clasif", width=65, anchor="center")
            grp_tree.heading("lider", text="Líder")
            grp_tree.column("lider", width=160, anchor="w")
            grp_tree.heading("integrantes", text="Integrantes")
            grp_tree.column("integrantes", width=75, anchor="center")
            grp_tree.heading("productos", text="Productos")
            grp_tree.column("productos", width=75, anchor="center")

            grp_tree.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")

            clasif_counts: Dict[str, int] = {}
            for g in self.service.grupos:
                c = g.get("clasificacion", "").strip() or "Sin clasificación"
                clasif_counts[c] = clasif_counts.get(c, 0) + 1
                grp_tree.insert("", "end", values=(
                    g.get("nombreGrupo", "Sin nombre"),
                    g.get("clasificacion", "") or "S/C",
                    g.get("lider", "No especificado"),
                    len(g.get("integrantes", [])),
                    len(g.get("productos", []))
                ))

            grp_tree.bind("<Double-1>", lambda event: self.show_view("Grupos"))

            footer_grp = tk.Frame(groups_frame, bg=PANEL)
            footer_grp.pack(fill="x", padx=16, pady=(0, 12))

            clasif_parts = [f"{k}: {v}" for k, v in sorted(clasif_counts.items(), key=lambda x: str(x[0]))]
            if clasif_parts:
                clasif_str = "Clasificaciones: " + " · ".join(clasif_parts)
            else:
                clasif_str = "Clasificaciones: N/A"
            tk.Label(footer_grp, text=clasif_str, bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left")
            ttk.Button(footer_grp, text="Ver módulo Grupos", command=lambda: self.show_view("Grupos")).pack(side="right")

        # Panel Derecho: Contenedor con Scroll para Investigadores y Repositorio
        right_container = tk.Frame(lower, bg=BG, width=350)
        right_container.pack(side="right", fill="both")
        right_container.pack_propagate(False)

        right_canvas = tk.Canvas(right_container, bg=BG, highlightthickness=0)
        right_scroll = ttk.Scrollbar(right_container, orient="vertical")

        def _custom_right_yview(*args) -> None:
            try:
                fits = False
                bbox = right_canvas.bbox("all")
                if bbox:
                    content_h = bbox[3] - bbox[1]
                    canv_h = right_canvas.winfo_height()
                    if content_h <= canv_h:
                        right_canvas.yview_moveto(0.0)
                        fits = True
                if not fits:
                    right_canvas.yview(*args)
                    y0, y1 = right_canvas.yview()
                    if y0 < 0.0:
                        right_canvas.yview_moveto(0.0)
                    elif y1 > 1.0:
                        right_canvas.yview_moveto(max(0.0, 1.0 - (y1 - y0)))
            except Exception:
                pass

        right_scroll.configure(command=_custom_right_yview)
        scrollable_right = tk.Frame(right_canvas, bg=BG)
        window_id = right_canvas.create_window((0, 0), window=scrollable_right, anchor="nw")

        right_scroll.pack(side="right", fill="y")
        right_canvas.pack(side="left", fill="both", expand=True)

        def _update_right_scroll_bounds(event=None) -> None:
            try:
                canv_w = right_canvas.winfo_width()
                canv_h = right_canvas.winfo_height()
                if canv_w > 1 and canv_h > 1:
                    right_canvas.itemconfig(window_id, width=canv_w)
                    bbox = right_canvas.bbox("all")
                    if bbox:
                        content_h = max(bbox[3] - bbox[1], 1)
                        eff_h = max(canv_h, content_h)
                        right_canvas.configure(scrollregion=(0, 0, canv_w, eff_h))
                        if content_h <= canv_h:
                            right_canvas.yview_moveto(0.0)
                            if right_scroll.winfo_ismapped():
                                right_scroll.pack_forget()
                        else:
                            if not right_scroll.winfo_ismapped():
                                right_scroll.pack(side="right", fill="y", before=right_canvas)
            except Exception:
                pass

        scrollable_right.bind("<Configure>", _update_right_scroll_bounds)
        right_canvas.bind("<Configure>", _update_right_scroll_bounds)
        right_canvas.configure(yscrollcommand=right_scroll.set)

        def _on_mousewheel(event) -> None:
            try:
                bbox = right_canvas.bbox("all")
                if bbox:
                    content_h = bbox[3] - bbox[1]
                    canv_h = right_canvas.winfo_height()
                    if content_h <= canv_h:
                        right_canvas.yview_moveto(0.0)
                    else:
                        if hasattr(event, "delta") and event.delta:
                            delta = int(-1 * (event.delta / 120))
                        else:
                            delta = 0
                        if delta != 0:
                            y0, y1 = right_canvas.yview()
                            if delta < 0 and y0 <= 0.0:
                                right_canvas.yview_moveto(0.0)
                            elif not (delta > 0 and y1 >= 1.0):
                                right_canvas.yview_scroll(delta, "units")
                                y0_n, y1_n = right_canvas.yview()
                                if y0_n < 0.0:
                                    right_canvas.yview_moveto(0.0)
                                elif y1_n > 1.0:
                                    right_canvas.yview_moveto(max(0.0, 1.0 - (y1_n - y0_n)))
            except Exception:
                pass

        def _bind_mouse(event=None) -> None:
            right_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mouse(event=None) -> None:
            try:
                right_canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass

        right_canvas.bind("<Enter>", _bind_mouse)
        right_canvas.bind("<Leave>", _unbind_mouse)
        scrollable_right.bind("<Enter>", _bind_mouse)
        scrollable_right.bind("<Leave>", _unbind_mouse)

        inv_panel = tk.Frame(scrollable_right, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        inv_panel.pack(fill="x", pady=(0, 10))

        tk.Label(inv_panel, text="Investigadores por Nivel", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(inv_panel, text="Categorización reconocida en Minciencias", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(0, 8))

        if not self.service.investigadores:
            tk.Label(inv_panel, text="No hay investigadores registrados.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(padx=16, pady=8)
            ttk.Button(inv_panel, text="Cargar desde CvLAC", command=lambda: self.show_view("Carga de Datos")).pack(padx=16, pady=(0, 12))
        else:
            cat_map = {
                "Investigador Emérito": 0,
                "Investigador Sénior": 0,
                "Investigador Asociado": 0,
                "Investigador Junior": 0,
                "En formación / Sin categoría": 0,
            }
            for inv in self.service.investigadores:
                cat_raw = inv.get("categoriaInvestigador", "").lower()
                if "emérito" in cat_raw or "emerito" in cat_raw:
                    cat_map["Investigador Emérito"] += 1
                elif "sénior" in cat_raw or "senior" in cat_raw:
                    cat_map["Investigador Sénior"] += 1
                elif "asociado" in cat_raw:
                    cat_map["Investigador Asociado"] += 1
                elif "junior" in cat_raw:
                    cat_map["Investigador Junior"] += 1
                else:
                    cat_map["En formación / Sin categoría"] += 1

            for cat_name, count in cat_map.items():
                row = tk.Frame(inv_panel, bg=PANEL)
                row.pack(fill="x", padx=16, pady=2)
                tk.Label(row, text=cat_name, bg=PANEL, fg=DARK, font=("Segoe UI", 9)).pack(side="left")
                if count > 0:
                    fg_col = PRIMARY
                else:
                    fg_col = MUTED
                tk.Label(row, text=str(count), bg=PANEL, fg=fg_col, font=("Segoe UI", 9, "bold")).pack(side="right")

            activos_cnt = stats["investigadores_activos"]
            tot_cnt = stats["investigadores"]
            if tot_cnt:
                pct_act = int(round(100 * activos_cnt / tot_cnt))
            else:
                pct_act = 0
            tk.Label(inv_panel, text=f"Actividad: {activos_cnt} de {tot_cnt} investigadores activos ({pct_act}%)", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(8, 8))
            ttk.Button(inv_panel, text="Ver módulo Investigadores", command=lambda: self.show_view("Investigadores")).pack(fill="x", padx=16, pady=(0, 10))

        repo_panel = tk.Frame(scrollable_right, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        repo_panel.pack(fill="x", pady=(0, 4))

        tk.Label(repo_panel, text="Gestión del Repositorio", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 2))

        last = self.service.last_saved or "Aún no se ha guardado en esta sesión"
        tk.Label(repo_panel, text="Último guardado en disco:", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=16, pady=(4, 1))
        tk.Label(repo_panel, text=last, bg=PANEL, fg=DARK, font=("Segoe UI", 8), wraplength=270, justify="left").pack(anchor="w", padx=16, pady=(0, 8))

        quick_btns = tk.Frame(repo_panel, bg=PANEL)
        quick_btns.pack(fill="x", padx=16, pady=(0, 10))
        ttk.Button(quick_btns, text="💾 Guardar datos", command=self.save_data).pack(fill="x", pady=2)
        ttk.Button(quick_btns, text="+ Incorporar datos", command=lambda: self.show_view("Carga de Datos")).pack(fill="x", pady=2)
        ttk.Button(quick_btns, text="📊 Explorar estadísticas", command=lambda: self.show_view("Estadísticas")).pack(fill="x", pady=2)

        def _attach_scroll(widget: tk.Misc) -> None:
            widget.bind("<Enter>", _bind_mouse, add="+")
            widget.bind("<Leave>", _unbind_mouse, add="+")
            for child in widget.winfo_children():
                _attach_scroll(child)

        _attach_scroll(scrollable_right)

    def build_investigators(self) -> None:
        self.heading("Investigadores", "Consulta y gestión de investigadores cargados desde CvLAC")
        bar = tk.Frame(self.content, bg=BG)
        bar.pack(fill="x", pady=(0, 10))
        entry = ttk.Entry(bar)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        entry.insert(0, "")
        ttk.Button(bar, text="Buscar", command=lambda: self.refresh_investigator_tree(tree, entry.get())).pack(side="left")
        ttk.Button(bar, text="Ver detalle", command=lambda: self.show_investigator_detail(tree)).pack(side="left", padx=8)
        ttk.Button(bar, text="Activar / desactivar", command=lambda: self.toggle_selected_investigator(tree)).pack(side="left")
        ttk.Button(bar, text="🗑️ Eliminar Investigador", command=lambda: self.delete_selected_investigator(tree)).pack(side="left", padx=8)
        ttk.Button(bar, text="+ Crear Investigador", command=lambda: self.open_create_investigator_dialog(tree)).pack(side="left")
        tree = self._create_tree(self.content, [("codigo", "Código RH", 120), ("nombre", "Nombre", 280), ("categoria", "Categoría", 220), ("nacionalidad", "Nacionalidad", 140), ("estado", "Estado", 100)])
        self.main_investigator_tree = tree
        entry.bind("<Return>", lambda event: self.refresh_investigator_tree(tree, entry.get()))
        tree.bind("<Double-1>", lambda event: self.show_investigator_detail(tree))
        self.refresh_investigator_tree(tree, "")

    def _create_tree(self, parent: tk.Misc, columns: List[Tuple[str, str, int]]) -> ttk.Treeview:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=[column[0] for column in columns], show="headings")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree

    def get_product_category(self, prod: Dict[str, Any]) -> str:
        cat_raw = prod.get("categoria", "")
        if not cat_raw:
            cat_raw = prod.get("tipoProducto", "")
        if not cat_raw:
            cat_raw = "Sin categoría"
        cat = str(cat_raw).strip()
        
        parts = cat.split()
        if parts:
            w = parts[0].lower().strip()
            w = w.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            if w.endswith("es") and len(w) > 3:
                w = w[:-2]
            elif w.endswith("s") and len(w) > 2:
                w = w[:-1]
            first_word = w
        else:
            first_word = "sin"
            
        if not hasattr(self, "cat_canonical_map"):
            self.cat_canonical_map = {}
            
        if first_word not in self.cat_canonical_map:
            self.cat_canonical_map[first_word] = cat
            
        return self.cat_canonical_map[first_word]

    def get_product_subtype(self, prod: Dict[str, Any]) -> str:
        sub_raw = prod.get("subtipo", "")
        if not sub_raw:
            sub_raw = prod.get("tipoProducto", "")
        if not sub_raw:
            return "Sin subtipo"
            
        sub = str(sub_raw).strip()
        low = sub.lower()
        
        if low.startswith("tipo:"):
            sub = sub[5:].strip()
            low = sub.lower()
            
        if low.startswith("otro ") or low.startswith("otra ") or low.startswith("otros ") or low.startswith("otras "):
            idx = sub.find(" ")
            if idx != -1:
                sub = sub[idx+1:].strip()
                low = sub.lower()
                
        if "capítulo" in low or "capitulo" in low:
            return "Capítulo de libro"
        elif "libro" in low:
            return "Libro"
        elif "artículo" in low or "articulo" in low:
            return "Artículo"
        elif "documento de trabajo" in low or "working paper" in low:
            return "Documento de trabajo"
        elif "consultoría" in low or "consultoria" in low:
            return "Consultoría"
        elif "software" in low:
            return "Software"
        elif "curso" in low:
            return "Curso de corta duración"
        elif "informe" in low:
            return "Informe de investigación"
        elif "manual" in low or "guía" in low or "guia" in low:
            return "Manuales y Guías"
            
        if len(sub) > 45:
            words = sub.split()
            if len(words) > 4:
                return " ".join(words[:4]).capitalize() + "..."
                
        if sub:
            return sub[0].upper() + sub[1:]
        return "Sin subtipo"
        
    def build_products_ui(self, parent: tk.Misc, products: List[Dict], authorship_mode: str = "") -> None:
        unique_prods = []
        seen = {}
        for prod in products:
            titulo = str(prod.get("titulo", ""))
            anio = str(prod.get("anio", 0))
            key = (canonical_key(titulo), anio)
            if titulo:
                if key not in seen:
                    pc = dict(prod)
                    seen[key] = pc
                    unique_prods.append(pc)
                else:
                    existing = seen[key]
                    if authorship_mode:
                        if existing.get("_grupo_nombre", "N/A") == "N/A" and prod.get("_grupo_nombre", "N/A") != "N/A":
                            existing["_grupo_nombre"] = prod.get("_grupo_nombre")
                        if existing.get("_autor_nombre", "N/A") == "N/A" and prod.get("_autor_nombre", "N/A") != "N/A":
                            existing["_autor_nombre"] = prod.get("_autor_nombre")
                            
        if authorship_mode == "general":
            inv_prods = []
            grp_prods = []
            for p in unique_prods:
                if p.get("_autor_nombre", "N/A") != "N/A":
                    inv_prods.append(p)
                if p.get("_grupo_nombre", "N/A") != "N/A":
                    grp_prods.append(p)
                    
            notebook_main = ttk.Notebook(parent)
            notebook_main.pack(fill="both", expand=True, padx=5, pady=5)
            
            f_inv = tk.Frame(notebook_main, bg=PANEL)
            notebook_main.add(f_inv, text="Investigadores")
            self._build_category_tabs(f_inv, inv_prods, "investigador")
            
            f_grp = tk.Frame(notebook_main, bg=PANEL)
            notebook_main.add(f_grp, text="Grupos")
            self._build_category_tabs(f_grp, grp_prods, "grupo")
        else:
            self._build_category_tabs(parent, unique_prods, authorship_mode)

    def _build_category_tabs(self, parent: tk.Misc, products: List[Dict], authorship_mode: str) -> None:
        by_category = {}
        for prod in products:
            cat = self.get_product_category(prod)
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(prod)
            
        if not by_category:
            tk.Label(parent, text="No hay productos registrados.", bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(pady=20)
        elif len(by_category) == 1:
            cat_name = list(by_category.keys())[0]
            cat_prods = by_category[cat_name]
            tk.Label(parent, text=f"Categoría: {cat_name}", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
            self._create_products_tree(parent, cat_prods, authorship_mode)
        else:
            notebook = ttk.Notebook(parent)
            notebook.pack(fill="both", expand=True, padx=5, pady=5)
            for cat_name, cat_prods in sorted(by_category.items(), key=lambda x: x[0]):
                frame = tk.Frame(notebook, bg=PANEL)
                notebook.add(frame, text=cat_name)
                self._create_products_tree(frame, cat_prods, authorship_mode)

    def _create_products_tree(self, parent: tk.Misc, products: List[Dict], authorship_mode: str = "") -> None:
        if authorship_mode == "investigador":
            cols = [
                ("titulo", "Título del producto", 360),
                ("autor", "Investigador", 160),
                ("anio", "Año", 45),
                ("subtipo", "Subtipo", 185)
            ]
        elif authorship_mode == "grupo":
            cols = [
                ("titulo", "Título del producto", 360),
                ("grupo", "Grupo", 160),
                ("anio", "Año", 45),
                ("subtipo", "Subtipo", 185)
            ]
        else:
            cols = [
                ("titulo", "Título del producto", 450),
                ("anio", "Año", 45),
                ("subtipo", "Subtipo", 180)
            ]
            
        tree = self._create_tree(parent, cols)
        for prod in sorted(products, key=lambda p: str(p.get("anio", "0")), reverse=True):
            titulo = str(prod.get("titulo", ""))
            anio = str(prod.get("anio", ""))
            subtipo = self.get_product_subtype(prod)
            if authorship_mode == "investigador":
                autor = prod.get("_autor_nombre", "N/A")
                tree.insert("", "end", values=(titulo, autor, anio, subtipo))
            elif authorship_mode == "grupo":
                grupo = prod.get("_grupo_nombre", "N/A")
                tree.insert("", "end", values=(titulo, grupo, anio, subtipo))
            else:
                tree.insert("", "end", values=(titulo, anio, subtipo))

    def _strip_accents(self, s: str) -> str:
        if s is None:
            return ""
        norm = unicodedata.normalize("NFD", str(s))
        return "".join(c for c in norm if unicodedata.category(c) != "Mn").lower()

    def _normalize_date_token(self, s: str) -> str:
        if s is None:
            return ""
        t = str(s).strip()
        low = t.lower()
        if not low or low in ("de", "actual", "de actual"):
            return "Actual"
        t = re.sub(r"^de\s+", "", t, flags=re.IGNORECASE)
        t = re.sub(r"([a-záéíóúñ]+)de\s*(\d{4})", r"\1 \2", t, flags=re.IGNORECASE)
        return t.strip()

    def _normalize_period_str(self, s: str) -> str:
        if s is None:
            return "-"
        raw = str(s).strip()
        if not raw:
            return "-"
        low = raw.lower()
        if low.endswith("de actual") or low.endswith(" de"):
            raw_clean = re.sub(r"\s+de(\s+actual)?$", "", raw, flags=re.IGNORECASE)
            m = re.match(r"([a-záéíóúñ]+(?:\s+de\s+|\s+)\d{4})", raw_clean, re.IGNORECASE)
            if m is not None:
                return f"{self._normalize_date_token(m.group(1))} - Actual"
            else:
                return f"{raw_clean} - Actual"
        m_two = re.match(r"([a-záéíóúñ]+(?:\s+de\s+|\s+)\d{4})\s+([a-záéíóúñ]+(?:\s+de\s+|\s+)\d{4}|\d{4})", raw, re.IGNORECASE)
        if m_two is not None:
            return f"{self._normalize_date_token(m_two.group(1))} - {self._normalize_date_token(m_two.group(2))}"
        return raw

    def _parse_experiencia_roles(self, rest_text: str) -> List[Tuple[str, str, str]]:
        roles = []
        if not rest_text:
            return roles

        role_pattern = re.compile(
            r"(?P<tag>Cargo|Titulo|Título|Nombre del curso):\s*(?P<val>.+?)(?=(?:\s*-\s*(?:Cargo|Titulo|Título|Nombre del curso|Miembro|Director|Investigaci[oó]n|Actividades|Pregrado|Especializaci[oó]n|Extensi[oó]n|Docencia|Servicio|Otro)|\s*Actividades|\s*$))",
            re.IGNORECASE
        )

        meses_regex = r"(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)"

        matches = role_pattern.findall(rest_text)
        for tag, raw_val in matches:
            tag_low = tag.lower()
            if "cargo" in tag_low:
                tipo_lbl = "Cargo"
            elif "curso" in tag_low:
                tipo_lbl = "Docencia"
            else:
                tipo_lbl = "Investigación"

            val_str = raw_val.strip()
            m_date = re.search(r"(" + meses_regex + r"(?:\s+de\s+|\s+)\d{4})\s*(.*)$", val_str, re.IGNORECASE)
            if m_date is not None:
                date_part = m_date.group(0).strip()
                title_clean = val_str[:m_date.start()].strip()
                if not title_clean:
                    title_clean = val_str
                    per_str = "-"
                else:
                    per_str = self._normalize_period_str(date_part)
            else:
                title_clean = val_str
                per_str = "-"

            title_clean = title_clean.rstrip(",").strip()
            if not title_clean:
                title_clean = tipo_lbl

            roles.append((title_clean, tipo_lbl, per_str))

        if not roles and rest_text:
            roles.append((rest_text, "Actividad", "-"))

        return roles

    def build_formacion_ui(self, parent: tk.Misc, items: List[Any]) -> None:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        cols = [
            ("nivel", "Nivel", 140),
            ("institucion", "Institución", 230),
            ("titulo", "Título / Programa", 220),
            ("periodo", "Período", 160),
            ("detalle", "Tesis / Detalle", 260)
        ]

        tree = ttk.Treeview(frame, columns=[col[0] for col in cols], show="headings")
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        for key, title, width in cols:
            tree.heading(key, text=title)
            if key in ("nivel", "periodo"):
                tree.column(key, width=width, anchor="center")
            else:
                tree.column(key, width=width, anchor="w")

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)

        niveles_conocidos = [
            "Pregrado/Universitario", "Doctorado", "Maestría/Magister", "Maestría", "Magister",
            "Especialización médica", "Especialización", "Perfeccionamiento", "Posdoctorado", "Postdoctorado",
            "Secundario", "Secundaria", "Bachillerato", "Primaria", "Técnico", "Tecnológico"
        ]

        date_pattern = re.compile(
            r"(?P<ini>[a-záéíóúñ]+(?:\s*de\s*|\s*)\d{4}|\d{4})\s*-\s*"
            r"(?P<fin>[a-záéíóúñ]+(?:\s*de\s*|\s*)\d{4}|\s*de\s*\d{4}|\s*de\b|\d{4}|actual)?(?:\s+(?P<extra>.*))?$",
            re.IGNORECASE
        )

        degree_keywords = [
            "doctorat", "doctorado", "doctor", "maestria", "magister", "master", "phd",
            "ingenieria", "ingeniero", "ingeniera", "licenciado", "licenciada", "licenciatura",
            "especializacion", "especialista", "tecnologo", "tecnologa", "tecnologia", "tecnico", "tecnica",
            "abogado", "abogada", "administrador", "administradora", "administracion",
            "arquitecto", "arquitecta", "arquitectura", "contador", "contadora", "contaduria",
            "economista", "economia", "medico", "medica", "medicina", "enfermero", "enfermera", "enfermeria",
            "psicologo", "psicologa", "psicologia", "odontologo", "odontologa", "odontologia",
            "filosofo", "filosofa", "filosofia", "sociologo", "sociologa", "sociologia",
            "comunicador", "comunicadora", "comunicacion", "periodista", "periodismo",
            "biologo", "biologa", "biologia", "quimico", "quimica", "fisico", "fisica", "matematico", "matematica",
            "programa", "articulacion", "posgrados", "auditora", "auditor", "salud mental",
            "epidemiologia", "relaciones publicas", "analytical chemistry"
        ]

        for raw_item in items:
            text_val = str(raw_item).strip()
            if text_val:
                nivel = "Otro"
                resto = text_val
                matched_niv = False
                for niv in niveles_conocidos:
                    if not matched_niv:
                        if resto.lower().startswith(niv.lower()):
                            nivel = niv
                            resto = resto[len(niv):].strip()
                            matched_niv = True

                m_date = date_pattern.search(resto)
                if m_date is not None:
                    middle = resto[:m_date.start()].strip()
                    f_ini = self._normalize_date_token(m_date.group("ini"))
                    raw_fin = m_date.group("fin")
                    if raw_fin is not None:
                        f_fin = self._normalize_date_token(raw_fin)
                    else:
                        f_fin = ""

                    if f_fin:
                        periodo = f"{f_ini} - {f_fin}"
                    else:
                        periodo = f_ini

                    raw_extra = m_date.group("extra")
                    if raw_extra is not None:
                        detalles = raw_extra.strip()
                    else:
                        detalles = ""
                else:
                    middle = resto
                    periodo = "-"
                    detalles = ""

                institucion = middle
                titulo = "-"
                if " - " in middle:
                    parts_dash = middle.split(" - ", 1)
                    institucion = parts_dash[0].strip()
                    titulo = parts_dash[1].strip()
                else:
                    words = middle.split()
                    split_idx = -1
                    found_split = False
                    for i in range(1, len(words)):
                        if not found_split:
                            w_norm = self._strip_accents(words[i])
                            for dk in degree_keywords:
                                if not found_split:
                                    dk_norm = self._strip_accents(dk.split()[0])
                                    if w_norm == dk_norm or w_norm.startswith(dk_norm):
                                        split_idx = i
                                        found_split = True

                    if split_idx != -1:
                        institucion = " ".join(words[:split_idx]).strip()
                        titulo = " ".join(words[split_idx:]).strip()

                if not institucion:
                    institucion = "-"
                if not titulo:
                    titulo = "-"
                if not periodo:
                    periodo = "-"
                if not detalles:
                    detalles = "-"

                tree.insert("", "end", values=(nivel, institucion, titulo, periodo, detalles))

    def build_experiencia_ui(self, parent: tk.Misc, items: List[Any]) -> None:
        toolbar = tk.Frame(parent, bg=PANEL)
        toolbar.pack(fill="x", padx=6, pady=(6, 2))

        def _expand_all() -> None:
            for item_id in tree.get_children():
                tree.item(item_id, open=True)

        def _collapse_all() -> None:
            for item_id in tree.get_children():
                tree.item(item_id, open=False)

        ttk.Button(toolbar, text="Expandir todo", command=_expand_all).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Colapsar todo", command=_collapse_all).pack(side="left")

        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        cols = [
            ("tipo", "Tipo", 120),
            ("dedicacion", "Dedicación", 140),
            ("periodo", "Período", 170)
        ]

        tree = ttk.Treeview(frame, columns=[col[0] for col in cols], show="tree headings")
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        tree.heading("#0", text="Institución / Cargo o Rol", anchor="w")
        tree.column("#0", width=360, anchor="w")

        for key, title, width in cols:
            tree.heading(key, text=title)
            if key == "tipo":
                tree.column(key, width=width, anchor="w")
            else:
                tree.column(key, width=width, anchor="center")

        tree.tag_configure("parent_row", font=("Segoe UI", 9, "bold"))
        tree.tag_configure("child_row", font=("Segoe UI", 9))

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)

        ded_pattern = re.compile(
            r"^(?P<inst>.+?)\s+Dedicaci[oó]n:\s*(?P<horas>\d+)?\s*(?:horas?\s*)?(?P<frec>Semanales|Mensuales)?\s+(?P<fechas>.+?)(?=\s+Actividades|\s*$)",
            re.IGNORECASE
        )

        for raw_item in items:
            item_str = str(raw_item).strip()
            if item_str:
                m_ded = ded_pattern.match(item_str)
                if m_ded is not None:
                    inst = m_ded.group("inst").strip()
                    horas = m_ded.group("horas")
                    frec = m_ded.group("frec")
                    if horas and frec:
                        dedicacion = f"{horas} horas {frec}"
                    elif horas:
                        dedicacion = f"{horas} horas"
                    else:
                        dedicacion = "No especificada"

                    periodo = self._normalize_period_str(m_ded.group("fechas"))
                    rest = item_str[m_ded.end():].strip()
                    roles = self._parse_experiencia_roles(rest)

                    p_iid = tree.insert("", "end", text=inst, values=("Institución", dedicacion, periodo), tags=("parent_row",), open=True)
                    for r_name, r_type, r_per in roles:
                        tree.insert(p_iid, "end", text=f"• {r_name}", values=(r_type, "-", r_per), tags=("child_row",))
                else:
                    meses_fallback = r"(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)"
                    date_pat_exp = re.compile(
                        r"(?P<ini>" + meses_fallback + r"(?:\s+de\s+|\s+)\d{4}|\d{4})\s*"
                        r"(?:-\s*(?P<fin>" + meses_fallback + r"(?:\s+de\s+|\s+)\d{4}|\s*de\s*\d{4}|\s*de\b|\d{4}|actual))?",
                        re.IGNORECASE
                    )
                    m_fdate = date_pat_exp.search(item_str)
                    if m_fdate is not None:
                        text_before = item_str[:m_fdate.start()].strip()
                        ini_f = m_fdate.group("ini")
                        fin_f = m_fdate.group("fin")
                        if fin_f:
                            periodo_f = f"{self._normalize_date_token(ini_f)} - {self._normalize_date_token(fin_f)}"
                        else:
                            periodo_f = self._normalize_date_token(ini_f)
                    else:
                        text_before = item_str
                        periodo_f = "-"

                    if " - Cargo:" in text_before or " - Cargo :" in text_before:
                        parts_c = re.split(r"\s*-\s*Cargo\s*:\s*", text_before, flags=re.IGNORECASE)
                        inst_f = parts_c[0].strip()
                        cargo_f = parts_c[1].strip()
                    else:
                        role_words = [
                            "docente", "profesor", "profesora", "investigador", "investigadora",
                            "decano", "decana", "director", "directora", "coordinador", "coordinadora",
                            "rector", "rectora", "analista", "gerente", "asesor", "asesora",
                            "consultor", "consultora", "ingeniero", "ingeniera", "desarrollador",
                            "desarrolladora", "tecnico", "tecnica", "asistente", "auxiliar"
                        ]
                        words_b = text_before.split()
                        split_b = -1
                        for i in range(1, len(words_b)):
                            if split_b == -1:
                                w_norm_b = self._strip_accents(words_b[i])
                                for rw in role_words:
                                    if split_b == -1:
                                        if w_norm_b == rw or w_norm_b.startswith(rw):
                                            split_b = i

                        if split_b != -1:
                            inst_f = " ".join(words_b[:split_b]).strip()
                            cargo_f = " ".join(words_b[split_b:]).strip()
                        else:
                            inst_f = text_before
                            cargo_f = ""

                    p_iid = tree.insert("", "end", text=inst_f, values=("Institución", "No especificada", periodo_f), tags=("parent_row",), open=True)
                    if cargo_f:
                        tree.insert(p_iid, "end", text=f"• {cargo_f}", values=("Cargo", "-", periodo_f), tags=("child_row",))

    def build_lineas_ui(self, parent: tk.Misc, items: List[Any]) -> None:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        
        cols = [
            ("nombre", "Nombre", 400),
            ("activa", "Activa", 100)
        ]
        
        tree = ttk.Treeview(frame, columns=[col[0] for col in cols], show="headings")
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=v_scroll.set)
        
        for key, title, width in cols:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
            
        v_scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        
        for raw_item in items:
            text_val = str(raw_item).strip()
            if text_val:
                partes = text_val.split(", Activa:")
                if len(partes) > 1:
                    nombre = partes[0].strip()
                    activa = partes[1].strip()
                else:
                    nombre = text_val
                    activa = "-"
                tree.insert("", "end", values=(nombre, activa))

    def build_areas_ui(self, parent: tk.Misc, items: List[Any]) -> None:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        
        cols = [
            ("gran_area", "Gran Área", 150),
            ("area", "Área de conocimiento", 200),
            ("disciplina", "Disciplina", 200)
        ]
        
        tree = ttk.Treeview(frame, columns=[col[0] for col in cols], show="headings")
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=v_scroll.set)
        
        for key, title, width in cols:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
            
        v_scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        
        for raw_item in items:
            text_val = str(raw_item).strip()
            if text_val:
                partes = text_val.split(" -- ")
                if len(partes) >= 3:
                    gran_area = partes[0].strip()
                    area = partes[1].strip()
                    disciplina = partes[2].strip()
                elif len(partes) == 2:
                    gran_area = partes[0].strip()
                    area = partes[1].strip()
                    disciplina = "-"
                else:
                    gran_area = text_val
                    area = "-"
                    disciplina = "-"
                tree.insert("", "end", values=(gran_area, area, disciplina))

    def build_reconocimientos_ui(self, parent: tk.Misc, items: List[Any]) -> None:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        
        cols = [
            ("reconocimiento", "Reconocimiento", 250),
            ("institucion", "Institución", 200),
            ("fecha", "Fecha", 100)
        ]
        
        tree = ttk.Treeview(frame, columns=[col[0] for col in cols], show="headings")
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        for key, title, width in cols:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
            
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)
        
        for raw_item in items:
            text_val = str(raw_item).strip()
            if text_val:
                partes_guion = text_val.rsplit(" - ", 1)
                fecha = "-"
                inst_reconocimiento = text_val
                if len(partes_guion) == 2:
                    fecha = partes_guion[1].strip()
                    fecha = self._normalize_date_token(fecha)
                    inst_reconocimiento = partes_guion[0].strip()
                
                partes_coma = inst_reconocimiento.split(",", 1)
                if len(partes_coma) == 2:
                    reconocimiento = partes_coma[0].strip()
                    institucion = partes_coma[1].strip()
                else:
                    reconocimiento = inst_reconocimiento
                    institucion = "-"
                    
                tree.insert("", "end", values=(reconocimiento, institucion, fecha))

    def build_proyectos_ui(self, parent: tk.Misc, items: List[Any]) -> None:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        
        cols = [
            ("tipo", "Tipo", 120),
            ("nombre", "Nombre", 200),
            ("periodo", "Período", 150),
            ("resumen", "Resumen", 250)
        ]
        
        tree = ttk.Treeview(frame, columns=[col[0] for col in cols], show="headings")
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        for key, title, width in cols:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
            
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)
        
        tipos_conocidos = [
            "Investigación y desarrollo",
            "Extensión y responsabilidad social CTI",
            "Desarrollo tecnológico",
            "Desarrollo experimental",
            "Otro"
        ]

        meses_proy = r"(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)"
        date_pat_proy = re.compile(
            r"(?P<ini>" + meses_proy + r"(?:\s+de\s+|\s+)\d{4}|\d{4})\s*"
            r"(?:-\s*(?P<fin>" + meses_proy + r"(?:\s+de\s+|\s+)\d{4}|\s*de\s*\d{4}|\s*de\b|\d{4}|actual))?",
            re.IGNORECASE
        )

        for raw_item in items:
            text_val = str(raw_item).strip()
            if text_val:
                texto = text_val
                if texto.startswith("Tipo de proyecto:"):
                    texto = texto[17:].strip()

                tipo = "-"
                nombre = texto
                matched_tipo = False
                for tk_tipo in tipos_conocidos:
                    if not matched_tipo:
                        if texto.startswith(tk_tipo):
                            tipo = tk_tipo
                            texto = texto[len(tk_tipo):].strip()
                            matched_tipo = True

                inicio_idx = texto.find("Inicio:")
                if inicio_idx != -1:
                    nombre = texto[:inicio_idx].strip()
                    resto = texto[inicio_idx + 7:].strip()

                    fin_idx = resto.find("Fin:")
                    resumen_idx = resto.find("Resumen")
                    duracion_idx = resto.find("Duración")

                    first_idx = len(resto)
                    if fin_idx != -1 and fin_idx < first_idx:
                        first_idx = fin_idx
                    if resumen_idx != -1 and resumen_idx < first_idx:
                        first_idx = resumen_idx
                    if duracion_idx != -1 and duracion_idx < first_idx:
                        first_idx = duracion_idx

                    if first_idx < len(resto):
                        inicio_str = resto[:first_idx].strip()
                    else:
                        inicio_str = resto.strip()

                    fin_str = ""
                    if fin_idx != -1:
                        fin_search_end = resto.find("Duración", fin_idx)
                        if fin_search_end == -1:
                            fin_search_end = resto.find("Resumen", fin_idx)
                        if fin_search_end == -1:
                            fin_search_end = len(resto)
                        fin_str = resto[fin_idx+4:fin_search_end].strip()

                    periodo = "-"
                    if inicio_str and fin_str:
                        periodo = f"{self._normalize_date_token(inicio_str)} - {self._normalize_date_token(fin_str)}"
                    elif inicio_str:
                        periodo = self._normalize_date_token(inicio_str)

                    resumen = "-"
                    if resumen_idx != -1:
                        resumen = resto[resumen_idx+7:].strip()
                else:
                    resumen_idx = texto.find("Resumen")
                    if resumen_idx != -1:
                        pre_resumen = texto[:resumen_idx].strip()
                        resumen = texto[resumen_idx+7:].strip()
                    else:
                        pre_resumen = texto
                        resumen = "-"

                    m_dp = date_pat_proy.search(pre_resumen)
                    if m_dp is not None:
                        nombre = pre_resumen[:m_dp.start()].strip()
                        ini_p = m_dp.group("ini")
                        fin_p = m_dp.group("fin")
                        if fin_p:
                            periodo = f"{self._normalize_date_token(ini_p)} - {self._normalize_date_token(fin_p)}"
                        else:
                            periodo = self._normalize_date_token(ini_p)
                    else:
                        nombre = pre_resumen
                        periodo = "-"

                tree.insert("", "end", values=(tipo, nombre, periodo, resumen))
                
        def on_double_click(event: tk.Event) -> None:
            item_id = tree.selection()
            if item_id:
                item_vals = tree.item(item_id[0], "values")
                if len(item_vals) >= 4:
                    res_text = item_vals[3]
                    if res_text and res_text != "-":
                        top = tk.Toplevel(parent)
                        top.title("Resumen del Proyecto")
                        top.geometry("500x300")
                        txt = tk.Text(top, wrap="word", bg=PANEL, font=("Segoe UI", 10), padx=10, pady=10)
                        txt.insert("end", res_text)
                        txt.config(state="disabled")
                        txt.pack(fill="both", expand=True)
                        ttk.Button(top, text="Cerrar", command=top.destroy).pack(pady=10)
                        
        tree.bind("<Double-1>", on_double_click)

    def refresh_investigator_tree(self, tree: ttk.Treeview, query: str) -> None:
        for iid in tree.get_children():
            tree.delete(iid)
        for item in self.service.search_investigators(query):
            if bool(item.get("activo", True)):
                state = "Activo"
            else:
                state = "Inactivo"
            categoria = item.get("categoriaInvestigador", "")
            disp_categoria = categoria
            if " con vigencia" in categoria:
                disp_categoria = categoria.split(" con vigencia")[0].strip()
            tree.insert("", "end", values=(item.get("codigoRh", ""), item.get("nombre", ""), disp_categoria, item.get("nacionalidad", ""), state))

    def toggle_selected_investigator(self, tree: ttk.Treeview) -> None:
        selected = tree.selection()
        if selected:
            values = tree.item(selected[0], "values")
            if values:
                if self.service.toggle_investigator(values[0]):
                    self.refresh_investigator_tree(tree, "")
                    self.status.set("Estado del investigador actualizado")

    def delete_selected_investigator(self, tree: ttk.Treeview) -> None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Eliminar Investigador", "Seleccione un investigador de la lista para eliminar.")
        else:
            values = tree.item(selected[0], "values")
            if values:
                target_cod = str(values[0]).strip()
                target_nom = str(values[1]).strip()
                target_id = target_cod
                if not target_id:
                    target_id = target_nom
                confirm = messagebox.askyesno(
                    "Confirmar Eliminación",
                    f"¿Está seguro de que desea eliminar al investigador?\n\nNombre: {target_nom}\nCódigo: {target_cod}\n\nEsta acción eliminará toda su información asociada en memoria.\n(Recuerde presionar 'Guardar datos' si desea persistir los cambios en disco).",
                    icon="warning"
                )
                if confirm:
                    if self.service.delete_investigator(target_id):
                        self.refresh_investigator_tree(tree, "")
                        self.status.set("Investigador eliminado de memoria (recuerde guardar datos)")
                        messagebox.showinfo("Investigador Eliminado", f"El investigador '{target_nom}' ha sido eliminado exitosamente de la memoria.\n\nRecuerde presionar 'Guardar datos' para persistir el cambio en disco.")
                    else:
                        messagebox.showerror("Error", "No fue posible encontrar o eliminar al investigador.")

    def show_investigator_detail_for_item(self, investigator: Dict[str, Any], tree: Optional[ttk.Treeview] = None) -> None:
        fields = [
            ("codigoRh", "Código RH"),
            ("nombre", "Nombre"),
            ("categoriaInvestigador", "Categoría Minciencias"),
            ("correo", "Correo electrónico"),
            ("orcid", "ORCID"),
            ("departamento", "Departamento"),
            ("ciudad", "Ciudad"),
            ("nacionalidad", "Nacionalidad"),
            ("sexo", "Sexo"),
            ("perfil", "Perfil / Biografía"),
            ("estadoParEvaluador", "Par evaluador"),
            ("nombreCitaciones", "Nombre en citaciones"),
            ("researcherId", "ResearcherID"),
            ("autorIdScopus", "Scopus ID"),
            ("googleScholar", "Google Scholar"),
            ("researchGate", "ResearchGate"),
            ("academiaEdu", "Academia.edu"),
            ("mendeley", "Mendeley"),
            ("linkedin", "LinkedIn"),
            ("repositorioInstitucional", "Repositorio institucional")
        ]
        lists = [
            ("Productos", investigator.get("productos", [])),
            ("Grupos de Investigación", investigator.get("gruposInvestigacion", [])),
            ("Formación académica", investigator.get("formacionAcademica", [])),
            ("Experiencia profesional", investigator.get("experienciaProfesional", [])),
            ("Líneas de investigación", investigator.get("lineasInvestigacion", [])),
            ("Proyectos", investigator.get("proyectos", [])),
            ("Áreas de conocimiento", investigator.get("areasConocimiento", [])),
            ("Semilleros", investigator.get("semilleros", [])),
            ("Reconocimientos", investigator.get("reconocimientos", [])),
            ("Idiomas", investigator.get("idiomas", []))
        ]
        self._detail_window("Detalle del investigador", investigator, fields, lists, entity_type="investigador", tree=tree)

    def show_investigator_detail(self, tree: ttk.Treeview) -> None:
        selected = tree.selection()
        values = ()
        if not selected:
            messagebox.showinfo("Detalle de investigador", "Seleccione un investigador de la lista para ver su información.")
        else:
            values = tree.item(selected[0], "values")
        if values:
            investigator = None
            _found_inv = False
            for item in self.service.investigadores:
                if not _found_inv:
                    if values[0] and str(item.get("codigoRh", "")).strip() == str(values[0]).strip():
                        investigator = item
                        _found_inv = True
                    elif not values[0] and str(item.get("nombre", "")).strip() == str(values[1]).strip():
                        investigator = item
                        _found_inv = True
            if investigator is not None:
                self.show_investigator_detail_for_item(investigator, tree)

    def build_groups(self) -> None:
        self.heading("Grupos de Investigación", "Consulta y gestión de grupos cargados desde GrupLAC")
        bar = tk.Frame(self.content, bg=BG)
        bar.pack(fill="x", pady=(0, 10))
        entry = ttk.Entry(bar)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(bar, text="Buscar", command=lambda: self.refresh_group_tree(tree, entry.get())).pack(side="left")
        ttk.Button(bar, text="Ver detalle", command=lambda: self.show_group_detail(tree)).pack(side="left", padx=8)
        ttk.Button(bar, text="🗑️ Eliminar Grupo", command=lambda: self.delete_selected_group(tree)).pack(side="left")
        ttk.Button(bar, text="+ Crear Grupo", command=lambda: self.open_create_group_dialog(tree)).pack(side="left", padx=8)
        tree = self._create_tree(self.content, [("codigo", "Código", 130), ("nombre", "Nombre", 340), ("lider", "Líder", 220), ("ciudad", "Ciudad", 140), ("categoria", "Clasificación", 130)])
        self.main_group_tree = tree
        entry.bind("<Return>", lambda event: self.refresh_group_tree(tree, entry.get()))
        tree.bind("<Double-1>", lambda event: self.show_group_detail(tree))
        self.refresh_group_tree(tree, "")

    def refresh_group_tree(self, tree: ttk.Treeview, query: str) -> None:
        for iid in tree.get_children():
            tree.delete(iid)
        for item in self.service.search_groups(query):
            tree.insert("", "end", values=(item.get("nroGrupo", ""), item.get("nombreGrupo", ""), item.get("lider", ""), item.get("ciudad", ""), item.get("clasificacion", "")))

    def delete_selected_group(self, tree: ttk.Treeview) -> None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Eliminar Grupo", "Seleccione un grupo de la lista para eliminar.")
        else:
            values = tree.item(selected[0], "values")
            if values:
                target_cod = str(values[0]).strip()
                target_nom = str(values[1]).strip()
                target_id = target_cod
                if not target_id:
                    target_id = target_nom
                confirm = messagebox.askyesno(
                    "Confirmar Eliminación",
                    f"¿Está seguro de que desea eliminar al grupo de investigación?\n\nNombre: {target_nom}\nCódigo: {target_cod}\n\nEsta acción eliminará toda la información del grupo en memoria (integrantes y productos propios).\n(Recuerde presionar 'Guardar datos' si desea persistir los cambios en disco).",
                    icon="warning"
                )
                if confirm:
                    if self.service.delete_group(target_id):
                        self.refresh_group_tree(tree, "")
                        self.status.set("Grupo eliminado de memoria (recuerde guardar datos)")
                        messagebox.showinfo("Grupo Eliminado", f"El grupo '{target_nom}' ha sido eliminado exitosamente de la memoria.\n\nRecuerde presionar 'Guardar datos' para persistir el cambio en disco.")
                    else:
                        messagebox.showerror("Error", "No fue posible encontrar o eliminar al grupo.")

    def show_group_detail_for_item(self, group: Dict[str, Any], tree: Optional[ttk.Treeview] = None) -> None:
        fields = [
            ("nroGrupo", "Código"),
            ("nombreGrupo", "Nombre del grupo"),
            ("anioFormacion", "Año de formación"),
            ("departamento", "Departamento"),
            ("ciudad", "Ciudad"),
            ("lider", "Líder"),
            ("clasificacion", "Clasificación"),
            ("areaConocimiento", "Área de conocimiento"),
            ("programaNacionalCti", "Programa nacional CTI"),
            ("programaNacionalCtiSecundario", "Programa nacional CTI secundario"),
            ("email", "Correo"),
            ("paginaWeb", "Página web"),
            ("planEstrategico", "Plan estratégico"),
            ("estadoArte", "Estado del arte"),
            ("objetivos", "Objetivos"),
            ("retos", "Retos"),
            ("vision", "Visión")
        ]
        lists = [
            ("Instituciones", group.get("instituciones", [])),
            ("Integrantes", group.get("integrantes", [])),
            ("Productos", group.get("productos", [])),
            ("Líneas de investigación", group.get("lineasInvestigacion", []))
        ]
        self._detail_window("Detalle del grupo", group, fields, lists, entity_type="grupo", tree=tree)

    def show_group_detail(self, tree: ttk.Treeview) -> None:
        selected = tree.selection()
        values = ()
        if not selected:
            messagebox.showinfo("Detalle del grupo", "Seleccione un grupo de la lista para ver su información.")
        else:
            values = tree.item(selected[0], "values")
        if values:
            group = None
            _found_grp = False
            for item in self.service.grupos:
                if not _found_grp:
                    if str(item.get("nroGrupo", "")).strip() == str(values[0]).strip():
                        group = item
                        _found_grp = True
            if group is not None:
                self.show_group_detail_for_item(group, tree)

    def _detail_window(
        self,
        title: str,
        data: Dict[str, Any],
        fields: List[Any],
        lists: Optional[List[Tuple[str, List[Any]]]] = None,
        entity_type: Optional[str] = None,
        tree: Optional[ttk.Treeview] = None
    ) -> None:
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("900x650")
        window.minsize(750, 550)

        active_edit_window: List[tk.Toplevel] = []

        def on_detail_close() -> None:
            if self._has_active_subwindows(active_edit_window):
                messagebox.showwarning(
                    "Modificación en curso",
                    "No se puede cerrar la ventana de detalles mientras la ventana de modificación esté abierta.\nPor favor guarde o cancele la modificación primero.",
                    parent=window
                )
            else:
                window.destroy()

        window.protocol("WM_DELETE_WINDOW", on_detail_close)

        notebook = ttk.Notebook(window)
        notebook.pack(fill="both", expand=True, padx=14, pady=(14, 8))

        info = tk.Frame(notebook, bg=PANEL)
        notebook.add(info, text="Información")
        info_scroll = ttk.Scrollbar(info, orient="vertical")
        info_scroll.pack(side="right", fill="y")
        text = tk.Text(info, wrap="word", bg=PANEL, fg=DARK, relief="flat", font=("Segoe UI", 10), yscrollcommand=info_scroll.set)
        text.pack(side="left", fill="both", expand=True, padx=12, pady=12)
        info_scroll.configure(command=text.yview)

        text.tag_config("bold_label", font=("Segoe UI", 10, "bold"), foreground=DARK)
        text.tag_config("hyperlink", foreground="#0d6efd", underline=True)

        url_regex = re.compile(r"https?://[^\s<>\"']+")
        tag_to_url: Dict[str, str] = {}
        link_counter = 0

        for item in fields:
            if isinstance(item, (tuple, list)):
                field_key, display_label = item[0], item[1]
            else:
                field_key, display_label = item, item
            val = data.get(field_key)
            if val not in (None, "", []):
                if isinstance(val, bool):
                    if val:
                        val_str = "Activo"
                    else:
                        val_str = "Inactivo"
                else:
                    val_str = str(val)
                text.insert("end", "{}:\n".format(display_label), "bold_label")
                matches = list(url_regex.finditer(val_str))
                if matches:
                    last_idx = 0
                    for match in matches:
                        start, end = match.span()
                        if start > last_idx:
                            text.insert("end", val_str[last_idx:start])
                        url_target = match.group(0)
                        tag_name = f"link_url_{link_counter}"
                        link_counter += 1
                        tag_to_url[tag_name] = url_target
                        text.insert("end", url_target, (tag_name, "hyperlink"))
                        last_idx = end
                    if last_idx < len(val_str):
                        text.insert("end", val_str[last_idx:])
                else:
                    text.insert("end", val_str)
                text.insert("end", "\n\n")

        def _on_text_click(event: tk.Event) -> None:
            idx = text.index(f"@{event.x},{event.y}")
            opened = False
            for tag in text.tag_names(idx):
                if not opened and tag in tag_to_url:
                    webbrowser.open_new_tab(tag_to_url[tag])
                    opened = True

        def _on_text_motion(event: tk.Event) -> None:
            idx = text.index(f"@{event.x},{event.y}")
            if any(tag in tag_to_url for tag in text.tag_names(idx)):
                text.config(cursor="hand2")
            else:
                text.config(cursor="")

        text.bind("<Button-1>", _on_text_click)
        text.bind("<Motion>", _on_text_motion)
        text.configure(state="disabled")

        if lists is None:
            lists = [("Integrantes", data.get("integrantes", [])), ("Productos", data.get("productos", [])), ("Líneas", data.get("lineasInvestigacion", []))]

        for title_text, values in lists:
            if values:
                pane = tk.Frame(notebook, bg=PANEL)
                notebook.add(pane, text=title_text)

                norm_title = re.sub(r"[^a-z]", "", unicodedata.normalize("NFD", title_text.lower()))
                if norm_title == "idiomas":
                    cols = [
                        ("idioma", "Idioma", 160),
                        ("habla", "Habla", 110),
                        ("escribe", "Escribe", 110),
                        ("lee", "Lee", 110),
                        ("entiende", "Entiende", 110),
                    ]
                    tree = self._create_tree(pane, cols)
                    for item in values:
                        line = str(item).strip()
                        if line:
                            norm_line = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", line.lower()))
                            if norm_line not in ("idiomahablaescribeleeentiende", "hablaescribeleeentiende"):
                                parts = [p.strip() for p in line.split("|")]
                                vals = (parts + [""] * 5)[:5]
                                tree.insert("", "end", values=vals)
                elif norm_title == "productos":
                    self.build_products_ui(pane, values)
                elif norm_title in ("formacionacademica", "formacion"):
                    self.build_formacion_ui(pane, values)
                elif norm_title in ("experienciaprofesional", "experiencia"):
                    self.build_experiencia_ui(pane, values)
                elif norm_title in ("lineasdeinvestigacion", "lineas"):
                    self.build_lineas_ui(pane, values)
                elif norm_title == "proyectos":
                    self.build_proyectos_ui(pane, values)
                elif norm_title in ("areasdeconocimiento", "areas"):
                    self.build_areas_ui(pane, values)
                elif norm_title == "reconocimientos":
                    self.build_reconocimientos_ui(pane, values)
                else:
                    scrollbar = ttk.Scrollbar(pane, orient="vertical")
                    scrollbar.pack(side="right", fill="y")
                    listbox = tk.Listbox(pane, font=("Segoe UI", 9), bg=PANEL, fg=DARK, relief="flat", yscrollcommand=scrollbar.set)
                    listbox.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
                    scrollbar.configure(command=listbox.yview)
                    for value in values:
                        if isinstance(value, dict):
                            if value.get("nombre"):
                                if value.get("vinculacion"):
                                    role = f" ({value.get('vinculacion')})"
                                else:
                                    role = ""
                                display = f"{value.get('nombre')}{role}"
                            elif value.get("titulo"):
                                y = value.get("anio") or value.get("ano")
                                if y:
                                    year = f" ({y})"
                                else:
                                    year = ""
                                if value.get("categoria"):
                                    cat = f"[{value.get('categoria')}] "
                                else:
                                    cat = ""
                                if value.get("autores"):
                                    authors = f" - {', '.join(value.get('autores', []))}"
                                else:
                                    authors = ""
                                display = f"{cat}{value.get('titulo')}{year}{authors}"
                            else:
                                display = str(value)
                        else:
                            display = str(value)
                        if display:
                            listbox.insert("end", display)
                            
                    def on_listbox_double_click(event: tk.Event, lb: tk.Listbox = listbox, w: tk.Toplevel = window) -> None:
                        selection = lb.curselection()
                        if selection:
                            text_val = lb.get(selection[0])
                            idx = text_val.find("Plan de trabajo:")
                            if idx != -1:
                                content = text_val[idx + 16:].strip()
                            else:
                                content = text_val
                            top = tk.Toplevel(w)
                            top.title("Detalle")
                            top.geometry("500x300")
                            txt = tk.Text(top, wrap="word", bg=PANEL, font=("Segoe UI", 10), padx=10, pady=10)
                            txt.insert("end", content)
                            txt.config(state="disabled")
                            txt.pack(fill="both", expand=True)
                            ttk.Button(top, text="Cerrar", command=top.destroy).pack(pady=10)
                            
                    listbox.bind("<Double-1>", on_listbox_double_click)

        bottom_bar = tk.Frame(window, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        bottom_bar.pack(fill="x", padx=14, pady=(0, 14))

        if entity_type == "investigador":
            def open_edit_inv() -> None:
                if self._has_active_subwindows(active_edit_window):
                    messagebox.showinfo("Modificación en curso", "La ventana de modificación ya se encuentra abierta.", parent=window)
                    active_edit_window[0].lift()
                    active_edit_window[0].focus_force()
                else:
                    self.open_edit_investigator_dialog(data, window, tree, active_edit_window)

            def delete_from_detail_inv() -> None:
                if self._has_active_subwindows(active_edit_window):
                    messagebox.showwarning("Modificación en curso", "No se puede eliminar mientras la ventana de modificación esté abierta.", parent=window)
                else:
                    target_nom = str(data.get("nombre", "Investigador")).strip()
                    target_cod = str(data.get("codigoRh", "")).strip()
                    target_id = target_cod
                    if not target_id:
                        target_id = target_nom
                    confirm = messagebox.askyesno(
                        "Confirmar Eliminación",
                        f"¿Está seguro de que desea eliminar al investigador actual?\n\nNombre: {target_nom}\nCódigo: {target_cod}\n\nEsta acción eliminará toda su información de la memoria y cerrará esta ventana.\n(Recuerde presionar 'Guardar datos' si desea persistir los cambios en disco).",
                        parent=window,
                        icon="warning"
                    )
                    if confirm:
                        if self.service.delete_investigator(target_id):
                            target_trees = []
                            if tree is not None:
                                target_trees.append(tree)
                            if getattr(self, "main_investigator_tree", None) is not None:
                                if self.main_investigator_tree not in target_trees:
                                    target_trees.append(self.main_investigator_tree)
                            for t in target_trees:
                                try:
                                    if t.winfo_exists():
                                        self.refresh_investigator_tree(t, "")
                                except Exception:
                                    pass
                            self.status.set("Investigador eliminado de memoria (recuerde guardar datos)")
                            messagebox.showinfo("Investigador Eliminado", f"El investigador '{target_nom}' ha sido eliminado exitosamente de la memoria.\n\nRecuerde presionar 'Guardar datos' para persistir el cambio en disco.")
                            window.destroy()
                        else:
                            messagebox.showerror("Error", "No fue posible eliminar al investigador.", parent=window)

            ttk.Button(bottom_bar, text="✏️ Modificar Datos", style="Primary.TButton", command=open_edit_inv).pack(side="left", padx=10, pady=8)
            ttk.Button(bottom_bar, text="🗑️ Eliminar Investigador", command=delete_from_detail_inv).pack(side="left", padx=4, pady=8)

        elif entity_type == "grupo":
            def open_edit_grp() -> None:
                if self._has_active_subwindows(active_edit_window):
                    messagebox.showinfo("Modificación en curso", "La ventana de modificación ya se encuentra abierta.", parent=window)
                    active_edit_window[0].lift()
                    active_edit_window[0].focus_force()
                else:
                    self.open_edit_group_dialog(data, window, tree, active_edit_window)

            def delete_from_detail_grp() -> None:
                if self._has_active_subwindows(active_edit_window):
                    messagebox.showwarning("Modificación en curso", "No se puede eliminar mientras la ventana de modificación esté abierta.", parent=window)
                else:
                    target_nom = str(data.get("nombreGrupo", "Grupo")).strip()
                    target_cod = str(data.get("nroGrupo", "")).strip()
                    target_id = target_cod
                    if not target_id:
                        target_id = target_nom
                    confirm = messagebox.askyesno(
                        "Confirmar Eliminación",
                        f"¿Está seguro de que desea eliminar al grupo actual?\n\nNombre: {target_nom}\nCódigo: {target_cod}\n\nEsta acción eliminará toda la información del grupo de la memoria y cerrará esta ventana.\n(Recuerde presionar 'Guardar datos' si desea persistir los cambios en disco).",
                        parent=window,
                        icon="warning"
                    )
                    if confirm:
                        if self.service.delete_group(target_id):
                            target_trees = []
                            if tree is not None:
                                target_trees.append(tree)
                            if getattr(self, "main_group_tree", None) is not None:
                                if self.main_group_tree not in target_trees:
                                    target_trees.append(self.main_group_tree)
                            for t in target_trees:
                                try:
                                    if t.winfo_exists():
                                        self.refresh_group_tree(t, "")
                                except Exception:
                                    pass
                            self.status.set("Grupo eliminado de memoria (recuerde guardar datos)")
                            messagebox.showinfo("Grupo Eliminado", f"El grupo '{target_nom}' ha sido eliminado exitosamente de la memoria.\n\nRecuerde presionar 'Guardar datos' para persistir el cambio en disco.")
                            window.destroy()
                        else:
                            messagebox.showerror("Error", "No fue posible eliminar al grupo.", parent=window)

            ttk.Button(bottom_bar, text="✏️ Modificar Datos", style="Primary.TButton", command=open_edit_grp).pack(side="left", padx=10, pady=8)
            ttk.Button(bottom_bar, text="🗑️ Eliminar Grupo", command=delete_from_detail_grp).pack(side="left", padx=4, pady=8)

        ttk.Button(bottom_bar, text="Cerrar", command=on_detail_close).pack(side="right", padx=10, pady=8)

    def _has_active_subwindows(self, subwindows: List[tk.Toplevel]) -> bool:
        has_open = False
        for w in list(subwindows):
            try:
                if w.winfo_exists():
                    has_open = True
            except Exception:
                pass
        return has_open

    def _open_products_subwindow(
        self,
        parent_win: tk.Toplevel,
        active_subs: List[tk.Toplevel],
        products_list: List[Dict[str, Any]],
        update_btn_cb: Any,
        is_group: bool = False
    ) -> None:
        sub = tk.Toplevel(parent_win)
        sub.title("Gestionar Productos")
        sub.geometry("780x640")
        sub.minsize(720, 560)
        sub.configure(bg=BG)
        active_subs.append(sub)

        def on_sub_close() -> None:
            if sub in active_subs:
                active_subs.remove(sub)
            sub.destroy()

        sub.protocol("WM_DELETE_WINDOW", on_sub_close)

        top_bar = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_bar.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(top_bar, text="📦 Gestión de Productos", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(top_bar, text="Agregue productos seleccionando la categoría y especificando el subtipo correspondiente.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))

        form_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form_frame.pack(fill="x", padx=14, pady=(0, 8))

        row1 = tk.Frame(form_frame, bg=PANEL)
        row1.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(row1, text="Título (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=14, anchor="w").pack(side="left")
        entry_titulo = ttk.Entry(row1)
        entry_titulo.pack(side="left", fill="x", expand=True)

        categorias_std = [
            "Artículos",
            "Libros",
            "Capítulos de libro",
            "Softwares",
            "Innovación de proceso o procedimiento",
            "Consultorías",
            "Informes de investigación",
            "Productos tecnológicos",
            "Empresas de base tecnológica",
            "Secretos empresariales",
            "Manuales y Guías Especializadas",
            "Documentos de trabajo",
            "Cursos de corta duración",
            "Textos en publicaciones no científicas",
            "Otra publicación divulgativa",
            "Demás trabajos",
            "Otro"
        ]

        row2 = tk.Frame(form_frame, bg=PANEL)
        row2.pack(fill="x", padx=12, pady=4)
        tk.Label(row2, text="Categoría (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=14, anchor="w").pack(side="left")
        combo_cat = ttk.Combobox(row2, values=categorias_std, state="readonly", width=28)
        combo_cat.set("Artículos")
        combo_cat.pack(side="left", padx=(0, 10))
        tk.Label(row2, text="Subtipo / Detalle:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
        entry_subtipo = ttk.Entry(row2)
        entry_subtipo.pack(side="left", fill="x", expand=True)

        row3 = tk.Frame(form_frame, bg=PANEL)
        row3.pack(fill="x", padx=12, pady=4)
        tk.Label(row3, text="Año:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_anio = ttk.Entry(row3, width=12)
        entry_anio.insert(0, str(datetime.now().year))
        entry_anio.pack(side="left", padx=(0, 10))
        entry_autores = None
        if not is_group:
            tk.Label(row3, text="Autores:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
            entry_autores = ttk.Entry(row3)
            entry_autores.pack(side="left", fill="x", expand=True)

        row4 = tk.Frame(form_frame, bg=PANEL)
        row4.pack(fill="x", padx=12, pady=4)
        tk.Label(row4, text="País:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_pais = ttk.Entry(row4, width=18)
        entry_pais.insert(0, "Colombia")
        entry_pais.pack(side="left", padx=(0, 10))
        tk.Label(row4, text="Descripción:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
        entry_desc = ttk.Entry(row4)
        entry_desc.pack(side="left", fill="x", expand=True)

        btn_bar = tk.Frame(form_frame, bg=PANEL)
        btn_bar.pack(fill="x", padx=12, pady=(6, 10))

        def add_product() -> None:
            tit = entry_titulo.get().strip()
            cat = combo_cat.get().strip()
            subt = entry_subtipo.get().strip()
            an = entry_anio.get().strip()
            aut = ""
            if entry_autores is not None:
                aut = entry_autores.get().strip()
            pa = entry_pais.get().strip()
            de = entry_desc.get().strip()

            if not tit:
                messagebox.showerror("Campo requerido", "El título del producto es obligatorio.", parent=sub)
            else:
                an_val = 0
                if an.isdigit():
                    an_val = int(an)
                aut_list = []
                if aut:
                    for a in aut.split(","):
                        a_clean = a.strip()
                        if a_clean:
                            aut_list.append(a_clean)
                tipo_prod = cat
                if subt:
                    tipo_prod = subt
                new_prod = {
                    "idProducto": "P" + str(len(products_list) + 1),
                    "titulo": tit,
                    "categoria": cat,
                    "tipoProducto": tipo_prod,
                    "subtipo": subt,
                    "anio": an_val,
                    "autores": aut_list,
                    "pais": pa,
                    "ciudad": "",
                    "institucion": "",
                    "doi": "",
                    "isbn": "",
                    "revista": "",
                    "editorial": "",
                    "disponibilidad": "",
                    "numeroContrato": "",
                    "descripcion": de,
                    "palabrasClave": "",
                    "areas": "",
                    "validado": False
                }
                products_list.append(new_prod)
                refresh_table()
                update_btn_cb()
                entry_titulo.delete(0, "end")
                entry_subtipo.delete(0, "end")
                if entry_autores is not None:
                    entry_autores.delete(0, "end")
                entry_desc.delete(0, "end")

        def delete_product() -> None:
            sel = prod_tree.selection()
            if sel:
                remove_idx = -1
                tree_idx = prod_tree.index(sel[0])
                if 0 <= tree_idx < len(products_list):
                    remove_idx = tree_idx
                else:
                    vals = prod_tree.item(sel[0], "values")
                    if vals:
                        target_id = str(vals[0])
                        idx = 0
                        while idx < len(products_list) and remove_idx == -1:
                            if str(products_list[idx].get("idProducto", "")) == target_id:
                                remove_idx = idx
                            idx += 1
                if remove_idx != -1:
                    products_list.pop(remove_idx)
                    refresh_table()
                    update_btn_cb()

        ttk.Button(btn_bar, text="+ Agregar Producto a la lista", style="Primary.TButton", command=add_product).pack(side="left")

        bottom_bar = tk.Frame(sub, bg=BG)
        bottom_bar.pack(side="bottom", fill="x", padx=14, pady=(0, 14))
        ttk.Button(bottom_bar, text="Eliminar seleccionado", command=delete_product).pack(side="left")
        ttk.Button(bottom_bar, text="Cerrar ventana", command=on_sub_close).pack(side="right")

        tree_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        cols = [("id", "ID", 50), ("titulo", "Título", 260), ("cat", "Categoría", 150), ("sub", "Subtipo", 160), ("anio", "Año", 60)]
        prod_tree = ttk.Treeview(tree_frame, columns=[c[0] for c in cols], show="headings")
        sb_prod = ttk.Scrollbar(tree_frame, orient="vertical", command=prod_tree.yview)
        prod_tree.configure(yscrollcommand=sb_prod.set)
        for cid, clbl, cwidth in cols:
            prod_tree.heading(cid, text=clbl)
            prod_tree.column(cid, width=cwidth, anchor="w")
        prod_tree.pack(side="left", fill="both", expand=True)
        sb_prod.pack(side="right", fill="y")

        def refresh_table() -> None:
            for item_id in prod_tree.get_children():
                prod_tree.delete(item_id)
            for p in products_list:
                prod_tree.insert("", "end", values=(
                    p.get("idProducto", ""),
                    p.get("titulo", ""),
                    p.get("categoria", ""),
                    p.get("subtipo", ""),
                    p.get("anio", "")
                ))

        refresh_table()

    def _open_simple_list_subwindow(
        self,
        parent_win: tk.Toplevel,
        active_subs: List[tk.Toplevel],
        title: str,
        prompt: str,
        target_list: List[str],
        update_btn_cb: Any,
        placeholder: str = ""
    ) -> None:
        sub = tk.Toplevel(parent_win)
        sub.title(title)
        sub.geometry("640x480")
        sub.configure(bg=BG)
        active_subs.append(sub)

        def on_sub_close() -> None:
            if sub in active_subs:
                active_subs.remove(sub)
            sub.destroy()

        sub.protocol("WM_DELETE_WINDOW", on_sub_close)

        top_bar = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_bar.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(top_bar, text=title, bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(top_bar, text="Ingrese los registros uno a uno para agregarlos a la lista.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))

        form_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form_frame.pack(fill="x", padx=14, pady=(0, 8))

        row1 = tk.Frame(form_frame, bg=PANEL)
        row1.pack(fill="x", padx=12, pady=8)
        tk.Label(row1, text=prompt, bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        entry_val = ttk.Entry(row1)
        if placeholder:
            entry_val.insert(0, placeholder)
        entry_val.pack(fill="x")

        list_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        lb = tk.Listbox(list_frame, font=("Segoe UI", 9), bg=PANEL, fg=DARK, relief="flat")
        sb_lb = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb_lb.set)
        lb.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        sb_lb.pack(side="right", fill="y")

        def refresh_lb() -> None:
            lb.delete(0, "end")
            for item in target_list:
                lb.insert("end", str(item))

        refresh_lb()

        def add_item() -> None:
            val = entry_val.get().strip()
            if not val:
                messagebox.showerror("Campo requerido", "Debe ingresar un texto para agregar.", parent=sub)
            else:
                target_list.append(val)
                refresh_lb()
                update_btn_cb()
                entry_val.delete(0, "end")

        def delete_item() -> None:
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                if 0 <= idx < len(target_list):
                    target_list.pop(idx)
                    refresh_lb()
                    update_btn_cb()

        btn_row = tk.Frame(form_frame, bg=PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Button(btn_row, text="+ Agregar a la lista", style="Primary.TButton", command=add_item).pack(side="left")

        bottom_bar = tk.Frame(sub, bg=BG)
        bottom_bar.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(bottom_bar, text="Eliminar seleccionado", command=delete_item).pack(side="left")
        ttk.Button(bottom_bar, text="Cerrar ventana", command=on_sub_close).pack(side="right")

    def _open_formacion_subwindow(
        self,
        parent_win: tk.Toplevel,
        active_subs: List[tk.Toplevel],
        target_list: List[str],
        update_btn_cb: Any
    ) -> None:
        sub = tk.Toplevel(parent_win)
        sub.title("Gestionar Formación Académica")
        sub.geometry("680x520")
        sub.configure(bg=BG)
        active_subs.append(sub)

        def on_sub_close() -> None:
            if sub in active_subs:
                active_subs.remove(sub)
            sub.destroy()

        sub.protocol("WM_DELETE_WINDOW", on_sub_close)

        top_bar = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_bar.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(top_bar, text="🎓 Formación Académica", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(top_bar, text="Registre estudios superiores, pregrados, posgrados o perfeccionamientos.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))

        form_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form_frame.pack(fill="x", padx=14, pady=(0, 8))

        row1 = tk.Frame(form_frame, bg=PANEL)
        row1.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(row1, text="Nivel (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=14, anchor="w").pack(side="left")
        combo_nivel = ttk.Combobox(row1, values=["Doctorado", "Maestría/Magister", "Especialización", "Pregrado/Universitario", "Perfeccionamiento"], state="readonly", width=22)
        combo_nivel.set("Pregrado/Universitario")
        combo_nivel.pack(side="left", padx=(0, 10))
        tk.Label(row1, text="Periodo / Años:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_periodo = ttk.Entry(row1)
        entry_periodo.pack(side="left", fill="x", expand=True)

        row2 = tk.Frame(form_frame, bg=PANEL)
        row2.pack(fill="x", padx=12, pady=4)
        tk.Label(row2, text="Institución (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=14, anchor="w").pack(side="left")
        entry_inst = ttk.Entry(row2)
        entry_inst.pack(side="left", fill="x", expand=True)

        row3 = tk.Frame(form_frame, bg=PANEL)
        row3.pack(fill="x", padx=12, pady=4)
        tk.Label(row3, text="Título / Programa (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=14, anchor="w").pack(side="left")
        entry_tit = ttk.Entry(row3)
        entry_tit.pack(side="left", fill="x", expand=True)

        row4 = tk.Frame(form_frame, bg=PANEL)
        row4.pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(row4, text="Tesis / Detalles:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_tesis = ttk.Entry(row4)
        entry_tesis.pack(side="left", fill="x", expand=True)

        list_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        lb = tk.Listbox(list_frame, font=("Segoe UI", 9), bg=PANEL, fg=DARK, relief="flat")
        sb_lb = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb_lb.set)
        lb.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        sb_lb.pack(side="right", fill="y")

        def refresh_lb() -> None:
            lb.delete(0, "end")
            for item in target_list:
                lb.insert("end", str(item))

        refresh_lb()

        def add_item() -> None:
            niv = combo_nivel.get().strip()
            inst = entry_inst.get().strip()
            prog = entry_tit.get().strip()
            per = entry_periodo.get().strip()
            tes = entry_tesis.get().strip()

            if not inst:
                messagebox.showerror("Campo requerido", "La institución es obligatoria.", parent=sub)
            elif not prog:
                messagebox.showerror("Campo requerido", "El título / programa es obligatorio.", parent=sub)
            else:
                record_str = f"{niv} {inst} - {prog}"
                if per:
                    record_str = f"{record_str} {per}"
                if tes:
                    record_str = f"{record_str} {tes}"
                target_list.append(record_str)
                refresh_lb()
                update_btn_cb()
                entry_inst.delete(0, "end")
                entry_tit.delete(0, "end")
                entry_periodo.delete(0, "end")
                entry_tesis.delete(0, "end")

        def delete_item() -> None:
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                if 0 <= idx < len(target_list):
                    target_list.pop(idx)
                    refresh_lb()
                    update_btn_cb()

        btn_row = tk.Frame(form_frame, bg=PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Button(btn_row, text="+ Agregar Formación a la lista", style="Primary.TButton", command=add_item).pack(side="left")

        bottom_bar = tk.Frame(sub, bg=BG)
        bottom_bar.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(bottom_bar, text="Eliminar seleccionado", command=delete_item).pack(side="left")
        ttk.Button(bottom_bar, text="Cerrar ventana", command=on_sub_close).pack(side="right")

    def _open_experiencia_subwindow(
        self,
        parent_win: tk.Toplevel,
        active_subs: List[tk.Toplevel],
        target_list: List[str],
        update_btn_cb: Any
    ) -> None:
        sub = tk.Toplevel(parent_win)
        sub.title("Gestionar Experiencia Profesional")
        sub.geometry("680x590")
        sub.minsize(640, 540)
        sub.configure(bg=BG)
        active_subs.append(sub)

        def on_sub_close() -> None:
            if sub in active_subs:
                active_subs.remove(sub)
            sub.destroy()

        sub.protocol("WM_DELETE_WINDOW", on_sub_close)

        top_bar = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_bar.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(top_bar, text="💼 Experiencia Profesional", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(top_bar, text="Registre cargos, dedicaciones e instituciones de desempeño profesional.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))

        form_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form_frame.pack(fill="x", padx=14, pady=(0, 8))

        row1 = tk.Frame(form_frame, bg=PANEL)
        row1.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(row1, text="Institución / Empresa (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=20, anchor="w").pack(side="left")
        entry_empresa = ttk.Entry(row1)
        entry_empresa.pack(side="left", fill="x", expand=True)

        row2 = tk.Frame(form_frame, bg=PANEL)
        row2.pack(fill="x", padx=12, pady=4)
        tk.Label(row2, text="Cargo / Dedicación (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=20, anchor="w").pack(side="left")
        entry_cargo = ttk.Entry(row2)
        entry_cargo.pack(side="left", fill="x", expand=True)

        row3 = tk.Frame(form_frame, bg=PANEL)
        row3.pack(fill="x", padx=12, pady=4)
        tk.Label(row3, text="Periodo / Fechas:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
        entry_periodo = ttk.Entry(row3)
        entry_periodo.pack(side="left", fill="x", expand=True)

        row4 = tk.Frame(form_frame, bg=PANEL)
        row4.pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(row4, text="Actividades / Detalles:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
        entry_act = ttk.Entry(row4)
        entry_act.pack(side="left", fill="x", expand=True)

        def add_item() -> None:
            emp = entry_empresa.get().strip()
            carg = entry_cargo.get().strip()
            per = entry_periodo.get().strip()
            act = entry_act.get().strip()

            if not emp:
                messagebox.showerror("Campo requerido", "La institución o empresa es obligatoria.", parent=sub)
            elif not carg:
                messagebox.showerror("Campo requerido", "El cargo o dedicación es obligatorio.", parent=sub)
            else:
                if per:
                    record_str = f"{emp} Dedicación: No especificada {per} Actividades de administración - Cargo: {carg} {per}"
                else:
                    record_str = f"{emp} Dedicación: No especificada Actividades de administración - Cargo: {carg}"
                if act:
                    record_str = f"{record_str} - {act}"
                target_list.append(record_str)
                refresh_lb()
                update_btn_cb()
                entry_empresa.delete(0, "end")
                entry_cargo.delete(0, "end")
                entry_periodo.delete(0, "end")
                entry_act.delete(0, "end")

        def delete_item() -> None:
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                if 0 <= idx < len(target_list):
                    target_list.pop(idx)
                    refresh_lb()
                    update_btn_cb()

        btn_row = tk.Frame(form_frame, bg=PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Button(btn_row, text="+ Agregar Experiencia a la lista", style="Primary.TButton", command=add_item).pack(side="left")

        bottom_bar = tk.Frame(sub, bg=BG)
        bottom_bar.pack(side="bottom", fill="x", padx=14, pady=(0, 14))
        ttk.Button(bottom_bar, text="Eliminar seleccionado", command=delete_item).pack(side="left")
        ttk.Button(bottom_bar, text="Cerrar ventana", command=on_sub_close).pack(side="right")

        list_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        lb = tk.Listbox(list_frame, font=("Segoe UI", 9), bg=PANEL, fg=DARK, relief="flat")
        sb_lb = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb_lb.set)
        lb.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        sb_lb.pack(side="right", fill="y")

        def refresh_lb() -> None:
            lb.delete(0, "end")
            for item in target_list:
                lb.insert("end", str(item))

        refresh_lb()

    def _open_proyectos_subwindow(
        self,
        parent_win: tk.Toplevel,
        active_subs: List[tk.Toplevel],
        target_list: List[str],
        update_btn_cb: Any
    ) -> None:
        sub = tk.Toplevel(parent_win)
        sub.title("Gestionar Proyectos")
        sub.geometry("680x500")
        sub.configure(bg=BG)
        active_subs.append(sub)

        def on_sub_close() -> None:
            if sub in active_subs:
                active_subs.remove(sub)
            sub.destroy()

        sub.protocol("WM_DELETE_WINDOW", on_sub_close)

        top_bar = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_bar.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(top_bar, text="📁 Gestión de Proyectos", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(top_bar, text="Registre proyectos de investigación, extensión o desarrollo tecnológico.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))

        form_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form_frame.pack(fill="x", padx=14, pady=(0, 8))

        row1 = tk.Frame(form_frame, bg=PANEL)
        row1.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(row1, text="Tipo de proyecto:", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=18, anchor="w").pack(side="left")
        combo_tipo = ttk.Combobox(row1, values=["Investigación y desarrollo", "Extensión y responsabilidad social CTI", "Desarrollo tecnológico", "Otro"], state="readonly", width=28)
        combo_tipo.set("Investigación y desarrollo")
        combo_tipo.pack(side="left", padx=(0, 10))
        tk.Label(row1, text="Periodo:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=10, anchor="w").pack(side="left")
        entry_per = ttk.Entry(row1)
        entry_per.pack(side="left", fill="x", expand=True)

        row2 = tk.Frame(form_frame, bg=PANEL)
        row2.pack(fill="x", padx=12, pady=4)
        tk.Label(row2, text="Título del proyecto (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=18, anchor="w").pack(side="left")
        entry_tit = ttk.Entry(row2)
        entry_tit.pack(side="left", fill="x", expand=True)

        row3 = tk.Frame(form_frame, bg=PANEL)
        row3.pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(row3, text="Resumen / Descripción:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_res = ttk.Entry(row3)
        entry_res.pack(side="left", fill="x", expand=True)

        list_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        lb = tk.Listbox(list_frame, font=("Segoe UI", 9), bg=PANEL, fg=DARK, relief="flat")
        sb_lb = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb_lb.set)
        lb.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        sb_lb.pack(side="right", fill="y")

        def refresh_lb() -> None:
            lb.delete(0, "end")
            for item in target_list:
                lb.insert("end", str(item))

        refresh_lb()

        def add_item() -> None:
            tip = combo_tipo.get().strip()
            tit = entry_tit.get().strip()
            per = entry_per.get().strip()
            res = entry_res.get().strip()

            if not tit:
                messagebox.showerror("Campo requerido", "El título del proyecto es obligatorio.", parent=sub)
            else:
                record_str = f"Tipo de proyecto: {tip} {tit}"
                if per:
                    if " - " in per:
                        p_parts = per.split(" - ", 1)
                        record_str = f"{record_str} Inicio: {p_parts[0].strip()} Fin: {p_parts[1].strip()}"
                    else:
                        record_str = f"{record_str} Inicio: {per}"
                if res:
                    record_str = f"{record_str} Resumen {res}"
                target_list.append(record_str)
                refresh_lb()
                update_btn_cb()
                entry_tit.delete(0, "end")
                entry_per.delete(0, "end")
                entry_res.delete(0, "end")

        def delete_item() -> None:
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                if 0 <= idx < len(target_list):
                    target_list.pop(idx)
                    refresh_lb()
                    update_btn_cb()

        btn_row = tk.Frame(form_frame, bg=PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Button(btn_row, text="+ Agregar Proyecto a la lista", style="Primary.TButton", command=add_item).pack(side="left")

        bottom_bar = tk.Frame(sub, bg=BG)
        bottom_bar.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(bottom_bar, text="Eliminar seleccionado", command=delete_item).pack(side="left")
        ttk.Button(bottom_bar, text="Cerrar ventana", command=on_sub_close).pack(side="right")

    def _open_idiomas_subwindow(
        self,
        parent_win: tk.Toplevel,
        active_subs: List[tk.Toplevel],
        target_list: List[str],
        update_btn_cb: Any
    ) -> None:
        sub = tk.Toplevel(parent_win)
        sub.title("Gestionar Idiomas")
        sub.geometry("660x480")
        sub.configure(bg=BG)
        active_subs.append(sub)

        def on_sub_close() -> None:
            if sub in active_subs:
                active_subs.remove(sub)
            sub.destroy()

        sub.protocol("WM_DELETE_WINDOW", on_sub_close)

        top_bar = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_bar.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(top_bar, text="🗣️ Gestión de Idiomas", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(top_bar, text="Indique los idiomas dominados y las competencias comunicativas.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))

        form_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form_frame.pack(fill="x", padx=14, pady=(0, 8))

        row1 = tk.Frame(form_frame, bg=PANEL)
        row1.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(row1, text="Idioma (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=12, anchor="w").pack(side="left")
        entry_idioma = ttk.Entry(row1, width=20)
        entry_idioma.pack(side="left", padx=(0, 10))

        levels = ["Deficiente", "Regular", "Aceptable", "Bueno", "Excelente"]
        row2 = tk.Frame(form_frame, bg=PANEL)
        row2.pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(row2, text="Habla:", bg=PANEL, fg=DARK, font=("Segoe UI", 9)).pack(side="left")
        combo_habla = ttk.Combobox(row2, values=levels, state="readonly", width=9)
        combo_habla.set("Bueno")
        combo_habla.pack(side="left", padx=(4, 10))

        tk.Label(row2, text="Escribe:", bg=PANEL, fg=DARK, font=("Segoe UI", 9)).pack(side="left")
        combo_escribe = ttk.Combobox(row2, values=levels, state="readonly", width=9)
        combo_escribe.set("Bueno")
        combo_escribe.pack(side="left", padx=(4, 10))

        tk.Label(row2, text="Lee:", bg=PANEL, fg=DARK, font=("Segoe UI", 9)).pack(side="left")
        combo_lee = ttk.Combobox(row2, values=levels, state="readonly", width=9)
        combo_lee.set("Bueno")
        combo_lee.pack(side="left", padx=(4, 10))

        tk.Label(row2, text="Entiende:", bg=PANEL, fg=DARK, font=("Segoe UI", 9)).pack(side="left")
        combo_entiende = ttk.Combobox(row2, values=levels, state="readonly", width=9)
        combo_entiende.set("Bueno")
        combo_entiende.pack(side="left", padx=(4, 4))

        list_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        lb = tk.Listbox(list_frame, font=("Segoe UI", 9), bg=PANEL, fg=DARK, relief="flat")
        sb_lb = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb_lb.set)
        lb.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        sb_lb.pack(side="right", fill="y")

        def refresh_lb() -> None:
            lb.delete(0, "end")
            for item in target_list:
                lb.insert("end", str(item))

        refresh_lb()

        def add_item() -> None:
            idioma = entry_idioma.get().strip()
            h = combo_habla.get().strip()
            e = combo_escribe.get().strip()
            l = combo_lee.get().strip()
            en = combo_entiende.get().strip()

            if not idioma:
                messagebox.showerror("Campo requerido", "El nombre del idioma es obligatorio.", parent=sub)
            else:
                line_str = f"{idioma} | {h} | {e} | {l} | {en}"
                target_list.append(line_str)
                refresh_lb()
                update_btn_cb()
                entry_idioma.delete(0, "end")

        def delete_item() -> None:
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                if 0 <= idx < len(target_list):
                    target_list.pop(idx)
                    refresh_lb()
                    update_btn_cb()

        btn_row = tk.Frame(form_frame, bg=PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Button(btn_row, text="+ Agregar Idioma a la lista", style="Primary.TButton", command=add_item).pack(side="left")

        bottom_bar = tk.Frame(sub, bg=BG)
        bottom_bar.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(bottom_bar, text="Eliminar seleccionado", command=delete_item).pack(side="left")
        ttk.Button(bottom_bar, text="Cerrar ventana", command=on_sub_close).pack(side="right")

    def _open_integrantes_subwindow(
        self,
        parent_win: tk.Toplevel,
        active_subs: List[tk.Toplevel],
        target_list: List[Dict[str, Any]],
        update_btn_cb: Any
    ) -> None:
        sub = tk.Toplevel(parent_win)
        sub.title("Gestionar Integrantes del Grupo")
        sub.geometry("740x600")
        sub.minsize(700, 540)
        sub.configure(bg=BG)
        active_subs.append(sub)

        def on_sub_close() -> None:
            if sub in active_subs:
                active_subs.remove(sub)
            sub.destroy()

        sub.protocol("WM_DELETE_WINDOW", on_sub_close)

        top_bar = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_bar.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(top_bar, text="👥 Integrantes del Grupo (* Mínimo 2)", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(top_bar, text="Seleccione de los investigadores registrados o agregue integrantes. (Doble clic en un integrante para editar su Código RH o Correo).", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))

        form_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form_frame.pack(fill="x", padx=14, pady=(0, 8))

        row_existing = tk.Frame(form_frame, bg=PANEL)
        row_existing.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(row_existing, text="Investigador existente:", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=20, anchor="w").pack(side="left")

        inv_options = ["(Ninguno / Manual)"]
        for inv in self.service.investigadores:
            nm = inv.get("nombre", "")
            cd = inv.get("codigoRh", "")
            if nm:
                inv_options.append(f"{nm} [{cd}]")

        combo_invs = ttk.Combobox(row_existing, values=inv_options, state="readonly", width=38)
        combo_invs.set(inv_options[0])
        combo_invs.pack(side="left", padx=(0, 8))

        row_manual1 = tk.Frame(form_frame, bg=PANEL)
        row_manual1.pack(fill="x", padx=12, pady=4)
        tk.Label(row_manual1, text="Nombre (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=20, anchor="w").pack(side="left")
        entry_nom = ttk.Entry(row_manual1)
        entry_nom.pack(side="left", fill="x", expand=True)

        row_manual2 = tk.Frame(form_frame, bg=PANEL)
        row_manual2.pack(fill="x", padx=12, pady=4)
        tk.Label(row_manual2, text="Código RH:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
        entry_cod = ttk.Entry(row_manual2, width=18)
        entry_cod.pack(side="left", padx=(0, 10))
        tk.Label(row_manual2, text="Rol / Vinculación:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
        entry_rol = ttk.Entry(row_manual2)
        entry_rol.insert(0, "Investigador")
        entry_rol.pack(side="left", fill="x", expand=True)

        row_manual3 = tk.Frame(form_frame, bg=PANEL)
        row_manual3.pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(row_manual3, text="Correo Electrónico:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
        entry_cor = ttk.Entry(row_manual3)
        entry_cor.pack(side="left", fill="x", expand=True)

        def on_existing_selected(event: Any) -> None:
            sel_text = combo_invs.get().strip()
            if sel_text and sel_text != "(Ninguno / Manual)":
                for inv in self.service.investigadores:
                    nm = inv.get("nombre", "")
                    cd = inv.get("codigoRh", "")
                    opt = f"{nm} [{cd}]"
                    if opt == sel_text:
                        entry_nom.delete(0, "end")
                        entry_nom.insert(0, nm)
                        entry_cod.delete(0, "end")
                        entry_cod.insert(0, cd)
                        entry_cor.delete(0, "end")
                        entry_cor.insert(0, inv.get("correo", ""))

        combo_invs.bind("<<ComboboxSelected>>", on_existing_selected)

        def add_member() -> None:
            nom = entry_nom.get().strip()
            cod = entry_cod.get().strip()
            rol = entry_rol.get().strip()
            cor = entry_cor.get().strip()

            if not nom:
                messagebox.showerror("Campo requerido", "El nombre del integrante es obligatorio.", parent=sub)
            else:
                exists = False
                for m in target_list:
                    if canonical_key(str(m.get("nombre", ""))) == canonical_key(nom):
                        exists = True
                    elif cod and canonical_key(str(m.get("codigoRh", ""))) == canonical_key(cod):
                        exists = True
                if exists:
                    messagebox.showwarning("Integrante duplicado", "El integrante ya se encuentra en la lista.", parent=sub)
                else:
                    new_mem = {
                        "nombre": nom,
                        "codigoRh": cod,
                        "correo": cor,
                        "rol": rol,
                        "vinculacion": rol,
                        "tipo": "INVESTIGADOR"
                    }
                    target_list.append(new_mem)
                    refresh_table()
                    update_btn_cb()
                    entry_nom.delete(0, "end")
                    entry_cod.delete(0, "end")
                    entry_cor.delete(0, "end")
                    combo_invs.set(inv_options[0])

        def delete_member() -> None:
            sel = tree_mem.selection()
            if sel:
                remove_idx = -1
                tree_idx = tree_mem.index(sel[0])
                if 0 <= tree_idx < len(target_list):
                    remove_idx = tree_idx
                else:
                    vals = tree_mem.item(sel[0], "values")
                    if vals:
                        target_name = str(vals[0])
                        target_cod = str(vals[1])
                        idx = 0
                        while idx < len(target_list) and remove_idx == -1:
                            m = target_list[idx]
                            if str(m.get("nombre", "")) == target_name and str(m.get("codigoRh", "")) == target_cod:
                                remove_idx = idx
                            elif str(m.get("nombre", "")).strip().casefold() == target_name.strip().casefold():
                                remove_idx = idx
                            idx += 1
                if remove_idx != -1:
                    target_list.pop(remove_idx)
                    refresh_table()
                    update_btn_cb()

        btn_row = tk.Frame(form_frame, bg=PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Button(btn_row, text="+ Agregar Integrante a la lista", style="Primary.TButton", command=add_member).pack(side="left")

        bottom_bar = tk.Frame(sub, bg=BG)
        bottom_bar.pack(side="bottom", fill="x", padx=14, pady=(0, 14))
        ttk.Button(bottom_bar, text="Eliminar seleccionado", command=delete_member).pack(side="left")
        ttk.Button(bottom_bar, text="Cerrar ventana", command=on_sub_close).pack(side="right")

        tree_frame = tk.Frame(sub, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        cols = [("nombre", "Nombre", 250), ("codigo", "Código RH", 120), ("rol", "Rol / Vinculación", 140), ("correo", "Correo", 140)]
        tree_mem = ttk.Treeview(tree_frame, columns=[c[0] for c in cols], show="headings")
        sb_mem = ttk.Scrollbar(tree_frame, orient="vertical", command=tree_mem.yview)
        tree_mem.configure(yscrollcommand=sb_mem.set)
        for cid, clbl, cwidth in cols:
            tree_mem.heading(cid, text=clbl)
            tree_mem.column(cid, width=cwidth, anchor="w")
        tree_mem.pack(side="left", fill="both", expand=True)
        sb_mem.pack(side="right", fill="y")

        def on_double_click_member(event: tk.Event) -> None:
            sel = tree_mem.selection()
            if sel:
                tree_idx = tree_mem.index(sel[0])
                target_mem = None
                if 0 <= tree_idx < len(target_list):
                    target_mem = target_list[tree_idx]
                else:
                    vals = tree_mem.item(sel[0], "values")
                    if vals:
                        t_nom = str(vals[0])
                        idx = 0
                        while idx < len(target_list) and target_mem is None:
                            if str(target_list[idx].get("nombre", "")).strip().casefold() == t_nom.strip().casefold():
                                target_mem = target_list[idx]
                            idx += 1

                if target_mem is not None:
                    edit_dlg = tk.Toplevel(sub)
                    edit_dlg.title("Editar Integrante del Grupo")
                    edit_dlg.geometry("480x360")
                    edit_dlg.minsize(440, 320)
                    edit_dlg.configure(bg=BG)
                    edit_dlg.transient(sub)
                    edit_dlg.grab_set()

                    e_top = tk.Frame(edit_dlg, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
                    e_top.pack(fill="x", padx=14, pady=(14, 10))
                    tk.Label(e_top, text="👤 Información del Integrante", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
                    tk.Label(e_top, text="Edite los datos del integrante (Nombre, Rol, Código RH y Correo).", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0, 8))

                    e_form = tk.Frame(edit_dlg, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
                    e_form.pack(fill="both", expand=True, padx=14, pady=(0, 10))

                    r_ed0 = tk.Frame(e_form, bg=PANEL)
                    r_ed0.pack(fill="x", padx=12, pady=(10, 4))
                    tk.Label(r_ed0, text="Nombre (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=16, anchor="w").pack(side="left")
                    ent_ed_nom = ttk.Entry(r_ed0)
                    ent_ed_nom.insert(0, str(target_mem.get("nombre", "")))
                    ent_ed_nom.pack(side="left", fill="x", expand=True)

                    r_ed_rol = tk.Frame(e_form, bg=PANEL)
                    r_ed_rol.pack(fill="x", padx=12, pady=4)
                    tk.Label(r_ed_rol, text="Rol / Vinculación:", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=16, anchor="w").pack(side="left")
                    ent_ed_rol = ttk.Entry(r_ed_rol)
                    cur_rol = str(target_mem.get("vinculacion", "") or target_mem.get("rol", "Integrante"))
                    ent_ed_rol.insert(0, cur_rol)
                    ent_ed_rol.pack(side="left", fill="x", expand=True)

                    r_ed1 = tk.Frame(e_form, bg=PANEL)
                    r_ed1.pack(fill="x", padx=12, pady=4)
                    tk.Label(r_ed1, text="Código RH:", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=16, anchor="w").pack(side="left")
                    ent_ed_cod = ttk.Entry(r_ed1)
                    ent_ed_cod.insert(0, str(target_mem.get("codigoRh", "")))
                    ent_ed_cod.pack(side="left", fill="x", expand=True)

                    r_ed2 = tk.Frame(e_form, bg=PANEL)
                    r_ed2.pack(fill="x", padx=12, pady=(4, 10))
                    tk.Label(r_ed2, text="Correo Electrónico:", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=16, anchor="w").pack(side="left")
                    ent_ed_cor = ttk.Entry(r_ed2)
                    ent_ed_cor.insert(0, str(target_mem.get("correo", "")))
                    ent_ed_cor.pack(side="left", fill="x", expand=True)

                    def save_member_data() -> None:
                        new_nom = ent_ed_nom.get().strip()
                        new_rol = ent_ed_rol.get().strip()
                        new_rh = ent_ed_cod.get().strip()
                        new_email = ent_ed_cor.get().strip()

                        if not new_nom:
                            messagebox.showerror("Campo requerido", "El nombre del integrante es obligatorio.", parent=edit_dlg)
                        else:
                            target_mem["nombre"] = new_nom
                            target_mem["rol"] = new_rol or "Integrante"
                            target_mem["vinculacion"] = new_rol or "Integrante"
                            target_mem["codigoRh"] = new_rh
                            target_mem["correo"] = new_email
                            refresh_table()
                            update_btn_cb()
                            edit_dlg.destroy()

                    e_btns = tk.Frame(edit_dlg, bg=BG)
                    e_btns.pack(fill="x", padx=14, pady=(0, 12))
                    ttk.Button(e_btns, text="💾 Guardar Cambios", style="Primary.TButton", command=save_member_data).pack(side="left")
                    ttk.Button(e_btns, text="Cancelar", command=edit_dlg.destroy).pack(side="right")

        tree_mem.bind("<Double-1>", on_double_click_member)

        def refresh_table() -> None:
            for item_id in tree_mem.get_children():
                tree_mem.delete(item_id)
            for m in target_list:
                rol_str = m.get("vinculacion", "")
                if not rol_str:
                    rol_str = m.get("rol", "")
                tree_mem.insert("", "end", values=(
                    m.get("nombre", ""),
                    m.get("codigoRh", ""),
                    rol_str,
                    m.get("correo", "")
                ))

        refresh_table()

    def open_create_investigator_dialog(self, tree: ttk.Treeview) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Crear Nuevo Investigador")
        dialog.geometry("780x700")
        dialog.minsize(700, 600)
        dialog.configure(bg=BG)

        active_subwindows: List[tk.Toplevel] = []
        added_productos: List[Dict[str, Any]] = []
        added_formacion: List[str] = []
        added_experiencia: List[str] = []
        added_lineas: List[str] = []
        added_proyectos: List[str] = []
        added_areas: List[str] = []
        added_reconocimientos: List[str] = []
        added_idiomas: List[str] = []

        def on_dialog_close() -> None:
            if self._has_active_subwindows(active_subwindows):
                messagebox.showwarning(
                    "Ventana secundaria abierta",
                    "No se puede cerrar esta ventana mientras haya ventanas adicionales abiertas.\nPor favor cierre primero las ventanas secundarias.",
                    parent=dialog
                )
            else:
                dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

        top_header = tk.Frame(dialog, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_header.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(top_header, text="➕ Crear Nuevo Investigador", bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(top_header, text="Complete los datos del investigador. Los campos con (*) son obligatorios. Las colecciones adicionales son opcionales.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(0, 12))

        container = tk.Frame(dialog, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_content = tk.Frame(canvas, bg=BG)
        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event: tk.Event) -> None:
            delta = 1
            if hasattr(event, "delta") and event.delta > 0:
                delta = -1
            canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        card1 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card1.pack(fill="x", pady=(0, 10))
        tk.Label(card1, text="Información Básica Obligatoria (*)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c1_1 = tk.Frame(card1, bg=PANEL)
        r_c1_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_1, text="Código RH (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_codigo = ttk.Entry(r_c1_1)
        entry_codigo.pack(side="left", fill="x", expand=True)

        r_c1_2 = tk.Frame(card1, bg=PANEL)
        r_c1_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_2, text="Nombre Completo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nombre = ttk.Entry(r_c1_2)
        entry_nombre.pack(side="left", fill="x", expand=True)

        r_c1_3 = tk.Frame(card1, bg=PANEL)
        r_c1_3.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_3, text="Nombre en Citaciones (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nom_cit = ttk.Entry(r_c1_3)
        entry_nom_cit.pack(side="left", fill="x", expand=True)

        r_c1_4 = tk.Frame(card1, bg=PANEL)
        r_c1_4.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_4, text="Departamento (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_depto = ttk.Entry(r_c1_4, width=22)
        entry_depto.pack(side="left", padx=(0, 10))
        tk.Label(r_c1_4, text="Ciudad (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=12, anchor="w").pack(side="left")
        entry_ciudad = ttk.Entry(r_c1_4)
        entry_ciudad.pack(side="left", fill="x", expand=True)

        r_c1_5 = tk.Frame(card1, bg=PANEL)
        r_c1_5.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_5, text="Nacionalidad (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nac = ttk.Entry(r_c1_5, width=22)
        entry_nac.insert(0, "Colombiana")
        entry_nac.pack(side="left", padx=(0, 10))
        tk.Label(r_c1_5, text="Sexo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=12, anchor="w").pack(side="left")
        combo_sexo = ttk.Combobox(r_c1_5, values=["Masculino", "Femenino", "Otro", ""], width=18)
        combo_sexo.pack(side="left")

        r_c1_6 = tk.Frame(card1, bg=PANEL)
        r_c1_6.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c1_6, text="Correo Electrónico (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_correo = ttk.Entry(r_c1_6)
        entry_correo.pack(side="left", fill="x", expand=True)

        card2 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card2.pack(fill="x", pady=(0, 10))
        tk.Label(card2, text="Información Personal y Académica (Opcional)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c2_1 = tk.Frame(card2, bg=PANEL)
        r_c2_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_1, text="Categoría Minciencias:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        combo_cat_inv = ttk.Combobox(r_c2_1, values=["Investigador Emérito", "Investigador Senior (I)", "Investigador Asociado (I)", "Investigador Junior (IJ)", "Sin categoría", ""], width=32)
        combo_cat_inv.pack(side="left", padx=(0, 10))
        tk.Label(r_c2_1, text="Institución:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        entry_inst = ttk.Entry(r_c2_1)
        entry_inst.pack(side="left", fill="x", expand=True)

        r_c2_2 = tk.Frame(card2, bg=PANEL)
        r_c2_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_2, text="ORCID:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_orcid = ttk.Entry(r_c2_2, width=32)
        entry_orcid.pack(side="left", padx=(0, 10))
        tk.Label(r_c2_2, text="Par Evaluador:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        combo_par = ttk.Combobox(r_c2_2, values=["Par evaluador reconocido por Minciencias.", "No", ""], width=24)
        combo_par.pack(side="left")

        r_c2_3 = tk.Frame(card2, bg=PANEL)
        r_c2_3.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c2_3, text="Perfil / Biografía:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_perfil = ttk.Entry(r_c2_3)
        entry_perfil.pack(side="left", fill="x", expand=True)

        card3 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card3.pack(fill="x", pady=(0, 10))
        tk.Label(card3, text="Identificadores y Redes Académicas (Opcional)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c3_1 = tk.Frame(card3, bg=PANEL)
        r_c3_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c3_1, text="ResearcherID:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_res_id = ttk.Entry(r_c3_1, width=28)
        entry_res_id.pack(side="left", padx=(0, 10))
        tk.Label(r_c3_1, text="Scopus ID:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_scopus = ttk.Entry(r_c3_1)
        entry_scopus.pack(side="left", fill="x", expand=True)

        r_c3_2 = tk.Frame(card3, bg=PANEL)
        r_c3_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c3_2, text="Google Scholar:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_scholar = ttk.Entry(r_c3_2, width=28)
        entry_scholar.pack(side="left", padx=(0, 10))
        tk.Label(r_c3_2, text="ResearchGate:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_rgate = ttk.Entry(r_c3_2)
        entry_rgate.pack(side="left", fill="x", expand=True)

        r_c3_3 = tk.Frame(card3, bg=PANEL)
        r_c3_3.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c3_3, text="Academia.edu:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_acad = ttk.Entry(r_c3_3, width=28)
        entry_acad.pack(side="left", padx=(0, 10))
        tk.Label(r_c3_3, text="Mendeley:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_mend = ttk.Entry(r_c3_3)
        entry_mend.pack(side="left", fill="x", expand=True)

        r_c3_4 = tk.Frame(card3, bg=PANEL)
        r_c3_4.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c3_4, text="LinkedIn:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_link = ttk.Entry(r_c3_4, width=28)
        entry_link.pack(side="left", padx=(0, 10))
        tk.Label(r_c3_4, text="Repositorio:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_repo = ttk.Entry(r_c3_4)
        entry_repo.pack(side="left", fill="x", expand=True)

        card4 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card4.pack(fill="x", pady=(0, 10))
        tk.Label(card4, text="Colecciones Adicionales (Ventanas Secundarias)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Label(card4, text="Estos campos son opcionales durante la creación. Cada botón despliega una ventana secundaria dedicada:", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(0, 10))

        grid_btns = tk.Frame(card4, bg=PANEL)
        grid_btns.pack(fill="x", padx=14, pady=(0, 12))

        btn_prod = ttk.Button(grid_btns, text="📦 Productos (0)", command=lambda: self._open_products_subwindow(dialog, active_subwindows, added_productos, update_badges))
        btn_prod.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        btn_form = ttk.Button(grid_btns, text="🎓 Formación (0)", command=lambda: self._open_formacion_subwindow(dialog, active_subwindows, added_formacion, update_badges))
        btn_form.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        btn_exp = ttk.Button(grid_btns, text="💼 Experiencia (0)", command=lambda: self._open_experiencia_subwindow(dialog, active_subwindows, added_experiencia, update_badges))
        btn_exp.grid(row=0, column=2, sticky="ew", padx=4, pady=4)

        btn_lin = ttk.Button(grid_btns, text="🔬 Líneas Inv. (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Líneas de Investigación", "Nombre de la línea de investigación:", added_lineas, update_badges, "Ej: Inteligencia Artificial, Activa: Si"))
        btn_lin.grid(row=0, column=3, sticky="ew", padx=4, pady=4)

        btn_proy = ttk.Button(grid_btns, text="📁 Proyectos (0)", command=lambda: self._open_proyectos_subwindow(dialog, active_subwindows, added_proyectos, update_badges))
        btn_proy.grid(row=1, column=0, sticky="ew", padx=4, pady=4)

        btn_area = ttk.Button(grid_btns, text="🌐 Áreas Conoc. (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Áreas de Conocimiento", "Gran Área -- Área -- Disciplina:", added_areas, update_badges, "Ej: Ingeniería y Tecnología -- Computación"))
        btn_area.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        btn_rec = ttk.Button(grid_btns, text="🏆 Reconocimientos (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Reconocimientos", "Reconocimiento / Otorgante / Año:", added_reconocimientos, update_badges, "Ej: Reconocimiento Investigador, Minciencias - 2024"))
        btn_rec.grid(row=1, column=2, sticky="ew", padx=4, pady=4)

        btn_idi = ttk.Button(grid_btns, text="🗣️ Idiomas (0)", command=lambda: self._open_idiomas_subwindow(dialog, active_subwindows, added_idiomas, update_badges))
        btn_idi.grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        for col_i in range(4):
            grid_btns.columnconfigure(col_i, weight=1)

        def update_badges() -> None:
            btn_prod.configure(text=f"📦 Productos ({len(added_productos)})")
            btn_form.configure(text=f"🎓 Formación ({len(added_formacion)})")
            btn_exp.configure(text=f"💼 Experiencia ({len(added_experiencia)})")
            btn_lin.configure(text=f"🔬 Líneas Inv. ({len(added_lineas)})")
            btn_proy.configure(text=f"📁 Proyectos ({len(added_proyectos)})")
            btn_area.configure(text=f"🌐 Áreas Conoc. ({len(added_areas)})")
            btn_rec.configure(text=f"🏆 Reconocimientos ({len(added_reconocimientos)})")
            btn_idi.configure(text=f"🗣️ Idiomas ({len(added_idiomas)})")

        def save_investigator() -> None:
            if self._has_active_subwindows(active_subwindows):
                messagebox.showwarning(
                    "Ventana secundaria abierta",
                    "No se puede continuar mientras existan ventanas secundarias abiertas.\nPor favor cierre primero las ventanas secundarias.",
                    parent=dialog
                )
            else:
                cod = entry_codigo.get().strip()
                nom = entry_nombre.get().strip()
                dep = entry_depto.get().strip()
                ciu = entry_ciudad.get().strip()
                nac = entry_nac.get().strip()
                sex = combo_sexo.get().strip()
                cor = entry_correo.get().strip()
                cit = entry_nom_cit.get().strip()

                if not cod:
                    messagebox.showerror("Campo obligatorio", "El código RH / identificador del investigador es obligatorio.", parent=dialog)
                elif not nom:
                    messagebox.showerror("Campo obligatorio", "El nombre completo del investigador es obligatorio.", parent=dialog)
                elif not cit:
                    messagebox.showerror("Campo obligatorio", "El nombre en citaciones del investigador es obligatorio.", parent=dialog)
                elif not dep:
                    messagebox.showerror("Campo obligatorio", "El departamento del investigador es obligatorio.", parent=dialog)
                elif not ciu:
                    messagebox.showerror("Campo obligatorio", "La ciudad del investigador es obligatoria.", parent=dialog)
                elif not nac:
                    messagebox.showerror("Campo obligatorio", "La nacionalidad del investigador es obligatoria.", parent=dialog)
                elif not sex:
                    messagebox.showerror("Campo obligatorio", "El sexo del investigador es obligatorio.", parent=dialog)
                elif not cor:
                    messagebox.showerror("Campo obligatorio", "El correo electrónico del investigador es obligatorio.", parent=dialog)
                else:
                    data = {
                        "codigoRh": cod,
                        "nombre": nom,
                        "correo": cor,
                        "orcid": entry_orcid.get().strip(),
                        "institucion": entry_inst.get().strip(),
                        "departamento": dep,
                        "ciudad": ciu,
                        "categoriaInvestigador": combo_cat_inv.get().strip(),
                        "perfil": entry_perfil.get().strip(),
                        "nombreCitaciones": cit,
                        "nacionalidad": nac,
                        "sexo": sex,
                        "estadoParEvaluador": combo_par.get().strip(),
                        "researcherId": entry_res_id.get().strip(),
                        "autorIdScopus": entry_scopus.get().strip(),
                        "googleScholar": entry_scholar.get().strip(),
                        "researchGate": entry_rgate.get().strip(),
                        "academiaEdu": entry_acad.get().strip(),
                        "mendeley": entry_mend.get().strip(),
                        "linkedin": entry_link.get().strip(),
                        "repositorioInstitucional": entry_repo.get().strip(),
                        "idiomas": list(added_idiomas),
                        "areasConocimiento": list(added_areas),
                        "lineasInvestigacion": list(added_lineas),
                        "formacionAcademica": list(added_formacion),
                        "experienciaProfesional": list(added_experiencia),
                        "gruposInvestigacion": [],
                        "semilleros": [],
                        "proyectos": list(added_proyectos),
                        "reconocimientos": list(added_reconocimientos),
                        "productos": list(added_productos),
                        "activo": True
                    }
                    ok, msg = self.service.create_investigator(data)
                    if ok:
                        messagebox.showinfo("Éxito", msg)
                        self.refresh_investigator_tree(tree, "")
                        self.status.set("Investigador agregado correctamente: " + nom)
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error al crear investigador", msg, parent=dialog)

        bottom_bar = tk.Frame(dialog, bg=BG)
        bottom_bar.pack(fill="x", padx=16, pady=(0, 14))
        ttk.Button(bottom_bar, text="Guardar Investigador", style="Primary.TButton", command=save_investigator).pack(side="left")
        ttk.Button(bottom_bar, text="Cancelar", command=on_dialog_close).pack(side="right")

    def open_edit_investigator_dialog(
        self,
        investigator: Dict[str, Any],
        detail_win: tk.Toplevel,
        tree: Optional[ttk.Treeview],
        active_edit_window: List[tk.Toplevel]
    ) -> None:
        dialog = tk.Toplevel(detail_win)
        dialog.title("Modificar Investigador - " + str(investigator.get("nombre", "")))
        dialog.geometry("780x700")
        dialog.minsize(700, 600)
        dialog.configure(bg=BG)
        active_edit_window.append(dialog)

        active_subwindows: List[tk.Toplevel] = []
        added_productos: List[Dict[str, Any]] = []
        for itm in investigator.get("productos", []):
            if isinstance(itm, dict):
                added_productos.append(copy.deepcopy(itm))
            else:
                added_productos.append({
                    "idProducto": "P" + str(len(added_productos) + 1),
                    "titulo": str(itm),
                    "categoria": "Otro",
                    "tipoProducto": "Otro",
                    "subtipo": "",
                    "anio": 0,
                    "autores": [],
                    "pais": "",
                    "ciudad": "",
                    "institucion": "",
                    "doi": "",
                    "isbn": "",
                    "revista": "",
                    "editorial": "",
                    "disponibilidad": "",
                    "numeroContrato": "",
                    "descripcion": "",
                    "palabrasClave": "",
                    "areas": "",
                    "validado": False
                })

        added_formacion: List[str] = list(investigator.get("formacionAcademica", []))
        added_experiencia: List[str] = list(investigator.get("experienciaProfesional", []))
        added_lineas: List[str] = list(investigator.get("lineasInvestigacion", []))
        added_proyectos: List[str] = list(investigator.get("proyectos", []))
        added_areas: List[str] = list(investigator.get("areasConocimiento", []))
        added_reconocimientos: List[str] = list(investigator.get("reconocimientos", []))
        added_idiomas: List[str] = list(investigator.get("idiomas", []))

        def on_dialog_close() -> None:
            if self._has_active_subwindows(active_subwindows):
                messagebox.showwarning(
                    "Ventana secundaria abierta",
                    "No se puede cerrar esta ventana mientras haya ventanas adicionales abiertas.\nPor favor cierre primero las ventanas secundarias.",
                    parent=dialog
                )
            else:
                if dialog in active_edit_window:
                    active_edit_window.remove(dialog)
                dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

        top_header = tk.Frame(dialog, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_header.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(top_header, text="✏️ Modificar Investigador", bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(top_header, text="Edite los datos del investigador. Los campos con (*) son obligatorios. Las colecciones adicionales se gestionan con sus botones.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(0, 12))

        container = tk.Frame(dialog, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_content = tk.Frame(canvas, bg=BG)
        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event: tk.Event) -> None:
            delta = 1
            if hasattr(event, "delta") and event.delta > 0:
                delta = -1
            canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        card1 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card1.pack(fill="x", pady=(0, 10))
        tk.Label(card1, text="Información Básica Obligatoria (*)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c1_1 = tk.Frame(card1, bg=PANEL)
        r_c1_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_1, text="Código RH (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_codigo = ttk.Entry(r_c1_1)
        entry_codigo.insert(0, str(investigator.get("codigoRh", "")))
        entry_codigo.pack(side="left", fill="x", expand=True)

        r_c1_2 = tk.Frame(card1, bg=PANEL)
        r_c1_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_2, text="Nombre Completo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nombre = ttk.Entry(r_c1_2)
        entry_nombre.insert(0, str(investigator.get("nombre", "")))
        entry_nombre.pack(side="left", fill="x", expand=True)

        r_c1_3 = tk.Frame(card1, bg=PANEL)
        r_c1_3.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_3, text="Nombre en Citaciones (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nom_cit = ttk.Entry(r_c1_3)
        entry_nom_cit.insert(0, str(investigator.get("nombreCitaciones", "")))
        entry_nom_cit.pack(side="left", fill="x", expand=True)

        r_c1_4 = tk.Frame(card1, bg=PANEL)
        r_c1_4.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_4, text="Departamento (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_depto = ttk.Entry(r_c1_4, width=22)
        entry_depto.insert(0, str(investigator.get("departamento", "")))
        entry_depto.pack(side="left", padx=(0, 10))
        tk.Label(r_c1_4, text="Ciudad (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=12, anchor="w").pack(side="left")
        entry_ciudad = ttk.Entry(r_c1_4)
        entry_ciudad.insert(0, str(investigator.get("ciudad", "")))
        entry_ciudad.pack(side="left", fill="x", expand=True)

        r_c1_5 = tk.Frame(card1, bg=PANEL)
        r_c1_5.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_5, text="Nacionalidad (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nac = ttk.Entry(r_c1_5, width=22)
        nac_val = str(investigator.get("nacionalidad", "")).strip()
        if not nac_val:
            nac_val = "Colombiana"
        entry_nac.insert(0, nac_val)
        entry_nac.pack(side="left", padx=(0, 10))
        tk.Label(r_c1_5, text="Sexo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=12, anchor="w").pack(side="left")
        combo_sexo = ttk.Combobox(r_c1_5, values=["Masculino", "Femenino", "Otro", ""], width=18)
        combo_sexo.set(str(investigator.get("sexo", "")))
        combo_sexo.pack(side="left")

        r_c1_6 = tk.Frame(card1, bg=PANEL)
        r_c1_6.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c1_6, text="Correo Electrónico (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_correo = ttk.Entry(r_c1_6)
        cor_val = str(investigator.get("correo", "") or investigator.get("email", "")).strip()
        entry_correo.insert(0, cor_val)
        entry_correo.pack(side="left", fill="x", expand=True)

        card2 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card2.pack(fill="x", pady=(0, 10))
        tk.Label(card2, text="Información Personal y Académica (Opcional)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c2_1 = tk.Frame(card2, bg=PANEL)
        r_c2_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_1, text="Categoría Minciencias:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        combo_cat_inv = ttk.Combobox(r_c2_1, values=["Investigador Emérito", "Investigador Senior (I)", "Investigador Asociado (I)", "Investigador Junior (IJ)", "Sin categoría", ""], width=32)
        combo_cat_inv.set(str(investigator.get("categoriaInvestigador", "")))
        combo_cat_inv.pack(side="left", padx=(0, 10))
        tk.Label(r_c2_1, text="Institución:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        entry_inst = ttk.Entry(r_c2_1)
        entry_inst.insert(0, str(investigator.get("institucion", "")))
        entry_inst.pack(side="left", fill="x", expand=True)

        r_c2_2 = tk.Frame(card2, bg=PANEL)
        r_c2_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_2, text="ORCID:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_orcid = ttk.Entry(r_c2_2, width=32)
        entry_orcid.insert(0, str(investigator.get("orcid", "")))
        entry_orcid.pack(side="left", padx=(0, 10))
        tk.Label(r_c2_2, text="Par Evaluador:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        combo_par = ttk.Combobox(r_c2_2, values=["Par evaluador reconocido por Minciencias.", "No", ""], width=24)
        combo_par.set(str(investigator.get("estadoParEvaluador", "")))
        combo_par.pack(side="left")

        r_c2_3 = tk.Frame(card2, bg=PANEL)
        r_c2_3.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c2_3, text="Perfil / Biografía:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_perfil = ttk.Entry(r_c2_3)
        entry_perfil.insert(0, str(investigator.get("perfil", "")))
        entry_perfil.pack(side="left", fill="x", expand=True)

        card3 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card3.pack(fill="x", pady=(0, 10))
        tk.Label(card3, text="Identificadores y Redes Académicas (Opcional)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c3_1 = tk.Frame(card3, bg=PANEL)
        r_c3_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c3_1, text="ResearcherID:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_res_id = ttk.Entry(r_c3_1, width=28)
        entry_res_id.insert(0, str(investigator.get("researcherId", "")))
        entry_res_id.pack(side="left", padx=(0, 10))
        tk.Label(r_c3_1, text="Scopus ID:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_scopus = ttk.Entry(r_c3_1)
        entry_scopus.insert(0, str(investigator.get("autorIdScopus", "")))
        entry_scopus.pack(side="left", fill="x", expand=True)

        r_c3_2 = tk.Frame(card3, bg=PANEL)
        r_c3_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c3_2, text="Google Scholar:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_scholar = ttk.Entry(r_c3_2, width=28)
        entry_scholar.insert(0, str(investigator.get("googleScholar", "")))
        entry_scholar.pack(side="left", padx=(0, 10))
        tk.Label(r_c3_2, text="ResearchGate:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_rgate = ttk.Entry(r_c3_2)
        entry_rgate.insert(0, str(investigator.get("researchGate", "")))
        entry_rgate.pack(side="left", fill="x", expand=True)

        r_c3_3 = tk.Frame(card3, bg=PANEL)
        r_c3_3.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c3_3, text="Academia.edu:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_acad = ttk.Entry(r_c3_3, width=28)
        entry_acad.insert(0, str(investigator.get("academiaEdu", "")))
        entry_acad.pack(side="left", padx=(0, 10))
        tk.Label(r_c3_3, text="Mendeley:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_mend = ttk.Entry(r_c3_3)
        entry_mend.insert(0, str(investigator.get("mendeley", "")))
        entry_mend.pack(side="left", fill="x", expand=True)

        r_c3_4 = tk.Frame(card3, bg=PANEL)
        r_c3_4.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c3_4, text="LinkedIn:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_link = ttk.Entry(r_c3_4, width=28)
        entry_link.insert(0, str(investigator.get("linkedin", "")))
        entry_link.pack(side="left", padx=(0, 10))
        tk.Label(r_c3_4, text="Repositorio:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        entry_repo = ttk.Entry(r_c3_4)
        entry_repo.insert(0, str(investigator.get("repositorioInstitucional", "")))
        entry_repo.pack(side="left", fill="x", expand=True)

        card4 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card4.pack(fill="x", pady=(0, 10))
        tk.Label(card4, text="Colecciones Adicionales (Ventanas Secundarias)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Label(card4, text="Puede agregar o eliminar elementos de cada colección mediante sus ventanas secundarias:", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(0, 10))

        grid_btns = tk.Frame(card4, bg=PANEL)
        grid_btns.pack(fill="x", padx=14, pady=(0, 12))

        btn_prod = ttk.Button(grid_btns, text="📦 Productos (0)", command=lambda: self._open_products_subwindow(dialog, active_subwindows, added_productos, update_badges))
        btn_prod.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        btn_form = ttk.Button(grid_btns, text="🎓 Formación (0)", command=lambda: self._open_formacion_subwindow(dialog, active_subwindows, added_formacion, update_badges))
        btn_form.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        btn_exp = ttk.Button(grid_btns, text="💼 Experiencia (0)", command=lambda: self._open_experiencia_subwindow(dialog, active_subwindows, added_experiencia, update_badges))
        btn_exp.grid(row=0, column=2, sticky="ew", padx=4, pady=4)

        btn_lin = ttk.Button(grid_btns, text="🔬 Líneas Inv. (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Líneas de Investigación", "Nombre de la línea de investigación:", added_lineas, update_badges, "Ej: Inteligencia Artificial, Activa: Si"))
        btn_lin.grid(row=0, column=3, sticky="ew", padx=4, pady=4)

        btn_proy = ttk.Button(grid_btns, text="📁 Proyectos (0)", command=lambda: self._open_proyectos_subwindow(dialog, active_subwindows, added_proyectos, update_badges))
        btn_proy.grid(row=1, column=0, sticky="ew", padx=4, pady=4)

        btn_area = ttk.Button(grid_btns, text="🌐 Áreas Conoc. (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Áreas de Conocimiento", "Gran Área -- Área -- Disciplina:", added_areas, update_badges, "Ej: Ingeniería y Tecnología -- Computación"))
        btn_area.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        btn_rec = ttk.Button(grid_btns, text="🏆 Reconocimientos (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Reconocimientos", "Reconocimiento / Otorgante / Año:", added_reconocimientos, update_badges, "Ej: Reconocimiento Investigador, Minciencias - 2024"))
        btn_rec.grid(row=1, column=2, sticky="ew", padx=4, pady=4)

        btn_idi = ttk.Button(grid_btns, text="🗣️ Idiomas (0)", command=lambda: self._open_idiomas_subwindow(dialog, active_subwindows, added_idiomas, update_badges))
        btn_idi.grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        for col_i in range(4):
            grid_btns.columnconfigure(col_i, weight=1)

        def update_badges() -> None:
            btn_prod.configure(text=f"📦 Productos ({len(added_productos)})")
            btn_form.configure(text=f"🎓 Formación ({len(added_formacion)})")
            btn_exp.configure(text=f"💼 Experiencia ({len(added_experiencia)})")
            btn_lin.configure(text=f"🔬 Líneas Inv. ({len(added_lineas)})")
            btn_proy.configure(text=f"📁 Proyectos ({len(added_proyectos)})")
            btn_area.configure(text=f"🌐 Áreas Conoc. ({len(added_areas)})")
            btn_rec.configure(text=f"🏆 Reconocimientos ({len(added_reconocimientos)})")
            btn_idi.configure(text=f"🗣️ Idiomas ({len(added_idiomas)})")

        update_badges()

        def save_investigator_changes() -> None:
            if self._has_active_subwindows(active_subwindows):
                messagebox.showwarning(
                    "Ventana secundaria abierta",
                    "No se puede continuar mientras existan ventanas secundarias abiertas.\nPor favor cierre primero las ventanas secundarias.",
                    parent=dialog
                )
            else:
                cod = entry_codigo.get().strip()
                nom = entry_nombre.get().strip()
                dep = entry_depto.get().strip()
                ciu = entry_ciudad.get().strip()
                nac = entry_nac.get().strip()
                sex = combo_sexo.get().strip()
                cor = entry_correo.get().strip()
                cit = entry_nom_cit.get().strip()

                if not cod:
                    messagebox.showerror("Campo obligatorio", "El código RH / identificador del investigador es obligatorio.", parent=dialog)
                elif not nom:
                    messagebox.showerror("Campo obligatorio", "El nombre completo del investigador es obligatorio.", parent=dialog)
                elif not cit:
                    messagebox.showerror("Campo obligatorio", "El nombre en citaciones del investigador es obligatorio.", parent=dialog)
                elif not dep:
                    messagebox.showerror("Campo obligatorio", "El departamento del investigador es obligatorio.", parent=dialog)
                elif not ciu:
                    messagebox.showerror("Campo obligatorio", "La ciudad del investigador es obligatoria.", parent=dialog)
                elif not nac:
                    messagebox.showerror("Campo obligatorio", "La nacionalidad del investigador es obligatoria.", parent=dialog)
                elif not sex:
                    messagebox.showerror("Campo obligatorio", "El sexo del investigador es obligatorio.", parent=dialog)
                elif not cor:
                    messagebox.showerror("Campo obligatorio", "El correo electrónico del investigador es obligatorio.", parent=dialog)
                else:
                    updated_data = {
                        "codigoRh": cod,
                        "nombre": nom,
                        "correo": cor,
                        "orcid": entry_orcid.get().strip(),
                        "institucion": entry_inst.get().strip(),
                        "departamento": dep,
                        "ciudad": ciu,
                        "categoriaInvestigador": combo_cat_inv.get().strip(),
                        "perfil": entry_perfil.get().strip(),
                        "nombreCitaciones": cit,
                        "nacionalidad": nac,
                        "sexo": sex,
                        "estadoParEvaluador": combo_par.get().strip(),
                        "researcherId": entry_res_id.get().strip(),
                        "autorIdScopus": entry_scopus.get().strip(),
                        "googleScholar": entry_scholar.get().strip(),
                        "researchGate": entry_rgate.get().strip(),
                        "academiaEdu": entry_acad.get().strip(),
                        "mendeley": entry_mend.get().strip(),
                        "linkedin": entry_link.get().strip(),
                        "repositorioInstitucional": entry_repo.get().strip(),
                        "idiomas": list(added_idiomas),
                        "areasConocimiento": list(added_areas),
                        "lineasInvestigacion": list(added_lineas),
                        "formacionAcademica": list(added_formacion),
                        "experienciaProfesional": list(added_experiencia),
                        "gruposInvestigacion": list(investigator.get("gruposInvestigacion", [])),
                        "semilleros": list(investigator.get("semilleros", [])),
                        "proyectos": list(added_proyectos),
                        "reconocimientos": list(added_reconocimientos),
                        "productos": list(added_productos),
                        "activo": bool(investigator.get("activo", True))
                    }
                    ok, msg = self.service.update_investigator(investigator, updated_data)
                    if ok:
                        messagebox.showinfo("Éxito", msg)
                        target_trees = []
                        if tree is not None:
                            target_trees.append(tree)
                        if getattr(self, "main_investigator_tree", None) is not None:
                            if self.main_investigator_tree not in target_trees:
                                target_trees.append(self.main_investigator_tree)
                        for t in target_trees:
                            try:
                                if t.winfo_exists():
                                    self.refresh_investigator_tree(t, "")
                            except Exception:
                                pass
                        self.status.set("Investigador modificado correctamente: " + nom)
                        if dialog in active_edit_window:
                            active_edit_window.remove(dialog)
                        dialog.destroy()
                        if detail_win.winfo_exists():
                            detail_win.destroy()
                            self.show_investigator_detail_for_item(investigator, tree)
                    else:
                        messagebox.showerror("Error al modificar investigador", msg, parent=dialog)

        bottom_bar = tk.Frame(dialog, bg=BG)
        bottom_bar.pack(fill="x", padx=16, pady=(0, 14))
        ttk.Button(bottom_bar, text="💾 Guardar Cambios", style="Primary.TButton", command=save_investigator_changes).pack(side="left")
        ttk.Button(bottom_bar, text="Cancelar", command=on_dialog_close).pack(side="right")

    def open_create_group_dialog(self, tree: ttk.Treeview) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Crear Nuevo Grupo de Investigación")
        dialog.geometry("780x720")
        dialog.minsize(700, 600)
        dialog.configure(bg=BG)

        active_subwindows: List[tk.Toplevel] = []
        added_integrantes: List[Dict[str, Any]] = []
        added_productos: List[Dict[str, Any]] = []
        added_lineas: List[str] = []
        added_instituciones: List[str] = []

        def on_dialog_close() -> None:
            if self._has_active_subwindows(active_subwindows):
                messagebox.showwarning(
                    "Ventana secundaria abierta",
                    "No se puede cerrar esta ventana mientras haya ventanas adicionales abiertas.\n"
                    "Por favor cierre primero las ventanas secundarias.",
                    parent=dialog
                )
            else:
                dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

        top_header = tk.Frame(dialog, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_header.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(top_header, text="➕ Crear Nuevo Grupo de Investigación", bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(top_header, text="Complete los datos obligatorios (*). Se requiere institución con su plan estratégico y al menos 2 integrantes.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(0, 12))

        container = tk.Frame(dialog, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_content = tk.Frame(canvas, bg=BG)
        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event: tk.Event) -> None:
            delta = 1
            if hasattr(event, "delta") and event.delta > 0:
                delta = -1
            canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        card1 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card1.pack(fill="x", pady=(0, 10))
        tk.Label(card1, text="Información Básica Obligatoria (*)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c1_1 = tk.Frame(card1, bg=PANEL)
        r_c1_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_1, text="Nombre del Grupo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nom_grp = ttk.Entry(r_c1_1)
        entry_nom_grp.pack(side="left", fill="x", expand=True)

        r_c1_2 = tk.Frame(card1, bg=PANEL)
        r_c1_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_2, text="Código / Nro Grupo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nro_grp = ttk.Entry(r_c1_2, width=22)
        entry_nro_grp.pack(side="left", padx=(0, 10))
        tk.Label(r_c1_2, text="Año de Formación (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=18, anchor="w").pack(side="left")
        entry_anio_grp = ttk.Entry(r_c1_2)
        entry_anio_grp.insert(0, str(datetime.now().year))
        entry_anio_grp.pack(side="left", fill="x", expand=True)

        r_c1_3 = tk.Frame(card1, bg=PANEL)
        r_c1_3.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_3, text="Líder del Grupo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_lider_grp = ttk.Entry(r_c1_3)
        entry_lider_grp.pack(side="left", fill="x", expand=True)

        r_c1_4 = tk.Frame(card1, bg=PANEL)
        r_c1_4.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_4, text="Departamento (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_depto_grp = ttk.Entry(r_c1_4, width=22)
        entry_depto_grp.pack(side="left", padx=(0, 10))
        tk.Label(r_c1_4, text="Ciudad (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=18, anchor="w").pack(side="left")
        entry_ciudad_grp = ttk.Entry(r_c1_4)
        entry_ciudad_grp.pack(side="left", fill="x", expand=True)

        r_c1_5 = tk.Frame(card1, bg=PANEL)
        r_c1_5.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_5, text="Correo Electrónico (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_email_grp = ttk.Entry(r_c1_5)
        entry_email_grp.pack(side="left", fill="x", expand=True)

        r_c1_6 = tk.Frame(card1, bg=PANEL)
        r_c1_6.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_6, text="Institución Avaladora (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_inst_grp = ttk.Entry(r_c1_6)
        entry_inst_grp.pack(side="left", fill="x", expand=True)

        r_c1_7 = tk.Frame(card1, bg=PANEL)
        r_c1_7.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c1_7, text="Plan Estratégico (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(anchor="w", pady=(0, 2))
        text_plan_grp = tk.Text(r_c1_7, height=3, wrap="word", bg="#fbfcfe", font=("Segoe UI", 9), relief="solid", bd=1)
        text_plan_grp.pack(fill="x")

        card2 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card2.pack(fill="x", pady=(0, 10))
        tk.Label(card2, text="Información General del Grupo (Opcional)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c2_1 = tk.Frame(card2, bg=PANEL)
        r_c2_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_1, text="Clasificación Minciencias:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        combo_clasif_grp = ttk.Combobox(r_c2_1, values=["A1", "A", "B", "C", "Reconocido", "Sin clasificación", ""], width=20)
        combo_clasif_grp.pack(side="left", padx=(0, 10))
        tk.Label(r_c2_1, text="Área Conocimiento:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_area_grp = ttk.Entry(r_c2_1)
        entry_area_grp.pack(side="left", fill="x", expand=True)

        r_c2_2 = tk.Frame(card2, bg=PANEL)
        r_c2_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_2, text="Programa Nacional CTI:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_cti_grp = ttk.Entry(r_c2_2)
        entry_cti_grp.pack(side="left", fill="x", expand=True)

        r_c2_3 = tk.Frame(card2, bg=PANEL)
        r_c2_3.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_3, text="Programa Secundario:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_cti_sec = ttk.Entry(r_c2_3)
        entry_cti_sec.pack(side="left", fill="x", expand=True)

        r_c2_4 = tk.Frame(card2, bg=PANEL)
        r_c2_4.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_4, text="Página Web:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_web_grp = ttk.Entry(r_c2_4, width=28)
        entry_web_grp.pack(side="left", padx=(0, 10))
        tk.Label(r_c2_4, text="Info Certificada:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_cert_grp = ttk.Entry(r_c2_4)
        entry_cert_grp.pack(side="left", fill="x", expand=True)

        r_c2_5 = tk.Frame(card2, bg=PANEL)
        r_c2_5.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_5, text="Estado del Arte:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_arte_grp = ttk.Entry(r_c2_5)
        entry_arte_grp.pack(side="left", fill="x", expand=True)

        r_c2_6 = tk.Frame(card2, bg=PANEL)
        r_c2_6.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_6, text="Objetivos:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_obj_grp = ttk.Entry(r_c2_6)
        entry_obj_grp.pack(side="left", fill="x", expand=True)

        r_c2_7 = tk.Frame(card2, bg=PANEL)
        r_c2_7.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c2_7, text="Retos y Visión:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_retos_grp = ttk.Entry(r_c2_7)
        entry_retos_grp.pack(side="left", fill="x", expand=True)

        card3 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card3.pack(fill="x", pady=(0, 10))
        tk.Label(card3, text="Integrantes Obligatorios y Colecciones Adicionales", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Label(card3, text="Es obligatorio registrar al menos 2 integrantes. Productos, líneas e instituciones adicionales son opcionales:", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(0, 10))

        grid_btns_grp = tk.Frame(card3, bg=PANEL)
        grid_btns_grp.pack(fill="x", padx=14, pady=(0, 12))

        def open_integrantes_for_new_grp() -> None:
            lider_nom = entry_lider_grp.get().strip()
            if lider_nom:
                lider_canon = canonical_key(lider_nom)
                already_has_lider = False
                for m in added_integrantes:
                    if canonical_key(str(m.get("nombre", ""))) == lider_canon:
                        already_has_lider = True
                    elif str(m.get("rol", "")).strip().lower() == "líder" or str(m.get("vinculacion", "")).strip().lower() == "líder":
                        already_has_lider = True

                if not already_has_lider:
                    matching_cod = ""
                    matching_cor = ""
                    for inv in self.service.investigadores:
                        if canonical_key(str(inv.get("nombre", ""))) == lider_canon:
                            matching_cod = str(inv.get("codigoRh", ""))
                            matching_cor = str(inv.get("correo", ""))

                    lider_mem = {
                        "nombre": lider_nom,
                        "codigoRh": matching_cod,
                        "correo": matching_cor,
                        "rol": "Líder",
                        "vinculacion": "Líder",
                        "tipo": "INVESTIGADOR"
                    }
                    added_integrantes.insert(0, lider_mem)
                    update_badges_grp()

            self._open_integrantes_subwindow(dialog, active_subwindows, added_integrantes, update_badges_grp)

        btn_mem_grp = ttk.Button(grid_btns_grp, text="👥 Integrantes (* Mínimo 2) (0)", style="Primary.TButton", command=open_integrantes_for_new_grp)
        btn_mem_grp.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        btn_prod_grp = ttk.Button(grid_btns_grp, text="📦 Productos (0)", command=lambda: self._open_products_subwindow(dialog, active_subwindows, added_productos, update_badges_grp, is_group=True))
        btn_prod_grp.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        btn_lin_grp = ttk.Button(grid_btns_grp, text="🔬 Líneas Inv. (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Líneas de Investigación", "Nombre de la línea de investigación:", added_lineas, update_badges_grp, "Ej: Ingeniería de Software"))
        btn_lin_grp.grid(row=0, column=2, sticky="ew", padx=4, pady=4)

        btn_inst_grp = ttk.Button(grid_btns_grp, text="🏛️ Instituciones Extras (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Instituciones Adicionales", "Nombre de la institución avaladora adicional:", added_instituciones, update_badges_grp, "Ej: Universidad Nacional - (Avalado)"))
        btn_inst_grp.grid(row=0, column=3, sticky="ew", padx=4, pady=4)

        for col_i in range(4):
            grid_btns_grp.columnconfigure(col_i, weight=1)

        def update_badges_grp() -> None:
            btn_mem_grp.configure(text=f"👥 Integrantes (* Mínimo 2) ({len(added_integrantes)})")
            btn_prod_grp.configure(text=f"📦 Productos ({len(added_productos)})")
            btn_lin_grp.configure(text=f"🔬 Líneas Inv. ({len(added_lineas)})")
            btn_inst_grp.configure(text=f"🏛️ Instituciones Extras ({len(added_instituciones)})")

        def save_group() -> None:
            if self._has_active_subwindows(active_subwindows):
                messagebox.showwarning(
                    "Ventana secundaria abierta",
                    "No se puede continuar mientras existan ventanas secundarias abiertas.\n"
                    "Por favor cierre primero las ventanas secundarias.",
                    parent=dialog
                )
            else:
                nom = entry_nom_grp.get().strip()
                nro = entry_nro_grp.get().strip()
                lid = entry_lider_grp.get().strip()
                ani = entry_anio_grp.get().strip()
                dep = entry_depto_grp.get().strip()
                ciu = entry_ciudad_grp.get().strip()
                em = entry_email_grp.get().strip()
                inst = entry_inst_grp.get().strip()
                plan = text_plan_grp.get("1.0", "end").strip()

                if not nom:
                    messagebox.showerror("Campo obligatorio", "El nombre del grupo es obligatorio.", parent=dialog)
                elif not nro:
                    messagebox.showerror("Campo obligatorio", "El código / número de grupo es obligatorio.", parent=dialog)
                elif not lid:
                    messagebox.showerror("Campo obligatorio", "El líder del grupo es obligatorio.", parent=dialog)
                elif not ani:
                    messagebox.showerror("Campo obligatorio", "El año de formación es obligatorio.", parent=dialog)
                elif not dep:
                    messagebox.showerror("Campo obligatorio", "El departamento es obligatorio.", parent=dialog)
                elif not ciu:
                    messagebox.showerror("Campo obligatorio", "La ciudad es obligatoria.", parent=dialog)
                elif not em:
                    messagebox.showerror("Campo obligatorio", "El correo electrónico es obligatorio.", parent=dialog)
                elif not inst:
                    messagebox.showerror("Campo obligatorio", "La institución avaladora es obligatoria.", parent=dialog)
                elif not plan:
                    messagebox.showerror("Campo obligatorio", "El plan estratégico / de trabajo es obligatorio.", parent=dialog)
                elif len(added_integrantes) < 2:
                    messagebox.showerror(
                        "Integrantes insuficientes",
                        f"El grupo requiere al menos 2 integrantes registrados (actualmente tiene {len(added_integrantes)}).\n"
                        "Abra la ventana de 'Integrantes' para agregarlos.",
                        parent=dialog
                    )
                else:
                    instituciones_list = [
                        f"{inst} - (Avalado)",
                        "Plan Estratégico",
                        f"Plan de trabajo: {plan}"
                    ]
                    for extra in added_instituciones:
                        instituciones_list.append(extra)

                    data = {
                        "nroGrupo": nro,
                        "nombreGrupo": nom,
                        "anioFormacion": ani,
                        "departamento": dep,
                        "ciudad": ciu,
                        "lider": lid,
                        "informacionCertificada": entry_cert_grp.get().strip(),
                        "paginaWeb": entry_web_grp.get().strip(),
                        "email": em,
                        "clasificacion": combo_clasif_grp.get().strip(),
                        "areaConocimiento": entry_area_grp.get().strip(),
                        "programaNacionalCti": entry_cti_grp.get().strip(),
                        "programaNacionalCtiSecundario": entry_cti_sec.get().strip(),
                        "planEstrategico": plan,
                        "estadoArte": entry_arte_grp.get().strip(),
                        "objetivos": entry_obj_grp.get().strip(),
                        "retos": entry_retos_grp.get().strip(),
                        "vision": "",
                        "instituciones": instituciones_list,
                        "lineasInvestigacion": list(added_lineas),
                        "integrantes": list(added_integrantes),
                        "productos": list(added_productos)
                    }
                    ok, msg = self.service.create_group(data)
                    if ok:
                        messagebox.showinfo("Éxito", msg)
                        self.refresh_group_tree(tree, "")
                        self.status.set("Grupo creado correctamente: " + nom)
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error al crear grupo", msg, parent=dialog)

        bottom_bar = tk.Frame(dialog, bg=BG)
        bottom_bar.pack(fill="x", padx=16, pady=(0, 14))
        ttk.Button(bottom_bar, text="Crear Grupo", style="Primary.TButton", command=save_group).pack(side="left")
        ttk.Button(bottom_bar, text="Cancelar", command=on_dialog_close).pack(side="right")

    def open_edit_group_dialog(
        self,
        group: Dict[str, Any],
        detail_win: tk.Toplevel,
        tree: Optional[ttk.Treeview],
        active_edit_window: List[tk.Toplevel]
    ) -> None:
        dialog = tk.Toplevel(detail_win)
        dialog.title("Modificar Grupo - " + str(group.get("nombreGrupo", "")))
        dialog.geometry("780x720")
        dialog.minsize(700, 600)
        dialog.configure(bg=BG)
        active_edit_window.append(dialog)

        active_subwindows: List[tk.Toplevel] = []
        added_integrantes: List[Dict[str, Any]] = []
        for itm in group.get("integrantes", []):
            if isinstance(itm, dict):
                added_integrantes.append(copy.deepcopy(itm))
            else:
                added_integrantes.append({
                    "nombre": str(itm),
                    "codigoRh": "",
                    "correo": "",
                    "rol": "Integrante",
                    "vinculacion": "Integrante",
                    "tipo": "INVESTIGADOR"
                })

        added_productos: List[Dict[str, Any]] = []
        for itm in group.get("productos", []):
            if isinstance(itm, dict):
                added_productos.append(copy.deepcopy(itm))
            else:
                added_productos.append({
                    "idProducto": "P" + str(len(added_productos) + 1),
                    "titulo": str(itm),
                    "categoria": "Otro",
                    "tipoProducto": "Otro",
                    "subtipo": "",
                    "anio": 0,
                    "autores": [],
                    "pais": "",
                    "ciudad": "",
                    "institucion": "",
                    "doi": "",
                    "isbn": "",
                    "revista": "",
                    "editorial": "",
                    "disponibilidad": "",
                    "numeroContrato": "",
                    "descripcion": "",
                    "palabrasClave": "",
                    "areas": "",
                    "validado": False
                })

        added_lineas: List[str] = list(group.get("lineasInvestigacion", []))

        orig_insts = group.get("instituciones", [])
        main_inst = ""
        added_instituciones: List[str] = []
        for itm in orig_insts:
            s_itm = str(itm).strip()
            s_itm_lower = s_itm.lower()
            if s_itm_lower.startswith("plan estrat") or s_itm_lower.startswith("plan de trabajo:"):
                pass
            else:
                if not main_inst:
                    if " - (avalado)" in s_itm_lower:
                        main_inst = re.sub(r"\s*-\s*\(avalado\)", "", s_itm, flags=re.IGNORECASE).strip()
                    else:
                        main_inst = s_itm
                else:
                    added_instituciones.append(s_itm)

        if not main_inst and group.get("institucion"):
            main_inst = str(group.get("institucion", "")).strip()

        plan_str = str(group.get("planEstrategico", "")).strip()
        if not plan_str:
            for itm in orig_insts:
                s_itm = str(itm).strip()
                if s_itm.lower().startswith("plan de trabajo:"):
                    plan_str = s_itm[16:].strip()

        def on_dialog_close() -> None:
            if self._has_active_subwindows(active_subwindows):
                messagebox.showwarning(
                    "Ventana secundaria abierta",
                    "No se puede cerrar esta ventana mientras haya ventanas adicionales abiertas.\n"
                    "Por favor cierre primero las ventanas secundarias.",
                    parent=dialog
                )
            else:
                if dialog in active_edit_window:
                    active_edit_window.remove(dialog)
                dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

        top_header = tk.Frame(dialog, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top_header.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(top_header, text="✏️ Modificar Grupo de Investigación", bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(top_header, text="Edite los datos obligatorios (*). Se requiere institución con su plan estratégico y al menos 2 integrantes.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(0, 12))

        container = tk.Frame(dialog, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_content = tk.Frame(canvas, bg=BG)
        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event: tk.Event) -> None:
            delta = 1
            if hasattr(event, "delta") and event.delta > 0:
                delta = -1
            canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        card1 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card1.pack(fill="x", pady=(0, 10))
        tk.Label(card1, text="Información Básica Obligatoria (*)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c1_1 = tk.Frame(card1, bg=PANEL)
        r_c1_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_1, text="Nombre del Grupo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nom_grp = ttk.Entry(r_c1_1)
        entry_nom_grp.insert(0, str(group.get("nombreGrupo", "")))
        entry_nom_grp.pack(side="left", fill="x", expand=True)

        r_c1_2 = tk.Frame(card1, bg=PANEL)
        r_c1_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_2, text="Código / Nro Grupo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_nro_grp = ttk.Entry(r_c1_2, width=22)
        entry_nro_grp.insert(0, str(group.get("nroGrupo", "")))
        entry_nro_grp.pack(side="left", padx=(0, 10))
        tk.Label(r_c1_2, text="Año de Formación (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=18, anchor="w").pack(side="left")
        entry_anio_grp = ttk.Entry(r_c1_2)
        entry_anio_grp.insert(0, str(group.get("anioFormacion", "") or datetime.now().year))
        entry_anio_grp.pack(side="left", fill="x", expand=True)

        r_c1_3 = tk.Frame(card1, bg=PANEL)
        r_c1_3.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_3, text="Líder del Grupo (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_lider_grp = ttk.Entry(r_c1_3)
        entry_lider_grp.insert(0, str(group.get("lider", "")))
        entry_lider_grp.pack(side="left", fill="x", expand=True)

        r_c1_4 = tk.Frame(card1, bg=PANEL)
        r_c1_4.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_4, text="Departamento (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_depto_grp = ttk.Entry(r_c1_4, width=22)
        entry_depto_grp.insert(0, str(group.get("departamento", "")))
        entry_depto_grp.pack(side="left", padx=(0, 10))
        tk.Label(r_c1_4, text="Ciudad (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=18, anchor="w").pack(side="left")
        entry_ciudad_grp = ttk.Entry(r_c1_4)
        entry_ciudad_grp.insert(0, str(group.get("ciudad", "")))
        entry_ciudad_grp.pack(side="left", fill="x", expand=True)

        r_c1_5 = tk.Frame(card1, bg=PANEL)
        r_c1_5.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_5, text="Correo Electrónico (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_email_grp = ttk.Entry(r_c1_5)
        entry_email_grp.insert(0, str(group.get("email", "")))
        entry_email_grp.pack(side="left", fill="x", expand=True)

        r_c1_6 = tk.Frame(card1, bg=PANEL)
        r_c1_6.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c1_6, text="Institución Avaladora (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
        entry_inst_grp = ttk.Entry(r_c1_6)
        entry_inst_grp.insert(0, main_inst)
        entry_inst_grp.pack(side="left", fill="x", expand=True)

        r_c1_7 = tk.Frame(card1, bg=PANEL)
        r_c1_7.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c1_7, text="Plan Estratégico (*):", bg=PANEL, fg=DARK, font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(anchor="w", pady=(0, 2))
        text_plan_grp = tk.Text(r_c1_7, height=3, wrap="word", bg="#fbfcfe", font=("Segoe UI", 9), relief="solid", bd=1)
        text_plan_grp.insert("1.0", plan_str)
        text_plan_grp.pack(fill="x")

        card2 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card2.pack(fill="x", pady=(0, 10))
        tk.Label(card2, text="Información General del Grupo (Opcional)", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        r_c2_1 = tk.Frame(card2, bg=PANEL)
        r_c2_1.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_1, text="Clasificación Minciencias:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        combo_clasif_grp = ttk.Combobox(r_c2_1, values=["A1", "A", "B", "C", "Reconocido", "Sin clasificación", ""], width=20)
        combo_clasif_grp.set(str(group.get("clasificacion", "")))
        combo_clasif_grp.pack(side="left", padx=(0, 10))
        tk.Label(r_c2_1, text="Área Conocimiento:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_area_grp = ttk.Entry(r_c2_1)
        entry_area_grp.insert(0, str(group.get("areaConocimiento", "")))
        entry_area_grp.pack(side="left", fill="x", expand=True)

        r_c2_2 = tk.Frame(card2, bg=PANEL)
        r_c2_2.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_2, text="Programa Nacional CTI:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_cti_grp = ttk.Entry(r_c2_2)
        entry_cti_grp.insert(0, str(group.get("programaNacionalCti", "")))
        entry_cti_grp.pack(side="left", fill="x", expand=True)

        r_c2_3 = tk.Frame(card2, bg=PANEL)
        r_c2_3.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_3, text="Programa Secundario:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_cti_sec = ttk.Entry(r_c2_3)
        entry_cti_sec.insert(0, str(group.get("programaNacionalCtiSecundario", "")))
        entry_cti_sec.pack(side="left", fill="x", expand=True)

        r_c2_4 = tk.Frame(card2, bg=PANEL)
        r_c2_4.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_4, text="Página Web:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_web_grp = ttk.Entry(r_c2_4, width=28)
        entry_web_grp.insert(0, str(group.get("paginaWeb", "")))
        entry_web_grp.pack(side="left", padx=(0, 10))
        tk.Label(r_c2_4, text="Info Certificada:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        entry_cert_grp = ttk.Entry(r_c2_4)
        entry_cert_grp.insert(0, str(group.get("informacionCertificada", "")))
        entry_cert_grp.pack(side="left", fill="x", expand=True)

        r_c2_5 = tk.Frame(card2, bg=PANEL)
        r_c2_5.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_5, text="Estado del Arte:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_arte_grp = ttk.Entry(r_c2_5)
        entry_arte_grp.insert(0, str(group.get("estadoArte", "")))
        entry_arte_grp.pack(side="left", fill="x", expand=True)

        r_c2_6 = tk.Frame(card2, bg=PANEL)
        r_c2_6.pack(fill="x", padx=14, pady=4)
        tk.Label(r_c2_6, text="Objetivos:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_obj_grp = ttk.Entry(r_c2_6)
        entry_obj_grp.insert(0, str(group.get("objetivos", "")))
        entry_obj_grp.pack(side="left", fill="x", expand=True)

        r_c2_7 = tk.Frame(card2, bg=PANEL)
        r_c2_7.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(r_c2_7, text="Retos y Visión:", bg=PANEL, fg=DARK, font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        entry_retos_grp = ttk.Entry(r_c2_7)
        entry_retos_grp.insert(0, str(group.get("retos", "")))
        entry_retos_grp.pack(side="left", fill="x", expand=True)

        card3 = tk.Frame(scrollable_content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card3.pack(fill="x", pady=(0, 10))
        tk.Label(card3, text="Integrantes Obligatorios y Colecciones Adicionales", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Label(card3, text="Es obligatorio registrar al menos 2 integrantes. Productos, líneas e instituciones adicionales son opcionales:", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(0, 10))

        grid_btns_grp = tk.Frame(card3, bg=PANEL)
        grid_btns_grp.pack(fill="x", padx=14, pady=(0, 12))

        def open_integrantes_for_edit_grp() -> None:
            lider_nom = entry_lider_grp.get().strip()
            if lider_nom:
                lider_canon = canonical_key(lider_nom)
                already_has_lider = False
                for m in added_integrantes:
                    if canonical_key(str(m.get("nombre", ""))) == lider_canon:
                        already_has_lider = True
                    elif str(m.get("rol", "")).strip().lower() == "líder" or str(m.get("vinculacion", "")).strip().lower() == "líder":
                        already_has_lider = True

                if not already_has_lider:
                    matching_cod = ""
                    matching_cor = ""
                    for inv in self.service.investigadores:
                        if canonical_key(str(inv.get("nombre", ""))) == lider_canon:
                            matching_cod = str(inv.get("codigoRh", ""))
                            matching_cor = str(inv.get("correo", ""))

                    lider_mem = {
                        "nombre": lider_nom,
                        "codigoRh": matching_cod,
                        "correo": matching_cor,
                        "rol": "Líder",
                        "vinculacion": "Líder",
                        "tipo": "INVESTIGADOR"
                    }
                    added_integrantes.insert(0, lider_mem)
                    update_badges_grp()

            self._open_integrantes_subwindow(dialog, active_subwindows, added_integrantes, update_badges_grp)

        btn_mem_grp = ttk.Button(grid_btns_grp, text="👥 Integrantes (* Mínimo 2) (0)", style="Primary.TButton", command=open_integrantes_for_edit_grp)
        btn_mem_grp.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        btn_prod_grp = ttk.Button(grid_btns_grp, text="📦 Productos (0)", command=lambda: self._open_products_subwindow(dialog, active_subwindows, added_productos, update_badges_grp, is_group=True))
        btn_prod_grp.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        btn_lin_grp = ttk.Button(grid_btns_grp, text="🔬 Líneas Inv. (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Líneas de Investigación", "Nombre de la línea de investigación:", added_lineas, update_badges_grp, "Ej: Ingeniería de Software"))
        btn_lin_grp.grid(row=0, column=2, sticky="ew", padx=4, pady=4)

        btn_inst_grp = ttk.Button(grid_btns_grp, text="🏛️ Instituciones Extras (0)", command=lambda: self._open_simple_list_subwindow(dialog, active_subwindows, "Instituciones Adicionales", "Nombre de la institución avaladora adicional:", added_instituciones, update_badges_grp, "Ej: Universidad Nacional - (Avalado)"))
        btn_inst_grp.grid(row=0, column=3, sticky="ew", padx=4, pady=4)

        for col_i in range(4):
            grid_btns_grp.columnconfigure(col_i, weight=1)

        def update_badges_grp() -> None:
            btn_mem_grp.configure(text=f"👥 Integrantes (* Mínimo 2) ({len(added_integrantes)})")
            btn_prod_grp.configure(text=f"📦 Productos ({len(added_productos)})")
            btn_lin_grp.configure(text=f"🔬 Líneas Inv. ({len(added_lineas)})")
            btn_inst_grp.configure(text=f"🏛️ Instituciones Extras ({len(added_instituciones)})")

        update_badges_grp()

        def save_group_changes() -> None:
            if self._has_active_subwindows(active_subwindows):
                messagebox.showwarning(
                    "Ventana secundaria abierta",
                    "No se puede continuar mientras existan ventanas secundarias abiertas.\n"
                    "Por favor cierre primero las ventanas secundarias.",
                    parent=dialog
                )
            else:
                nom = entry_nom_grp.get().strip()
                nro = entry_nro_grp.get().strip()
                lid = entry_lider_grp.get().strip()
                ani = entry_anio_grp.get().strip()
                dep = entry_depto_grp.get().strip()
                ciu = entry_ciudad_grp.get().strip()
                em = entry_email_grp.get().strip()
                inst = entry_inst_grp.get().strip()
                plan = text_plan_grp.get("1.0", "end").strip()

                if not nom:
                    messagebox.showerror("Campo obligatorio", "El nombre del grupo es obligatorio.", parent=dialog)
                elif not nro:
                    messagebox.showerror("Campo obligatorio", "El código / número de grupo es obligatorio.", parent=dialog)
                elif not lid:
                    messagebox.showerror("Campo obligatorio", "El líder del grupo es obligatorio.", parent=dialog)
                elif not ani:
                    messagebox.showerror("Campo obligatorio", "El año de formación es obligatorio.", parent=dialog)
                elif not dep:
                    messagebox.showerror("Campo obligatorio", "El departamento es obligatorio.", parent=dialog)
                elif not ciu:
                    messagebox.showerror("Campo obligatorio", "La ciudad es obligatoria.", parent=dialog)
                elif not em:
                    messagebox.showerror("Campo obligatorio", "El correo electrónico es obligatorio.", parent=dialog)
                elif not inst:
                    messagebox.showerror("Campo obligatorio", "La institución avaladora es obligatoria.", parent=dialog)
                elif not plan:
                    messagebox.showerror("Campo obligatorio", "El plan estratégico / de trabajo es obligatorio.", parent=dialog)
                elif len(added_integrantes) < 2:
                    messagebox.showerror(
                        "Integrantes insuficientes",
                        f"El grupo requiere al menos 2 integrantes registrados (actualmente tiene {len(added_integrantes)}).\n"
                        "Abra la ventana de 'Integrantes' para agregarlos.",
                        parent=dialog
                    )
                else:
                    instituciones_list = [
                        f"{inst} - (Avalado)",
                        "Plan Estratégico",
                        f"Plan de trabajo: {plan}"
                    ]
                    for extra in added_instituciones:
                        instituciones_list.append(extra)

                    updated_data = {
                        "nroGrupo": nro,
                        "nombreGrupo": nom,
                        "anioFormacion": ani,
                        "departamento": dep,
                        "ciudad": ciu,
                        "lider": lid,
                        "informacionCertificada": entry_cert_grp.get().strip(),
                        "paginaWeb": entry_web_grp.get().strip(),
                        "email": em,
                        "clasificacion": combo_clasif_grp.get().strip(),
                        "areaConocimiento": entry_area_grp.get().strip(),
                        "programaNacionalCti": entry_cti_grp.get().strip(),
                        "programaNacionalCtiSecundario": entry_cti_sec.get().strip(),
                        "planEstrategico": plan,
                        "estadoArte": entry_arte_grp.get().strip(),
                        "objetivos": entry_obj_grp.get().strip(),
                        "retos": entry_retos_grp.get().strip(),
                        "vision": str(group.get("vision", "")),
                        "instituciones": instituciones_list,
                        "lineasInvestigacion": list(added_lineas),
                        "integrantes": list(added_integrantes),
                        "productos": list(added_productos)
                    }
                    ok, msg = self.service.update_group(group, updated_data)
                    if ok:
                        messagebox.showinfo("Éxito", msg)
                        target_trees = []
                        if tree is not None:
                            target_trees.append(tree)
                        if getattr(self, "main_group_tree", None) is not None:
                            if self.main_group_tree not in target_trees:
                                target_trees.append(self.main_group_tree)
                        for t in target_trees:
                            try:
                                if t.winfo_exists():
                                    self.refresh_group_tree(t, "")
                            except Exception:
                                pass
                        self.status.set("Grupo modificado correctamente: " + nom)
                        if dialog in active_edit_window:
                            active_edit_window.remove(dialog)
                        dialog.destroy()
                        if detail_win.winfo_exists():
                            detail_win.destroy()
                            self.show_group_detail_for_item(group, tree)
                    else:
                        messagebox.showerror("Error al modificar grupo", msg, parent=dialog)

        bottom_bar = tk.Frame(dialog, bg=BG)
        bottom_bar.pack(fill="x", padx=16, pady=(0, 14))
        ttk.Button(bottom_bar, text="💾 Guardar Cambios", style="Primary.TButton", command=save_group_changes).pack(side="left")
        ttk.Button(bottom_bar, text="Cancelar", command=on_dialog_close).pack(side="right")

    def build_loading(self) -> None:
        self.heading("Carga de Datos", "Carga estructurada desde los portales CvLAC y GrupLAC de MinCiencias")
        container = tk.Frame(self.content, bg=BG)
        container.pack(fill="both", expand=True)
        left = tk.Frame(container, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, width=430)
        left.pack(side="left", fill="y", padx=(0, 10))
        tk.Label(left, text="Origen de datos", bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=(18, 12))
        kind = tk.StringVar(value="investigador")
        tk.Radiobutton(left, text="Investigador · CvLAC", variable=kind, value="investigador", bg=PANEL, fg=DARK, selectcolor=PANEL, activebackground=PANEL).pack(anchor="w", padx=18, pady=4)
        tk.Radiobutton(left, text="Grupo · GrupLAC", variable=kind, value="grupo", bg=PANEL, fg=DARK, selectcolor=PANEL, activebackground=PANEL).pack(anchor="w", padx=18, pady=4)
        tk.Label(left, text="URL", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(16, 4))
        url_entry = ttk.Entry(left)
        url_entry.pack(fill="x", padx=18)

        result_text = tk.Text(left, height=10, wrap="word", bg="#fbfcfe", relief="flat", font=("Segoe UI", 9), state="disabled")

        def clear_and_set_result(texto: str) -> None:
            result_text.config(state="normal")
            result_text.delete("1.0", "end")
            result_text.insert("end", texto)
            result_text.config(state="disabled")

        def append_result(texto: str) -> None:
            result_text.config(state="normal")
            result_text.insert("end", texto)
            result_text.config(state="disabled")

        def do_scrape() -> None:
            target_kind = kind.get()
            raw_url = url_entry.get().strip()
            valido, norm_url, error_msg = validar_url_minciencias(target_kind, raw_url)
            if not valido:
                clear_and_set_result("⚠️ Validación de URL fallida:\n\n" + error_msg + "\n")
                self.status.set("URL no válida para la carga")
            else:
                clear_and_set_result("Procesando...\n")
                def worker() -> None:
                    ok, result, message = self.service.scrape_and_add(target_kind, norm_url)
                    def finish() -> None:
                        clear_and_set_result(message + "\n\n")
                        if ok:
                            append_result("Tipo: {}\n".format(result.get("tipo", "")))
                            append_result("Identificador: {}\n".format(result.get("codigoRh", result.get("nroGrupo", ""))))
                            append_result("Nombre: {}\n".format(result.get("nombre", result.get("nombreGrupo", ""))))
                            self.status.set(message)
                            render_summary(target_kind, result)
                        else:
                            self.status.set("Carga no completada")
                    self.after(0, finish)
                threading.Thread(target=worker, daemon=True).start()

        url_entry.bind("<Return>", lambda event: do_scrape())
        ttk.Button(left, text="Cargar información desde URL", style="Primary.TButton", command=do_scrape).pack(fill="x", padx=18, pady=(8, 12))

        # ---------------------------------------------------------
        # CARGA DESDE ARCHIVO LOCAL (PDF / CSV)
        # ---------------------------------------------------------
        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=18, pady=(4, 10))
        tk.Label(left, text="Carga desde archivo local", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(0, 4))
        tk.Label(left, text="Documentos oficiales MinCiencias (CvLAC / GrupLAC):", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=18, pady=(0, 6))

        def do_load_pdf() -> None:
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo PDF de MinCiencias (CvLAC o GrupLAC)",
                filetypes=[("Archivos PDF (*.pdf)", "*.pdf")]
            )
            if file_path:
                clear_and_set_result("Procesando archivo PDF...\nRuta: " + str(file_path) + "\n\n")
                self.status.set("Extrayendo información desde PDF...")

                def worker() -> None:
                    ok, result, message = self.service.process_pdf_file(file_path)
                    def finish() -> None:
                        clear_and_set_result(message + "\n\n")
                        if ok:
                            tipo_res = result.get("tipo", "")
                            append_result("Tipo: {}\n".format(tipo_res))
                            if tipo_res == "INVESTIGADOR":
                                append_result("Identificador: {}\n".format(result.get("codigoRh", "")))
                                append_result("Nombre: {}\n".format(result.get("nombre", "")))
                                append_result("Productos extraídos: {}\n".format(len(result.get("productos", []))))
                                render_summary("investigador", result)
                            elif tipo_res == "GRUPO":
                                append_result("Código grupo: {}\n".format(result.get("nroGrupo", "")))
                                append_result("Nombre grupo: {}\n".format(result.get("nombreGrupo", "")))
                                append_result("Integrantes: {}\n".format(len(result.get("integrantes", []))))
                                append_result("Productos extraídos: {}\n".format(len(result.get("productos", []))))
                                render_summary("grupo", result)
                            elif tipo_res == "LOTE":
                                append_result("Grupos cargados: {}\n".format(len(result.get("grupos", []))))
                                append_result("Investigadores cargados: {}\n".format(len(result.get("investigadores", []))))
                                render_lote_summary(result)
                            self.status.set(message)
                        else:
                            self.status.set(message)
                    self.after(0, finish)
                threading.Thread(target=worker, daemon=True).start()

        ttk.Button(left, text="📄 Cargar archivo PDF (CvLAC / GrupLAC)", style="Primary.TButton", command=do_load_pdf).pack(fill="x", padx=18, pady=(0, 6))

        def do_load_csv() -> None:
            file_paths = filedialog.askopenfilenames(
                title="Seleccionar archivo(s) CSV de MinCiencias (CvLAC o GrupLAC)",
                filetypes=[("Archivos CSV (*.csv)", "*.csv")]
            )
            if file_paths:
                clear_and_set_result("Procesando " + str(len(file_paths)) + " archivo(s) CSV...\n\n")
                self.status.set("Extrayendo información desde archivo(s) CSV...")

                def worker() -> None:
                    report = self.service.process_csv_files(list(file_paths))
                    def finish() -> None:
                        clear_and_set_result("=== RESUMEN DE IMPORTACIÓN CSV ===\n")
                        append_result("Total archivos seleccionados: " + str(report.get("total_archivos", 0)) + "\n")
                        append_result("Archivos procesados con éxito: " + str(report.get("archivos_exitosos", 0)) + "\n")
                        append_result("Archivos con errores o rechazados: " + str(report.get("archivos_fallidos", 0)) + "\n")
                        append_result("Entidades incorporadas: " + str(report.get("total_incorporados", 0)) + "\n")
                        append_result("Entidades duplicadas omitidas: " + str(report.get("total_duplicados", 0)) + "\n\n")

                        append_result("--- DETALLES POR ARCHIVO ---\n")
                        last_valid_result = None
                        detalles = report.get("detalles", [])
                        d_idx = 0
                        while d_idx < len(detalles):
                            det = detalles[d_idx]
                            estado_txt = "ÉXITO"
                            if not det.get("exito", False):
                                estado_txt = "RECHAZADO"
                            append_result("[" + estado_txt + "] " + str(det.get("archivo", "")) + ": " + str(det.get("mensaje", "")) + "\n")
                            if det.get("exito", False) and det.get("resultado"):
                                last_valid_result = det.get("resultado")
                            d_idx += 1

                        if last_valid_result:
                            tipo_last = last_valid_result.get("tipo", "")
                            if tipo_last == "INVESTIGADOR":
                                render_summary("investigador", last_valid_result)
                            elif tipo_last == "GRUPO":
                                render_summary("grupo", last_valid_result)
                            elif tipo_last == "LOTE":
                                render_lote_summary(last_valid_result)

                        res_msg = "Procesados: " + str(report.get("archivos_exitosos", 0)) + " exitosos, " + str(report.get("archivos_fallidos", 0)) + " fallidos."
                        self.status.set(res_msg)
                    self.after(0, finish)
                threading.Thread(target=worker, daemon=True).start()

        ttk.Button(left, text="📊 Cargar archivo(s) CSV (CvLAC / GrupLAC)", style="Primary.TButton", command=do_load_csv).pack(fill="x", padx=18, pady=(0, 14))

        result_text.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        right = tk.Frame(container, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="both", expand=True)

        def render_empty_summary() -> None:
            for w in right.winfo_children():
                w.destroy()
            header = tk.Frame(right, bg=PANEL)
            header.pack(fill="x", padx=20, pady=(18, 10))
            tk.Label(header, text="Resumen de datos cargados", bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w")
            tk.Label(header, text="Visualización en tiempo real del registro extraído.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

            box = tk.Frame(right, bg="#f8fafc", highlightbackground=BORDER, highlightthickness=1)
            box.pack(fill="both", expand=True, padx=20, pady=(10, 20))

            center_frame = tk.Frame(box, bg="#f8fafc")
            center_frame.place(relx=0.5, rely=0.45, anchor="center")

            tk.Label(center_frame, text="📋", font=("Segoe UI", 36), bg="#f8fafc").pack(pady=(0, 10))
            tk.Label(center_frame, text="No hay información reciente cargada", font=("Segoe UI", 12, "bold"), fg=DARK, bg="#f8fafc").pack(pady=(0, 6))
            tk.Label(
                center_frame,
                text="Seleccione el origen (Investigador o Grupo) a la izquierda, ingrese el enlace oficial de MinCiencias (CvLAC o GrupLAC) y presione 'Cargar información'.\n\nAl completar la extracción, aquí aparecerá la síntesis completa de los datos registrados.",
                font=("Segoe UI", 9),
                fg=MUTED,
                bg="#f8fafc",
                wraplength=440,
                justify="center"
            ).pack()

        def render_summary(data_kind: str, data: Dict[str, Any]) -> None:
            for w in right.winfo_children():
                w.destroy()

            header = tk.Frame(right, bg=PANEL)
            header.pack(fill="x", padx=20, pady=(16, 10))
            if data_kind == "investigador":
                title_text = "Resumen del investigador cargado"
            else:
                title_text = "Resumen del grupo cargado"
            tk.Label(header, text=title_text, bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w")

            canvas_frame = tk.Frame(right, bg=PANEL)
            canvas_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

            canvas = tk.Canvas(canvas_frame, bg=PANEL, highlightthickness=0)
            scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical")

            def _custom_yview(*args) -> None:
                try:
                    fits = False
                    bbox = canvas.bbox("all")
                    if bbox:
                        content_h = bbox[3] - bbox[1]
                        canv_h = canvas.winfo_height()
                        if content_h <= canv_h:
                            canvas.yview_moveto(0.0)
                            fits = True
                    if not fits:
                        canvas.yview(*args)
                        y0, y1 = canvas.yview()
                        if y0 < 0.0:
                            canvas.yview_moveto(0.0)
                        elif y1 > 1.0:
                            canvas.yview_moveto(max(0.0, 1.0 - (y1 - y0)))
                except Exception:
                    pass

            scrollbar.configure(command=_custom_yview)
            scroll_content = tk.Frame(canvas, bg=PANEL)
            canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            def _update_scroll_bounds(event: Optional[tk.Event] = None) -> None:
                try:
                    canv_w = canvas.winfo_width()
                    canv_h = canvas.winfo_height()
                    if canv_w > 1 and canv_h > 1:
                        canvas.itemconfig(canvas_window, width=canv_w)
                        bbox = canvas.bbox("all")
                        if bbox:
                            content_h = max(bbox[3] - bbox[1], 1)
                            eff_h = max(canv_h, content_h)
                            canvas.configure(scrollregion=(0, 0, canv_w, eff_h))
                            if content_h <= canv_h:
                                canvas.yview_moveto(0.0)
                                if scrollbar.winfo_ismapped():
                                    scrollbar.pack_forget()
                            else:
                                if not scrollbar.winfo_ismapped():
                                    scrollbar.pack(side="right", fill="y", before=canvas)
                except Exception:
                    pass

            canvas.bind("<Configure>", _update_scroll_bounds)
            scroll_content.bind("<Configure>", _update_scroll_bounds)
            canvas.configure(yscrollcommand=scrollbar.set)

            card = tk.Frame(scroll_content, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", pady=(0, 12))

            if data_kind == "investigador":
                nombre = data.get("nombre", "Investigador sin nombre")
                rh = data.get("codigoRh", "N/A")
                cat = data.get("categoriaInvestigador", "Sin categoría")
                nac = data.get("nacionalidad", "No especificada")
                sexo = data.get("sexo", "No especificado")
                inst = data.get("institucion", "No registrada")
                productos = data.get("productos", [])
                proyectos = data.get("proyectos", [])
                idiomas = data.get("idiomas", [])
                formacion = data.get("formacionAcademica", [])
                experiencia = data.get("experienciaProfesional", [])

                ch = tk.Frame(card, bg="#f8fafc", padx=14, pady=10)
                ch.pack(fill="x")
                tk.Label(ch, text=nombre, font=("Segoe UI", 13, "bold"), fg=DARK, bg="#f8fafc").pack(anchor="w")
                tk.Label(ch, text=f"Perfil CvLAC  •  Código RH: {rh}", font=("Segoe UI", 9), fg=PRIMARY, bg="#f8fafc").pack(anchor="w")

                body = tk.Frame(card, bg="#ffffff", padx=14, pady=12)
                body.pack(fill="x")

                details = [
                    ("Categoría", cat),
                    ("Nacionalidad", nac),
                    ("Sexo", sexo),
                    ("Institución principal", inst)
                ]
                for label_txt, val_txt in details:
                    if val_txt:
                        row = tk.Frame(body, bg="#ffffff")
                        row.pack(fill="x", pady=2)
                        tk.Label(row, text=f"{label_txt}: ", font=("Segoe UI", 9, "bold"), fg=DARK, bg="#ffffff").pack(side="left")
                        tk.Label(row, text=str(val_txt), font=("Segoe UI", 9), fg=MUTED, bg="#ffffff", wraplength=480, justify="left").pack(side="left")

                metrics_frame = tk.Frame(scroll_content, bg=PANEL)
                metrics_frame.pack(fill="x", pady=(0, 12))

                if any("habla" in i.lower() for i in idiomas):
                    base_len = len(idiomas) - 1
                else:
                    base_len = len(idiomas)
                valid_idiomas_cnt = max(0, base_len)
                stats_items = [
                    ("Productos", len(productos)),
                    ("Proyectos", len(proyectos)),
                    ("Idiomas", valid_idiomas_cnt),
                    ("Formación", len(formacion)),
                    ("Experiencia", len(experiencia)),
                ]
                for idx, (st_name, st_val) in enumerate(stats_items):
                    m_card = tk.Frame(metrics_frame, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=6, pady=8)
                    if idx > 0:
                        padx_val = 2
                    else:
                        padx_val = 0
                    m_card.grid(row=0, column=idx, sticky="nsew", padx=padx_val)
                    metrics_frame.grid_columnconfigure(idx, weight=1)
                    tk.Label(m_card, text=str(st_val), font=("Segoe UI", 13, "bold"), fg=PRIMARY, bg="#ffffff").pack()
                    tk.Label(m_card, text=st_name, font=("Segoe UI", 8), fg=MUTED, bg="#ffffff").pack()

                if productos:
                    p_card = tk.Frame(scroll_content, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
                    p_card.pack(fill="x")
                    tk.Label(p_card, text=f"Productos destacados ({min(4, len(productos))} de {len(productos)})", font=("Segoe UI", 10, "bold"), fg=DARK, bg="#ffffff").pack(anchor="w", pady=(0, 8))
                    for p in productos[:4]:
                        p_tit = p.get("titulo", "Sin título")
                        p_cat = p.get("categoria", "")
                        p_yr = p.get("anio", "")
                        if p_yr:
                            p_yr_str = f" ({p_yr})"
                        else:
                            p_yr_str = ""
                        p_txt = f"• [{p_cat}] {p_tit}{p_yr_str}"
                        tk.Label(p_card, text=p_txt, font=("Segoe UI", 9), fg=DARK, bg="#ffffff", anchor="w", justify="left", wraplength=500).pack(anchor="w", pady=2)

                lineas_inv = data.get("lineasInvestigacion", [])
                if lineas_inv:
                    l_card = tk.Frame(scroll_content, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
                    l_card.pack(fill="x", pady=(10, 0))
                    tk.Label(l_card, text=f"Líneas de investigación ({len(lineas_inv)})", font=("Segoe UI", 10, "bold"), fg=DARK, bg="#ffffff").pack(anchor="w", pady=(0, 8))
                    for lin in lineas_inv[:5]:
                        tk.Label(l_card, text=f"• {lin}", font=("Segoe UI", 9), fg=DARK, bg="#ffffff", anchor="w", justify="left", wraplength=500).pack(anchor="w", pady=2)

                recons = data.get("reconocimientos", [])
                if recons:
                    r_card = tk.Frame(scroll_content, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
                    r_card.pack(fill="x", pady=(10, 0))
                    tk.Label(r_card, text=f"Reconocimientos ({len(recons)})", font=("Segoe UI", 10, "bold"), fg=DARK, bg="#ffffff").pack(anchor="w", pady=(0, 8))
                    for rec in recons[:5]:
                        tk.Label(r_card, text=f"• {rec}", font=("Segoe UI", 9), fg=DARK, bg="#ffffff", anchor="w", justify="left", wraplength=500).pack(anchor="w", pady=2)

                if idiomas:
                    id_card = tk.Frame(scroll_content, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
                    id_card.pack(fill="x", pady=(10, 0))
                    tk.Label(id_card, text=f"Idiomas ({valid_idiomas_cnt})", font=("Segoe UI", 10, "bold"), fg=DARK, bg="#ffffff").pack(anchor="w", pady=(0, 8))
                    for idm in idiomas:
                        if "habla" not in idm.lower():
                            tk.Label(id_card, text=f"• {idm}", font=("Segoe UI", 9), fg=DARK, bg="#ffffff", anchor="w", justify="left", wraplength=500).pack(anchor="w", pady=2)
            else:
                nombre = data.get("nombreGrupo", "Grupo sin nombre")
                nro = data.get("nroGrupo", "N/A")
                lider = data.get("lider", "No especificado")
                clasif = data.get("clasificacion", "Sin clasificar")
                anio = data.get("anioFormacion", "")
                ciudad = data.get("ciudad", "")
                depto = data.get("departamento", "")
                area = data.get("areaConocimiento", "")
                integrantes = data.get("integrantes", [])
                productos = data.get("productos", [])
                lineas = data.get("lineasInvestigacion", [])
                instituciones = data.get("instituciones", [])

                ch = tk.Frame(card, bg="#f8fafc", padx=14, pady=10)
                ch.pack(fill="x")
                tk.Label(ch, text=nombre, font=("Segoe UI", 13, "bold"), fg=DARK, bg="#f8fafc").pack(anchor="w")
                tk.Label(ch, text=f"Grupo GrupLAC  •  Código: {nro}", font=("Segoe UI", 9), fg=PRIMARY, bg="#f8fafc").pack(anchor="w")

                body = tk.Frame(card, bg="#ffffff", padx=14, pady=12)
                body.pack(fill="x")

                ubica = f"{ciudad}, {depto}".strip(" ,") or "No registrada"
                details = [
                    ("Líder", lider),
                    ("Clasificación", clasif),
                    ("Año de formación", anio),
                    ("Ubicación", ubica),
                    ("Área de conocimiento", area)
                ]
                for label_txt, val_txt in details:
                    if val_txt:
                        row = tk.Frame(body, bg="#ffffff")
                        row.pack(fill="x", pady=2)
                        tk.Label(row, text=f"{label_txt}: ", font=("Segoe UI", 9, "bold"), fg=DARK, bg="#ffffff").pack(side="left")
                        tk.Label(row, text=str(val_txt), font=("Segoe UI", 9), fg=MUTED, bg="#ffffff", wraplength=480, justify="left").pack(side="left")

                metrics_frame = tk.Frame(scroll_content, bg=PANEL)
                metrics_frame.pack(fill="x", pady=(0, 12))

                stats_items = [
                    ("Integrantes", len(integrantes)),
                    ("Productos", len(productos)),
                    ("Líneas", len(lineas)),
                    ("Instituciones", len(instituciones)),
                ]
                for idx, (st_name, st_val) in enumerate(stats_items):
                    m_card = tk.Frame(metrics_frame, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=6, pady=8)
                    if idx > 0:
                        padx_val = 2
                    else:
                        padx_val = 0
                    m_card.grid(row=0, column=idx, sticky="nsew", padx=padx_val)
                    metrics_frame.grid_columnconfigure(idx, weight=1)
                    tk.Label(m_card, text=str(st_val), font=("Segoe UI", 13, "bold"), fg=PRIMARY, bg="#ffffff").pack()
                    tk.Label(m_card, text=st_name, font=("Segoe UI", 8), fg=MUTED, bg="#ffffff").pack()

                if productos:
                    p_card = tk.Frame(scroll_content, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
                    p_card.pack(fill="x")
                    tk.Label(p_card, text=f"Productos destacados ({min(4, len(productos))} de {len(productos)})", font=("Segoe UI", 10, "bold"), fg=DARK, bg="#ffffff").pack(anchor="w", pady=(0, 8))
                    for p in productos[:4]:
                        p_tit = p.get("titulo", "Sin título")
                        p_cat = p.get("categoria", "")
                        if p_cat:
                            p_txt = f"• [{p_cat}] {p_tit}"
                        else:
                            p_txt = f"• {p_tit}"
                        tk.Label(p_card, text=p_txt, font=("Segoe UI", 9), fg=DARK, bg="#ffffff", anchor="w", justify="left", wraplength=500).pack(anchor="w", pady=2)

                if lineas:
                    lg_card = tk.Frame(scroll_content, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
                    lg_card.pack(fill="x", pady=(10, 0))
                    tk.Label(lg_card, text=f"Líneas de investigación ({len(lineas)})", font=("Segoe UI", 10, "bold"), fg=DARK, bg="#ffffff").pack(anchor="w", pady=(0, 8))
                    for lin in lineas[:5]:
                        tk.Label(lg_card, text=f"• {lin}", font=("Segoe UI", 9), fg=DARK, bg="#ffffff", anchor="w", justify="left", wraplength=500).pack(anchor="w", pady=2)

                if instituciones:
                    inst_card = tk.Frame(scroll_content, bg="#ffffff", highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
                    inst_card.pack(fill="x", pady=(10, 0))
                    tk.Label(inst_card, text=f"Instituciones vinculadas ({len(instituciones)})", font=("Segoe UI", 10, "bold"), fg=DARK, bg="#ffffff").pack(anchor="w", pady=(0, 8))
                    for inst_item in instituciones[:5]:
                        tk.Label(inst_card, text=f"• {inst_item}", font=("Segoe UI", 9), fg=DARK, bg="#ffffff", anchor="w", justify="left", wraplength=500).pack(anchor="w", pady=2)

            def _on_wheel(event: tk.Event) -> None:
                try:
                    bbox = canvas.bbox("all")
                    if bbox:
                        canv_h = canvas.winfo_height()
                        content_h = bbox[3] - bbox[1]
                        if content_h <= canv_h:
                            canvas.yview_moveto(0.0)
                        else:
                            if getattr(event, "num", None) == 4:
                                delta = -1
                            elif getattr(event, "num", None) == 5:
                                delta = 1
                            elif hasattr(event, "delta") and event.delta:
                                delta = int(-1 * (event.delta / 120))
                            else:
                                delta = 0

                            if delta != 0:
                                y0, y1 = canvas.yview()
                                if delta < 0 and y0 <= 0.0:
                                    canvas.yview_moveto(0.0)
                                elif not (delta > 0 and y1 >= 1.0):
                                    canvas.yview_scroll(delta, "units")
                                    y0_new, y1_new = canvas.yview()
                                    if y0_new < 0.0:
                                        canvas.yview_moveto(0.0)
                                    elif y1_new > 1.0:
                                        canvas.yview_moveto(max(0.0, 1.0 - (y1_new - y0_new)))
                except Exception:
                    pass

            def _bind_mousewheel_tree(w: tk.Misc) -> None:
                w.bind("<MouseWheel>", _on_wheel, add="+")
                w.bind("<Button-4>", _on_wheel, add="+")
                w.bind("<Button-5>", _on_wheel, add="+")
                for child in w.winfo_children():
                    _bind_mousewheel_tree(child)

            _bind_mousewheel_tree(right)

            def _bind_all(event=None) -> None:
                canvas.bind_all("<MouseWheel>", _on_wheel)
                canvas.bind_all("<Button-4>", _on_wheel)
                canvas.bind_all("<Button-5>", _on_wheel)

            def _unbind_all(event=None) -> None:
                try:
                    canvas.unbind_all("<MouseWheel>")
                    canvas.unbind_all("<Button-4>")
                    canvas.unbind_all("<Button-5>")
                except Exception:
                    pass

            canvas_frame.bind("<Enter>", _bind_all)
            canvas_frame.bind("<Leave>", _unbind_all)
            canvas.bind("<Enter>", _bind_all)
            canvas.bind("<Leave>", _unbind_all)
            scroll_content.bind("<Enter>", _bind_all)
            scroll_content.bind("<Leave>", _unbind_all)
            canvas.after_idle(_update_scroll_bounds)

        def render_lote_summary(data: Dict[str, Any]) -> None:
            for w in right.winfo_children():
                w.destroy()

            header = tk.Frame(right, bg=PANEL)
            header.pack(fill="x", padx=20, pady=(16, 10))
            tk.Label(header, text="Resumen de Lote Cargado (PDF)", bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w")

            grupos = data.get("grupos", [])
            investigadores = data.get("investigadores", [])

            canvas_frame = tk.Frame(right, bg=PANEL)
            canvas_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

            canvas = tk.Canvas(canvas_frame, bg=PANEL, highlightthickness=0)
            scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            scroll_content = tk.Frame(canvas, bg=PANEL)
            canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            canvas.configure(yscrollcommand=scrollbar.set)

            def _update_scroll(event=None):
                canvas.itemconfig(canvas_window, width=canvas.winfo_width())
                canvas.configure(scrollregion=canvas.bbox("all"))

            canvas.bind("<Configure>", _update_scroll)
            scroll_content.bind("<Configure>", _update_scroll)

            metrics_frame = tk.Frame(scroll_content, bg="#f8fafc", highlightbackground=BORDER, highlightthickness=1)
            metrics_frame.pack(fill="x", pady=(0, 14), padx=4)

            tk.Label(metrics_frame, text="📊 Resumen Consolidado del Lote", bg="#f8fafc", fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
            tk.Label(metrics_frame, text="Grupos de investigación: {}  |  Investigadores individuales: {}".format(len(grupos), len(investigadores)), bg="#f8fafc", fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0, 10))

            if len(grupos) > 0:
                tk.Label(scroll_content, text="Grupos de Investigación", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=4, pady=(6, 4))
                g_idx = 0
                while g_idx < len(grupos):
                    grp = grupos[g_idx]
                    card = tk.Frame(scroll_content, bg="#f8fafc", highlightbackground=BORDER, highlightthickness=1)
                    card.pack(fill="x", pady=4, padx=4)
                    tk.Label(card, text="🏛️ " + str(grp.get("nombreGrupo", "Grupo")), bg="#f8fafc", fg=DARK, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
                    tk.Label(card, text="Código: {} | Líder: {} | Integrantes: {} | Productos: {}".format(
                        grp.get("nroGrupo", ""), grp.get("lider", "N/A"), len(grp.get("integrantes", [])), len(grp.get("productos", []))
                    ), bg="#f8fafc", fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(0, 6))
                    g_idx += 1

            if len(investigadores) > 0:
                tk.Label(scroll_content, text="Investigadores Individuales", bg=PANEL, fg=DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=4, pady=(12, 4))
                i_idx = 0
                while i_idx < len(investigadores):
                    inv = investigadores[i_idx]
                    card = tk.Frame(scroll_content, bg="#f8fafc", highlightbackground=BORDER, highlightthickness=1)
                    card.pack(fill="x", pady=4, padx=4)
                    tk.Label(card, text="👤 " + str(inv.get("nombre", "Investigador")), bg="#f8fafc", fg=DARK, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
                    tk.Label(card, text="Código RH: {} | Categoría: {} | Productos: {}".format(
                        inv.get("codigoRh", ""), inv.get("categoriaInvestigador", "Sin categoría"), len(inv.get("productos", []))
                    ), bg="#f8fafc", fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(0, 6))
                    i_idx += 1

        render_empty_summary()

    def build_statistics(self):
        if not hasattr(self, "stats_current_view"):
            self.stats_current_view = "General"
        if not hasattr(self, "stats_selected_category"):
            self.stats_selected_category = "Todos"
        if not hasattr(self, "stats_selected_time"):
            self.stats_selected_time = "Todos los tiempos"
        if not hasattr(self, "stats_manual_start"):
            self.stats_manual_start = None
        if not hasattr(self, "stats_manual_end"):
            self.stats_manual_end = None
        if not hasattr(self, "stats_selected_items"):
            self.stats_selected_items = []
            
        if self.stats_current_view == "General":
            self.heading("Estadísticas Generales", "Visualización exploratoria general de la producción de los investigadores y grupos registrados en el sistema")
        elif self.stats_current_view == "Investigadores":
            def go_back():
                self.stats_current_view = "General"
                self.show_view("Estadísticas")
            btn_frame = tk.Frame(self.content, bg=BG)
            btn_frame.pack(fill="x", pady=(0, 10))
            ttk.Button(btn_frame, text="← Regresar a estadísticas generales", command=go_back).pack(side="left")
            self.heading("Estadísticas de los Investigadores", "Listado de investigadores para consulta detallada de su producción científica")
        elif self.stats_current_view == "Grupos":
            def go_back():
                self.stats_current_view = "General"
                self.show_view("Estadísticas")
            btn_frame = tk.Frame(self.content, bg=BG)
            btn_frame.pack(fill="x", pady=(0, 10))
            ttk.Button(btn_frame, text="← Regresar a estadísticas generales", command=go_back).pack(side="left")
            self.heading("Estadísticas de los Grupos de Investigación", "Listado de grupos para consulta detallada de su producción científica")
        stats = self.service.statistics()
        
        products_list = []
        if self.stats_current_view in ("General", "Investigadores"):
            for inv in self.service.investigadores:
                for prod in inv.get("productos", []):
                    pc = dict(prod)
                    pc["_autor_nombre"] = inv.get("nombre", "N/A")
                    pc["_grupo_nombre"] = "N/A"
                    products_list.append(pc)
        if self.stats_current_view in ("General", "Grupos"):
            for grp in self.service.grupos:
                for prod in grp.get("productos", []):
                    pc = dict(prod)
                    autores = pc.get("autores", [])
                    if isinstance(autores, list) and autores:
                        pc["_autor_nombre"] = str(autores[0])
                        if len(autores) > 1:
                            pc["_autor_nombre"] += " y otros"
                    elif isinstance(autores, str) and autores:
                        pc["_autor_nombre"] = str(autores)
                    else:
                        pc["_autor_nombre"] = "N/A"
                    pc["_grupo_nombre"] = str(grp.get("nombreGrupo", "N/A"))
                    products_list.append(pc)
                    
        unique_products_dict = {}
        for prod in products_list:
            titulo = str(prod.get("titulo", ""))
            anio = str(prod.get("anio", 0))
            key = (canonical_key(titulo), anio)
            if titulo:
                if key not in unique_products_dict:
                    unique_products_dict[key] = dict(prod)
                else:
                    existing = unique_products_dict[key]
                    if existing.get("_grupo_nombre", "N/A") == "N/A" and prod.get("_grupo_nombre", "N/A") != "N/A":
                        existing["_grupo_nombre"] = prod.get("_grupo_nombre")
                    if existing.get("_autor_nombre", "N/A") == "N/A" and prod.get("_autor_nombre", "N/A") != "N/A":
                        existing["_autor_nombre"] = prod.get("_autor_nombre")
        unique_products = list(unique_products_dict.values())
                
        categorias_disponibles = []
        for prod in unique_products:
            mapped_cat = self.get_product_category(prod)
            if mapped_cat not in categorias_disponibles:
                categorias_disponibles.append(mapped_cat)
                
        categorias_disponibles.sort()
        categorias_disponibles.insert(0, "Todos")
        
        if self.stats_selected_category not in categorias_disponibles:
            self.stats_selected_category = "Todos"
        
        all_years = []
        for prod in unique_products:
            year_raw = prod.get("anio", "")
            if str(year_raw).isdigit():
                y = int(year_raw)
                if y > 1000 and y not in all_years:
                    all_years.append(y)
        all_years.sort()
        if all_years:
            min_year_global = min(all_years)
            max_year_global = max(all_years)
        else:
            min_year_global = datetime.now().year
            max_year_global = datetime.now().year
            
        filter_frame = tk.Frame(self.content, bg=BG)
        filter_frame.pack(fill="x", pady=(0, 10))
        tk.Label(filter_frame, text="Filtrar por tipo de producto:", bg=BG, fg=DARK, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
        
        selected_category = tk.StringVar(value=self.stats_selected_category)
        def on_cat_change(*args):
            self.stats_selected_category = selected_category.get()
        selected_category.trace_add("write", on_cat_change)
        
        category_menu = ttk.Combobox(filter_frame, textvariable=selected_category, values=categorias_disponibles, state="readonly", width=35)
        category_menu.pack(side="left")
        
        tk.Label(filter_frame, text="Filtrar por año:", bg=BG, fg=DARK, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(15, 8))
        
        time_options = ["Todos los tiempos", "Último año", "Últimos 2 años", "Últimos 3 años", "Últimos 4 años", "Últimos 5 años", "Rango manual"]
        selected_time = tk.StringVar(value=self.stats_selected_time)
        def on_time_change(*args):
            self.stats_selected_time = selected_time.get()
        selected_time.trace_add("write", on_time_change)
        time_menu = ttk.Combobox(filter_frame, textvariable=selected_time, values=time_options, state="readonly", width=18)
        time_menu.pack(side="left")
        
        start_val = min_year_global
        if self.stats_manual_start is not None:
            start_val = self.stats_manual_start
            
        end_val = max_year_global
        if self.stats_manual_end is not None:
            end_val = self.stats_manual_end
        manual_start_year = tk.IntVar(value=start_val)
        manual_end_year = tk.IntVar(value=end_val)
        def on_start_change(*args):
            self.stats_manual_start = manual_start_year.get()
        def on_end_change(*args):
            self.stats_manual_end = manual_end_year.get()
        manual_start_year.trace_add("write", on_start_change)
        manual_end_year.trace_add("write", on_end_change)
        popup_ref = {"win": None}
        
        def show_manual_popup(event=None):
            if selected_time.get() != "Rango manual":
                if popup_ref["win"]:
                    try:
                        popup_ref["win"].destroy()
                    except Exception:
                        pass
                    popup_ref["win"] = None
            else:
                if not popup_ref["win"]:
                    win = tk.Toplevel(self)
                    win.wm_overrideredirect(True)
                    win.configure(bg="#ffffff", highlightbackground=BORDER, highlightthickness=1)
                    x = time_menu.winfo_rootx()
                    y = time_menu.winfo_rooty() + time_menu.winfo_height()
                    win.geometry(f"250x145+{x}+{y}")
                    
                    title_frame = tk.Frame(win, bg="#ffffff")
                    title_frame.pack(fill="x", pady=(10, 5))
                    tk.Label(title_frame, text="Rango de años (Scroll)", bg="#ffffff", fg=DARK, font=("Segoe UI", 10, "bold")).pack()
                    
                    roulette_frame = tk.Frame(win, bg="#ffffff")
                    roulette_frame.pack(fill="x", pady=5)
                    
                    def create_roulette(parent, title_text, var):
                        container = tk.Frame(parent, bg="#ffffff")
                        tk.Label(container, text=title_text, bg="#ffffff", fg=MUTED, font=("Segoe UI", 9)).pack(pady=(0, 2))
                        
                        frame = tk.Frame(container, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0")
                        frame.pack()
                        canvas = tk.Canvas(frame, width=80, height=80, bg="#ffffff", highlightthickness=0)
                        canvas.pack()
                        
                        def draw_wheel():
                            canvas.delete("all")
                            val = var.get()
                            
                            canvas.create_rectangle(5, 26, 75, 54, fill="#f1f5f9", outline="")
                            canvas.create_text(40, 40, text=str(val), fill=PRIMARY, font=("Segoe UI", 13, "bold"))
                            
                            if val > min_year_global:
                                canvas.create_text(40, 13, text=str(val - 1), fill=MUTED, font=("Segoe UI", 9))
                            if val < max_year_global:
                                canvas.create_text(40, 67, text=str(val + 1), fill=MUTED, font=("Segoe UI", 9))
                                
                        def on_scroll(e):
                            try:
                                delta = 0
                                if getattr(e, "num", None) == 4:
                                    delta = 1
                                elif getattr(e, "num", None) == 5:
                                    delta = -1
                                elif hasattr(e, "delta") and e.delta:
                                    delta = int(e.delta / 120)
                                    
                                if delta < 0:
                                    cur = var.get()
                                    if cur < max_year_global:
                                        var.set(cur + 1)
                                        draw_wheel()
                                elif delta > 0:
                                    cur = var.get()
                                    if cur > min_year_global:
                                        var.set(cur - 1)
                                        draw_wheel()
                            except Exception:
                                pass
                                
                        def on_click(e):
                            y_pos = e.y
                            if y_pos < 26:
                                cur = var.get()
                                if cur > min_year_global:
                                    var.set(cur - 1)
                                    draw_wheel()
                            elif y_pos > 54:
                                cur = var.get()
                                if cur < max_year_global:
                                    var.set(cur + 1)
                                    draw_wheel()
                                    
                        canvas.bind("<MouseWheel>", on_scroll)
                        canvas.bind("<Button-4>", on_scroll)
                        canvas.bind("<Button-5>", on_scroll)
                        canvas.bind("<Button-1>", on_click)
                        
                        draw_wheel()
                        return container
                        
                    left_roulette = create_roulette(roulette_frame, "Inicio", manual_start_year)
                    left_roulette.pack(side="left", expand=True)
                    right_roulette = create_roulette(roulette_frame, "Fin", manual_end_year)
                    right_roulette.pack(side="right", expand=True)
                    
                    popup_ref["win"] = win
                    
        time_menu.bind("<<ComboboxSelected>>", show_manual_popup)
        
        
        if self.stats_current_view == "General":
            cards = tk.Frame(self.content, bg=BG)
            cards.pack(fill="x")
            
            card_inv = self.card(cards, "Investigadores", str(stats["investigadores"]), "Presiona aquí para ver estadísticas")
            card_inv.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            cards.grid_columnconfigure(0, weight=1)
            
            card_grp = self.card(cards, "Grupos", str(stats["grupos"]), "Presiona aquí para ver estadísticas")
            card_grp.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
            cards.grid_columnconfigure(1, weight=1)
            
            def goto_investigadores(e):
                self.stats_current_view = "Investigadores"
                self.stats_selected_items = []
                self.show_view("Estadísticas")
            def goto_grupos(e):
                self.stats_current_view = "Grupos"
                self.stats_selected_items = []
                self.show_view("Estadísticas")
                
            for w in card_inv.winfo_children():
                w.bind("<Button-1>", goto_investigadores)
            card_inv.bind("<Button-1>", goto_investigadores)
            card_inv.config(cursor="hand2")
            for w in card_grp.winfo_children():
                w.bind("<Button-1>", goto_grupos)
            card_grp.bind("<Button-1>", goto_grupos)
            card_grp.config(cursor="hand2")
            
            card_prod_frame = tk.Frame(cards, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            card_prod_frame.grid(row=0, column=2, sticky="nsew", padx=(0, 8))
            cards.grid_columnconfigure(2, weight=1)
            tk.Label(card_prod_frame, text="PRODUCTOS", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(14, 3))
            prod_val_lbl = tk.Label(card_prod_frame, text=str(stats["productos"]), bg=PANEL, fg=DARK, font=("Segoe UI", 26, "bold"))
            prod_val_lbl.pack(anchor="w", padx=16)
            tk.Label(card_prod_frame, text="Presiona aquí para ver el listado", bg=PANEL, fg=PRIMARY, font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(0, 10))
            card_prod_frame.configure(pady=10)
            
            def open_stats_products(event):
                if hasattr(self, "stats_current_filtered_products"):
                    prods = self.stats_current_filtered_products
                    if not prods:
                        messagebox.showinfo("Productos", "No hay productos para mostrar con los filtros actuales.", parent=self)
                    else:
                        win = tk.Toplevel(self)
                        win.title("Listado de Productos - Estadísticas Generales")
                        win.geometry("900x600")
                        self.build_products_ui(win, prods, authorship_mode="general")
                
            for w in card_prod_frame.winfo_children():
                w.bind("<Button-1>", open_stats_products)
            card_prod_frame.bind("<Button-1>", open_stats_products)
            card_prod_frame.config(cursor="hand2")
            
            charts = tk.Frame(self.content, bg=BG)
            charts.pack(fill="both", expand=True, pady=16)
            bar_panel = tk.Frame(charts, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            bar_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
            pie_panel = tk.Frame(charts, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            pie_panel.pack(side="right", fill="both", expand=True)
            tk.Label(bar_panel, text="Productos por año", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="center", pady=12)
            bar = tk.Canvas(bar_panel, bg=PANEL, highlightthickness=0)
            bar.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            bar.config(cursor="hand2")
            
            pie_label = tk.Label(pie_panel, text="Distribución por categoría", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold"))
            pie_label.pack(anchor="center", pady=12)
            pie = tk.Canvas(pie_panel, bg=PANEL, highlightthickness=0)
            pie.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            pie.config(cursor="hand2")
            
            self.current_bar_data = {}
            self.current_pie_data = {}
            self.current_pie_is_subtype = False
            
            def on_bar_click(event):
                self.show_bar_detail(self.current_bar_data)
                
            def on_pie_click(event):
                self.show_pie_detail(self.current_pie_data, self.current_pie_is_subtype, self.current_bar_data)
                
            bar.bind("<Button-1>", on_bar_click)
            pie.bind("<Button-1>", on_pie_click)
            
            def update_statistics():
                if popup_ref["win"]:
                    try:
                        popup_ref["win"].destroy()
                    except Exception:
                        pass
                    popup_ref["win"] = None
                    
                cat_selected = selected_category.get()
                time_selected = selected_time.get()
                
                filtered_years = {}
                filtered_cats_or_subs = {}
                filtered_count = 0
                self.stats_current_filtered_products = []
                
                if cat_selected == "Todos":
                    pie_label.config(text="Distribución por categoría")
                else:
                    pie_label.config(text="Distribución por subtipo")
                    
                current_year_dt = datetime.now().year
                
                for prod in unique_products:
                    cat = self.get_product_category(prod)
                    year_raw = prod.get("anio", "")
                    if not year_raw:
                        year_raw = "Sin año"
                    year = str(year_raw).strip()
                    
                    include_by_time = False
                    if time_selected == "Todos los tiempos":
                        include_by_time = True
                    else:
                        if year.isdigit():
                            y_int = int(year)
                            if time_selected == "Último año":
                                if y_int == current_year_dt:
                                    include_by_time = True
                            elif time_selected == "Últimos 2 años":
                                if y_int >= current_year_dt - 1:
                                    include_by_time = True
                            elif time_selected == "Últimos 3 años":
                                if y_int >= current_year_dt - 2:
                                    include_by_time = True
                            elif time_selected == "Últimos 4 años":
                                if y_int >= current_year_dt - 3:
                                    include_by_time = True
                            elif time_selected == "Últimos 5 años":
                                if y_int >= current_year_dt - 4:
                                    include_by_time = True
                            elif time_selected == "Rango manual":
                                if y_int >= manual_start_year.get() and y_int <= manual_end_year.get():
                                    include_by_time = True
                    
                    if include_by_time:
                        subtipo = self.get_product_subtype(prod)
                        
                        if cat_selected == "Todos":
                            self.stats_current_filtered_products.append(prod)
                            if year in filtered_years:
                                filtered_years[year] = filtered_years[year] + 1
                            else:
                                filtered_years[year] = 1
                                
                            if cat in filtered_cats_or_subs:
                                filtered_cats_or_subs[cat] = filtered_cats_or_subs[cat] + 1
                            else:
                                filtered_cats_or_subs[cat] = 1
                                
                            filtered_count = filtered_count + 1
                        elif cat_selected == cat:
                            self.stats_current_filtered_products.append(prod)
                            if year in filtered_years:
                                filtered_years[year] = filtered_years[year] + 1
                            else:
                                filtered_years[year] = 1
                                
                            if subtipo in filtered_cats_or_subs:
                                filtered_cats_or_subs[subtipo] = filtered_cats_or_subs[subtipo] + 1
                            else:
                                filtered_cats_or_subs[subtipo] = 1
                                
                            filtered_count = filtered_count + 1
                        
                self.current_bar_data = filtered_years
                self.current_pie_data = filtered_cats_or_subs
                if cat_selected == "Todos":
                    self.current_pie_is_subtype = False
                else:
                    self.current_pie_is_subtype = True
                    
                prod_val_lbl.config(text=str(filtered_count))
                self.draw_bar_chart(bar, filtered_years)
                
                if len(filtered_cats_or_subs) == 1:
                    self.draw_text_info(pie, filtered_cats_or_subs, filtered_years, cat_selected != "Todos")
                else:
                    self.draw_pie_chart(pie, filtered_cats_or_subs)
                
            ttk.Button(filter_frame, text="Aplicar Filtro", command=update_statistics).pack(side="left", padx=8)
            
            def render_charts(event=None):
                update_statistics()
                
            bar.bind("<Configure>", render_charts)
            pie.bind("<Configure>", render_charts)
            self.after(80, render_charts)

        else:
            list_frame = tk.Frame(self.content, bg=BG)
            list_frame.pack(fill="both", expand=True, pady=16)
            tk.Label(list_frame, text="Presiona el botón 'Aplicar Filtro' para ver las estadísticas de la selección", bg=BG, fg=PRIMARY, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))
            
            if self.stats_current_view == "Investigadores":
                cols = [("selector", "\u2610 Todos", 50, "center"), ("codigoRh", "Código RH", 130, "w"), ("nombre", "Nombre", 340, "w"), ("categoria", "Categoría Minciencias", 220, "w")]
                items_data = []
                for idx, inv in enumerate(self.service.investigadores):
                    cod = inv.get("codigoRh", "")
                    nom = inv.get("nombre", "")
                    cat = inv.get("categoriaInvestigador", "")
                    if " con vigencia" in cat:
                        cat = cat.split(" con vigencia")[0].strip()
                    items_data.append((str(idx), cod, nom, cat))
            else:
                cols = [("selector", "\u2610 Todos", 50, "center"), ("codigo", "Código", 130, "w"), ("nombre", "Nombre", 340, "w"), ("lider", "Líder", 220, "w")]
                items_data = []
                for idx, grp in enumerate(self.service.grupos):
                    cod = grp.get("nroGrupo", "")
                    nom = grp.get("nombreGrupo", "")
                    lider = grp.get("lider", "")
                    items_data.append((str(idx), cod, nom, lider))
            
            tree = ttk.Treeview(list_frame, columns=[c[0] for c in cols], show="headings")
            for c_id, c_text, c_width, c_anchor in cols:
                tree.heading(c_id, text=c_text)
                tree.column(c_id, width=c_width, anchor=c_anchor)
                
            sb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=sb.set)
            tree.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            
            for d in items_data:
                tag_val = "\u2610"
                if d[0] in self.stats_selected_items:
                    tag_val = "\u2611"
                tree.insert("", "end", iid=d[0], values=(tag_val, *d[1:]))
            
            if len(self.stats_selected_items) > 0 and len(self.stats_selected_items) == len(items_data):
                tree.heading("selector", text="\u2611 Todos")
                
            def on_tree_click(event):
                region = tree.identify("region", event.x, event.y)
                if region == "heading":
                    col = tree.identify_column(event.x)
                    if col == "#1":
                        all_items = tree.get_children()
                        if len(self.stats_selected_items) == len(all_items):
                            self.stats_selected_items.clear()
                            for item in all_items:
                                vals = list(tree.item(item, "values"))
                                vals[0] = "\u2610"
                                tree.item(item, values=vals)
                            tree.heading("#1", text="\u2610 Todos")
                        else:
                            self.stats_selected_items.clear()
                            for item in all_items:
                                vals = list(tree.item(item, "values"))
                                vals[0] = "\u2611"
                                tree.item(item, values=vals)
                                self.stats_selected_items.append(item)
                            tree.heading("#1", text="\u2611 Todos")
                elif region == "cell":
                    col = tree.identify_column(event.x)
                    if col == "#1":
                        item = tree.identify_row(event.y)
                        if item:
                            vals = list(tree.item(item, "values"))
                            if vals[0] == "\u2610":
                                vals[0] = "\u2611"
                                if item not in self.stats_selected_items:
                                    self.stats_selected_items.append(item)
                            else:
                                vals[0] = "\u2610"
                                if item in self.stats_selected_items:
                                    self.stats_selected_items.remove(item)
                            tree.item(item, values=vals)
                            if len(self.stats_selected_items) == len(tree.get_children()):
                                tree.heading("#1", text="\u2611 Todos")
                            else:
                                tree.heading("#1", text="\u2610 Todos")
            
            tree.bind("<ButtonRelease-1>", on_tree_click)
            
            def open_large_popup():
                if popup_ref["win"]:
                    try:
                        popup_ref["win"].destroy()
                    except Exception:
                        pass
                    popup_ref["win"] = None
                    
                if not self.stats_selected_items:
                    messagebox.showerror("Error", "Debe seleccionar al menos 1 elemento para generar estadísticas.", parent=self)
                else:
                    
                    cat_selected = selected_category.get()
                    time_selected = selected_time.get()
                
                    filtered_years = {}
                    filtered_cats_or_subs = {}
                    filtered_count = 0
                    popup_filtered_products = []
                
                    current_year_dt = datetime.now().year
                
                    target_products = []
                    if self.stats_current_view == "Investigadores":
                        for idx_str in self.stats_selected_items:
                            idx_int = int(idx_str)
                            if idx_int < len(self.service.investigadores):
                                inv = self.service.investigadores[idx_int]
                                for prod in inv.get("productos", []):
                                    pc = dict(prod)
                                    pc["_autor_nombre"] = inv.get("nombre", "N/A")
                                    pc["_grupo_nombre"] = "N/A"
                                    target_products.append(pc)
                    else:
                        for idx_str in self.stats_selected_items:
                            idx_int = int(idx_str)
                            if idx_int < len(self.service.grupos):
                                grp = self.service.grupos[idx_int]
                                for prod in grp.get("productos", []):
                                    pc = dict(prod)
                                    autores = pc.get("autores", [])
                                    if isinstance(autores, list) and autores:
                                        pc["_autor_nombre"] = str(autores[0])
                                        if len(autores) > 1:
                                            pc["_autor_nombre"] += " y otros"
                                    elif isinstance(autores, str) and autores:
                                        pc["_autor_nombre"] = str(autores)
                                    else:
                                        pc["_autor_nombre"] = "N/A"
                                    pc["_grupo_nombre"] = str(grp.get("nombreGrupo", "N/A"))
                                    target_products.append(pc)
                                
                    unique_target_prods_dict = {}
                    for prod in target_products:
                        t_titulo = str(prod.get("titulo", ""))
                        t_anio = str(prod.get("anio", 0))
                        t_key = (canonical_key(t_titulo), t_anio)
                        if t_titulo:
                            if t_key not in unique_target_prods_dict:
                                unique_target_prods_dict[t_key] = dict(prod)
                            else:
                                existing = unique_target_prods_dict[t_key]
                                if existing.get("_grupo_nombre", "N/A") == "N/A" and prod.get("_grupo_nombre", "N/A") != "N/A":
                                    existing["_grupo_nombre"] = prod.get("_grupo_nombre")
                                if existing.get("_autor_nombre", "N/A") == "N/A" and prod.get("_autor_nombre", "N/A") != "N/A":
                                    existing["_autor_nombre"] = prod.get("_autor_nombre")
                    unique_target_prods = list(unique_target_prods_dict.values())
                
                    for prod in unique_target_prods:
                        cat = self.get_product_category(prod)
                        year_raw = prod.get("anio", "")
                        if not year_raw:
                            year_raw = "Sin año"
                        year = str(year_raw).strip()
                    
                        include_by_time = False
                        if time_selected == "Todos los tiempos":
                            include_by_time = True
                        else:
                            if year.isdigit():
                                y_int = int(year)
                                if time_selected == "Último año":
                                    if y_int == current_year_dt:
                                        include_by_time = True
                                elif time_selected == "Últimos 2 años":
                                    if y_int >= current_year_dt - 1:
                                        include_by_time = True
                                elif time_selected == "Últimos 3 años":
                                    if y_int >= current_year_dt - 2:
                                        include_by_time = True
                                elif time_selected == "Últimos 4 años":
                                    if y_int >= current_year_dt - 3:
                                        include_by_time = True
                                elif time_selected == "Últimos 5 años":
                                    if y_int >= current_year_dt - 4:
                                        include_by_time = True
                                elif time_selected == "Rango manual":
                                    if y_int >= manual_start_year.get() and y_int <= manual_end_year.get():
                                        include_by_time = True
                    
                        if include_by_time:
                            subtipo = self.get_product_subtype(prod)
                        
                            if cat_selected == "Todos":
                                popup_filtered_products.append(prod)
                                if year in filtered_years:
                                    filtered_years[year] = filtered_years[year] + 1
                                else:
                                    filtered_years[year] = 1
                                
                                if cat in filtered_cats_or_subs:
                                    filtered_cats_or_subs[cat] = filtered_cats_or_subs[cat] + 1
                                else:
                                    filtered_cats_or_subs[cat] = 1
                                
                                filtered_count = filtered_count + 1
                            elif cat_selected == cat:
                                popup_filtered_products.append(prod)
                                if year in filtered_years:
                                    filtered_years[year] = filtered_years[year] + 1
                                else:
                                    filtered_years[year] = 1
                                
                                if subtipo in filtered_cats_or_subs:
                                    filtered_cats_or_subs[subtipo] = filtered_cats_or_subs[subtipo] + 1
                                else:
                                    filtered_cats_or_subs[subtipo] = 1
                                
                                filtered_count = filtered_count + 1
                            
                    win = tk.Toplevel(self)
                    title_str = ""
                    if self.stats_current_view == "Investigadores":
                        if len(self.stats_selected_items) == 1:
                            title_str = "Estadísticas de producción del investigador seleccionado"
                        else:
                            title_str = "Estadísticas de producción de los investigadores seleccionados"
                    else:
                        if len(self.stats_selected_items) == 1:
                            title_str = "Estadísticas de producción del grupo seleccionado"
                        else:
                            title_str = "Estadísticas de producción de los grupos seleccionados"
                        
                    win.title(title_str)
                    win.geometry("1100x650")
                    win.configure(bg=BG)
                    win.update_idletasks()
                    x_c = (win.winfo_screenwidth() - win.winfo_width()) // 2
                    y_c = (win.winfo_screenheight() - win.winfo_height()) // 2
                    win.geometry(f"+{x_c}+{y_c}")
                
                    tk.Label(win, text=title_str, bg=BG, fg=DARK, font=("Segoe UI", 16, "bold")).pack(pady=15)
                
                    main_canvas = tk.Canvas(win, bg=BG, highlightthickness=0)
                    main_scroll = ttk.Scrollbar(win, orient="vertical", command=main_canvas.yview)
                    content_frame = tk.Frame(main_canvas, bg=BG)
                
                    main_canvas.configure(yscrollcommand=main_scroll.set)
                    main_scroll.pack(side="right", fill="y")
                    main_canvas.pack(side="left", fill="both", expand=True, padx=20, pady=(0, 20))
                
                    main_canvas.create_window((0, 0), window=content_frame, anchor="nw", tags="content_frame")
                
                    def _update_alignment(event=None):
                        main_canvas.update_idletasks()
                        bbox = main_canvas.bbox("content_frame")
                        if bbox:
                            cw = main_canvas.winfo_width()
                            ch = main_canvas.winfo_height()
                            fh = content_frame.winfo_reqheight()
                            if fh < ch:
                                main_canvas.coords("content_frame", 0, (ch - fh) / 2)
                            else:
                                main_canvas.coords("content_frame", 0, 0)
                            main_canvas.configure(scrollregion=main_canvas.bbox("all"))

                    def _on_content_config(event):
                        _update_alignment()
                    
                    content_frame.bind("<Configure>", _on_content_config)
                
                    def _on_main_canvas_config(event):
                        main_canvas.itemconfig("content_frame", width=event.width)
                        _update_alignment()
                    
                    main_canvas.bind("<Configure>", _on_main_canvas_config)
                
                    def _on_mousewheel_main(event):
                        main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                    win.bind("<MouseWheel>", _on_mousewheel_main)
                
                    top_panel = tk.Frame(content_frame, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
                    top_panel.pack(fill="x", pady=(0, 15))
                
                    btn_frame = tk.Frame(top_panel, bg=PANEL)
                    btn_frame.pack(fill="x", pady=10)
                
                    def open_popup_products():
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
                            self.build_products_ui(pwin, popup_filtered_products, authorship_mode=mode)
                    
                    ttk.Button(btn_frame, text="Ver Productos", command=open_popup_products).pack(anchor="center")
                
                    tk.Label(top_panel, text="Producción por Año", bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="center", pady=10)
                
                    bar_canvas = tk.Canvas(top_panel, bg=PANEL, highlightthickness=0, height=350)
                    bar_canvas.pack(fill="x", padx=15, pady=10)
                    bar_canvas.update_idletasks()
                    self.draw_bar_chart(bar_canvas, filtered_years)
                    bar_canvas.bind("<Configure>", lambda e: self.draw_bar_chart(bar_canvas, filtered_years))
                
                    left_info = tk.Frame(top_panel, bg=PANEL)
                    left_info.pack(fill="x", padx=15, pady=10)
                
                    info_container = tk.Frame(left_info, bg=PANEL)
                    info_container.pack(anchor="center")
                
                    items_years = sorted(filtered_years.items(), key=lambda item: str(item[0]))
                    valid_ys = []
                    for y, c in items_years:
                        if str(y).isdigit():
                            valid_ys.append(int(y))
                    if valid_ys:
                        y_min = min(valid_ys)
                        y_max = max(valid_ys)
                        y_span = y_max - y_min + 1
                        y_avg = 0
                        if y_span > 0:
                            y_avg = round(filtered_count / y_span, 1)
                        else:
                            y_avg = filtered_count
                        
                        tk.Label(info_container, text=f"Producción: {filtered_count} productos", bg=PANEL, fg=DARK, font=("Segoe UI", 10, "bold")).pack(anchor="center")
                        tk.Label(info_container, text=f"Años activos: {y_min} - {y_max}", bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="center")
                        tk.Label(info_container, text=f"Promedio general: {y_avg} prod/año", bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="center")
                
                    bottom_panel = tk.Frame(content_frame, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
                    bottom_panel.pack(fill="x", pady=(0, 15))
                
                    is_sub = (cat_selected != "Todos")
                    title_pie = ""
                    if is_sub:
                        title_pie = "Distribución por subtipo"
                    else:
                        title_pie = "Distribución por categoría"
                    
                    tk.Label(bottom_panel, text=title_pie, bg=PANEL, fg=DARK, font=("Segoe UI", 12, "bold")).pack(anchor="center", pady=10)
                
                    pie_container = tk.Frame(bottom_panel, bg=PANEL)
                    pie_container.pack(fill="x", padx=15, pady=10)
                
                    pie_canvas = tk.Canvas(pie_container, bg=PANEL, highlightthickness=0, width=400, height=400)
                    pie_canvas.pack(side="left", fill="both", expand=True, padx=(0, 20))
                    pie_canvas.update_idletasks()
                
                    if len(filtered_cats_or_subs) == 1:
                        pie_canvas.bind("<Configure>", lambda e: self.draw_text_info(pie_canvas, filtered_cats_or_subs, filtered_years, is_sub))
                        self.draw_text_info(pie_canvas, filtered_cats_or_subs, filtered_years, is_sub)
                    else:
                        palette = ["#3f75bd", "#5c8cd6", "#7ea4df", "#a1bce9", "#c3d5f2", "#e6eefb", "#2a548c", "#1d3e6a", "#152a48"]
                        pie_items = sorted(filtered_cats_or_subs.items(), key=lambda item: item[1], reverse=True)
                    
                        def draw_pie(event=None):
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
                                w = max(pie_canvas.winfo_width(), 100)
                            h = max(pie_canvas.winfo_height(), 100)
                            total_val = sum(v for _, v in pie_items)
                            size = min(w, h) - 40
                            if size < 50:
                                size = 50
                            x0 = (w - size) / 2
                            y0 = (h - size) / 2
                            start = 0.0
                            for idx, (label, value) in enumerate(pie_items):
                                if total_val:
                                    extent = 360.0 * value / total_val
                                    color = palette[idx % len(palette)]
                                    pie_canvas.create_arc(x0, y0, x0 + size, y0 + size, start=start, extent=extent, fill=color, outline=PANEL)
                                    start += extent
                                
                        pie_canvas.bind("<Configure>", draw_pie)
                        pie_canvas.after(50, draw_pie)
                    
                        legend_container = tk.Frame(pie_container, bg=PANEL)
                        if pie_items:
                            legend_container.pack(side="left", fill="both", expand=True)
                    
                        leg_canvas = tk.Canvas(legend_container, bg=PANEL, highlightthickness=0, height=400)
                        leg_scroll = ttk.Scrollbar(legend_container, orient="vertical", command=leg_canvas.yview)
                        legend_frame = tk.Frame(leg_canvas, bg=PANEL)
                    
                        leg_canvas.configure(yscrollcommand=leg_scroll.set)
                        leg_canvas.pack(side="left", fill="both", expand=True)
                    
                        leg_canvas.create_window((0, 0), window=legend_frame, anchor="n", tags="legend_inner")
                    
                        def _update_leg_align(event=None):
                            leg_canvas.update_idletasks()
                            fh = legend_frame.winfo_reqheight()
                            ch = leg_canvas.winfo_height()
                            cw = leg_canvas.winfo_width()
                            y = 0
                            if fh < ch:
                                y = (ch - fh) / 2
                            leg_canvas.coords("legend_inner", cw / 2, y)
                        
                        def _on_leg_config(event=None):
                            _update_leg_align()
                            bbox = leg_canvas.bbox("all")
                            if bbox:
                                leg_canvas.configure(scrollregion=bbox)
                            if bbox[3] > leg_canvas.winfo_height():
                                if not leg_scroll.winfo_ismapped():
                                    leg_scroll.pack(side="right", fill="y", before=leg_canvas)
                            else:
                                if leg_scroll.winfo_ismapped():
                                    leg_scroll.pack_forget()
                                
                        legend_frame.bind("<Configure>", _on_leg_config)
                        def _on_leg_canvas_config(event):
                            _update_leg_align()
                            _on_leg_config()
                        leg_canvas.bind("<Configure>", _on_leg_canvas_config)
                    
                        def _on_mousewheel_leg(event):
                            bbox = leg_canvas.bbox("all")
                            if bbox and bbox[3] > leg_canvas.winfo_height():
                                leg_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                                return "break"
                    
                        def _bind_leg_scroll(w):
                            w.bind("<MouseWheel>", _on_mousewheel_leg)
                            for child in w.winfo_children():
                                _bind_leg_scroll(child)
                            
                        for i, (label_name, val) in enumerate(pie_items):
                            color = palette[i % len(palette)]
                            row = tk.Frame(legend_frame, bg=PANEL)
                            row.pack(fill="x", pady=4)
                            tk.Label(row, text="■", fg=color, bg=PANEL, font=("Segoe UI", 14)).pack(side="left", padx=(0, 8))
                            pct = 0
                            if filtered_count:
                                pct = val / filtered_count * 100
                            tk.Label(row, text=f"{label_name} ({val}) - {pct:.1f}%", bg=PANEL, fg=DARK, font=("Segoe UI", 10), wraplength=450, justify="left").pack(side="left")
                        
                        _bind_leg_scroll(legend_frame)
                        leg_canvas.bind("<MouseWheel>", _on_mousewheel_leg)

            ttk.Button(filter_frame, text="Aplicar Filtro", command=open_large_popup).pack(side="left", padx=8)
            
    def draw_bar_chart(self, canvas: tk.Canvas, data: Dict[str, int]) -> None:
        canvas.delete("all")
        width = max(canvas.winfo_width(), 450)
        height = max(canvas.winfo_height(), 300)
        if not data:
            canvas.create_text(width / 2, height / 2, text="Sin datos suficientes para graficar", fill=MUTED, font=("Segoe UI", 10))
        else:
            items = sorted(data.items(), key=lambda item: str(item[0]))
            max_value = max(data.values())
            count = len(items)
            
            max_slot = 60
            avail_width = width - 100
            slot = avail_width / max(count, 1)
            
            if slot > max_slot:
                slot = max_slot
                
            plot_width = count * slot
            left = (width - plot_width) / 2
            bottom = height - 45
            top = 30
            plot_height = bottom - top
            
            canvas.create_line(left - 20, bottom, left + plot_width + 20, bottom, fill=BORDER)
            bar_width = max(18, slot * 0.58)
            for index, (label, value) in enumerate(items):
                x = left + slot * index + slot / 2
                bar_height = plot_height * value / max_value
                y0 = bottom - bar_height
                canvas.create_rectangle(x - bar_width / 2, y0, x + bar_width / 2, bottom, fill="#3f75bd", outline="")
                canvas.create_text(x, y0 - 10, text=str(value), fill=DARK, font=("Segoe UI", 8, "bold"))
                canvas.create_text(x, bottom + 16, text=str(label), fill=MUTED, font=("Segoe UI", 8), angle=45)

    def draw_text_info(self, canvas: tk.Canvas, data: Dict[str, int], years_data: Dict[str, int], is_subtype: bool = True):
        canvas.delete("all")
        width = max(canvas.winfo_width(), 450)
        height = max(canvas.winfo_height(), 300)
        
        label_text = "Desconocido"
        total = 0
        for l, t in data.items():
            label_text = l
            total = t
        
        valid_years = []
        for y, count in years_data.items():
            if str(y).isdigit():
                valid_years.append(int(y))
                
        if valid_years:
            min_y = min(valid_years)
            max_y = max(valid_years)
            span = max_y - min_y + 1
            if span > 0:
                avg = total / span
            else:
                avg = total
            avg_round = round(avg, 1)
            years_text = f"{min_y} - {max_y}"
            avg_text = f"{avg_round} prod/año"
        else:
            years_text = "No disponible"
            avg_text = "N/A"
            
        y_pos = height / 2 - 40
        if is_subtype:
            canvas.create_text(width / 2, y_pos, text="Categoría de subtipo único", fill=PRIMARY, font=("Segoe UI", 12, "bold"))
            canvas.create_text(width / 2, y_pos + 30, text=f"Subtipo: {label_text}", fill=DARK, font=("Segoe UI", 11))
        else:
            canvas.create_text(width / 2, y_pos, text="Única categoría registrada", fill=PRIMARY, font=("Segoe UI", 12, "bold"))
            canvas.create_text(width / 2, y_pos + 30, text=f"Categoría: {label_text}", fill=DARK, font=("Segoe UI", 11))
            
        canvas.create_text(width / 2, y_pos + 55, text=f"Total acumulado: {total} productos", fill=MUTED, font=("Segoe UI", 10))
        canvas.create_text(width / 2, y_pos + 80, text=f"Período de actividad: {years_text}", fill=MUTED, font=("Segoe UI", 10))
        canvas.create_text(width / 2, y_pos + 105, text=f"Promedio de producción: {avg_text}", fill=MUTED, font=("Segoe UI", 10))

    def draw_pie_chart(self, canvas: tk.Canvas, data: Dict[str, int]) -> None:
        canvas.delete("all")
        width = max(canvas.winfo_width(), 450)
        height = max(canvas.winfo_height(), 300)
        if not data:
            canvas.create_text(width / 2, height / 2, text="Sin datos suficientes para graficar", fill=MUTED, font=("Segoe UI", 10))
        else:
            palette = ["#3f75bd", "#6ca56c", "#d6a644", "#9b69bc", "#cf6e7c", "#55a8b2", "#8c9ba5"]
            items = sorted(data.items(), key=lambda item: item[1], reverse=True)
            max_categories = 6
            if len(items) > max_categories:
                chart_items = list(items[:max_categories])
                otros_count = sum(val for _, val in items[max_categories:])
                if otros_count > 0:
                    chart_items.append(("Otras categorías", otros_count))
            else:
                chart_items = list(items)

            total = sum(val for _, val in chart_items)
            size = min(width * 0.46, height * 0.72)
            x0 = 20
            y0 = (height - size) / 2
            start = 0.0
            for index, (label, value) in enumerate(chart_items):
                if total:
                    if index == len(chart_items) - 1:
                        extent = 360.0 - start
                    else:
                        extent = 360.0 * value / total
                    color = palette[index % len(palette)]
                    canvas.create_arc(x0, y0, x0 + size, y0 + size, start=start, extent=extent, fill=color, outline=PANEL)
                    start += extent

            legend_x = x0 + size + 24
            legend_y = max(18, int((height - len(chart_items) * 22) / 2))
            for index, (label, value) in enumerate(chart_items):
                color = palette[index % len(palette)]
                canvas.create_rectangle(legend_x, legend_y, legend_x + 12, legend_y + 12, fill=color, outline="")
                if len(label) <= 34:
                    disp_text = label
                else:
                    disp_text = label[:31] + "..."
                canvas.create_text(legend_x + 18, legend_y + 6, text=f"{disp_text} ({value})", anchor="w", fill=DARK, font=("Segoe UI", 8))
                legend_y += 22

    def draw_large_pie_chart(self, canvas: tk.Canvas, data: Dict[str, int]):
        canvas.delete("all")
        width = max(canvas.winfo_width(), 600)
        height = max(canvas.winfo_height(), 600)
        if not data:
            canvas.create_text(width / 2, height / 2, text="Sin datos", fill=MUTED)
        else:
            palette = ["#3f75bd", "#6ca56c", "#d6a644", "#9b69bc", "#cf6e7c", "#55a8b2", "#8c9ba5"]
            items = sorted(data.items(), key=lambda item: item[1], reverse=True)
            total = sum(val for _, val in items)
            
            size = min(width * 0.7, height * 0.5)
            x0 = (width - size) / 2
            y0 = 20
            
            start = 0.0
            for index, (label, value) in enumerate(items):
                if total:
                    extent = 360.0 * value / total
                    if extent >= 1.0:
                        color = palette[index % len(palette)]
                        canvas.create_arc(x0, y0, x0 + size, y0 + size, start=start, extent=extent, fill=color, outline=PANEL)
                    start += extent
                    
            legend_y = y0 + size + 30
            legend_x = 20
            for index, (label, value) in enumerate(items):
                color = palette[index % len(palette)]
                canvas.create_rectangle(legend_x, legend_y, legend_x + 14, legend_y + 14, fill=color, outline="")
                if total > 0:
                    pct = round(100 * value / total, 1)
                else:
                    pct = 0.0
                texto = f"{label} - {value} ({pct}%)"
                canvas.create_text(legend_x + 22, legend_y + 7, text=texto, anchor="w", fill=DARK, font=("Segoe UI", 10))
                legend_y += 26
                
    def show_pie_detail(self, data: Dict[str, int], is_subtype: bool, years_data: Dict[str, int]):
        win = tk.Toplevel(self)
        if is_subtype:
            win.title("Detalle: Distribución por Subtipo")
        else:
            win.title("Detalle: Distribución por Categoría")
        win.geometry("900x650")
        
        left_frame = tk.Frame(win, bg=PANEL)
        left_frame.pack(side="left", fill="both", expand=True)
        
        canvas = tk.Canvas(left_frame, bg=PANEL, highlightthickness=0)
        scroll_y = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        right_frame = tk.Frame(win, bg=BG, width=350)
        right_frame.pack(side="right", fill="y")
        right_frame.pack_propagate(False)
        
        tk.Label(right_frame, text="Información Detallada", bg=BG, fg=DARK, font=("Segoe UI", 14, "bold")).pack(pady=(20, 10), padx=15, anchor="w")
        
        if data:
            total_items = sum(data.values())
            num_cats = len(data)
            items_sorted = sorted(data.items(), key=lambda x: x[1], reverse=True)
            max_cat, max_val = items_sorted[0]
            min_cat, min_val = items_sorted[-1]
            
            info_text = f"Total de productos: {total_items}\n\n"
            if is_subtype:
                info_text += f"Cantidad de subtipos: {num_cats}\n\n"
                info_text += f"Subtipo más frecuente:\n- {max_cat} ({max_val})\n\n"
                info_text += f"Subtipo menos frecuente:\n- {min_cat} ({min_val})"
            else:
                info_text += f"Cantidad de categorías: {num_cats}\n\n"
                info_text += f"Categoría más frecuente:\n- {max_cat} ({max_val})\n\n"
                info_text += f"Categoría menos frecuente:\n- {min_cat} ({min_val})"
                
            tk.Label(right_frame, text=info_text, bg=BG, fg=MUTED, font=("Segoe UI", 11), justify="left", wraplength=320).pack(padx=15, anchor="w")
            
            tk.Label(right_frame, text="Desglose completo:", bg=BG, fg=DARK, font=("Segoe UI", 12, "bold")).pack(pady=(20, 10), padx=15, anchor="w")
            
            list_frame = tk.Frame(right_frame, bg=BG)
            list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 20))
            
            tree = ttk.Treeview(list_frame, columns=("nombre", "cantidad"), show="headings")
            tree.heading("nombre", text="Nombre")
            tree.heading("cantidad", text="Cantidad")
            tree.column("nombre", width=220)
            tree.column("cantidad", width=80, anchor="center")
            
            for label, value in items_sorted:
                tree.insert("", "end", values=(label, value))
                
            sb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=sb.set)
            tree.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            
        def on_resize(event):
            if len(data) == 1:
                self.draw_text_info(canvas, data, years_data, is_subtype)
            else:
                self.draw_large_pie_chart(canvas, data)
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
            
        canvas.bind("<Configure>", on_resize)
        def on_mousewheel(event):
            widget_under_mouse = win.winfo_containing(event.x_root, event.y_root)
            if widget_under_mouse == canvas or widget_under_mouse == left_frame:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        win.bind("<MouseWheel>", on_mousewheel)
        
    def show_bar_detail(self, data: Dict[str, int]):
        win = tk.Toplevel(self)
        win.title("Detalle: Productos por Año")
        win.geometry("900x550")
        
        left_frame = tk.Frame(win, bg=PANEL)
        left_frame.pack(side="left", fill="both", expand=True)
        
        canvas = tk.Canvas(left_frame, bg=PANEL, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=20, pady=20)
        
        right_frame = tk.Frame(win, bg=BG, width=350)
        right_frame.pack(side="right", fill="y")
        right_frame.pack_propagate(False)
        
        tk.Label(right_frame, text="Información Detallada", bg=BG, fg=DARK, font=("Segoe UI", 14, "bold")).pack(pady=(20, 10), padx=15, anchor="w")
        
        if data:
            valid_years = []
            for y in data.keys():
                if str(y).isdigit():
                    valid_years.append(int(y))
                    
            total_items = sum(data.values())
            
            if valid_years:
                min_y = min(valid_years)
                max_y = max(valid_years)
                span = max_y - min_y + 1
                if span > 0:
                    avg = total_items / span
                else:
                    avg = total_items
                avg_round = round(avg, 1)
                
                items_sorted_by_val = sorted(data.items(), key=lambda x: x[1], reverse=True)
                best_year, best_val = items_sorted_by_val[0]
                
                info_text = f"Total acumulado: {total_items} productos\n\n"
                info_text += f"Años con producción: {len(valid_years)}\n\n"
                info_text += f"Rango activo: {min_y} - {max_y}\n\n"
                info_text += f"Promedio anual (en rango): {avg_round}\n\n"
                info_text += f"Año más productivo: {best_year} ({best_val} prod.)"
            else:
                info_text = f"Total acumulado: {total_items} productos\n\nNo hay años válidos detectados."
                
            tk.Label(right_frame, text=info_text, bg=BG, fg=MUTED, font=("Segoe UI", 11), justify="left").pack(padx=15, anchor="w")
            
            tk.Label(right_frame, text="Desglose por año:", bg=BG, fg=DARK, font=("Segoe UI", 12, "bold")).pack(pady=(20, 10), padx=15, anchor="w")
            
            list_frame = tk.Frame(right_frame, bg=BG)
            list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 20))
            
            tree = ttk.Treeview(list_frame, columns=("anio", "cantidad"), show="headings")
            tree.heading("anio", text="Año")
            tree.heading("cantidad", text="Cantidad")
            tree.column("anio", width=150)
            tree.column("cantidad", width=150, anchor="center")
            
            for y, val in sorted(data.items(), key=lambda x: str(x[0]), reverse=True):
                tree.insert("", "end", values=(y, val))
                
            sb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=sb.set)
            tree.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            
        def on_resize(event):
            self.draw_bar_chart(canvas, data)
            
        canvas.bind("<Configure>", on_resize)

    def build_reports(self) -> None:
        self.heading("Reportes / Análisis", "Consultas consolidadas y preparación de salidas analíticas")
        panel = tk.Frame(self.content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="Generador de reportes", bg=PANEL, fg=DARK, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=(18, 8))
        description = "Genera vistas tabulares detalladas o exporta la información general del sistema en formato de texto."
        tk.Label(panel, text=description, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=760, justify="left").pack(anchor="w", padx=18, pady=(0, 18))
        ttk.Button(panel, text="Resumen de investigadores", command=self.report_investigators).pack(anchor="w", padx=18, pady=4)
        ttk.Button(panel, text="Resumen de grupos", command=self.report_groups).pack(anchor="w", padx=18, pady=4)
        ttk.Button(panel, text="Resumen de producción", command=self.report_products).pack(anchor="w", padx=18, pady=4)
        ttk.Button(panel, text="Guardar Información del Dashboard", command=self.export_dashboard).pack(anchor="w", padx=18, pady=4)

    def report_investigators(self) -> None:
        stats = self.service.statistics()
        win = tk.Toplevel(self)
        win.title(f"Resumen de investigadores (Total: {stats['investigadores']}, Activos: {stats['investigadores_activos']})")
        win.geometry("800x400")
        
        tree = ttk.Treeview(win, columns=("codigo", "nombre", "categoria"), show="headings")
        tree.heading("codigo", text="Código RH")
        tree.heading("nombre", text="Nombre")
        tree.heading("categoria", text="Categoría")
        
        tree.column("codigo", width=120)
        tree.column("nombre", width=300)
        tree.column("categoria", width=150)
        
        for item in self.service.investigadores:
            tree.insert("", "end", values=(
                item.get("codigoRh", ""),
                item.get("nombre", ""),
                item.get("categoriaInvestigador", "")
            ))
            
        scroll = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def report_groups(self) -> None:
        win = tk.Toplevel(self)
        win.title(f"Resumen de grupos (Total: {len(self.service.grupos)})")
        win.geometry("900x400")
        
        tree = ttk.Treeview(win, columns=("nro", "nombre", "lider", "clasificacion"), show="headings")
        tree.heading("nro", text="Número")
        tree.heading("nombre", text="Nombre del Grupo")
        tree.heading("lider", text="Líder")
        tree.heading("clasificacion", text="Clasificación")
        
        tree.column("nro", width=120)
        tree.column("nombre", width=300)
        tree.column("lider", width=250)
        tree.column("clasificacion", width=150)
        
        for item in self.service.grupos:
            tree.insert("", "end", values=(
                item.get("nroGrupo", ""),
                item.get("nombreGrupo", ""),
                item.get("lider", ""),
                item.get("clasificacion", "")
            ))
            
        scroll = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def report_products(self) -> None:
        stats = self.service.statistics()
        win = tk.Toplevel(self)
        win.title(f"Resumen de producción (Total únicos: {stats['productos']})")
        win.geometry("400x400")
        
        tree = ttk.Treeview(win, columns=("anio", "cantidad"), show="headings")
        tree.heading("anio", text="Año")
        tree.heading("cantidad", text="Cantidad de Productos")
        
        for year, count in sorted(stats.get("anios", {}).items(), key=lambda item: str(item[0])):
            tree.insert("", "end", values=(year, count))
            
        scroll = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def export_dashboard(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", 
            initialfile="Reporte PEA-i Dashboard",
            filetypes=[("Archivo de texto", "*.txt")]
        )
        if path:
            dash = self.service.dashboard()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("="*50 + "\n")
                    f.write("      REPORTE PEA-i DASHBOARD\n")
                    f.write("="*50 + "\n\n")
                    
                    f.write("--- ESTADÍSTICAS GENERALES ---\n")
                    stats = dash.get("stats", {})
                    f.write(f"Total Investigadores: {stats.get('investigadores', 0)}\n")
                    f.write(f"Investigadores Activos: {stats.get('investigadores_activos', 0)}\n")
                    f.write(f"Total Grupos: {stats.get('grupos', 0)}\n")
                    f.write(f"Total Productos (Únicos): {stats.get('productos', 0)}\n\n")
                    
                    f.write("--- PRODUCCIÓN POR AÑO ---\n")
                    anios = stats.get("anios", {})
                    for anio, cant in sorted(anios.items(), key=lambda item: str(item[0])):
                        f.write(f"{anio}: {cant} productos\n")
                    f.write("\n")
                    
                    f.write("--- INVESTIGADORES CARGADOS ---\n")
                    for inv in self.service.investigadores:
                        f.write(f"- {inv.get('nombre', 'Sin Nombre')} (RH: {inv.get('codigoRh', 'N/A')})\n")
                    f.write("\n")
                    
                    f.write("--- GRUPOS CARGADOS ---\n")
                    for grp in self.service.grupos:
                        f.write(f"- {grp.get('nombreGrupo', 'Sin Nombre')} (Nro: {grp.get('nroGrupo', 'N/A')})\n")
                messagebox.showinfo("Exportación", "Dashboard exportado correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No fue posible exportar: {str(e)}")

    def save_data(self) -> None:
        ok = self.service.save_all()
        if ok:
            self.status.set("Datos guardados correctamente")
            if getattr(self, "current_view", "") == "Inicio":
                self.show_view("Inicio")
            messagebox.showinfo("Guardar datos", "Los investigadores y grupos fueron guardados en JSON.")
        else:
            self.status.set("No se pudieron guardar todos los datos")
            messagebox.showerror("Guardar datos", "No fue posible escribir los archivos JSON.")


# =========================================================================
# PUNTOS DE ENTRADA Y CONTROL DEL APLICATIVO
# =========================================================================

def run_api() -> None:
    """Inicia el servidor API local para servir solicitudes desde C++."""
    service = ApplicationService()
    server = LocalAPIServer(service, HOST, PORT)
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        server.shutdown()


def run_gui() -> None:
    """Inicia la interfaz grafica de usuario en modo escritorio Tkinter."""
    service = ApplicationService()
    app = PEAApp(service)
    app.mainloop()


def parse_arguments():
    """Parsea los argumentos de linea de comandos."""
    parser = argparse.ArgumentParser(
        prog="PEA-i",
        description="PEA-i Programa Estadístico de Análisis de Investigacion"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Inicia la API local en 127.0.0.1:8765 para integracion con C++"
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.api:
        run_api()
    else:
        run_gui()


if __name__ == "__main__":
    main()
