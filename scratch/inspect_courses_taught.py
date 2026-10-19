import fitz

doc = fitz.open(r"C:\Users\camil\Desktop\Aith Bismarck.pdf")
text = "\n".join([p.get_text() for p in doc])
text = text.replace("\xa0", " ")

pos = text.find("Producción técnica - Cursos de corta duración dictados")
print(repr(text[pos:pos+700]))
