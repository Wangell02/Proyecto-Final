import fitz

doc = fitz.open(r"C:\Users\camil\Desktop\Aitice.pdf")
text = "\n".join([p.get_text() for p in doc])
text = text.replace("\xa0", " ")

lines = text.splitlines()

for i, l in enumerate(lines):
    if l in ["PRODUCCIÓN BIBLIOGRÁFICA", "Artículos publicados", "Libros publicados", "Capítulos de libro publicados", "PRODUCCIÓN TÉCNICA Y TECNOLÓGICA", "Softwares"]:
        print(f"Linea {i}: {l}")
        for j in range(i+1, min(i+15, len(lines))):
            print(f"   {j}: {repr(lines[j])}")
