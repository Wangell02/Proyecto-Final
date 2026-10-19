import fitz
import re

doc = fitz.open(r"C:\Users\camil\Desktop\Aith Bismarck.pdf")
text = "\n".join([p.get_text() for p in doc])
text = text.replace("\xa0", " ")

# Miremos las primeras 3 entradas de cursos de corta duración
pos = text.find("Cursos de corta duración")
print(repr(text[pos:pos+1200]))
