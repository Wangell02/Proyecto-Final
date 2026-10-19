import fitz

doc = fitz.open(r"C:\Users\camil\Desktop\Aitice.pdf")
text = "\n".join([p.get_text() for p in doc])
text = text.replace("\xa0", " ")

print("Total paginas:", len(doc))
print("Longitud de texto:", len(text))
print("\n--- PRIMERAS 60 LINEAS ---")
for i, l in enumerate(text.splitlines()[:60]):
    print(f"{i}: {repr(l)}")
