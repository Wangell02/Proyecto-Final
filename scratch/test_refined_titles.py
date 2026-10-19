import fitz
import re

doc = fitz.open(r"C:\Users\camil\Desktop\Aith Bismarck.pdf")
text = "\n".join([p.get_text() for p in doc])
text = text.replace("\xa0", " ")

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

def extract_title(bloque, tipo_header):
    # 1. Comillas
    m_comillas = re.search(r'"([^"\r\n]{5,})"', bloque)
    if m_comillas:
        return m_comillas.group(1).strip()
    
    # 2. Titulo: ...
    m_tit = re.search(r'Titulo:\s*([^\n\r]+)', bloque, re.IGNORECASE)
    if m_tit:
        t = m_tit.group(1).strip()
        t = re.split(r'\s+Tipo\s+de\s+trabajo', t, flags=re.IGNORECASE)[0]
        return t.strip()
    
    # 3. Analizar primera línea
    lineas = [l.strip() for l in bloque.split("\n") if l.strip()]
    if not lineas:
        return ""
    primera = lineas[0]
    
    # Cortar etiquetas finales conocidas
    for tag in [r',\s*Finalidad:', r',\s*Nombre\s+comercial:', r',\s*\. En:', r',\s*contrato/registro:', r'\s+Estado:']:
        m_tag = re.search(tag, primera, re.IGNORECASE)
        if m_tag:
            primera = primera[:m_tag.start()]
            break
            
    # Quitar posibles autores (lo que esté antes de la primera coma si parece nombre)
    partes = primera.split(",")
    if len(partes) > 1:
        # La primera parte es el autor, el resto es el titulo
        cand = ",".join(partes[1:]).strip()
        if len(cand) > 5:
            primera = cand
            
    return primera.strip()

print("Muestreo de productos extraidos con logica refinada:")
for i in range(min(15, len(p_matches))):
    start = p_matches[i].end()
    end = p_matches[i+1].start() if i+1 < len(p_matches) else len(text)
    hdr = p_matches[i].group(1).strip()
    blk = text[start:end].strip()
    tit = extract_title(blk, hdr)
    anios = re.findall(r'\b(19\d\d|20[0-3]\d)\b', blk)
    anio = int(anios[-1]) if anios else 0
    print(f"{i+1}. {hdr[:35]} | {anio} | -> {tit}")
