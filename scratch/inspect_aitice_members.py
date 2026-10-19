import fitz

doc = fitz.open(r"C:\Users\camil\Desktop\Aitice.pdf")
text = "\n".join([p.get_text() for p in doc])
text = text.replace("\xa0", " ")

lines = text.splitlines()
print("\n--- LINEAS 55 A 120 (INTEGRANTES) ---")
for i, l in enumerate(lines[55:120], start=55):
    print(f"{i}: {repr(l)}")
