import fitz
import re

doc = fitz.open(r"C:\Users\camil\Desktop\Aith Bismarck.pdf")
text = "\n".join([p.get_text() for p in doc])
text = text.replace("\xa0", " ")

# Buscar encabezados de productos tipo MinCiencias
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
pat = re.compile(rf"(?:^|\n)({header_combined})\n", re.IGNORECASE)

matches = list(pat.finditer(text))
print("Total productos encontrados:", len(matches))

prods = []
for i in range(len(matches)):
    start = matches[i].end()
    end = matches[i+1].start() if i + 1 < len(matches) else len(text)
    tipo_encabezado = matches[i].group(1).strip()
    bloque = text[start:end].strip()
    
    # Extraer titulo
    titulo = ""
    m_comillas = re.search(r'"([^"\r\n]{5,})"', bloque)
    if m_comillas:
        titulo = m_comillas.group(1).strip()
    else:
        # En MinCiencias, formato: AUTOR1, AUTOR2, TITULO . En: ...
        # O: Titulo: TITULO Tipo de trabajo...
        m_tit_lbl = re.search(r'Titulo:\s*([^\n\r]+)', bloque, re.IGNORECASE)
        if m_tit_lbl:
            titulo = m_tit_lbl.group(1).strip()
        else:
            lineas = [l.strip() for l in bloque.split("\n") if l.strip()]
            if lineas:
                # Si la primera linea son autores y la segunda o coma tiene titulo
                primera = lineas[0]
                partes = primera.split(",")
                if len(partes) > 1 and len(partes[-1].strip()) > 5:
                    titulo = partes[-1].strip()
                elif len(lineas) > 1 and len(lineas[1]) > 5:
                    titulo = lineas[1].strip()
                else:
                    titulo = primera
    
    # Limpiar prefijos
    titulo = re.sub(r'^[•\-\*#]+\s*', '', titulo)
    titulo = re.sub(r'^\d+\s*[\.\-\)]\s*', '', titulo)
    
    # Extraer anio
    anios = re.findall(r'\b(19\d\d|20[0-3]\d)\b', bloque)
    anio = int(anios[-1]) if anios else 0
    
    # Categoria
    cat = "Artículo"
    tipo_low = tipo_encabezado.lower()
    if "software" in tipo_low:
        cat = "Software"
    elif "capítulo" in tipo_low or "capitulo" in tipo_low or "libro" in tipo_low:
        cat = "Capítulo de libro"
    elif "consultor" in tipo_low:
        cat = "Consultoría"
    elif "tutoria" in tipo_low or "trabajos dirigidos" in tipo_low:
        cat = "Trabajo dirigido"
    elif "jurado" in tipo_low:
        cat = "Jurado / Evaluación"
    elif "empresa" in tipo_low:
        cat = "Empresa de base tecnológica"
    
    if len(titulo) > 3:
        prods.append((cat, titulo, anio))

print("Total productos procesados:", len(prods))
for cat, tit, anio in prods[:10]:
    print(f"[{cat}] ({anio}) -> {tit[:60]}")
