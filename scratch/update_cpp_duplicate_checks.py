import re

with open(r"DLDD-MAFF-JDLA.cpp", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Extract canonicalKey definition
m_canon = re.search(r'static string canonicalKey\(const string &texto\) \{.*?\n\}\n', content, re.DOTALL)
assert m_canon is not None, "canonicalKey definition not found in cpp!"
canon_def = m_canon.group(0)

# Remove old canonicalKey from line ~736
content = content[:m_canon.start()] + content[m_canon.end():]

# Place canonicalKey right before "// LISTA DE INVESTIGADORES"
pos_lista_inv = content.find("// LISTA DE INVESTIGADORES")
assert pos_lista_inv != -1, "LISTA DE INVESTIGADORES not found in cpp!"

content = content[:pos_lista_inv] + canon_def + "\n" + content[pos_lista_inv:]

# 2. Add buscarCoincidencia to ListaInvestigadores
buscar_coincidencia_inv = '''  Investigador *buscarCoincidencia(const Investigador *otro) {
    if (!otro) {
      return NULL;
    }
    string codOtro = otro->codigoRh;
    string nomOtro = canonicalKey(otro->nombre);
    string orcidOtro = canonicalKey(otro->orcid);
    string correoOtro = canonicalKey(otro->email);

    NodoInvestigador *actual = cabeza;
    Investigador *encontrado = NULL;

    while (actual && !encontrado) {
      Investigador *cur = actual->investigador;
      if (cur) {
        bool coincide = false;
        if (!codOtro.empty() && !cur->codigoRh.empty() && codOtro == cur->codigoRh) {
          coincide = true;
        }
        if (!coincide && !nomOtro.empty() && nomOtro.size() >= 4) {
          string nomCur = canonicalKey(cur->nombre);
          if (nomOtro == nomCur) {
            coincide = true;
          }
        }
        if (!coincide && !orcidOtro.empty() && orcidOtro.size() >= 8) {
          string orcidCur = canonicalKey(cur->orcid);
          if (orcidOtro == orcidCur) {
            coincide = true;
          }
        }
        if (!coincide && !correoOtro.empty() && correoOtro.size() >= 5) {
          string correoCur = canonicalKey(cur->email);
          if (correoOtro == correoCur) {
            coincide = true;
          }
        }

        if (coincide) {
          encontrado = cur;
        }
      }
      actual = actual->sig;
    }

    return encontrado;
  }

'''

pos_buscar_inv = content.find("Investigador *buscar(string codigo) {")
assert pos_buscar_inv != -1, "buscar in ListaInvestigadores not found!"
content = content[:pos_buscar_inv] + buscar_coincidencia_inv + content[pos_buscar_inv:]

# 3. Add buscarGrupoCoincidencia to Multilistas
buscar_coincidencia_grp = '''  NodoGrupo *buscarGrupoCoincidencia(const GrupoInvestigacion *otro) {
    if (!otro) {
      return NULL;
    }
    string numOtro = otro->nroGrupo;
    string nomOtro = canonicalKey(otro->nombreGrupo);

    NodoGrupo *actual = cabeza;
    NodoGrupo *encontrado = NULL;

    while (actual && !encontrado) {
      GrupoInvestigacion *cur = actual->grupo;
      if (cur) {
        bool coincide = false;
        if (!numOtro.empty() && !cur->nroGrupo.empty() && numOtro == cur->nroGrupo) {
          coincide = true;
        }
        if (!coincide && !nomOtro.empty() && nomOtro.size() >= 4) {
          string nomCur = canonicalKey(cur->nombreGrupo);
          if (nomOtro == nomCur) {
            coincide = true;
          }
        }

        if (coincide) {
          encontrado = actual;
        }
      }
      actual = actual->sig;
    }

    return encontrado;
  }

'''

pos_buscar_grp = content.find("NodoGrupo *buscarGrupo(string idGrupo) {")
assert pos_buscar_grp != -1, "buscarGrupo in Multilistas not found!"
content = content[:pos_buscar_grp] + buscar_coincidencia_grp + content[pos_buscar_grp:]

# 4. In cargarInvestigador(): replace listasInv.buscar(investigador->codigoRh)
old_ci = "if (listasInv.buscar(investigador->codigoRh) != NULL)"
new_ci = "if (listasInv.buscarCoincidencia(investigador) != NULL)"
assert old_ci in content, "old_ci not found!"
content = content.replace(old_ci, new_ci, 1)

# 5. In cargarGrupo(): replace multilistas.buscarGrupo(grupo->nroGrupo)
old_cg = "if (multilistas.buscarGrupo(grupo->nroGrupo) != NULL)"
new_cg = "if (multilistas.buscarGrupoCoincidencia(grupo) != NULL)"
assert old_cg in content, "old_cg not found!"
content = content.replace(old_cg, new_cg, 1)

# 6. In cargarDesdePdfConsola(): replace in investigators and groups
old_cpdf_inv = "if (listasInv.buscar(inv->codigoRh) != NULL)"
new_cpdf_inv = "if (listasInv.buscarCoincidencia(inv) != NULL)"
assert old_cpdf_inv in content, "old_cpdf_inv not found!"
content = content.replace(old_cpdf_inv, new_cpdf_inv, 1)

old_cpdf_grp = "if (multilistas.buscarGrupo(grp->nroGrupo) != NULL)"
new_cpdf_grp = "if (multilistas.buscarGrupoCoincidencia(grp) != NULL)"
assert old_cpdf_grp in content, "old_cpdf_grp not found!"
content = content.replace(old_cpdf_grp, new_cpdf_grp, 1)

with open(r"DLDD-MAFF-JDLA.cpp", "w", encoding="utf-8") as f:
    f.write(content)

print("Actualización de DLDD-MAFF-JDLA.cpp completada con éxito!")
