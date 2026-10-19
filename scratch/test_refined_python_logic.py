import fitz
import re
from typing import Dict, Any, List, Tuple

def clean_text(s: str) -> str:
    if not s:
        return ""
    return " ".join(str(s).split()).strip()

def canonical_key(s: str) -> str:
    if not s:
        return ""
    norm = s.strip().lower()
    for o, d in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n')]:
        norm = norm.replace(o, d)
    return re.sub(r'[^a-z0-9]', '', norm)

class MockService:
    def __init__(self):
        self.investigadores = []
        self.grupos = []

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
            return True, "Investigador cargado correctamente."
        elif tipo == "grupo":
            duplicate = False
            for current in self.grupos:
                if self._is_duplicate_group(result, current):
                    duplicate = True
            if duplicate:
                return False, "El grupo ya se encuentra cargado."
            self.grupos.append(result)
            return True, "Grupo cargado correctamente."
        else:
            return False, "El resultado del scraper no tiene un tipo válido."

print("=== PRUEBA DE SERVICIO Y DUPLICADOS ===")
service = MockService()
# 1. Simular carga de Adith desde web
inv_web = {"tipo": "INVESTIGADOR", "codigoRh": "0000799157", "nombre": "Adith Bismarck Pérez Orozco", "productos": []}
ok1, msg1 = service.add_scraped_result(inv_web)
print(f"Carga web Adith: ok={ok1}, msg={msg1}")

# 2. Simular carga de Adith desde PDF (codigo distinto INV_ADITHBISM, mismo nombre)
inv_pdf = {"tipo": "INVESTIGADOR", "codigoRh": "INV_ADITHBISM", "nombre": "Adith Bismarck Pérez Orozco", "productos": []}
ok2, msg2 = service.add_scraped_result(inv_pdf)
print(f"Carga PDF Adith: ok={ok2}, msg={msg2}")
assert ok2 is False, "Debe rechazar Adith por nombre duplicado!"

# 3. Simular carga de AITICE desde web
grp_web = {"tipo": "GRUPO", "nroGrupo": "COL0081234", "nombreGrupo": "AITICE", "lider": "Armando Lopez"}
ok3, msg3 = service.add_scraped_result(grp_web)
print(f"Carga web AITICE: ok={ok3}, msg={msg3}")

# 4. Simular carga de AITICE desde PDF (codigo distinto GRP_AITICE, mismo nombre)
grp_pdf = {"tipo": "GRUPO", "nroGrupo": "GRP_AITICE", "nombreGrupo": "AITICE", "lider": "Armando Javier Lopez Sierra"}
ok4, msg4 = service.add_scraped_result(grp_pdf)
print(f"Carga PDF AITICE: ok={ok4}, msg={msg4}")
assert ok4 is False, "Debe rechazar AITICE por nombre duplicado!"

print("Todas las aserciones de duplicados pasaron satisfactoriamente!")
