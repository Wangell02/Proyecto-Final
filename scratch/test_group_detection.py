import fitz
import re

def check_pdf(path):
    doc = fitz.open(path)
    text = "\n".join([p.get_text() for p in doc])
    text = text.replace("\xa0", " ")
    
    # Marcadores de Grupo
    is_group = False
    if "año y mes de formación" in text.lower() or "ano y mes de formacion" in text.lower():
        is_group = True
    elif "integrantes del grupo" in text.lower() and ("horas dedicación" in text.lower() or "horas dedicacion" in text.lower()):
        is_group = True
    elif "datos básicos" in text.lower() and "líder" in text.lower():
        is_group = True
    elif "gruplac" in text.lower() or "datos generales del grupo" in text.lower():
        is_group = True
    elif "líneas de investigación declaradas por el grupo" in text.lower() or "lineas de investigacion declaradas por el grupo" in text.lower():
        is_group = True

    # Marcadores de CvLAC
    is_cvlac = False
    if "hoja de vida" in text.lower() and ("par evaluador" in text.lower() or "nombre en citaciones" in text.lower()):
        is_cvlac = True
    elif "cvlac" in text.lower() or "currículum vítae" in text.lower() or "curriculum vitae" in text.lower():
        is_cvlac = True

    print(f"File: {path}")
    print(f"  is_group: {is_group}, is_cvlac: {is_cvlac}")
    if is_group and not is_cvlac:
        print("  -> GRUPO")
    elif is_cvlac and not is_group:
        print("  -> INVESTIGADOR")
    else:
        print("  -> MIXTO / LOTE")

check_pdf(r"C:\Users\camil\Desktop\Aith Bismarck.pdf")
check_pdf(r"C:\Users\camil\Desktop\Aitice.pdf")
