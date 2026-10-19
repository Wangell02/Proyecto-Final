
#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#ifdef _WIN32
#include <conio.h>
#include <windows.h>
#include <winhttp.h>
#else
// Fallback para sistemas no Windows
#include <stdio.h>
#include <termios.h>
#include <unistd.h>

inline void gotoxy(int x, int y) { printf("\033[%d;%dH", y, x); }

inline void Sleep(int ms) { usleep(ms * 1000); }

#endif

using namespace std;

// =========================================================================
// gotoxy NATIVO PARA WINDOWS
// =========================================================================

#ifdef _WIN32

void gotoxy(int x, int y) {

  COORD coord;

  coord.X = x;
  coord.Y = y;

  SetConsoleCursorPosition(GetStdHandle(STD_OUTPUT_HANDLE), coord);
}

#endif

// =========================================================================
// PERSISTENCIA EN TXT PLANO
// =========================================================================

// =========================================================================
// PRODUCTO DE INVESTIGACION
// =========================================================================

struct ProductoInvestigacion {

  string idProducto;
  string titulo;
  string categoria;
  bool validado;
  int anio;

  // Datos que pueden aparecer en GrupLAC/CvLAC.
  string tipoProducto;
  string subtipo;
  string doi;
  string isbn;
  string revista;
  string editorial;
  string disponibilidad;
  string institucion;
  string ciudad;
  string pais;
  string numeroContrato;
  string descripcion;
  string palabrasClave;
  string areas;

  vector<string> autores;

  ProductoInvestigacion(string id = "", string t = "", string c = "",
                        bool v = false, int a = 0, string tipo = "",
                        string sub = "", string d = "", string i = "",
                        string r = "", string e = "", string disp = "",
                        string inst = "", string ciu = "", string p = "",
                        string contrato = "", string desc = "",
                        string palabras = "", string ars = "")
      : idProducto(id), titulo(t), categoria(c), validado(v), anio(a),
        tipoProducto(tipo), subtipo(sub), doi(d), isbn(i), revista(r),
        editorial(e), disponibilidad(disp), institucion(inst), ciudad(ciu),
        pais(p), numeroContrato(contrato), descripcion(desc),
        palabrasClave(palabras), areas(ars) {}
};

// =========================================================================
// NODO PRODUCTO//
// =========================================================================
// NODO PRODUCTO
// =========================================================================

struct NodoProducto {

  ProductoInvestigacion *producto;
  NodoProducto *sig;

  NodoProducto(ProductoInvestigacion *p) : producto(p), sig(NULL) {}

  ~NodoProducto() { delete producto; }
};

// =========================================================================
// INVESTIGADOR
// =========================================================================

struct Investigador {

  string codigoRh;
  string nombre;
  string correo;

  // Datos complementarios que pueden aparecer en CvLAC.
  string orcid;
  string institucion;
  string departamento;
  string ciudad;
  string categoriaInvestigador;
  string perfil;
  string nombreCitaciones;
  string nacionalidad;
  string sexo;
  string estadoParEvaluador;

  string researcherId;
  string autorIdScopus;
  string googleScholar;
  string researchGate;
  string academiaEdu;
  string mendeley;
  string linkedin;
  string repositorioInstitucional;

  vector<string> idiomas;

  // Secciones de la hoja de vida.
  vector<string> areasConocimiento;
  vector<string> lineasInvestigacion;
  vector<string> formacionAcademica;
  vector<string> experienciaProfesional;
  vector<string> gruposInvestigacion;
  vector<string> semilleros;
  vector<string> proyectos;
  vector<string> reconocimientos;

  NodoProducto *productos;

  bool activo;

  Investigador(string id = "", string nom = "", string corr = "", string o = "",
               string inst = "", string dep = "", string ciu = "",
               string categoria = "", string per = "")
      : codigoRh(id), nombre(nom), correo(corr), orcid(o), institucion(inst),
        departamento(dep), ciudad(ciu), categoriaInvestigador(categoria),
        perfil(per), productos(NULL), activo(true) {}

  ~Investigador() {

    NodoProducto *actual = productos;

    while (actual) {

      NodoProducto *siguiente = actual->sig;

      delete actual;

      actual = siguiente;
    }

    productos = NULL;
  }

  int contarProductos() const {
    int total = 0;
    NodoProducto *actual = productos;
    while (actual) {
      total++;
      actual = actual->sig;
    }
    return total;
  }

  void agregarProducto(ProductoInvestigacion *producto) {

    if (producto) {

      NodoProducto *nuevo = new NodoProducto(producto);

      if (!productos) {

        productos = nuevo;

      } else {

        NodoProducto *actual = productos;

        while (actual->sig) {

          actual = actual->sig;
        }

        actual->sig = nuevo;
      }
    }
  }
};

// =========================================================================
// NODO INVESTIGADOR//
// =========================================================================
// NODO INVESTIGADOR
// =========================================================================

struct NodoInvestigador {

  Investigador *investigador;

  NodoInvestigador *ant;
  NodoInvestigador *sig;

  NodoInvestigador(Investigador *inv)
      : investigador(inv), ant(NULL), sig(NULL) {}

  ~NodoInvestigador() {

    delete investigador;

    investigador = NULL;
  }
};

// =========================================================================
// GRUPO DE INVESTIGACION
// =========================================================================

struct GrupoInvestigacion {

  string nroGrupo;
  string nombreGrupo;

  // Datos basicos observables en GrupLAC.
  string anioFormacion;
  string departamento;
  string ciudad;
  string lider;
  string informacionCertificada;
  string paginaWeb;
  string email;
  string clasificacion;
  string areaConocimiento;
  string programaNacionalCti;
  string programaNacionalCtiSecundario;

  // Informacion descriptiva.
  string planEstrategico;
  string estadoArte;
  string objetivos;
  string retos;
  string vision;

  vector<string> instituciones;
  vector<string> lineasInvestigacion;

  bool activo;

  GrupoInvestigacion(string num = "", string nom = "", string anio = "",
                     string dep = "", string ciu = "", string lid = "",
                     string certificado = "", string web = "", string mail = "",
                     string clasif = "", string area = "", string programa = "",
                     string programaSec = "", string plan = "",
                     string estado = "", string obj = "", string ret = "",
                     string vis = "")
      : nroGrupo(num), nombreGrupo(nom), anioFormacion(anio), departamento(dep),
        ciudad(ciu), lider(lid), informacionCertificada(certificado),
        paginaWeb(web), email(mail), clasificacion(clasif),
        areaConocimiento(area), programaNacionalCti(programa),
        programaNacionalCtiSecundario(programaSec), planEstrategico(plan),
        estadoArte(estado), objetivos(obj), retos(ret), vision(vis),
        activo(true) {}
};

// =========================================================================
// NODO GRUPO//
// =========================================================================
// NODO GRUPO
// =========================================================================

struct NodoGrupo {

  GrupoInvestigacion *grupo;

  // Los investigadores almacenados dentro del grupo
  // son copias independientes.
  NodoInvestigador *hijoIntegrantes;

  // Los productos pertenecen al grupo.
  NodoProducto *hijoProductos;

  NodoGrupo *sig;

  NodoGrupo(GrupoInvestigacion *g)
      : grupo(g), hijoIntegrantes(NULL), hijoProductos(NULL), sig(NULL) {}

  ~NodoGrupo() {

    // Liberar grupo
    delete grupo;

    // Liberar integrantes
    NodoInvestigador *inv = hijoIntegrantes;

    while (inv) {

      NodoInvestigador *siguiente = inv->sig;

      delete inv;

      inv = siguiente;
    }

    // Liberar productos
    NodoProducto *prod = hijoProductos;

    while (prod) {

      NodoProducto *siguiente = prod->sig;

      delete prod;

      prod = siguiente;
    }

    grupo = NULL;
    hijoIntegrantes = NULL;
    hijoProductos = NULL;
  }
};

// =========================================================================
static string canonicalKey(const string &texto) {
  string resultado = "";
  bool espacioPrevio = false;
  size_t i = 0;

  while (i < texto.size()) {
    unsigned char c = static_cast<unsigned char>(texto[i]);
    char conv = ' ';
    bool multiocteto = false;

    // Reconocimiento de caracteres UTF-8 comunes en espanol (prefijo 0xC3)
    if (c == 0xC3 && i + 1 < texto.size()) {
      unsigned char c2 = static_cast<unsigned char>(texto[i + 1]);
      if (c2 == 0xA1 || c2 == 0x81) {
        conv = 'a';
        multiocteto = true;
      } else if (c2 == 0xA9 || c2 == 0x89) {
        conv = 'e';
        multiocteto = true;
      } else if (c2 == 0xAD || c2 == 0x8D) {
        conv = 'i';
        multiocteto = true;
      } else if (c2 == 0xB3 || c2 == 0x93) {
        conv = 'o';
        multiocteto = true;
      } else if (c2 == 0xBA || c2 == 0x9A || c2 == 0xBC || c2 == 0x9C) {
        conv = 'u';
        multiocteto = true;
      } else if (c2 == 0xB1 || c2 == 0x91) {
        conv = 'n';
        multiocteto = true;
      }
      if (multiocteto) {
        i++;
      }
    }

    if (!multiocteto) {
      if (c >= 'A' && c <= 'Z') {
        conv = static_cast<char>(c + ('a' - 'A'));
      } else if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) {
        conv = static_cast<char>(c);
      } else {
        conv = ' ';
      }
    }

    if (conv != ' ') {
      resultado += conv;
      espacioPrevio = false;
    } else {
      if (!espacioPrevio && !resultado.empty()) {
        resultado += ' ';
        espacioPrevio = true;
      }
    }

    i++;
  }

  if (!resultado.empty() && resultado[resultado.size() - 1] == ' ') {
    resultado = resultado.substr(0, resultado.size() - 1);
  }

  return resultado;
}

// LISTA DE INVESTIGADORES
// =========================================================================

class ListaInvestigadores {

private:
  NodoInvestigador *cabeza;
  NodoInvestigador *cola;

public:
  ListaInvestigadores() : cabeza(NULL), cola(NULL) {}

  ~ListaInvestigadores() { limpiar(); }

  // ---------------------------------------------------------
  // AGREGAR
  // ---------------------------------------------------------

  void agregar(Investigador *inv) {

    if (inv) {

      NodoInvestigador *nuevo = new NodoInvestigador(inv);

      if (!cabeza) {

        cabeza = nuevo;
        cola = nuevo;
      } else {

        cola->sig = nuevo;

        nuevo->ant = cola;

        cola = nuevo;
      }
    }
  }

  // ---------------------------------------------------------
  // BUSCAR
  // ---------------------------------------------------------

  Investigador *buscarCoincidencia(const Investigador *otro) {
    if (!otro) {
      return NULL;
    }
    string codOtro = otro->codigoRh;
    string nomOtro = canonicalKey(otro->nombre);
    string orcidOtro = canonicalKey(otro->orcid);
    string correoOtro = canonicalKey(otro->correo);

    NodoInvestigador *actual = cabeza;
    Investigador *encontrado = NULL;

    while (actual && !encontrado) {
      Investigador *cur = actual->investigador;
      if (cur) {
        bool coincide = false;
        if (!codOtro.empty() && !cur->codigoRh.empty() &&
            codOtro == cur->codigoRh) {
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
          string correoCur = canonicalKey(cur->correo);
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

  Investigador *buscar(string codigo) {

    NodoInvestigador *actual = cabeza;

    while (actual) {

      if (actual->investigador->codigoRh == codigo) {

        return actual->investigador;
      }

      actual = actual->sig;
    }

    return NULL;
  }

  // ---------------------------------------------------------
  // ACTIVAR / DESACTIVAR
  // ---------------------------------------------------------

  void activar(string codigo) {
    Investigador *inv = buscar(codigo);
    if (inv) {
      inv->activo = true;
    }
  }

  void desactivar(string codigo) {

    Investigador *inv = buscar(codigo);

    if (inv) {

      inv->activo = false;
    }
  }

  bool alternarEstado(string codigo) {
    Investigador *inv = buscar(codigo);
    if (inv) {
      if (inv->activo) {
        inv->activo = false;
      } else {
        inv->activo = true;
      }
      return true;
    }
    return false;
  }

  // ---------------------------------------------------------
  // ELIMINAR INVESTIGADOR (DELETE)
  // ---------------------------------------------------------

  bool eliminar(string codigo) {
    NodoInvestigador *actual = cabeza;
    bool eliminado = false;

    while (actual != NULL && !eliminado) {
      if (actual->investigador != NULL &&
          actual->investigador->codigoRh == codigo) {
        if (actual->ant != NULL) {
          actual->ant->sig = actual->sig;
        } else {
          cabeza = actual->sig;
        }

        if (actual->sig != NULL) {
          actual->sig->ant = actual->ant;
        } else {
          cola = actual->ant;
        }

        actual->sig = NULL;
        actual->ant = NULL;
        delete actual;
        eliminado = true;
      } else {
        actual = actual->sig;
      }
    }

    return eliminado;
  }

  // ---------------------------------------------------------
  // OBTENER CABEZA
  // ---------------------------------------------------------

  NodoInvestigador *getCabeza() { return cabeza; }

  // ---------------------------------------------------------
  // LIMPIAR
  // ---------------------------------------------------------

  void limpiar() {

    NodoInvestigador *actual = cabeza;

    while (actual) {

      NodoInvestigador *siguiente = actual->sig;

      delete actual;

      actual = siguiente;
    }

    cabeza = NULL;
    cola = NULL;
  }
};

// =========================================================================
// MULTILISTA DE GRUPOS
// =========================================================================

class MultilistaGrupos {

private:
  NodoGrupo *cabeza;

public:
  MultilistaGrupos() : cabeza(NULL) {}

  ~MultilistaGrupos() { limpiar(); }

  // ---------------------------------------------------------
  // AGREGAR GRUPO
  // ---------------------------------------------------------

  void agregarGrupo(GrupoInvestigacion *g) {

    if (g) {

      NodoGrupo *nuevo = new NodoGrupo(g);

      if (!cabeza) {

        cabeza = nuevo;

      } else {

        NodoGrupo *actual = cabeza;

        while (actual->sig) {

          actual = actual->sig;
        }

        actual->sig = nuevo;
      }
    }
  }

  // ---------------------------------------------------------
  // BUSCAR GRUPO
  // ---------------------------------------------------------

  NodoGrupo *buscarGrupoCoincidencia(const GrupoInvestigacion *otro) {
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
        if (!numOtro.empty() && !cur->nroGrupo.empty() &&
            numOtro == cur->nroGrupo) {
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

  NodoGrupo *buscarGrupo(string idGrupo) {

    NodoGrupo *actual = cabeza;

    while (actual) {

      if (actual->grupo->nroGrupo == idGrupo) {

        return actual;
      }

      actual = actual->sig;
    }

    return NULL;
  }

  // ---------------------------------------------------------
  // ACTIVAR / DESACTIVAR GRUPO
  // ---------------------------------------------------------

  void activarGrupo(string idGrupo) {
    NodoGrupo *g = buscarGrupo(idGrupo);
    if (g && g->grupo) {
      g->grupo->activo = true;
    }
  }

  void desactivarGrupo(string idGrupo) {
    NodoGrupo *g = buscarGrupo(idGrupo);
    if (g && g->grupo) {
      g->grupo->activo = false;
    }
  }

  bool alternarEstadoGrupo(string idGrupo) {
    NodoGrupo *g = buscarGrupo(idGrupo);
    if (g && g->grupo) {
      if (g->grupo->activo) {
        g->grupo->activo = false;
      } else {
        g->grupo->activo = true;
      }
      return true;
    }
    return false;
  }

  // ---------------------------------------------------------
  // AGREGAR INTEGRANTE
  // ---------------------------------------------------------

  void agregarIntegrante(string idGrupo, Investigador *inv) {

    if (inv) {

      NodoGrupo *grupo = buscarGrupo(idGrupo);

      if (grupo) {

        NodoInvestigador *nuevo = new NodoInvestigador(inv);

        nuevo->sig = grupo->hijoIntegrantes;

        if (grupo->hijoIntegrantes) {

          grupo->hijoIntegrantes->ant = nuevo;
        }

        grupo->hijoIntegrantes = nuevo;
      }
    }
  }

  // ---------------------------------------------------------
  // AGREGAR PRODUCTO
  // ---------------------------------------------------------

  void agregarProducto(string idGrupo, ProductoInvestigacion *producto) {

    if (producto) {

      NodoGrupo *grupo = buscarGrupo(idGrupo);

      if (grupo) {

        NodoProducto *nuevo = new NodoProducto(producto);

        if (!grupo->hijoProductos) {

          grupo->hijoProductos = nuevo;

        } else {

          NodoProducto *actual = grupo->hijoProductos;

          while (actual->sig) {

            actual = actual->sig;
          }

          actual->sig = nuevo;
        }
      }
    }
  }

  // ---------------------------------------------------------
  // ELIMINAR GRUPO (DELETE)
  // ---------------------------------------------------------

  bool eliminarGrupo(string idGrupo) {
    NodoGrupo *anterior = NULL;
    NodoGrupo *actual = cabeza;
    bool eliminado = false;

    while (actual != NULL && !eliminado) {
      if (actual->grupo != NULL && actual->grupo->nroGrupo == idGrupo) {
        if (anterior == NULL) {
          cabeza = actual->sig;
        } else {
          anterior->sig = actual->sig;
        }
        actual->sig = NULL;
        delete actual;
        eliminado = true;
      } else {
        anterior = actual;
        actual = actual->sig;
      }
    }

    return eliminado;
  }

  // ---------------------------------------------------------
  // OBTENER CABEZA
  // ---------------------------------------------------------

  NodoGrupo *getCabeza() { return cabeza; }

  // ---------------------------------------------------------
  // LIMPIAR
  // ---------------------------------------------------------

  void limpiar() {

    NodoGrupo *actual = cabeza;

    while (actual) {

      NodoGrupo *siguiente = actual->sig;

      delete actual;

      actual = siguiente;
    }

    cabeza = NULL;
  }
};

// =========================================================================
// PILA DE OPERACIONES
// =========================================================================

class PilaOperaciones {

private:
  vector<string> operaciones;

public:
  void push(string op) { operaciones.push_back(op); }

  string pop() {

    if (operaciones.empty())
      return "";

    string op = operaciones.back();

    operaciones.pop_back();

    return op;
  }

  bool empty() { return operaciones.empty(); }
};

// =========================================================================
// COLA DE PROCESAMIENTO
// =========================================================================

class ColaProcesamiento {

private:
  vector<ProductoInvestigacion *> cola;

public:
  void enqueue(ProductoInvestigacion *p) {

    if (p)
      cola.push_back(p);
  }

  ProductoInvestigacion *dequeue() {

    if (cola.empty())
      return NULL;

    ProductoInvestigacion *p = cola.front();

    cola.erase(cola.begin());

    return p;
  }

  bool empty() { return cola.empty(); }
};

// =========================================================================
// HIPERCUBO
// =========================================================================

class HipercuboInformacion {

private:
  double ***matriz;

  int N;
  int M;
  int K;

public:
  HipercuboInformacion(int grupos, int categorias, int anios)
      : matriz(NULL), N(grupos), M(categorias), K(anios) {

    matriz = new double **[N];

    for (int i = 0; i < N; ++i) {

      matriz[i] = new double *[M];

      for (int j = 0; j < M; ++j) {

        matriz[i][j] = new double[K];

        for (int k = 0; k < K; ++k) {

          matriz[i][j][k] = 0.0;
        }
      }
    }
  }

  ~HipercuboInformacion() {

    if (matriz) {

      for (int i = 0; i < N; ++i) {

        for (int j = 0; j < M; ++j) {

          delete[] matriz[i][j];
        }

        delete[] matriz[i];
      }

      delete[] matriz;

      matriz = NULL;
    }
  }

  void registrarDato(int g, int c, int a, double valor) {

    if (g >= 0 && g < N && c >= 0 && c < M && a >= 0 && a < K) {

      matriz[g][c][a] += valor;
    }
  }

  void generarResumenEstadistico() {

    cout << "Resumen Estadistico Generado..." << endl;
  }
};

// =========================================================================
// NORMALIZACION CANONICA DE CADENAS (EQUIVALENTE A PYTHON canonical_key)
// =========================================================================

// =========================================================================
// GENERACION DE FIRMA UNICA DE PRODUCTO (TITULO CANONICO + ANIO)
// =========================================================================

static string generarFirmaProducto(const string &titulo, int anio) {
  ostringstream flujo;
  flujo << canonicalKey(titulo) << "#" << anio;
  return flujo.str();
}

static void fusionarInvestigador(Investigador *destino, Investigador *fuente) {
  if (destino != NULL && fuente != NULL) {
    if (destino->codigoRh.empty() && !fuente->codigoRh.empty()) {
      destino->codigoRh = fuente->codigoRh;
    }
    if (destino->correo.empty() && !fuente->correo.empty()) {
      destino->correo = fuente->correo;
    }
    if (destino->orcid.empty() && !fuente->orcid.empty()) {
      destino->orcid = fuente->orcid;
    }
    if (destino->institucion.empty() && !fuente->institucion.empty()) {
      destino->institucion = fuente->institucion;
    }
    if (destino->departamento.empty() && !fuente->departamento.empty()) {
      destino->departamento = fuente->departamento;
    }
    if (destino->ciudad.empty() && !fuente->ciudad.empty()) {
      destino->ciudad = fuente->ciudad;
    }
    if ((destino->categoriaInvestigador.empty() || destino->categoriaInvestigador == "Sin categoria") &&
        !fuente->categoriaInvestigador.empty() && fuente->categoriaInvestigador != "Sin categoria") {
      destino->categoriaInvestigador = fuente->categoriaInvestigador;
    }
    if (destino->perfil.empty() && !fuente->perfil.empty()) {
      destino->perfil = fuente->perfil;
    }
    if (destino->nombreCitaciones.empty() && !fuente->nombreCitaciones.empty()) {
      destino->nombreCitaciones = fuente->nombreCitaciones;
    }
    if (destino->nacionalidad.empty() && !fuente->nacionalidad.empty()) {
      destino->nacionalidad = fuente->nacionalidad;
    }
    if (destino->sexo.empty() && !fuente->sexo.empty()) {
      destino->sexo = fuente->sexo;
    }
    if (destino->estadoParEvaluador.empty() && !fuente->estadoParEvaluador.empty()) {
      destino->estadoParEvaluador = fuente->estadoParEvaluador;
    }
    if (destino->researcherId.empty() && !fuente->researcherId.empty()) {
      destino->researcherId = fuente->researcherId;
    }
    if (destino->autorIdScopus.empty() && !fuente->autorIdScopus.empty()) {
      destino->autorIdScopus = fuente->autorIdScopus;
    }
    if (destino->googleScholar.empty() && !fuente->googleScholar.empty()) {
      destino->googleScholar = fuente->googleScholar;
    }
    if (destino->researchGate.empty() && !fuente->researchGate.empty()) {
      destino->researchGate = fuente->researchGate;
    }
    if (destino->academiaEdu.empty() && !fuente->academiaEdu.empty()) {
      destino->academiaEdu = fuente->academiaEdu;
    }
    if (destino->mendeley.empty() && !fuente->mendeley.empty()) {
      destino->mendeley = fuente->mendeley;
    }
    if (destino->linkedin.empty() && !fuente->linkedin.empty()) {
      destino->linkedin = fuente->linkedin;
    }
    if (destino->repositorioInstitucional.empty() && !fuente->repositorioInstitucional.empty()) {
      destino->repositorioInstitucional = fuente->repositorioInstitucional;
    }

    NodoProducto *actF = fuente->productos;
    while (actF != NULL) {
      ProductoInvestigacion *pF = actF->producto;
      if (pF != NULL) {
        string firmaF = generarFirmaProducto(pF->titulo, pF->anio);
        bool yaExiste = false;
        NodoProducto *actD = destino->productos;
        while (actD != NULL && !yaExiste) {
          if (actD->producto != NULL) {
            string firmaD = generarFirmaProducto(actD->producto->titulo, actD->producto->anio);
            if (firmaD == firmaF) {
              yaExiste = true;
            }
          }
          actD = actD->sig;
        }

        if (!yaExiste) {
          ProductoInvestigacion *copiaP = new ProductoInvestigacion(*pF);
          destino->agregarProducto(copiaP);
        }
      }
      actF = actF->sig;
    }
  }
}

// =========================================================================
// REGISTRO Y GESTOR DE PRODUCTOS UNICOS (CONTROL DE DUPLICADOS)
// =========================================================================

struct RegistroProductoUnico {
  ProductoInvestigacion *producto;
  string firma;
  vector<string> gruposVinculados;
  vector<string> investigadoresVinculados;
  int aparicionesTotales;

  RegistroProductoUnico(ProductoInvestigacion *p = NULL, string f = "")
      : producto(p), firma(f), aparicionesTotales(1) {}
};

class GestorProductosUnicos {
private:
  vector<RegistroProductoUnico> catalogo;
  int totalBruto;

  void registrarEnCatalogo(ProductoInvestigacion *prod,
                           const string &nombreGrupo, const string &nombreInv) {
    if (prod != NULL) {
      totalBruto++;
      string firma = generarFirmaProducto(prod->titulo, prod->anio);

      bool encontrado = false;
      size_t indiceEncontrado = 0;
      size_t i = 0;

      while (i < catalogo.size() && !encontrado) {
        if (catalogo[i].firma == firma) {
          encontrado = true;
          indiceEncontrado = i;
        }
        i++;
      }

      if (encontrado) {
        catalogo[indiceEncontrado].aparicionesTotales++;

        if (!nombreGrupo.empty()) {
          bool grupoYaRegistrado = false;
          size_t g = 0;
          while (g < catalogo[indiceEncontrado].gruposVinculados.size() &&
                 !grupoYaRegistrado) {
            if (catalogo[indiceEncontrado].gruposVinculados[g] == nombreGrupo) {
              grupoYaRegistrado = true;
            }
            g++;
          }
          if (!grupoYaRegistrado) {
            catalogo[indiceEncontrado].gruposVinculados.push_back(nombreGrupo);
          }
        }

        if (!nombreInv.empty()) {
          bool invYaRegistrado = false;
          size_t invIdx = 0;
          while (
              invIdx <
                  catalogo[indiceEncontrado].investigadoresVinculados.size() &&
              !invYaRegistrado) {
            if (catalogo[indiceEncontrado].investigadoresVinculados[invIdx] ==
                nombreInv) {
              invYaRegistrado = true;
            }
            invIdx++;
          }
          if (!invYaRegistrado) {
            catalogo[indiceEncontrado].investigadoresVinculados.push_back(
                nombreInv);
          }
        }

        if (catalogo[indiceEncontrado].producto->doi.empty() &&
            !prod->doi.empty()) {
          catalogo[indiceEncontrado].producto->doi = prod->doi;
        }
        if (!catalogo[indiceEncontrado].producto->validado && prod->validado) {
          catalogo[indiceEncontrado].producto->validado = true;
        }
        if (catalogo[indiceEncontrado].producto->revista.empty() &&
            !prod->revista.empty()) {
          catalogo[indiceEncontrado].producto->revista = prod->revista;
        }
        if (catalogo[indiceEncontrado].producto->isbn.empty() &&
            !prod->isbn.empty()) {
          catalogo[indiceEncontrado].producto->isbn = prod->isbn;
        }
      } else {
        RegistroProductoUnico nuevoReg(prod, firma);
        if (!nombreGrupo.empty()) {
          nuevoReg.gruposVinculados.push_back(nombreGrupo);
        }
        if (!nombreInv.empty()) {
          nuevoReg.investigadoresVinculados.push_back(nombreInv);
        }
        catalogo.push_back(nuevoReg);
      }
    }
  }

public:
  GestorProductosUnicos() : totalBruto(0) {}

  void limpiar() {
    catalogo.clear();
    totalBruto = 0;
  }

  void consolidar(ListaInvestigadores &listasInv,
                  MultilistaGrupos &multilistas) {
    limpiar();

    NodoInvestigador *actInv = listasInv.getCabeza();
    while (actInv != NULL) {
      if (actInv->investigador != NULL) {
        string nomInv = actInv->investigador->nombre;
        NodoProducto *actProd = actInv->investigador->productos;
        while (actProd != NULL) {
          registrarEnCatalogo(actProd->producto, "", nomInv);
          actProd = actProd->sig;
        }
      }
      actInv = actInv->sig;
    }

    NodoGrupo *actGrupo = multilistas.getCabeza();
    while (actGrupo != NULL) {
      if (actGrupo->grupo != NULL) {
        string nomGrupo = actGrupo->grupo->nombreGrupo;

        NodoProducto *actProdG = actGrupo->hijoProductos;
        while (actProdG != NULL) {
          registrarEnCatalogo(actProdG->producto, nomGrupo, "");
          actProdG = actProdG->sig;
        }

        NodoInvestigador *actInt = actGrupo->hijoIntegrantes;
        while (actInt != NULL) {
          if (actInt->investigador != NULL) {
            string nomInt = actInt->investigador->nombre;
            NodoProducto *actProdInt = actInt->investigador->productos;
            while (actProdInt != NULL) {
              registrarEnCatalogo(actProdInt->producto, nomGrupo, nomInt);
              actProdInt = actProdInt->sig;
            }
          }
          actInt = actInt->sig;
        }
      }
      actGrupo = actGrupo->sig;
    }
  }

  int obtenerTotalBruto() const { return totalBruto; }

  int obtenerTotalUnicos() const { return static_cast<int>(catalogo.size()); }

  int obtenerTotalDuplicados() const {
    int unicos = static_cast<int>(catalogo.size());
    if (totalBruto > unicos) {
      return totalBruto - unicos;
    }
    return 0;
  }

  const vector<RegistroProductoUnico> &getCatalogo() const { return catalogo; }

  vector<string> obtenerCategoriasDisponibles() const {
    vector<string> categorias;
    size_t i = 0;
    while (i < catalogo.size()) {
      if (catalogo[i].producto != NULL) {
        string cat = catalogo[i].producto->categoria;
        if (cat.empty()) {
          cat = catalogo[i].producto->tipoProducto;
        }
        if (cat.empty()) {
          cat = "Sin Categoria";
        }

        bool existeCat = false;
        size_t cIdx = 0;
        while (cIdx < categorias.size() && !existeCat) {
          if (categorias[cIdx] == cat) {
            existeCat = true;
          }
          cIdx++;
        }
        if (!existeCat) {
          categorias.push_back(cat);
        }
      }
      i++;
    }
    return categorias;
  }

  int contarPorCategoria(const string &catBuscada) const {
    int contador = 0;
    size_t i = 0;
    while (i < catalogo.size()) {
      if (catalogo[i].producto != NULL) {
        string cat = catalogo[i].producto->categoria;
        if (cat.empty()) {
          cat = catalogo[i].producto->tipoProducto;
        }
        if (cat.empty()) {
          cat = "Sin Categoria";
        }
        if (cat == catBuscada) {
          contador++;
        }
      }
      i++;
    }
    return contador;
  }

  vector<int> obtenerAniosDisponibles() const {
    vector<int> anios;
    size_t i = 0;
    while (i < catalogo.size()) {
      if (catalogo[i].producto != NULL) {
        int anio = catalogo[i].producto->anio;
        if (anio > 1000) {
          bool existeAnio = false;
          size_t aIdx = 0;
          while (aIdx < anios.size() && !existeAnio) {
            if (anios[aIdx] == anio) {
              existeAnio = true;
            }
            aIdx++;
          }
          if (!existeAnio) {
            anios.push_back(anio);
          }
        }
      }
      i++;
    }
    return anios;
  }

  int contarPorAnio(int anioBuscado) const {
    int contador = 0;
    size_t i = 0;
    while (i < catalogo.size()) {
      if (catalogo[i].producto != NULL) {
        if (catalogo[i].producto->anio == anioBuscado) {
          contador++;
        }
      }
      i++;
    }
    return contador;
  }
};

// =========================================================================
// LECTOR DE ARCHIVOS Y WEB
// =========================================================================

class LectorArchivosYWeb {

private:
  string ultimoError;

#ifdef _WIN32
  HANDLE procesoScraper;

  static HANDLE s_procesoScraper;
  static DWORD s_pidScraper;
  static HANDLE s_jobScraper;
  static bool s_manejadorRegistrado;
  static string s_ultimoTipoCierre;

  static void inicializarJobScraper() {
    if (s_jobScraper == NULL) {
      s_jobScraper = CreateJobObjectA(NULL, NULL);
      if (s_jobScraper != NULL) {
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION jeli;
        ZeroMemory(&jeli, sizeof(jeli));
        jeli.BasicLimitInformation.LimitFlags =
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        SetInformationJobObject(s_jobScraper, JobObjectExtendedLimitInformation,
                                &jeli, sizeof(jeli));
      }
    }
  }

  static void registrarEventoCierre(const string &tipo,
                                    const string &descripcion) {
    ofstream bitacora("scraper_cierre.log", ios::out | ios::app);
    if (bitacora.is_open()) {
      SYSTEMTIME st;
      GetLocalTime(&st);
      char fechaHora[64];
      wsprintfA(fechaHora, "%04d-%02d-%02d %02d:%02d:%02d", st.wYear, st.wMonth,
                st.wDay, st.wHour, st.wMinute, st.wSecond);
      bitacora << "[" << fechaHora << "] [" << tipo << "] " << descripcion;
      if (s_pidScraper != 0) {
        bitacora << " (PID: " << s_pidScraper << ")";
      }
      bitacora << endl;
      bitacora.close();
    }
  }

  static void matarProcesoScraper() {
    if (s_pidScraper != 0) {
      char comando[128];
      wsprintfA(comando, "taskkill /F /T /PID %lu >nul 2>&1", s_pidScraper);
      system(comando);
    }

    if (s_jobScraper != NULL) {
      TerminateJobObject(s_jobScraper, 0);
      CloseHandle(s_jobScraper);
      s_jobScraper = NULL;
    }

    if (s_procesoScraper != NULL) {
      TerminateProcess(s_procesoScraper, 0);
      WaitForSingleObject(s_procesoScraper, 1000);
      CloseHandle(s_procesoScraper);
      s_procesoScraper = NULL;
    }

    s_pidScraper = 0;
  }

  static BOOL WINAPI ManejadorConsola(DWORD tipoControl) {
    if (tipoControl == CTRL_C_EVENT || tipoControl == CTRL_BREAK_EVENT ||
        tipoControl == CTRL_CLOSE_EVENT || tipoControl == CTRL_LOGOFF_EVENT ||
        tipoControl == CTRL_SHUTDOWN_EVENT) {
      cerrarScraperForzado(tipoControl);
      return TRUE;
    } else {
      return FALSE;
    }
  }
#endif

  // =========================================================
  // SEPARAR CAMPOS
  // =========================================================

  vector<string> separarCampos(const string &linea) {

    vector<string> campos;
    string campo;

    for (size_t i = 0; i < linea.size(); ++i) {

      if (linea[i] == '\t') {

        campos.push_back(campo);

        campo = "";
      } else {

        campo += linea[i];
      }
    }

    campos.push_back(campo);

    return campos;
  }

  // =========================================================
  // CONVERTIR TEXTO A BOOLEANO
  // =========================================================

  bool convertirBooleano(const string &valor) {

    return valor == "1" || valor == "true" || valor == "TRUE" ||
           valor == "si" || valor == "SI";
  }

  // =========================================================
  // CONVERTIR TEXTO A ENTERO
  // =========================================================

  int convertirEntero(const string &valor) {

    if (valor.empty())
      return 0;

    return atoi(valor.c_str());
  }

  // =========================================================
  // OBTENER CAMPO OPCIONAL
  // =========================================================

  string campoOpcional(const vector<string> &campos, size_t indice) {

    if (indice < campos.size())
      return campos[indice];

    return "";
  }

  // =========================================================
  // CREAR PRODUCTO DESDE CAMPOS
  // =========================================================

  ProductoInvestigacion *productoDesdeCampos(const vector<string> &campos) {

    if (campos.size() < 6)
      return NULL;

    return new ProductoInvestigacion(
        campos[1], campos[2], campos[3], convertirBooleano(campos[4]),
        convertirEntero(campos[5]), campoOpcional(campos, 6),
        campoOpcional(campos, 7), campoOpcional(campos, 8),
        campoOpcional(campos, 9), campoOpcional(campos, 10),
        campoOpcional(campos, 11), campoOpcional(campos, 12),
        campoOpcional(campos, 13), campoOpcional(campos, 14),
        campoOpcional(campos, 15), campoOpcional(campos, 16),
        campoOpcional(campos, 17), campoOpcional(campos, 18),
        campoOpcional(campos, 19));
  }

#ifdef _WIN32

  // =========================================================
  // CONVERTIR NUMERO A TEXTO
  // =========================================================

  string numeroATexto(unsigned long numero) {

    ostringstream flujo;

    flujo << numero;

    return flujo.str();
  }

  // =========================================================
  // ESCAPAR TEXTO PARA JSON
  // =========================================================

  string escaparJson(const string &valor) {

    string salida;

    for (size_t i = 0; i < valor.size(); ++i) {

      unsigned char c = static_cast<unsigned char>(valor[i]);

      if (c == '"') {

        salida += "\\\"";
      } else if (c == '\\') {

        salida += "\\\\";
      } else if (c == '\n') {

        salida += "\\n";
      } else if (c == '\r') {

        salida += "\\r";
      } else if (c == '\t') {

        salida += "\\t";
      } else if (c < 32) {

        salida += ' ';
      } else {

        salida += static_cast<char>(c);
      }
    }

    return salida;
  }

  // =========================================================
  // CONVERTIR STRING A WSTRING
  // =========================================================

  wstring stringToWide(const string &texto) {

    int tamano = MultiByteToWideChar(CP_UTF8, 0, texto.c_str(), -1, NULL, 0);

    if (tamano == 0)
      return L"";

    vector<wchar_t> buffer(tamano);

    MultiByteToWideChar(CP_UTF8, 0, texto.c_str(), -1, &buffer[0], tamano);

    return wstring(&buffer[0]);
  }

  // =========================================================
  // OBTENER DIRECTORIO DEL EJECUTABLE
  // =========================================================

  string obtenerDirectorioEjecutable() {

    char ruta[MAX_PATH];

    DWORD longitud = GetModuleFileNameA(NULL, ruta, MAX_PATH);

    if (longitud == 0)
      return "";

    string completa(ruta, longitud);

    size_t posicion = completa.find_last_of("\\/");

    if (posicion == string::npos)
      return "";

    return completa.substr(0, posicion);
  }

  // =========================================================
  // COMPROBAR ARCHIVO
  // =========================================================

  bool archivoExiste(const string &ruta) {

    ifstream archivo(ruta.c_str());

    bool existe = archivo.is_open();

    archivo.close();

    return existe;
  }

  // =========================================================
  // OBTENER RUTA DEL SCRAPER
  // =========================================================

  string obtenerRutaScraper() {

    string directorio = obtenerDirectorioEjecutable();

    if (!directorio.empty()) {
      string c1 = directorio + "\\PEA-i-Scraper.exe";
      if (archivoExiste(c1))
        return c1;

      string c2 = directorio + "\\PEA-i.exe";
      if (archivoExiste(c2))
        return c2;

      string c3 = directorio + "\\scraper\\PEA-i-Scraper.exe";
      if (archivoExiste(c3))
        return c3;

      string c4 = directorio + "\\scraper\\PEA-i.exe";
      if (archivoExiste(c4))
        return c4;

      string c5 = directorio + "\\PEA-Scraper\\dist\\PEA-i.exe";
      if (archivoExiste(c5))
        return c5;

      string c6 = directorio + "\\PEA-Scraper\\PEA-i-Scraper.exe";
      if (archivoExiste(c6))
        return c6;

      string c7 = directorio + "\\PEA-Scraper\\PEA-i.exe";
      if (archivoExiste(c7))
        return c7;

      string c8 = directorio + "\\Python\\PEA-i-Scraper.exe";
      if (archivoExiste(c8))
        return c8;

      string c9 = directorio + "\\Python\\PEA-i.exe";
      if (archivoExiste(c9))
        return c9;
    }

    if (archivoExiste("PEA-i-Scraper.exe"))
      return "PEA-i-Scraper.exe";
    if (archivoExiste("PEA-i.exe"))
      return "PEA-i.exe";
    if (archivoExiste("scraper\\PEA-i-Scraper.exe"))
      return "scraper\\PEA-i-Scraper.exe";
    if (archivoExiste("scraper\\PEA-i.exe"))
      return "scraper\\PEA-i.exe";
    if (archivoExiste("PEA-Scraper\\dist\\PEA-i.exe"))
      return "PEA-Scraper\\dist\\PEA-i.exe";
    if (archivoExiste("PEA-Scraper\\PEA-i-Scraper.exe"))
      return "PEA-Scraper\\PEA-i-Scraper.exe";
    if (archivoExiste("PEA-Scraper\\PEA-i.exe"))
      return "PEA-Scraper\\PEA-i.exe";

    return "";
  }

  // =========================================================
  // INICIAR SCRAPER PYTHON
  // =========================================================

  bool iniciarScraperPython() {

#ifdef _WIN32
    registrarManejadorConsola();

    if (s_procesoScraper != NULL) {
      DWORD estado = WaitForSingleObject(s_procesoScraper, 0);

      if (estado == WAIT_TIMEOUT) {
        if (consultarHealth()) {
          return true;
        }
      }

      matarProcesoScraper();
    }

    STARTUPINFOA inicio;
    PROCESS_INFORMATION proceso;

    ZeroMemory(&inicio, sizeof(inicio));
    ZeroMemory(&proceso, sizeof(proceso));
    inicio.cb = sizeof(inicio);

    BOOL creado = FALSE;
    string ruta = "";

    if (archivoExiste("PEA-Scraper\\DLDD-MAFF-JDLA.py")) {
      string comandoPy = "python \"PEA-Scraper\\DLDD-MAFF-JDLA.py\" --api";
      vector<char> bufferPy(comandoPy.begin(), comandoPy.end());
      bufferPy.push_back('\0');
      creado = CreateProcessA(NULL, &bufferPy[0], NULL, NULL, FALSE,
                              CREATE_NO_WINDOW, NULL, NULL, &inicio, &proceso);
    }

    if (!creado) {
      ruta = obtenerRutaScraper();

      if (ruta.empty()) {
        ultimoError =
            "No se encontro el ejecutable del scraper (PEA-i-Scraper.exe ni "
            "PEA-i.exe) ni el script PEA-Scraper\\DLDD-MAFF-JDLA.py.";
        return false;
      }

      string comando = "\"" + ruta + "\" --api";
      vector<char> bufferComando(comando.begin(), comando.end());
      bufferComando.push_back('\0');

      string directorio = ruta;
      size_t posicion = directorio.find_last_of("\\/");
      if (posicion != string::npos) {
        directorio = directorio.substr(0, posicion);
      } else {
        directorio = "";
      }

      LPCSTR directorioTrabajo = NULL;
      if (!directorio.empty()) {
        directorioTrabajo = directorio.c_str();
      }

      creado = CreateProcessA(ruta.c_str(), &bufferComando[0], NULL, NULL,
                              FALSE, CREATE_NO_WINDOW, NULL, directorioTrabajo,
                              &inicio, &proceso);
    }

    if (!creado) {
      ultimoError = "No se pudo iniciar el scraper. Error de Windows: " +
                    numeroATexto(static_cast<unsigned long>(GetLastError()));
      return false;
    }

    CloseHandle(proceso.hThread);

    procesoScraper = proceso.hProcess;
    s_procesoScraper = proceso.hProcess;
    s_pidScraper = proceso.dwProcessId;

    inicializarJobScraper();
    if (s_jobScraper != NULL) {
      AssignProcessToJobObject(s_jobScraper, proceso.hProcess);
    }

    return true;
#else
    ultimoError =
        "El inicio automatico del scraper esta preparado para Windows.";
    return false;
#endif
  }

  // =========================================================
  // LEER RESPUESTA HTTP
  // =========================================================

  bool leerRespuesta(HINTERNET solicitud, string &respuesta) {

    respuesta.clear();

    DWORD disponibles = 0;

    bool terminar = false;

    while (!terminar && WinHttpQueryDataAvailable(solicitud, &disponibles)) {

      if (disponibles == 0) {

        terminar = true;
      } else {

        vector<char> buffer(disponibles + 1);

        DWORD leidos = 0;

        BOOL leyo =
            WinHttpReadData(solicitud, &buffer[0], disponibles, &leidos);

        if (!leyo)
          return false;

        if (leidos == 0) {

          terminar = true;
        } else {

          respuesta.append(&buffer[0], leidos);
        }
      }
    }

    return true;
  }

  // =========================================================
  // CONSULTAR HEALTH
  // =========================================================

  bool consultarHealth() {

    HINTERNET sesion =
        WinHttpOpen(L"PEA-i-Cpp98/1.0", WINHTTP_ACCESS_TYPE_NO_PROXY,
                    WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);

    if (!sesion)
      return false;

    WinHttpSetTimeouts(sesion, 1000, 1000, 1000, 2000);

    HINTERNET conexion = WinHttpConnect(sesion, L"127.0.0.1", 8765, 0);

    if (!conexion) {

      WinHttpCloseHandle(sesion);

      return false;
    }

    HINTERNET solicitud =
        WinHttpOpenRequest(conexion, L"GET", L"/health", NULL,
                           WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, 0);

    if (!solicitud) {

      WinHttpCloseHandle(conexion);

      WinHttpCloseHandle(sesion);

      return false;
    }

    BOOL enviado = WinHttpSendRequest(solicitud, WINHTTP_NO_ADDITIONAL_HEADERS,
                                      0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0);

    bool correcto = false;

    if (enviado) {

      BOOL recibido = WinHttpReceiveResponse(solicitud, NULL);

      if (recibido) {

        DWORD estado = 0;

        DWORD tamano = sizeof(estado);

        BOOL consultado = WinHttpQueryHeaders(
            solicitud, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
            WINHTTP_HEADER_NAME_BY_INDEX, &estado, &tamano,
            WINHTTP_NO_HEADER_INDEX);

        if (consultado && estado >= 200 && estado < 300) {

          correcto = true;
        }
      }
    }

    WinHttpCloseHandle(solicitud);

    WinHttpCloseHandle(conexion);

    WinHttpCloseHandle(sesion);

    return correcto;
  }

  // =========================================================
  // ESPERAR SERVIDOR PYTHON
  // =========================================================

  bool esperarServidor() {

    for (int intento = 0; intento < 50; ++intento) {

      if (procesoScraper != NULL &&
          WaitForSingleObject(procesoScraper, 0) == WAIT_OBJECT_0) {

        ultimoError = "PEA-i.exe termino antes de levantar la API.";

        return false;
      }

      if (consultarHealth())
        return true;

      Sleep(200);
    }

    ultimoError = "PEA-i.exe no respondio en localhost:8765.";

    return false;
  }

  // =========================================================
  // REALIZAR POST
  // =========================================================

  bool realizarPost(const string &ruta, const string &cuerpo,
                    string &respuesta) {

    respuesta.clear();

    HINTERNET sesion =
        WinHttpOpen(L"PEA-i-Cpp98/1.0", WINHTTP_ACCESS_TYPE_NO_PROXY,
                    WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);

    if (!sesion) {

      ultimoError = "WinHttpOpen fallo.";

      return false;
    }

    WinHttpSetTimeouts(sesion, 5000, 5000, 15000, 60000);

    HINTERNET conexion = WinHttpConnect(sesion, L"127.0.0.1", 8765, 0);

    if (!conexion) {

      ultimoError = "No se pudo conectar con localhost:8765.";

      WinHttpCloseHandle(sesion);

      return false;
    }

    wstring rutaWide = stringToWide(ruta);

    HINTERNET solicitud =
        WinHttpOpenRequest(conexion, L"POST", rutaWide.c_str(), NULL,
                           WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, 0);

    if (!solicitud) {

      ultimoError = "No se pudo crear la solicitud HTTP.";

      WinHttpCloseHandle(conexion);

      WinHttpCloseHandle(sesion);

      return false;
    }

    const wchar_t *encabezados =
        L"Content-Type: application/json; charset=utf-8\r\n"
        L"Accept: text/plain\r\n";

    BOOL enviado = WinHttpSendRequest(
        solicitud, encabezados, static_cast<DWORD>(-1), (LPVOID)cuerpo.c_str(),
        static_cast<DWORD>(cuerpo.size()), static_cast<DWORD>(cuerpo.size()),
        0);

    bool correcto = false;

    if (!enviado) {

      ultimoError = "WinHttpSendRequest fallo.";
    } else {

      BOOL recibido = WinHttpReceiveResponse(solicitud, NULL);

      if (!recibido) {

        ultimoError = "WinHttpReceiveResponse fallo.";
      } else {

        DWORD estado = 0;

        DWORD tamano = sizeof(estado);

        BOOL consultado = WinHttpQueryHeaders(
            solicitud, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
            WINHTTP_HEADER_NAME_BY_INDEX, &estado, &tamano,
            WINHTTP_NO_HEADER_INDEX);

        if (!consultado) {

          ultimoError = "No fue posible obtener el codigo HTTP.";
        } else if (estado < 200 || estado >= 300) {

          ultimoError = "La API Python devolvio HTTP " +
                        numeroATexto(static_cast<unsigned long>(estado));

          leerRespuesta(solicitud, respuesta);
        } else {

          if (leerRespuesta(solicitud, respuesta)) {

            correcto = true;
          } else {

            ultimoError = "No se pudo leer la respuesta del scraper.";
          }
        }
      }
    }

    WinHttpCloseHandle(solicitud);

    WinHttpCloseHandle(conexion);

    WinHttpCloseHandle(sesion);

    return correcto;
  }

#endif

  // =========================================================
  // GUARDAR RESPUESTA RECIBIDA
  // =========================================================

  void guardarRespuestaBruta(const string &respuesta) {

    ofstream archivo("scraping_ultima_respuesta.txt",
                     ios::out | ios::trunc | ios::binary);

    if (archivo.is_open()) {
      archivo << respuesta;

      archivo.close();
    }
  }

  // =========================================================
  // AGREGAR AUTOR A PRODUCTO
  // =========================================================

  void agregarAutor(ProductoInvestigacion *producto,
                    const vector<string> &campos) {

    if (producto != NULL && campos.size() >= 2) {

      producto->autores.push_back(campos[1]);
    }
  }

  // =========================================================
  // PARSEAR INVESTIGADOR
  // =========================================================

  Investigador *parsearInvestigador(const string &respuesta) {

    stringstream flujo(respuesta);

    string linea;

    Investigador *investigador = NULL;

    ProductoInvestigacion *productoActual = NULL;

    bool estadoOk = false;

    bool tipoCorrecto = false;

    while (getline(flujo, linea)) {

      if (!linea.empty()) {

        vector<string> campos = separarCampos(linea);

        if (!campos.empty()) {

          if (campos[0] == "ESTADO") {

            if (campos.size() >= 2 && campos[1] == "OK")
              estadoOk = true;
          } else if (campos[0] == "ERROR") {

            if (campos.size() >= 2)
              ultimoError = campos[1];
          } else if (campos[0] == "TIPO") {

            if (campos.size() >= 2 && campos[1] == "INVESTIGADOR")
              tipoCorrecto = true;
          } else if (campos[0] == "INVESTIGADOR") {

            if (campos.size() >= 3) {

              investigador = new Investigador(
                  campos[1], campos[2], campoOpcional(campos, 3),
                  campoOpcional(campos, 4), campoOpcional(campos, 5),
                  campoOpcional(campos, 6), campoOpcional(campos, 7),
                  campoOpcional(campos, 8), campoOpcional(campos, 9));

              if (campos.size() >= 11)
                investigador->activo = convertirBooleano(campos[10]);
            }
          } else if (campos[0] == "NOMBRE_CITACIONES") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->nombreCitaciones = campos[1];
          } else if (campos[0] == "NACIONALIDAD") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->nacionalidad = campos[1];
          } else if (campos[0] == "SEXO") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->sexo = campos[1];
          } else if (campos[0] == "ESTADO_PAR_EVALUADOR") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->estadoParEvaluador = campos[1];
          } else if (campos[0] == "RESEARCHER_ID") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->researcherId = campos[1];
          } else if (campos[0] == "AUTOR_ID_SCOPUS") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->autorIdScopus = campos[1];
          } else if (campos[0] == "GOOGLE_SCHOLAR") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->googleScholar = campos[1];
          } else if (campos[0] == "RESEARCHGATE") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->researchGate = campos[1];
          } else if (campos[0] == "ACADEMIA_EDU") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->academiaEdu = campos[1];
          } else if (campos[0] == "MENDELEY") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->mendeley = campos[1];
          } else if (campos[0] == "LINKEDIN") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->linkedin = campos[1];
          } else if (campos[0] == "REPOSITORIO_INSTITUCIONAL") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->repositorioInstitucional = campos[1];
          } else if (campos[0] == "IDIOMA") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->idiomas.push_back(campos[1]);
          } else if (campos[0] == "AREA_CONOCIMIENTO") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->areasConocimiento.push_back(campos[1]);
          } else if (campos[0] == "LINEA_INVESTIGACION") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->lineasInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "FORMACION") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->formacionAcademica.push_back(campos[1]);
          } else if (campos[0] == "EXPERIENCIA") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->experienciaProfesional.push_back(campos[1]);
          } else if (campos[0] == "GRUPO_INVESTIGACION") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->gruposInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "SEMILLERO") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->semilleros.push_back(campos[1]);
          } else if (campos[0] == "PROYECTO") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->proyectos.push_back(campos[1]);
          } else if (campos[0] == "RECONOCIMIENTO") {

            if (investigador != NULL && campos.size() >= 2)
              investigador->reconocimientos.push_back(campos[1]);
          } else if (campos[0] == "PRODUCTO") {

            productoActual = productoDesdeCampos(campos);

            if (investigador != NULL && productoActual != NULL)
              investigador->agregarProducto(productoActual);
          } else if (campos[0] == "AUTOR") {

            agregarAutor(productoActual, campos);
          } else if (campos[0] == "PRODUCTO_FIN") {

            productoActual = NULL;
          }
        }
      }
    }

    if (!estadoOk || !tipoCorrecto || investigador == NULL) {

      if (investigador != NULL)
        delete investigador;

      return NULL;
    }

    return investigador;
  }

  // =========================================================
  // PARSEAR GRUPO
  // =========================================================

  bool parsearGrupo(const string &respuesta, GrupoInvestigacion *&grupo,
                    vector<Investigador *> &integrantes,
                    vector<ProductoInvestigacion *> &productos) {

    grupo = NULL;

    integrantes.clear();
    productos.clear();

    stringstream flujo(respuesta);

    string linea;

    Investigador *integranteActual = NULL;

    ProductoInvestigacion *productoActual = NULL;

    bool estadoOk = false;

    bool tipoCorrecto = false;

    while (getline(flujo, linea)) {

      if (!linea.empty()) {

        vector<string> campos = separarCampos(linea);

        if (!campos.empty()) {

          if (campos[0] == "ESTADO") {

            if (campos.size() >= 2 && campos[1] == "OK")
              estadoOk = true;
          } else if (campos[0] == "ERROR") {

            if (campos.size() >= 2)
              ultimoError = campos[1];
          } else if (campos[0] == "TIPO") {

            if (campos.size() >= 2 && campos[1] == "GRUPO")
              tipoCorrecto = true;
          } else if (campos[0] == "GRUPO") {

            if (campos.size() >= 3) {

              grupo = new GrupoInvestigacion(campos[1], campos[2]);
            }
          } else if (campos[0] == "ANIO_FORMACION") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->anioFormacion = campos[1];
          } else if (campos[0] == "DEPARTAMENTO") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->departamento = campos[1];
          } else if (campos[0] == "CIUDAD") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->ciudad = campos[1];
          } else if (campos[0] == "LIDER") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->lider = campos[1];
          } else if (campos[0] == "INFORMACION_CERTIFICADA") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->informacionCertificada = campos[1];
          } else if (campos[0] == "PAGINA_WEB") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->paginaWeb = campos[1];
          } else if (campos[0] == "EMAIL") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->email = campos[1];
          } else if (campos[0] == "CLASIFICACION") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->clasificacion = campos[1];
          } else if (campos[0] == "AREA_CONOCIMIENTO") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->areaConocimiento = campos[1];
          } else if (campos[0] == "PROGRAMA_NACIONAL_CTI") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->programaNacionalCti = campos[1];
          } else if (campos[0] == "PROGRAMA_NACIONAL_CTI_SECUNDARIO") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->programaNacionalCtiSecundario = campos[1];
          } else if (campos[0] == "PLAN_ESTRATEGICO") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->planEstrategico = campos[1];
          } else if (campos[0] == "ESTADO_ARTE") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->estadoArte = campos[1];
          } else if (campos[0] == "OBJETIVOS") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->objetivos = campos[1];
          } else if (campos[0] == "RETOS") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->retos = campos[1];
          } else if (campos[0] == "VISION") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->vision = campos[1];
          } else if (campos[0] == "INSTITUCION") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->instituciones.push_back(campos[1]);
          } else if (campos[0] == "LINEA_INVESTIGACION") {

            if (grupo != NULL && campos.size() >= 2)
              grupo->lineasInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE") {

            if (campos.size() >= 3) {

              integranteActual = new Investigador(
                  campos[1], campos[2], campoOpcional(campos, 3),
                  campoOpcional(campos, 4), campoOpcional(campos, 5),
                  campoOpcional(campos, 6), campoOpcional(campos, 7),
                  campoOpcional(campos, 8), campoOpcional(campos, 9));

              if (campos.size() >= 11)
                integranteActual->activo = convertirBooleano(campos[10]);

              integrantes.push_back(integranteActual);
            }
          } else if (campos[0] == "INTEGRANTE_NOMBRE_CITACIONES") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->nombreCitaciones = campos[1];
          } else if (campos[0] == "INTEGRANTE_NACIONALIDAD") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->nacionalidad = campos[1];
          } else if (campos[0] == "INTEGRANTE_SEXO") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->sexo = campos[1];
          } else if (campos[0] == "INTEGRANTE_ESTADO_PAR_EVALUADOR") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->estadoParEvaluador = campos[1];
          } else if (campos[0] == "INTEGRANTE_RESEARCHER_ID") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->researcherId = campos[1];
          } else if (campos[0] == "INTEGRANTE_AUTOR_ID_SCOPUS") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->autorIdScopus = campos[1];
          } else if (campos[0] == "INTEGRANTE_GOOGLE_SCHOLAR") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->googleScholar = campos[1];
          } else if (campos[0] == "INTEGRANTE_RESEARCHGATE") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->researchGate = campos[1];
          } else if (campos[0] == "INTEGRANTE_ACADEMIA_EDU") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->academiaEdu = campos[1];
          } else if (campos[0] == "INTEGRANTE_MENDELEY") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->mendeley = campos[1];
          } else if (campos[0] == "INTEGRANTE_LINKEDIN") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->linkedin = campos[1];
          } else if (campos[0] == "INTEGRANTE_REPOSITORIO_INSTITUCIONAL") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->repositorioInstitucional = campos[1];
          } else if (campos[0] == "INTEGRANTE_IDIOMA") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->idiomas.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_AREA") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->areasConocimiento.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_LINEA") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->lineasInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_FORMACION") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->formacionAcademica.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_EXPERIENCIA") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->experienciaProfesional.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_GRUPO") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->gruposInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_SEMILLERO") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->semilleros.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_PROYECTO") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->proyectos.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_RECONOCIMIENTO") {

            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->reconocimientos.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_PRODUCTO") {

            productoActual = productoDesdeCampos(campos);

            if (integranteActual != NULL && productoActual != NULL)
              integranteActual->agregarProducto(productoActual);
          } else if (campos[0] == "INTEGRANTE_FIN") {

            integranteActual = NULL;

            productoActual = NULL;
          } else if (campos[0] == "FIN_INTEGRANTE") {

            integranteActual = NULL;

            productoActual = NULL;
          } else if (campos[0] == "PRODUCTO") {

            productoActual = productoDesdeCampos(campos);

            if (productoActual != NULL)
              productos.push_back(productoActual);
          } else if (campos[0] == "AUTOR") {

            agregarAutor(productoActual, campos);
          } else if (campos[0] == "PRODUCTO_FIN") {

            productoActual = NULL;
          }
        }
      }
    }

    if (!estadoOk || !tipoCorrecto || grupo == NULL) {

      if (grupo != NULL) {

        delete grupo;

        grupo = NULL;
      }

      for (size_t i = 0; i < integrantes.size(); ++i) {

        delete integrantes[i];
      }

      for (size_t i = 0; i < productos.size(); ++i) {

        delete productos[i];
      }

      integrantes.clear();
      productos.clear();

      if (ultimoError.empty())
        ultimoError = "La respuesta de Python no contiene un grupo valido.";

      return false;
    }

    return true;
  }

public:
#ifdef _WIN32

  LectorArchivosYWeb() : ultimoError(""), procesoScraper(NULL) {}

  ~LectorArchivosYWeb() { cerrarScraperNormal(); }

  static void registrarManejadorConsola() {
    if (!s_manejadorRegistrado) {
      SetConsoleCtrlHandler(ManejadorConsola, TRUE);
      atexit(cerrarScraperAlSalir);
      s_manejadorRegistrado = true;
    }
  }

  static void cerrarScraperAlSalir() {
    if (s_procesoScraper != NULL || s_pidScraper != 0) {
      cerrarScraperNormal();
    }
  }

  static void cerrarScraperNormal() {
    if (!(s_procesoScraper == NULL && s_pidScraper == 0)) {
      s_ultimoTipoCierre = "CIERRE_NORMAL (Desde menu principal)";
      registrarEventoCierre(
          "CIERRE_NORMAL",
          "Salida ordenada del sistema desde el menu principal (Opcion 6).");
      matarProcesoScraper();
    }
  }

  static void cerrarScraperForzado(DWORD tipoControl) {
    s_ultimoTipoCierre = "CIERRE_FORZADO (Ventana cerrada con la 'X' o senal)";
    string motivo = "Cierre forzado de la ventana de consola.";
    if (tipoControl == CTRL_CLOSE_EVENT) {
      motivo = "Ventana de consola cerrada directamente con la 'X' de Windows "
               "(CTRL_CLOSE_EVENT).";
    } else if (tipoControl == CTRL_C_EVENT) {
      motivo =
          "Interrupcion forzada mediante CTRL+C por el usuario (CTRL_C_EVENT).";
    } else if (tipoControl == CTRL_BREAK_EVENT) {
      motivo = "Interrupcion forzada CTRL+BREAK (CTRL_BREAK_EVENT).";
    } else if (tipoControl == CTRL_SHUTDOWN_EVENT ||
               tipoControl == CTRL_LOGOFF_EVENT) {
      motivo =
          "Cierre de sesion o apagado forzado del sistema operativo Windows.";
    }

    registrarEventoCierre("CIERRE_FORZADO", motivo);
    matarProcesoScraper();
  }

  bool estaScraperActivo() const {
    if (s_procesoScraper == NULL && s_pidScraper == 0) {
      return false;
    }
    if (s_procesoScraper != NULL) {
      DWORD codigoSalida = 0;
      if (GetExitCodeProcess(s_procesoScraper, &codigoSalida) &&
          codigoSalida == STILL_ACTIVE) {
        return true;
      }
    }
    return false;
  }

  DWORD obtenerPidScraper() const { return s_pidScraper; }

  string obtenerUltimoTipoCierre() const { return s_ultimoTipoCierre; }

  vector<string> obtenerUltimosRegistrosLog(int maxLineas) const {
    vector<string> lineas;
    ifstream archivo("scraper_cierre.log");
    if (!archivo.is_open()) {
      lineas.push_back(
          "Sin historial registrado todavia en scraper_cierre.log");
      return lineas;
    }
    string l;
    vector<string> todas;
    while (getline(archivo, l)) {
      if (!l.empty()) {
        todas.push_back(l);
      }
    }
    archivo.close();
    if (todas.empty()) {
      lineas.push_back("El archivo scraper_cierre.log esta vacio.");
      return lineas;
    }
    int inicio = static_cast<int>(todas.size()) - maxLineas;
    if (inicio < 0)
      inicio = 0;
    for (size_t i = static_cast<size_t>(inicio); i < todas.size(); ++i) {
      lineas.push_back(todas[i]);
    }
    return lineas;
  }

#else

  LectorArchivosYWeb() : ultimoError("") {}

  ~LectorArchivosYWeb() {}

  static void registrarManejadorConsola() {}
  static void cerrarScraperAlSalir() {}
  static void cerrarScraperNormal() {}
  static void cerrarScraperForzado(int) {}
  bool estaScraperActivo() const { return false; }
  unsigned long obtenerPidScraper() const { return 0; }
  string obtenerUltimoTipoCierre() const { return "N/A"; }
  vector<string> obtenerUltimosRegistrosLog(int) const {
    vector<string> v;
    v.push_back("No disponible en sistemas no Windows.");
    return v;
  }

#endif

  // ---------------------------------------------------------
  // OBTENER ULTIMO ERROR
  // ---------------------------------------------------------

  string getUltimoError() const { return ultimoError; }

  string getRutaScraper() {

#ifdef _WIN32

    return obtenerRutaScraper();

#else

    return "";

#endif
  }

  // ---------------------------------------------------------
  // VALIDACION DE URLS DE MINCIENCIAS (CvLAC Y GrupLAC)
  // ---------------------------------------------------------

  static string limpiarEspaciosTexto(const string &texto) {
    size_t inicio = 0;
    while (inicio < texto.size() &&
           (texto[inicio] == ' ' || texto[inicio] == '\t' ||
            texto[inicio] == '\r' || texto[inicio] == '\n')) {
      inicio++;
    }
    if (inicio >= texto.size()) {
      return "";
    }
    size_t fin = texto.size() - 1;
    while (fin > inicio && (texto[fin] == ' ' || texto[fin] == '\t' ||
                            texto[fin] == '\r' || texto[fin] == '\n')) {
      fin--;
    }
    return texto.substr(inicio, fin - inicio + 1);
  }

  static string aMinusculasTexto(const string &texto) {
    string resultado = texto;
    for (size_t i = 0; i < resultado.size(); ++i) {
      char c = resultado[i];
      if (c >= 'A' && c <= 'Z') {
        resultado[i] = static_cast<char>(c + ('a' - 'A'));
      }
    }
    return resultado;
  }

  static string sanitizarRutaArchivo(const string &texto) {
    string limpia = limpiarEspaciosTexto(texto);
    if (limpia.size() >= 2) {
      char primero = limpia[0];
      char ultimo = limpia[limpia.size() - 1];
      if ((primero == '"' && ultimo == '"') ||
          (primero == '\'' && ultimo == '\'')) {
        limpia = limpia.substr(1, limpia.size() - 2);
        limpia = limpiarEspaciosTexto(limpia);
      }
    }
    return limpia;
  }

  static bool validarUrlMinciencias(const string &tipo,
                                    const string &urlOriginal,
                                    string &urlNormalizada,
                                    string &mensajeError) {
    urlNormalizada.clear();
    mensajeError.clear();

    string urlLimpia = limpiarEspaciosTexto(urlOriginal);
    if (urlLimpia.empty()) {
      mensajeError = "Debe ingresar una URL para procesar la carga.";
      return false;
    }

    string urlConProtocolo = urlLimpia;
    string urlMinTemp = aMinusculasTexto(urlLimpia);
    if (urlMinTemp.substr(0, 7) != "http://" &&
        urlMinTemp.substr(0, 8) != "https://") {
      urlConProtocolo = "https://" + urlLimpia;
    }

    string urlMinus = aMinusculasTexto(urlConProtocolo);

    string sinProto = urlMinus;
    if (sinProto.substr(0, 8) == "https://") {
      sinProto = sinProto.substr(8);
    } else if (sinProto.substr(0, 7) == "http://") {
      sinProto = sinProto.substr(7);
    }

    size_t posFinHost = sinProto.find_first_of("/?#:");
    string host;
    if (posFinHost == string::npos) {
      host = sinProto;
    } else {
      host = sinProto.substr(0, posFinHost);
    }

    if (host != "scienti.minciencias.gov.co") {
      mensajeError = "URL invalida: El enlace debe pertenecer al dominio "
                     "oficial 'scienti.minciencias.gov.co'.";
      return false;
    }

    string tipoMin = aMinusculasTexto(tipo);

    if (tipoMin == "investigador") {
      if (urlMinus.find("/gruplac") != string::npos) {
        mensajeError =
            "Incompatibilidad de tipo: La URL ingresada corresponde a un grupo "
            "(GrupLAC) y no a un investigador (CvLAC). Seleccione la opcion de "
            "cargar grupo si desea registrar este enlace.";
        return false;
      }
      if (urlMinus.find("/cvlac") == string::npos) {
        mensajeError =
            "URL de investigador invalida: El enlace debe corresponder a un "
            "perfil CvLAC (debe contener '/cvlac').";
        return false;
      }
    } else if (tipoMin == "grupo") {
      if (urlMinus.find("/cvlac") != string::npos) {
        mensajeError =
            "Incompatibilidad de tipo: La URL ingresada corresponde a un "
            "investigador (CvLAC) y no a un grupo (GrupLAC). Seleccione la "
            "opcion de cargar investigador si desea registrar este enlace.";
        return false;
      }
      if (urlMinus.find("/gruplac") == string::npos) {
        mensajeError = "URL de grupo invalida: El enlace debe corresponder a "
                       "un grupo GrupLAC (debe contener '/gruplac').";
        return false;
      }
    } else {
      mensajeError = "Tipo de entidad no reconocido: '" + tipo + "'.";
      return false;
    }

    urlNormalizada = urlConProtocolo;
    return true;
  }

  // ---------------------------------------------------------
  // CARGAR INVESTIGADOR DESDE CVLAC
  // ---------------------------------------------------------

  Investigador *cargarInvestigadorDesdeWeb(const string &url) {

    string urlNormalizada;
    string errorValidacion;
    if (!validarUrlMinciencias("investigador", url, urlNormalizada,
                               errorValidacion)) {
      ultimoError = errorValidacion;
      gotoxy(15, 11);
      cout << "Validacion de URL fallida:        ";
      gotoxy(15, 12);
      cout << "URL: " << url;
      gotoxy(15, 13);
      cout << "Error: " << ultimoError;
      return NULL;
    }

    gotoxy(15, 11);
    cout << "Cargando investigador desde CvLAC...";

    gotoxy(15, 12);
    cout << "URL: " << urlNormalizada;

#ifdef _WIN32

    ultimoError = "";

    if (!iniciarScraperPython()) {

      gotoxy(15, 13);
      cout << "Error: " << ultimoError;

      return NULL;
    }

    if (!esperarServidor()) {

      gotoxy(15, 13);
      cout << "Error: " << ultimoError;

      return NULL;
    }

    string cuerpo = "{\"tipoBusqueda\":\"investigador\","
                    "\"url\":\"" +
                    escaparJson(urlNormalizada) + "\"}";

    string respuesta;

    if (!realizarPost("/scraping", cuerpo, respuesta)) {

      gotoxy(15, 13);
      cout << "Error: " << ultimoError;

      return NULL;
    }

    guardarRespuestaBruta(respuesta);

    Investigador *investigador = parsearInvestigador(respuesta);

    if (investigador == NULL) {

      if (ultimoError.empty())
        ultimoError = "No se pudo interpretar la respuesta del scraper.";

      gotoxy(15, 13);
      cout << "Error: " << ultimoError;

      return NULL;
    }

    return investigador;

#else

    (void)url;

    ultimoError = "El puente HTTP del scraper esta preparado para Windows.";

    gotoxy(15, 13);
    cout << "Error: " << ultimoError;

    return NULL;

#endif
  }

  // ---------------------------------------------------------
  // CARGAR GRUPO DESDE GRUPLAC
  // ---------------------------------------------------------

  bool cargarGrupoDesdeWeb(const string &url, GrupoInvestigacion *&grupo,
                           vector<Investigador *> &integrantes,
                           vector<ProductoInvestigacion *> &productos) {

    string urlNormalizada;
    string errorValidacion;
    if (!validarUrlMinciencias("grupo", url, urlNormalizada, errorValidacion)) {
      ultimoError = errorValidacion;
      grupo = NULL;
      integrantes.clear();
      productos.clear();
      gotoxy(15, 11);
      cout << "Validacion de URL fallida:        ";
      gotoxy(15, 12);
      cout << "URL: " << url;
      gotoxy(15, 13);
      cout << "Error: " << ultimoError;
      return false;
    }

    gotoxy(15, 11);
    cout << "Cargando grupo desde GrupLAC...";

    gotoxy(15, 12);
    cout << "URL: " << urlNormalizada;

#ifdef _WIN32

    ultimoError = "";

    grupo = NULL;

    integrantes.clear();
    productos.clear();

    if (!iniciarScraperPython()) {

      gotoxy(15, 13);
      cout << "Error: " << ultimoError;

      return false;
    }

    if (!esperarServidor()) {

      gotoxy(15, 13), cout << "Error: " << ultimoError;

      return false;
    }

    string cuerpo = "{\"tipoBusqueda\":\"grupo\","
                    "\"url\":\"" +
                    escaparJson(urlNormalizada) + "\"}";

    string respuesta;

    if (!realizarPost("/scraping", cuerpo, respuesta)) {

      gotoxy(15, 13);
      cout << "Error: " << ultimoError;

      return false;
    }

    guardarRespuestaBruta(respuesta);

    if (!parsearGrupo(respuesta, grupo, integrantes, productos)) {

      if (ultimoError.empty())
        ultimoError = "No se pudo interpretar la respuesta del scraper.";

      gotoxy(15, 13);
      cout << "Error: " << ultimoError;

      return false;
    }

    return true;

#else

    (void)url;
    (void)grupo;
    (void)integrantes;
    (void)productos;

    ultimoError = "El puente HTTP del scraper esta preparado para Windows.";

    gotoxy(15, 13);
    cout << "Error: " << ultimoError;

    return false;

#endif
  }

  // ---------------------------------------------------------
  // CARGAR DESDE ARCHIVO (PUENTE HTTP CON PYTHON)
  // ---------------------------------------------------------

  bool cargarDesdeArchivo(const string &tipoArchivo, const string &rutaArchivo,
                          string &respuesta) {
#ifdef _WIN32
    ultimoError = "";

    if (!iniciarScraperPython()) {
      return false;
    }

    if (!esperarServidor()) {
      return false;
    }

    string cuerpo = "{\"tipoArchivo\":\"" + escaparJson(tipoArchivo) +
                    "\",\"ruta\":\"" + escaparJson(rutaArchivo) + "\"}";

    if (!realizarPost("/cargar-archivo", cuerpo, respuesta)) {
      return false;
    }

    guardarRespuestaBruta(respuesta);
    return true;
#else
    (void)tipoArchivo;
    (void)rutaArchivo;
    (void)respuesta;
    ultimoError = "El puente HTTP del scraper esta preparado para Windows.";
    return false;
#endif
  }

  // ---------------------------------------------------------
  // PARSEAR LOTE (MULTIPLES GRUPOS E INVESTIGADORES)
  // ---------------------------------------------------------

  bool parsearLote(const string &respuesta,
                   vector<GrupoInvestigacion *> &grupos,
                   vector<vector<Investigador *>> &integrantesGrupos,
                   vector<vector<ProductoInvestigacion *>> &productosGrupos,
                   vector<Investigador *> &investigadores) {

    grupos.clear();
    integrantesGrupos.clear();
    productosGrupos.clear();
    investigadores.clear();

    stringstream flujo(respuesta);
    string linea;

    GrupoInvestigacion *grupoActual = NULL;
    vector<Investigador *> integrantesActuales;
    vector<ProductoInvestigacion *> productosActuales;
    Investigador *integranteActual = NULL;

    Investigador *investigadorActual = NULL;
    ProductoInvestigacion *productoActual = NULL;

    bool estadoOk = false;
    bool esInvestigadorUnico = false;
    bool esGrupoUnico = false;

    while (getline(flujo, linea)) {
      if (!linea.empty()) {
        vector<string> campos = separarCampos(linea);
        if (!campos.empty()) {
          if (campos[0] == "ESTADO") {
            if (campos.size() >= 2 && campos[1] == "OK") {
              estadoOk = true;
            }
          } else if (campos[0] == "ERROR") {
            if (campos.size() >= 2) {
              ultimoError = campos[1];
            }
          } else if (campos[0] == "TIPO") {
            if (campos.size() >= 2) {
              if (campos[1] == "INVESTIGADOR") {
                esInvestigadorUnico = true;
              } else if (campos[1] == "GRUPO") {
                esGrupoUnico = true;
              }
            }
          } else if (campos[0] == "GRUPO") {
            if (campos.size() >= 3) {
              grupoActual = new GrupoInvestigacion(campos[1], campos[2]);
              integrantesActuales.clear();
              productosActuales.clear();
              integranteActual = NULL;
              productoActual = NULL;
            }
          } else if (campos[0] == "ANIO_FORMACION") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->anioFormacion = campos[1];
          } else if (campos[0] == "DEPARTAMENTO") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->departamento = campos[1];
            else if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->departamento = campos[1];
          } else if (campos[0] == "CIUDAD") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->ciudad = campos[1];
            else if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->ciudad = campos[1];
          } else if (campos[0] == "LIDER") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->lider = campos[1];
          } else if (campos[0] == "INFORMACION_CERTIFICADA") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->informacionCertificada = campos[1];
          } else if (campos[0] == "PAGINA_WEB") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->paginaWeb = campos[1];
          } else if (campos[0] == "EMAIL") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->email = campos[1];
          } else if (campos[0] == "CLASIFICACION") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->clasificacion = campos[1];
          } else if (campos[0] == "AREA_CONOCIMIENTO") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->areaConocimiento = campos[1];
            else if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->areasConocimiento.push_back(campos[1]);
          } else if (campos[0] == "PROGRAMA_NACIONAL_CTI") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->programaNacionalCti = campos[1];
          } else if (campos[0] == "PROGRAMA_NACIONAL_CTI_SECUNDARIO") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->programaNacionalCtiSecundario = campos[1];
          } else if (campos[0] == "PLAN_ESTRATEGICO") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->planEstrategico = campos[1];
          } else if (campos[0] == "ESTADO_ARTE") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->estadoArte = campos[1];
          } else if (campos[0] == "OBJETIVOS") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->objetivos = campos[1];
          } else if (campos[0] == "RETOS") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->retos = campos[1];
          } else if (campos[0] == "VISION") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->vision = campos[1];
          } else if (campos[0] == "INSTITUCION") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->instituciones.push_back(campos[1]);
          } else if (campos[0] == "LINEA_INVESTIGACION") {
            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->lineasInvestigacion.push_back(campos[1]);
            else if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->lineasInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE") {
            if (campos.size() >= 3) {
              integranteActual = new Investigador(
                  campos[1], campos[2], campoOpcional(campos, 3),
                  campoOpcional(campos, 4), campoOpcional(campos, 5),
                  campoOpcional(campos, 6), campoOpcional(campos, 7),
                  campoOpcional(campos, 8), campoOpcional(campos, 9));
              if (campos.size() >= 11)
                integranteActual->activo = convertirBooleano(campos[10]);
              integrantesActuales.push_back(integranteActual);
              productoActual = NULL;
            }
          } else if (campos[0] == "INTEGRANTE_NOMBRE_CITACIONES") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->nombreCitaciones = campos[1];
          } else if (campos[0] == "INTEGRANTE_NACIONALIDAD") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->nacionalidad = campos[1];
          } else if (campos[0] == "INTEGRANTE_SEXO") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->sexo = campos[1];
          } else if (campos[0] == "INTEGRANTE_ESTADO_PAR_EVALUADOR") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->estadoParEvaluador = campos[1];
          } else if (campos[0] == "INTEGRANTE_RESEARCHER_ID") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->researcherId = campos[1];
          } else if (campos[0] == "INTEGRANTE_AUTOR_ID_SCOPUS") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->autorIdScopus = campos[1];
          } else if (campos[0] == "INTEGRANTE_GOOGLE_SCHOLAR") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->googleScholar = campos[1];
          } else if (campos[0] == "INTEGRANTE_RESEARCHGATE") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->researchGate = campos[1];
          } else if (campos[0] == "INTEGRANTE_ACADEMIA_EDU") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->academiaEdu = campos[1];
          } else if (campos[0] == "INTEGRANTE_MENDELEY") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->mendeley = campos[1];
          } else if (campos[0] == "INTEGRANTE_LINKEDIN") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->linkedin = campos[1];
          } else if (campos[0] == "INTEGRANTE_REPOSITORIO_INSTITUCIONAL") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->repositorioInstitucional = campos[1];
          } else if (campos[0] == "INTEGRANTE_IDIOMA") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->idiomas.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_FORMACION") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->formacionAcademica.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_EXPERIENCIA") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->experienciaProfesional.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_GRUPO") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->gruposInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_SEMILLERO") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->semilleros.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_PROYECTO") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->proyectos.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_RECONOCIMIENTO") {
            if (integranteActual != NULL && campos.size() >= 2)
              integranteActual->reconocimientos.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_PRODUCTO") {
            productoActual = productoDesdeCampos(campos);
            if (integranteActual != NULL && productoActual != NULL)
              integranteActual->agregarProducto(productoActual);
          } else if (campos[0] == "FIN_INTEGRANTE" ||
                     campos[0] == "INTEGRANTE_FIN") {
            integranteActual = NULL;
            productoActual = NULL;
          } else if (campos[0] == "FIN_GRUPO") {
            if (grupoActual != NULL) {
              grupos.push_back(grupoActual);
              integrantesGrupos.push_back(integrantesActuales);
              productosGrupos.push_back(productosActuales);
              grupoActual = NULL;
              integrantesActuales.clear();
              productosActuales.clear();
            }
            productoActual = NULL;
          } else if (campos[0] == "INVESTIGADOR") {
            if (campos.size() >= 3) {
              investigadorActual = new Investigador(
                  campos[1], campos[2], campoOpcional(campos, 3),
                  campoOpcional(campos, 4), campoOpcional(campos, 5),
                  campoOpcional(campos, 6), campoOpcional(campos, 7),
                  campoOpcional(campos, 8), campoOpcional(campos, 9));
              if (campos.size() >= 11)
                investigadorActual->activo = convertirBooleano(campos[10]);
              productoActual = NULL;
            }
          } else if (campos[0] == "NOMBRE_CITACIONES") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->nombreCitaciones = campos[1];
          } else if (campos[0] == "NACIONALIDAD") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->nacionalidad = campos[1];
          } else if (campos[0] == "SEXO") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->sexo = campos[1];
          } else if (campos[0] == "ESTADO_PAR_EVALUADOR") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->estadoParEvaluador = campos[1];
          } else if (campos[0] == "RESEARCHER_ID") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->researcherId = campos[1];
          } else if (campos[0] == "AUTOR_ID_SCOPUS") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->autorIdScopus = campos[1];
          } else if (campos[0] == "GOOGLE_SCHOLAR") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->googleScholar = campos[1];
          } else if (campos[0] == "RESEARCHGATE") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->researchGate = campos[1];
          } else if (campos[0] == "ACADEMIA_EDU") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->academiaEdu = campos[1];
          } else if (campos[0] == "MENDELEY") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->mendeley = campos[1];
          } else if (campos[0] == "LINKEDIN") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->linkedin = campos[1];
          } else if (campos[0] == "REPOSITORIO_INSTITUCIONAL") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->repositorioInstitucional = campos[1];
          } else if (campos[0] == "IDIOMA") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->idiomas.push_back(campos[1]);
          } else if (campos[0] == "FORMACION") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->formacionAcademica.push_back(campos[1]);
          } else if (campos[0] == "EXPERIENCIA") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->experienciaProfesional.push_back(campos[1]);
          } else if (campos[0] == "GRUPO_INVESTIGACION") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->gruposInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "SEMILLERO") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->semilleros.push_back(campos[1]);
          } else if (campos[0] == "PROYECTO") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->proyectos.push_back(campos[1]);
          } else if (campos[0] == "RECONOCIMIENTO") {
            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->reconocimientos.push_back(campos[1]);
          } else if (campos[0] == "PRODUCTO") {
            productoActual = productoDesdeCampos(campos);
            if (productoActual != NULL) {
              if (grupoActual != NULL) {
                productosActuales.push_back(productoActual);
              } else if (investigadorActual != NULL) {
                investigadorActual->agregarProducto(productoActual);
              }
            }
          } else if (campos[0] == "AUTOR") {
            agregarAutor(productoActual, campos);
          } else if (campos[0] == "PRODUCTO_FIN") {
            productoActual = NULL;
          } else if (campos[0] == "FIN_INVESTIGADOR") {
            if (investigadorActual != NULL) {
              investigadores.push_back(investigadorActual);
              investigadorActual = NULL;
            }
            productoActual = NULL;
          }
        }
      }
    }

    if (grupoActual != NULL) {
      grupos.push_back(grupoActual);
      integrantesGrupos.push_back(integrantesActuales);
      productosGrupos.push_back(productosActuales);
      grupoActual = NULL;
      integrantesActuales.clear();
      productosActuales.clear();
    }
    if (investigadorActual != NULL) {
      investigadores.push_back(investigadorActual);
      investigadorActual = NULL;
    }

    if (esInvestigadorUnico && investigadores.empty()) {
      Investigador *soloInv = parsearInvestigador(respuesta);
      if (soloInv != NULL) {
        investigadores.push_back(soloInv);
      }
    } else if (esGrupoUnico && grupos.empty()) {
      GrupoInvestigacion *soloGrp = NULL;
      vector<Investigador *> integs;
      vector<ProductoInvestigacion *> prods;
      if (parsearGrupo(respuesta, soloGrp, integs, prods) && soloGrp != NULL) {
        grupos.push_back(soloGrp);
        integrantesGrupos.push_back(integs);
        productosGrupos.push_back(prods);
      }
    }

    if (!estadoOk || (grupos.empty() && investigadores.empty())) {
      if (ultimoError.empty()) {
        ultimoError =
            "No se pudieron extraer entidades validas de la respuesta.";
      }
      return false;
    }

    return true;
  }
};

#ifdef _WIN32
HANDLE LectorArchivosYWeb::s_procesoScraper = NULL;
DWORD LectorArchivosYWeb::s_pidScraper = 0;
HANDLE LectorArchivosYWeb::s_jobScraper = NULL;
bool LectorArchivosYWeb::s_manejadorRegistrado = false;
string LectorArchivosYWeb::s_ultimoTipoCierre =
    "NINGUNO (Aun no iniciado o activo)";
#endif

// =========================================================================
// PERSISTENCIA DE ARCHIVOS
// =========================================================================

class PersistenciaArchivos {

private:
  const string ARCHIVO_INVESTIGADORES;
  const string ARCHIVO_GRUPOS;

  // =========================================================
  // SEPARAR CAMPOS DE UNA LINEA
  // =========================================================

  vector<string> separarCampos(const string &linea) {

    vector<string> campos;
    string campo;

    for (size_t i = 0; i < linea.size(); ++i) {

      if (linea[i] == '\t') {

        campos.push_back(campo);

        campo = "";
      } else {

        campo += linea[i];
      }
    }

    campos.push_back(campo);

    return campos;
  }

  // =========================================================
  // CONVERTIR TEXTO A BOOLEANO
  // =========================================================

  bool convertirBooleano(const string &valor) {

    return valor == "1" || valor == "true" || valor == "TRUE" ||
           valor == "si" || valor == "SI";
  }

  // =========================================================
  // BOOLEANO A TEXTO
  // =========================================================

  string booleanoATexto(bool valor) {

    if (valor)
      return "1";

    return "0";
  }

  // =========================================================
  // SANITIZAR TEXTO
  // =========================================================

  string sanitizar(const string &valor) {

    string salida = valor;

    for (size_t i = 0; i < salida.size(); ++i) {

      if (salida[i] == '\t' || salida[i] == '\r' || salida[i] == '\n') {

        salida[i] = ' ';
      }
    }

    return salida;
  }

  // =========================================================
  // OBTENER CAMPO OPCIONAL
  // =========================================================

  string campoOpcional(const vector<string> &campos, size_t indice) {

    if (indice < campos.size())
      return campos[indice];

    return "";
  }

  // =========================================================
  // ESCRIBIR LISTA
  // =========================================================

  void escribirLista(ofstream &archivo, const string &etiqueta,
                     const vector<string> &lista) {

    for (size_t i = 0; i < lista.size(); ++i) {

      archivo << etiqueta << '\t' << sanitizar(lista[i]) << "\n";
    }
  }

  // =========================================================
  // ESCRIBIR PRODUCTO
  // =========================================================

  void escribirProducto(ofstream &archivo, const string &etiqueta,
                        ProductoInvestigacion *producto) {

    if (producto) {

      archivo << etiqueta << '\t' << sanitizar(producto->idProducto) << '\t'
              << sanitizar(producto->titulo) << '\t'
              << sanitizar(producto->categoria) << '\t'
              << booleanoATexto(producto->validado) << '\t' << producto->anio
              << '\t' << sanitizar(producto->tipoProducto) << '\t'
              << sanitizar(producto->subtipo) << '\t'
              << sanitizar(producto->doi) << '\t' << sanitizar(producto->isbn)
              << '\t' << sanitizar(producto->revista) << '\t'
              << sanitizar(producto->editorial) << '\t'
              << sanitizar(producto->disponibilidad) << '\t'
              << sanitizar(producto->institucion) << '\t'
              << sanitizar(producto->ciudad) << '\t'
              << sanitizar(producto->pais) << '\t'
              << sanitizar(producto->numeroContrato) << '\t'
              << sanitizar(producto->descripcion) << '\t'
              << sanitizar(producto->palabrasClave) << '\t'
              << sanitizar(producto->areas) << "\n";

      escribirLista(archivo, "AUTOR", producto->autores);

      archivo << "PRODUCTO_FIN\n";
    }
  }

public:
  PersistenciaArchivos()
      : ARCHIVO_INVESTIGADORES("investigadores.txt"),
        ARCHIVO_GRUPOS("grupos.txt") {}

  // =========================================================
  // VERIFICACION DE EXISTENCIA DE ARCHIVOS
  // =========================================================

  bool existeArchivo(const string &ruta) const {
    ifstream archivo(ruta.c_str());
    return archivo.is_open();
  }

  bool existeArchivoInvestigadores() const {
    return existeArchivo(ARCHIVO_INVESTIGADORES);
  }

  bool existeArchivoGrupos() const { return existeArchivo(ARCHIVO_GRUPOS); }

  bool existenArchivosPersistencia() const {
    return existeArchivoInvestigadores() && existeArchivoGrupos();
  }

  string getArchivoInvestigadores() const { return ARCHIVO_INVESTIGADORES; }

  string getArchivoGrupos() const { return ARCHIVO_GRUPOS; }

  // =========================================================
  // GUARDAR INVESTIGADORES
  // =========================================================

  bool guardarInvestigadores(ListaInvestigadores &lista) {

    ofstream archivo(ARCHIVO_INVESTIGADORES.c_str(), ios::trunc);

    if (!archivo.is_open()) {
      return false;
    }

    archivo << "TIPO\tINVESTIGADORES\n";

    NodoInvestigador *actual = lista.getCabeza();

    while (actual) {

      Investigador *inv = actual->investigador;

      archivo << "INVESTIGADOR\t" << sanitizar(inv->codigoRh) << '\t'
              << sanitizar(inv->nombre) << '\t' << sanitizar(inv->correo)
              << '\t' << sanitizar(inv->orcid) << '\t'
              << sanitizar(inv->institucion) << '\t'
              << sanitizar(inv->departamento) << '\t' << sanitizar(inv->ciudad)
              << '\t' << sanitizar(inv->categoriaInvestigador) << '\t'
              << sanitizar(inv->perfil) << '\t' << booleanoATexto(inv->activo)
              << "\n";

      archivo << "NOMBRE_CITACIONES\t" << sanitizar(inv->nombreCitaciones)
              << "\n";
      archivo << "NACIONALIDAD\t" << sanitizar(inv->nacionalidad) << "\n";
      archivo << "SEXO\t" << sanitizar(inv->sexo) << "\n";
      archivo << "ESTADO_PAR_EVALUADOR\t" << sanitizar(inv->estadoParEvaluador)
              << "\n";
      archivo << "RESEARCHER_ID\t" << sanitizar(inv->researcherId) << "\n";
      archivo << "AUTOR_ID_SCOPUS\t" << sanitizar(inv->autorIdScopus) << "\n";
      archivo << "GOOGLE_SCHOLAR\t" << sanitizar(inv->googleScholar) << "\n";
      archivo << "RESEARCHGATE\t" << sanitizar(inv->researchGate) << "\n";
      archivo << "ACADEMIA_EDU\t" << sanitizar(inv->academiaEdu) << "\n";
      archivo << "MENDELEY\t" << sanitizar(inv->mendeley) << "\n";
      archivo << "LINKEDIN\t" << sanitizar(inv->linkedin) << "\n";
      archivo << "REPOSITORIO_INSTITUCIONAL\t"
              << sanitizar(inv->repositorioInstitucional) << "\n";

      escribirLista(archivo, "IDIOMA", inv->idiomas);

      escribirLista(archivo, "AREA_CONOCIMIENTO", inv->areasConocimiento);

      escribirLista(archivo, "LINEA_INVESTIGACION", inv->lineasInvestigacion);

      escribirLista(archivo, "FORMACION", inv->formacionAcademica);

      escribirLista(archivo, "EXPERIENCIA", inv->experienciaProfesional);

      escribirLista(archivo, "GRUPO_INVESTIGACION", inv->gruposInvestigacion);

      escribirLista(archivo, "SEMILLERO", inv->semilleros);

      escribirLista(archivo, "PROYECTO", inv->proyectos);

      escribirLista(archivo, "RECONOCIMIENTO", inv->reconocimientos);

      NodoProducto *producto = inv->productos;

      while (producto) {

        escribirProducto(archivo, "PRODUCTO", producto->producto);

        producto = producto->sig;
      }

      archivo << "FIN_INVESTIGADOR\n";

      actual = actual->sig;
    }

    archivo << "FIN\n";

    archivo.close();

    return true;
  }

  // =========================================================
  // CARGAR INVESTIGADORES
  // =========================================================

  bool cargarInvestigadores(ListaInvestigadores &lista) {

    ifstream archivo(ARCHIVO_INVESTIGADORES.c_str());

    if (!archivo.is_open()) {
      return false;
    }

    lista.limpiar();

    string linea;

    Investigador *investigadorActual = NULL;

    ProductoInvestigacion *productoActual = NULL;

    bool huboError = false;

    bool huboDatos = false;

    while (getline(archivo, linea) && !huboError) {

      if (!linea.empty()) {

        vector<string> campos = separarCampos(linea);

        if (!campos.empty()) {

          if (campos[0] == "INVESTIGADOR") {

            if (campos.size() >= 4) {

              investigadorActual = new Investigador(
                  campos[1], campos[2], campos[3], campoOpcional(campos, 4),
                  campoOpcional(campos, 5), campoOpcional(campos, 6),
                  campoOpcional(campos, 7), campoOpcional(campos, 8),
                  campoOpcional(campos, 9));

              if (campos.size() >= 11)
                investigadorActual->activo = convertirBooleano(campos[10]);

              lista.agregar(investigadorActual);

              huboDatos = true;
            } else {

              huboError = true;
            }
          } else if (campos[0] == "NOMBRE_CITACIONES") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->nombreCitaciones = campos[1];
          } else if (campos[0] == "NACIONALIDAD") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->nacionalidad = campos[1];
          } else if (campos[0] == "SEXO") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->sexo = campos[1];
          } else if (campos[0] == "ESTADO_PAR_EVALUADOR") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->estadoParEvaluador = campos[1];
          } else if (campos[0] == "RESEARCHER_ID") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->researcherId = campos[1];
          } else if (campos[0] == "AUTOR_ID_SCOPUS") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->autorIdScopus = campos[1];
          } else if (campos[0] == "GOOGLE_SCHOLAR") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->googleScholar = campos[1];
          } else if (campos[0] == "RESEARCHGATE") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->researchGate = campos[1];
          } else if (campos[0] == "ACADEMIA_EDU") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->academiaEdu = campos[1];
          } else if (campos[0] == "MENDELEY") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->mendeley = campos[1];
          } else if (campos[0] == "LINKEDIN") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->linkedin = campos[1];
          } else if (campos[0] == "REPOSITORIO_INSTITUCIONAL") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->repositorioInstitucional = campos[1];
          } else if (campos[0] == "IDIOMA") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->idiomas.push_back(campos[1]);
          } else if (campos[0] == "AREA_CONOCIMIENTO") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->areasConocimiento.push_back(campos[1]);
          } else if (campos[0] == "LINEA_INVESTIGACION") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->lineasInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "FORMACION") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->formacionAcademica.push_back(campos[1]);
          } else if (campos[0] == "EXPERIENCIA") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->experienciaProfesional.push_back(campos[1]);
          } else if (campos[0] == "GRUPO_INVESTIGACION") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->gruposInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "SEMILLERO") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->semilleros.push_back(campos[1]);
          } else if (campos[0] == "PROYECTO") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->proyectos.push_back(campos[1]);
          } else if (campos[0] == "RECONOCIMIENTO") {

            if (investigadorActual != NULL && campos.size() >= 2)
              investigadorActual->reconocimientos.push_back(campos[1]);
          } else if (campos[0] == "PRODUCTO") {

            if (investigadorActual != NULL && campos.size() >= 6) {

              productoActual = new ProductoInvestigacion(
                  campos[1], campos[2], campos[3], convertirBooleano(campos[4]),
                  atoi(campos[5].c_str()), campoOpcional(campos, 6),
                  campoOpcional(campos, 7), campoOpcional(campos, 8),
                  campoOpcional(campos, 9), campoOpcional(campos, 10),
                  campoOpcional(campos, 11), campoOpcional(campos, 12),
                  campoOpcional(campos, 13), campoOpcional(campos, 14),
                  campoOpcional(campos, 15), campoOpcional(campos, 16),
                  campoOpcional(campos, 17), campoOpcional(campos, 18),
                  campoOpcional(campos, 19));

              investigadorActual->agregarProducto(productoActual);
            } else {

              huboError = true;
            }
          } else if (campos[0] == "AUTOR") {

            if (productoActual != NULL && campos.size() >= 2)
              productoActual->autores.push_back(campos[1]);
          } else if (campos[0] == "PRODUCTO_FIN") {

            productoActual = NULL;
          } else if (campos[0] == "FIN_INVESTIGADOR") {

            investigadorActual = NULL;

            productoActual = NULL;
          }
        }
      }
    }

    archivo.close();

    if (huboError || !huboDatos)
      return false;

    return true;
  }

  // =========================================================
  // GUARDAR GRUPOS
  // =========================================================

  bool guardarGrupos(MultilistaGrupos &grupos) {

    ofstream archivo(ARCHIVO_GRUPOS.c_str(), ios::trunc);

    if (!archivo.is_open()) {
      return false;
    }

    archivo << "TIPO\tGRUPOS\n";

    NodoGrupo *grupo = grupos.getCabeza();

    while (grupo) {

      GrupoInvestigacion *g = grupo->grupo;

      archivo << "GRUPO\t" << sanitizar(g->nroGrupo) << '\t'
              << sanitizar(g->nombreGrupo) << "\n";

      archivo << "ANIO_FORMACION\t" << sanitizar(g->anioFormacion) << "\n";

      archivo << "DEPARTAMENTO\t" << sanitizar(g->departamento) << "\n";

      archivo << "CIUDAD\t" << sanitizar(g->ciudad) << "\n";

      archivo << "LIDER\t" << sanitizar(g->lider) << "\n";

      archivo << "INFORMACION_CERTIFICADA\t"
              << sanitizar(g->informacionCertificada) << "\n";

      archivo << "PAGINA_WEB\t" << sanitizar(g->paginaWeb) << "\n";

      archivo << "EMAIL\t" << sanitizar(g->email) << "\n";

      archivo << "CLASIFICACION\t" << sanitizar(g->clasificacion) << "\n";

      archivo << "AREA_CONOCIMIENTO\t" << sanitizar(g->areaConocimiento)
              << "\n";

      archivo << "PROGRAMA_NACIONAL_CTI\t" << sanitizar(g->programaNacionalCti)
              << "\n";

      archivo << "PROGRAMA_NACIONAL_CTI_SECUNDARIO\t"
              << sanitizar(g->programaNacionalCtiSecundario) << "\n";

      archivo << "PLAN_ESTRATEGICO\t" << sanitizar(g->planEstrategico) << "\n";

      archivo << "ESTADO_ARTE\t" << sanitizar(g->estadoArte) << "\n";

      archivo << "OBJETIVOS\t" << sanitizar(g->objetivos) << "\n";

      archivo << "RETOS\t" << sanitizar(g->retos) << "\n";

      archivo << "VISION\t" << sanitizar(g->vision) << "\n";

      archivo << "ACTIVO\t" << booleanoATexto(g->activo) << "\n";

      escribirLista(archivo, "INSTITUCION", g->instituciones);

      escribirLista(archivo, "LINEA_INVESTIGACION", g->lineasInvestigacion);

      NodoInvestigador *inv = grupo->hijoIntegrantes;

      while (inv) {

        Investigador *investigador = inv->investigador;

        archivo << "INTEGRANTE\t" << sanitizar(investigador->codigoRh) << '\t'
                << sanitizar(investigador->nombre) << '\t'
                << sanitizar(investigador->correo) << '\t'
                << sanitizar(investigador->orcid) << '\t'
                << sanitizar(investigador->institucion) << '\t'
                << sanitizar(investigador->departamento) << '\t'
                << sanitizar(investigador->ciudad) << '\t'
                << sanitizar(investigador->categoriaInvestigador) << '\t'
                << sanitizar(investigador->perfil) << '\t'
                << booleanoATexto(investigador->activo) << "\n";

        archivo << "INTEGRANTE_NOMBRE_CITACIONES\t"
                << sanitizar(investigador->nombreCitaciones) << "\n";
        archivo << "INTEGRANTE_NACIONALIDAD\t"
                << sanitizar(investigador->nacionalidad) << "\n";
        archivo << "INTEGRANTE_SEXO\t" << sanitizar(investigador->sexo) << "\n";
        archivo << "INTEGRANTE_ESTADO_PAR_EVALUADOR\t"
                << sanitizar(investigador->estadoParEvaluador) << "\n";
        archivo << "INTEGRANTE_RESEARCHER_ID\t"
                << sanitizar(investigador->researcherId) << "\n";
        archivo << "INTEGRANTE_AUTOR_ID_SCOPUS\t"
                << sanitizar(investigador->autorIdScopus) << "\n";
        archivo << "INTEGRANTE_GOOGLE_SCHOLAR\t"
                << sanitizar(investigador->googleScholar) << "\n";
        archivo << "INTEGRANTE_RESEARCHGATE\t"
                << sanitizar(investigador->researchGate) << "\n";
        archivo << "INTEGRANTE_ACADEMIA_EDU\t"
                << sanitizar(investigador->academiaEdu) << "\n";
        archivo << "INTEGRANTE_MENDELEY\t" << sanitizar(investigador->mendeley)
                << "\n";
        archivo << "INTEGRANTE_LINKEDIN\t" << sanitizar(investigador->linkedin)
                << "\n";
        archivo << "INTEGRANTE_REPOSITORIO_INSTITUCIONAL\t"
                << sanitizar(investigador->repositorioInstitucional) << "\n";

        escribirLista(archivo, "INTEGRANTE_IDIOMA", investigador->idiomas);

        escribirLista(archivo, "INTEGRANTE_AREA",
                      investigador->areasConocimiento);

        escribirLista(archivo, "INTEGRANTE_LINEA",
                      investigador->lineasInvestigacion);

        escribirLista(archivo, "INTEGRANTE_FORMACION",
                      investigador->formacionAcademica);

        escribirLista(archivo, "INTEGRANTE_EXPERIENCIA",
                      investigador->experienciaProfesional);

        escribirLista(archivo, "INTEGRANTE_GRUPO",
                      investigador->gruposInvestigacion);

        escribirLista(archivo, "INTEGRANTE_SEMILLERO",
                      investigador->semilleros);

        escribirLista(archivo, "INTEGRANTE_PROYECTO", investigador->proyectos);

        escribirLista(archivo, "INTEGRANTE_RECONOCIMIENTO",
                      investigador->reconocimientos);

        NodoProducto *producto = investigador->productos;

        while (producto) {

          escribirProducto(archivo, "INTEGRANTE_PRODUCTO", producto->producto);

          producto = producto->sig;
        }

        archivo << "FIN_INTEGRANTE\n";

        inv = inv->sig;
      }

      NodoProducto *productoGrupo = grupo->hijoProductos;

      while (productoGrupo) {

        escribirProducto(archivo, "PRODUCTO", productoGrupo->producto);

        productoGrupo = productoGrupo->sig;
      }

      archivo << "FIN_GRUPO\n";

      grupo = grupo->sig;
    }

    archivo << "FIN\n";

    archivo.close();

    return true;
  }

  // =========================================================
  // CARGAR GRUPOS
  // =========================================================

  bool cargarGrupos(MultilistaGrupos &grupos) {

    ifstream archivo(ARCHIVO_GRUPOS.c_str());

    if (!archivo.is_open()) {
      return false;
    }

    grupos.limpiar();

    string linea;

    NodoGrupo *grupoActual = NULL;

    ProductoInvestigacion *productoActual = NULL;

    bool huboError = false;

    bool huboDatos = false;

    while (getline(archivo, linea) && !huboError) {

      if (!linea.empty()) {

        vector<string> campos = separarCampos(linea);

        if (!campos.empty()) {

          if (campos[0] == "GRUPO") {

            if (campos.size() >= 3) {

              grupos.agregarGrupo(new GrupoInvestigacion(campos[1], campos[2]));

              grupoActual = grupos.buscarGrupo(campos[1]);

              huboDatos = true;
            } else {

              huboError = true;
            }
          } else if (campos[0] == "ANIO_FORMACION") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->anioFormacion = campos[1];
          } else if (campos[0] == "DEPARTAMENTO") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->departamento = campos[1];
          } else if (campos[0] == "CIUDAD") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->ciudad = campos[1];
          } else if (campos[0] == "LIDER") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->lider = campos[1];
          } else if (campos[0] == "INFORMACION_CERTIFICADA") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->informacionCertificada = campos[1];
          } else if (campos[0] == "PAGINA_WEB") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->paginaWeb = campos[1];
          } else if (campos[0] == "EMAIL") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->email = campos[1];
          } else if (campos[0] == "CLASIFICACION") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->clasificacion = campos[1];
          } else if (campos[0] == "AREA_CONOCIMIENTO") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->areaConocimiento = campos[1];
          } else if (campos[0] == "PROGRAMA_NACIONAL_CTI") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->programaNacionalCti = campos[1];
          } else if (campos[0] == "PROGRAMA_NACIONAL_CTI_SECUNDARIO") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->programaNacionalCtiSecundario = campos[1];
          } else if (campos[0] == "PLAN_ESTRATEGICO") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->planEstrategico = campos[1];
          } else if (campos[0] == "ESTADO_ARTE") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->estadoArte = campos[1];
          } else if (campos[0] == "OBJETIVOS") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->objetivos = campos[1];
          } else if (campos[0] == "RETOS") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->retos = campos[1];
          } else if (campos[0] == "VISION") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->vision = campos[1];
          } else if (campos[0] == "ACTIVO") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->activo = convertirBooleano(campos[1]);
          } else if (campos[0] == "INSTITUCION") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->instituciones.push_back(campos[1]);
          } else if (campos[0] == "LINEA_INVESTIGACION") {

            if (grupoActual != NULL && campos.size() >= 2)
              grupoActual->grupo->lineasInvestigacion.push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE") {

            if (grupoActual != NULL && campos.size() >= 4) {

              Investigador *integrante = new Investigador(
                  campos[1], campos[2], campos[3], campoOpcional(campos, 4),
                  campoOpcional(campos, 5), campoOpcional(campos, 6),
                  campoOpcional(campos, 7), campoOpcional(campos, 8),
                  campoOpcional(campos, 9));

              if (campos.size() >= 11)
                integrante->activo = convertirBooleano(campos[10]);

              grupos.agregarIntegrante(grupoActual->grupo->nroGrupo,
                                       integrante);

              grupoActual = grupos.buscarGrupo(grupoActual->grupo->nroGrupo);

              productoActual = NULL;
            } else {

              huboError = true;
            }
          } else if (campos[0] == "INTEGRANTE_NOMBRE_CITACIONES") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->nombreCitaciones =
                  campos[1];
          } else if (campos[0] == "INTEGRANTE_NACIONALIDAD") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->nacionalidad =
                  campos[1];
          } else if (campos[0] == "INTEGRANTE_SEXO") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->sexo = campos[1];
          } else if (campos[0] == "INTEGRANTE_ESTADO_PAR_EVALUADOR") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->estadoParEvaluador =
                  campos[1];
          } else if (campos[0] == "INTEGRANTE_RESEARCHER_ID") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->researcherId =
                  campos[1];
          } else if (campos[0] == "INTEGRANTE_AUTOR_ID_SCOPUS") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->autorIdScopus =
                  campos[1];
          } else if (campos[0] == "INTEGRANTE_GOOGLE_SCHOLAR") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->googleScholar =
                  campos[1];
          } else if (campos[0] == "INTEGRANTE_RESEARCHGATE") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->researchGate =
                  campos[1];
          } else if (campos[0] == "INTEGRANTE_ACADEMIA_EDU") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->academiaEdu =
                  campos[1];
          } else if (campos[0] == "INTEGRANTE_MENDELEY") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->mendeley = campos[1];
          } else if (campos[0] == "INTEGRANTE_LINKEDIN") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->linkedin = campos[1];
          } else if (campos[0] == "INTEGRANTE_REPOSITORIO_INSTITUCIONAL") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador
                  ->repositorioInstitucional = campos[1];
          } else if (campos[0] == "INTEGRANTE_IDIOMA") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->idiomas.push_back(
                  campos[1]);
          } else if (campos[0] == "INTEGRANTE_AREA") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->areasConocimiento
                  .push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_LINEA") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->lineasInvestigacion
                  .push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_FORMACION") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->formacionAcademica
                  .push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_EXPERIENCIA") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->experienciaProfesional
                  .push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_GRUPO") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->gruposInvestigacion
                  .push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_SEMILLERO") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->semilleros.push_back(
                  campos[1]);
          } else if (campos[0] == "INTEGRANTE_PROYECTO") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->proyectos.push_back(
                  campos[1]);
          } else if (campos[0] == "INTEGRANTE_RECONOCIMIENTO") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 2)
              grupoActual->hijoIntegrantes->investigador->reconocimientos
                  .push_back(campos[1]);
          } else if (campos[0] == "INTEGRANTE_PRODUCTO") {

            if (grupoActual != NULL && grupoActual->hijoIntegrantes != NULL &&
                campos.size() >= 6) {

              productoActual = new ProductoInvestigacion(
                  campos[1], campos[2], campos[3], convertirBooleano(campos[4]),
                  atoi(campos[5].c_str()), campoOpcional(campos, 6),
                  campoOpcional(campos, 7), campoOpcional(campos, 8),
                  campoOpcional(campos, 9), campoOpcional(campos, 10),
                  campoOpcional(campos, 11), campoOpcional(campos, 12),
                  campoOpcional(campos, 13), campoOpcional(campos, 14),
                  campoOpcional(campos, 15), campoOpcional(campos, 16),
                  campoOpcional(campos, 17), campoOpcional(campos, 18),
                  campoOpcional(campos, 19));

              grupoActual->hijoIntegrantes->investigador->agregarProducto(
                  productoActual);
            } else {

              huboError = true;
            }
          } else if (campos[0] == "PRODUCTO") {

            if (grupoActual != NULL && campos.size() >= 6) {

              productoActual = new ProductoInvestigacion(
                  campos[1], campos[2], campos[3], convertirBooleano(campos[4]),
                  atoi(campos[5].c_str()), campoOpcional(campos, 6),
                  campoOpcional(campos, 7), campoOpcional(campos, 8),
                  campoOpcional(campos, 9), campoOpcional(campos, 10),
                  campoOpcional(campos, 11), campoOpcional(campos, 12),
                  campoOpcional(campos, 13), campoOpcional(campos, 14),
                  campoOpcional(campos, 15), campoOpcional(campos, 16),
                  campoOpcional(campos, 17), campoOpcional(campos, 18),
                  campoOpcional(campos, 19));

              grupos.agregarProducto(grupoActual->grupo->nroGrupo,
                                     productoActual);
            } else {

              huboError = true;
            }
          } else if (campos[0] == "AUTOR") {

            if (productoActual != NULL && campos.size() >= 2)
              productoActual->autores.push_back(campos[1]);
          } else if (campos[0] == "PRODUCTO_FIN") {

            productoActual = NULL;
          } else if (campos[0] == "FIN_INTEGRANTE") {

            productoActual = NULL;
          } else if (campos[0] == "FIN_GRUPO") {

            grupoActual = NULL;

            productoActual = NULL;
          }
        }
      }
    }

    archivo.close();

    if (huboError || !huboDatos)
      return false;

    return true;
  }
};

// =========================================================================
// ESTRUCTURAS Y UTILIDADES PARA REPORTES DE ESTADISTICAS DE PRODUCCION
// =========================================================================

struct ItemEstadistica {
  string titulo;
  int anio;
  string categoria;
  string subtipo;
  string autorNombre;
  string grupoNombre;
  string firma;

  ItemEstadistica()
      : titulo(""), anio(0), categoria("Sin categoria"), subtipo("Sin subtipo"),
        autorNombre("N/A"), grupoNombre("N/A"), firma("") {}
};

struct FiltroEstadistica {
  string categoria;
  int modoTiempo; // 0: Todos, 1: Ultimo anio, 2: 2 anios, 3: 3 anios, 4: 4 anios, 5: 5 anios, 6: Manual
  int anioManualInicio;
  int anioManualFin;

  FiltroEstadistica()
      : categoria("Todos"), modoTiempo(0), anioManualInicio(0),
        anioManualFin(0) {}
};

struct EntradaConteoEstadistica {
  string etiqueta;
  int cantidad;
  double porcentaje;

  EntradaConteoEstadistica(const string &et = "", int c = 0, double p = 0.0)
      : etiqueta(et), cantidad(c), porcentaje(p) {}
};

static string normalizarSubtipoProducto(const string &subRaw,
                                        const string &tipoRaw) {
  string sub = subRaw;
  if (sub.empty()) {
    sub = tipoRaw;
  }
  if (sub.empty()) {
    return "Sin subtipo";
  }

  // trim inicial y final
  size_t start = 0;
  while (start < sub.size() &&
         (sub[start] == ' ' || sub[start] == '\t' || sub[start] == '\r' ||
          sub[start] == '\n')) {
    start++;
  }
  size_t fin = sub.size();
  while (fin > start &&
         (sub[fin - 1] == ' ' || sub[fin - 1] == '\t' || sub[fin - 1] == '\r' ||
          sub[fin - 1] == '\n')) {
    fin--;
  }

  if (start >= fin) {
    return "Sin subtipo";
  }
  sub = sub.substr(start, fin - start);

  string low = "";
  size_t idxL = 0;
  while (idxL < sub.size()) {
    low += (char)tolower((unsigned char)sub[idxL]);
    idxL++;
  }

  if (low.rfind("tipo:", 0) == 0) {
    if (sub.size() > 5) {
      sub = sub.substr(5);
      start = 0;
      while (start < sub.size() && (sub[start] == ' ' || sub[start] == '\t')) {
        start++;
      }
      sub = sub.substr(start);
      low = "";
      idxL = 0;
      while (idxL < sub.size()) {
        low += (char)tolower((unsigned char)sub[idxL]);
        idxL++;
      }
    }
  }

  bool tienePrefijoOtro = false;
  if (low.rfind("otro ", 0) == 0 || low.rfind("otra ", 0) == 0 ||
      low.rfind("otros ", 0) == 0 || low.rfind("otras ", 0) == 0) {
    tienePrefijoOtro = true;
  }

  if (tienePrefijoOtro) {
    size_t posEspacio = sub.find(' ');
    if (posEspacio != string::npos) {
      sub = sub.substr(posEspacio + 1);
      start = 0;
      while (start < sub.size() && (sub[start] == ' ' || sub[start] == '\t')) {
        start++;
      }
      sub = sub.substr(start);
      low = "";
      idxL = 0;
      while (idxL < sub.size()) {
        low += (char)tolower((unsigned char)sub[idxL]);
        idxL++;
      }
    }
  }

  if (low.find("capitulo") != string::npos ||
      low.find("capítulo") != string::npos) {
    return "Capitulo de libro";
  } else if (low.find("libro") != string::npos) {
    return "Libro";
  } else if (low.find("articulo") != string::npos ||
             low.find("artículo") != string::npos) {
    return "Articulo";
  } else if (low.find("documento de trabajo") != string::npos ||
             low.find("working paper") != string::npos) {
    return "Documento de trabajo";
  } else if (low.find("consultoria") != string::npos ||
             low.find("consultoría") != string::npos) {
    return "Consultoria";
  } else if (low.find("software") != string::npos) {
    return "Software";
  } else if (low.find("curso") != string::npos) {
    return "Curso de corta duracion";
  } else if (low.find("informe") != string::npos) {
    return "Informe de investigacion";
  } else if (low.find("manual") != string::npos ||
             low.find("guia") != string::npos ||
             low.find("guía") != string::npos) {
    return "Manuales y Guias";
  }

  if (sub.size() > 45) {
    vector<string> palabras;
    string palabra = "";
    size_t pIdx = 0;
    while (pIdx < sub.size()) {
      if (sub[pIdx] == ' ') {
        if (!palabra.empty()) {
          palabras.push_back(palabra);
          palabra = "";
        }
      } else {
        palabra += sub[pIdx];
      }
      pIdx++;
    }
    if (!palabra.empty()) {
      palabras.push_back(palabra);
    }
    if (palabras.size() > 4) {
      string resultado = palabras[0] + " " + palabras[1] + " " + palabras[2] +
                         " " + palabras[3] + "...";
      if (!resultado.empty()) {
        resultado[0] = (char)toupper((unsigned char)resultado[0]);
      }
      return resultado;
    }
  }

  if (!sub.empty()) {
    sub[0] = (char)toupper((unsigned char)sub[0]);
    return sub;
  }
  return "Sin subtipo";
}

static vector<ItemEstadistica> consolidarItemsUnicos(
    const vector<ItemEstadistica> &origen) {
  vector<ItemEstadistica> unicos;
  size_t i = 0;
  while (i < origen.size()) {
    const ItemEstadistica &item = origen[i];
    if (!item.titulo.empty()) {
      bool encontrado = false;
      size_t uIdx = 0;
      size_t idxEncontrado = 0;
      while (uIdx < unicos.size() && !encontrado) {
        if (unicos[uIdx].firma == item.firma) {
          encontrado = true;
          idxEncontrado = uIdx;
        }
        uIdx++;
      }
      if (!encontrado) {
        unicos.push_back(item);
      } else {
        if (unicos[idxEncontrado].grupoNombre == "N/A" &&
            item.grupoNombre != "N/A") {
          unicos[idxEncontrado].grupoNombre = item.grupoNombre;
        }
        if (unicos[idxEncontrado].autorNombre == "N/A" &&
            item.autorNombre != "N/A") {
          unicos[idxEncontrado].autorNombre = item.autorNombre;
        }
      }
    }
    i++;
  }
  return unicos;
}

static int calcularAnioReferencia(const vector<ItemEstadistica> &items) {
  time_t t = time(NULL);
  tm *localT = localtime(&t);
  int anioRef = 1900 + localT->tm_year;
  size_t i = 0;
  while (i < items.size()) {
    if (items[i].anio > anioRef) {
      anioRef = items[i].anio;
    }
    i++;
  }
  return anioRef;
}

static bool itemPasaFiltro(const ItemEstadistica &item,
                           const FiltroEstadistica &filtro, int anioRef) {
  bool pasaCat = false;
  if (filtro.categoria == "Todos") {
    pasaCat = true;
  } else if (filtro.categoria == item.categoria) {
    pasaCat = true;
  }

  bool pasaTiempo = false;
  if (filtro.modoTiempo == 0) {
    pasaTiempo = true;
  } else if (item.anio > 1000) {
    if (filtro.modoTiempo == 1) {
      if (item.anio == anioRef) {
        pasaTiempo = true;
      }
    } else if (filtro.modoTiempo == 2) {
      if (item.anio >= anioRef - 1) {
        pasaTiempo = true;
      }
    } else if (filtro.modoTiempo == 3) {
      if (item.anio >= anioRef - 2) {
        pasaTiempo = true;
      }
    } else if (filtro.modoTiempo == 4) {
      if (item.anio >= anioRef - 3) {
        pasaTiempo = true;
      }
    } else if (filtro.modoTiempo == 5) {
      if (item.anio >= anioRef - 4) {
        pasaTiempo = true;
      }
    } else if (filtro.modoTiempo == 6) {
      if (item.anio >= filtro.anioManualInicio &&
          item.anio <= filtro.anioManualFin) {
        pasaTiempo = true;
      }
    }
  }

  if (pasaCat && pasaTiempo) {
    return true;
  }
  return false;
}

static string obtenerDescripcionPeriodo(const FiltroEstadistica &filtro,
                                        int anioRef) {
  if (filtro.modoTiempo == 0) {
    return "Todos los anios (Todos los tiempos)";
  } else if (filtro.modoTiempo == 1) {
    return "Ultimo anio (" + to_string(anioRef) + ")";
  } else if (filtro.modoTiempo == 2) {
    return "Ultimos 2 anios (" + to_string(anioRef - 1) + " - " +
           to_string(anioRef) + ")";
  } else if (filtro.modoTiempo == 3) {
    return "Ultimos 3 anios (" + to_string(anioRef - 2) + " - " +
           to_string(anioRef) + ")";
  } else if (filtro.modoTiempo == 4) {
    return "Ultimos 4 anios (" + to_string(anioRef - 3) + " - " +
           to_string(anioRef) + ")";
  } else if (filtro.modoTiempo == 5) {
    return "Ultimos 5 anios (" + to_string(anioRef - 4) + " - " +
           to_string(anioRef) + ")";
  } else if (filtro.modoTiempo == 6) {
    return "Periodo manual (" + to_string(filtro.anioManualInicio) + " - " +
           to_string(filtro.anioManualFin) + ")";
  }
  return "Sin filtro";
}

static vector<int> parsearSeleccionIndices(const string &entrada, int maxVal) {
  vector<int> indices;
  string limpia = "";
  size_t i = 0;
  while (i < entrada.size()) {
    char ch = entrada[i];
    if (isdigit((unsigned char)ch)) {
      limpia += ch;
    } else {
      if (!limpia.empty()) {
        int val = atoi(limpia.c_str());
        if (val >= 1 && val <= maxVal) {
          bool yaEsta = false;
          size_t k = 0;
          while (k < indices.size() && !yaEsta) {
            if (indices[k] == val) {
              yaEsta = true;
            }
            k++;
          }
          if (!yaEsta) {
            indices.push_back(val);
          }
        }
        limpia = "";
      }
    }
    i++;
  }
  if (!limpia.empty()) {
    int val = atoi(limpia.c_str());
    if (val >= 1 && val <= maxVal) {
      bool yaEsta = false;
      size_t k = 0;
      while (k < indices.size() && !yaEsta) {
        if (indices[k] == val) {
          yaEsta = true;
        }
        k++;
      }
      if (!yaEsta) {
        indices.push_back(val);
      }
    }
  }
  return indices;
}

// =========================================================================
// MOTOR DE CONSOLA//
// =========================================================================
// MOTOR DE CONSOLA
// =========================================================================

class MotorConsolaC {

private:
  // =========================================================
  // ESTRUCTURAS PRINCIPALES
  // =========================================================

  ListaInvestigadores listasInv;

  MultilistaGrupos multilistas;

  // =========================================================
  // MODULO DE LECTURA WEB
  // =========================================================

  LectorArchivosYWeb lectorWeb;

  // =========================================================
  // MODULO DE PERSISTENCIA
  // =========================================================

  PersistenciaArchivos persistencia;

  // =========================================================
  // GESTOR DE PRODUCTOS UNICOS (CONTROL DE DUPLICADOS)
  // =========================================================

  GestorProductosUnicos gestorProductos;

  // =========================================================
  // DIBUJAR MARCO
  // =========================================================

  void dibujarMarco() {

#ifdef _WIN32
    system("cls");
#else
    system("clear");
#endif

    gotoxy(10, 2);
    cout << "==========================================================";

    gotoxy(10, 3);
    cout << "|        PROYECTO PEA-i (Programa Estadistico UPC)       |";

    gotoxy(10, 4);
    cout << "==========================================================";
  }

  // =========================================================
  // PAUSAR
  // =========================================================

  void pausar() {

    gotoxy(10, 20);
    cout << "Presione cualquier tecla para continuar...";

    getch();
  }

  void pausarDinamico() {
    cout << "  Presione cualquier tecla para continuar...";
    getch();
    cout << "\n";
  }

  bool esperarTeclaPaginacion(bool esUltimaPagina) {
    if (!esUltimaPagina) {
      cout << "  [Enter / Cualquier tecla]: Siguiente pagina | [Esc]: Salir de "
              "la lista\n";
    } else {
      cout << "  Fin del listado de productos. Presione cualquier tecla para "
              "terminar...";
    }
    int tecla = getch();
    if (!esUltimaPagina) {
      if (tecla == 27) {
        return false;
      }
    }
    return true;
  }

  // =========================================================
  // CONTEO AUXILIAR DE ENTIDADES
  // =========================================================

  int contarInvestigadoresTotales() {
    int c = 0;
    NodoInvestigador *act = listasInv.getCabeza();
    while (act != NULL) {
      c++;
      act = act->sig;
    }
    return c;
  }

  int contarGruposTotales() {
    int c = 0;
    NodoGrupo *act = multilistas.getCabeza();
    while (act != NULL) {
      c++;
      act = act->sig;
    }
    return c;
  }

  // =========================================================
  // REPORTES ANALITICOS Y PRODUCTOS UNICOS
  // =========================================================

  void mostrarListadoProductosUnicos() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "--- LISTADO DE PRODUCTOS UNICOS Y VINCULACIONES ---";

    const vector<RegistroProductoUnico> &cat = gestorProductos.getCatalogo();
    if (cat.empty()) {
      gotoxy(12, 8);
      cout << "No hay productos cargados en el sistema.";
    } else {
      int y = 7;
      size_t i = 0;
      while (i < cat.size() && y < 18) {
        gotoxy(12, y++);
        string tit = cat[i].producto->titulo;
        if (tit.size() > 40) {
          tit = tit.substr(0, 37) + "...";
        }
        cout << (i + 1) << ". " << tit << " (" << cat[i].producto->anio << ")";

        gotoxy(15, y++);
        cout << "Cat: " << cat[i].producto->categoria;
        if (cat[i].aparicionesTotales > 1) {
          cout << " | COMPARTIDO (" << cat[i].aparicionesTotales
               << " apariciones)";
        }
        y++;
        i++;
      }
    }
    pausar();
  }

  void mostrarDistribucionCategorias() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "--- DISTRIBUCION DE PRODUCTOS UNICOS POR CATEGORIA ---";

    vector<string> categorias = gestorProductos.obtenerCategoriasDisponibles();
    if (categorias.empty()) {
      gotoxy(12, 8);
      cout << "No hay categorias de productos para mostrar.";
    } else {
      int y = 8;
      size_t i = 0;
      while (i < categorias.size() && y < 18) {
        int cantidad = gestorProductos.contarPorCategoria(categorias[i]);
        gotoxy(14, y++);
        string nombreCat = categorias[i];
        if (nombreCat.size() > 35) {
          nombreCat = nombreCat.substr(0, 32) + "...";
        }
        cout << "- " << nombreCat << ": " << cantidad << " producto(s)";
        i++;
      }
    }
    pausar();
  }

  void mostrarDistribucionAnios() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "--- DISTRIBUCION TEMPORAL DE PRODUCTOS UNICOS ---";

    vector<int> anios = gestorProductos.obtenerAniosDisponibles();
    if (anios.empty()) {
      gotoxy(12, 8);
      cout << "No hay anos de productos registrados.";
    } else {
      size_t a1 = 0;
      while (a1 < anios.size()) {
        size_t a2 = a1 + 1;
        while (a2 < anios.size()) {
          if (anios[a1] > anios[a2]) {
            int temp = anios[a1];
            anios[a1] = anios[a2];
            anios[a2] = temp;
          }
          a2++;
        }
        a1++;
      }

      int y = 8;
      size_t i = 0;
      while (i < anios.size() && y < 18) {
        int cantidad = gestorProductos.contarPorAnio(anios[i]);
        gotoxy(16, y++);
        cout << "- Anio " << anios[i] << ": " << cantidad
             << " producto(s) unico(s)";
        i++;
      }
    }
    pausar();
  }

  // =========================================================
  // APARTADO: ESTADISTICAS DE PRODUCCION (GENERALES, INVESTIGADORES Y GRUPOS)
  // =========================================================

  void imprimirTablaDistribucion(
      const string &titulo,
      const vector<EntradaConteoEstadistica> &entradas, int total) {
    cout << "  --- " << titulo << " ---\n";
    cout << "  +--------------------------------------------+----------+------------+\n";
    cout << "  | " << left << setw(42) << "Etiqueta / Concepto" << " | "
         << right << setw(8) << "Cantidad" << " | "
         << right << setw(10) << "Porcentaje" << " |\n";
    cout << "  +--------------------------------------------+----------+------------+\n";

    size_t i = 0;
    while (i < entradas.size()) {
      string etiqueta = entradas[i].etiqueta;
      if (etiqueta.size() > 42) {
        etiqueta = etiqueta.substr(0, 39) + "...";
      }
      ostringstream flujoPorc;
      flujoPorc << fixed << setprecision(1) << entradas[i].porcentaje << " %";

      cout << "  | " << left << setw(42) << etiqueta << " | "
           << right << setw(8) << entradas[i].cantidad << " | "
           << right << setw(10) << flujoPorc.str() << " |\n";
      i++;
    }
    cout << "  +--------------------------------------------+----------+------------+\n";
    cout << "  | " << left << setw(42) << "TOTAL" << " | "
         << right << setw(8) << total << " | "
         << right << setw(10) << "100.0 %" << " |\n";
    cout << "  +--------------------------------------------+----------+------------+\n\n";
  }

  void mostrarTablasEstadisticas(const vector<ItemEstadistica> &filtrados,
                                 const FiltroEstadistica &filtro) {
    if (filtrados.empty()) {
      cout << "  [!] No hay productos que coincidan con los filtros actuales.\n\n";
    } else {
      int total = static_cast<int>(filtrados.size());

      if (filtro.categoria == "Todos") {
        vector<EntradaConteoEstadistica> entradasCat;
        size_t i = 0;
        while (i < filtrados.size()) {
          string cat = filtrados[i].categoria;
          bool encontrada = false;
          size_t c = 0;
          while (c < entradasCat.size() && !encontrada) {
            if (entradasCat[c].etiqueta == cat) {
              entradasCat[c].cantidad++;
              encontrada = true;
            }
            c++;
          }
          if (!encontrada) {
            entradasCat.push_back(EntradaConteoEstadistica(cat, 1, 0.0));
          }
          i++;
        }

        size_t s1 = 0;
        while (s1 < entradasCat.size()) {
          size_t s2 = s1 + 1;
          while (s2 < entradasCat.size()) {
            if (entradasCat[s1].cantidad < entradasCat[s2].cantidad) {
              EntradaConteoEstadistica tmp = entradasCat[s1];
              entradasCat[s1] = entradasCat[s2];
              entradasCat[s2] = tmp;
            }
            s2++;
          }
          s1++;
        }

        size_t p = 0;
        while (p < entradasCat.size()) {
          entradasCat[p].porcentaje =
              (entradasCat[p].cantidad * 100.0) / total;
          p++;
        }

        imprimirTablaDistribucion("DISTRIBUCION POR CATEGORIA", entradasCat,
                                  total);
      }

      vector<EntradaConteoEstadistica> entradasSub;
      size_t j = 0;
      while (j < filtrados.size()) {
        string sub = filtrados[j].subtipo;
        bool encontrada = false;
        size_t s = 0;
        while (s < entradasSub.size() && !encontrada) {
          if (entradasSub[s].etiqueta == sub) {
            entradasSub[s].cantidad++;
            encontrada = true;
          }
          s++;
        }
        if (!encontrada) {
          entradasSub.push_back(EntradaConteoEstadistica(sub, 1, 0.0));
        }
        j++;
      }

      size_t o1 = 0;
      while (o1 < entradasSub.size()) {
        size_t o2 = o1 + 1;
        while (o2 < entradasSub.size()) {
          if (entradasSub[o1].cantidad < entradasSub[o2].cantidad) {
            EntradaConteoEstadistica tmp = entradasSub[o1];
            entradasSub[o1] = entradasSub[o2];
            entradasSub[o2] = tmp;
          }
          o2++;
        }
        o1++;
      }

      size_t q = 0;
      while (q < entradasSub.size()) {
        entradasSub[q].porcentaje =
            (entradasSub[q].cantidad * 100.0) / total;
        q++;
      }

      string tituloSub = "DISTRIBUCION POR SUBTIPO";
      if (filtro.categoria != "Todos") {
        tituloSub =
            "DISTRIBUCION POR SUBTIPO (Categoria: " + filtro.categoria + ")";
      }
      imprimirTablaDistribucion(tituloSub, entradasSub, total);
    }
  }

  void seleccionarFiltroCategoria(
      FiltroEstadistica &filtro,
      const vector<ItemEstadistica> &todosLosProductos) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== SELECCIONAR FILTRO POR CATEGORIA ===";
    cout << "\n\n";

    vector<string> categorias;
    size_t i = 0;
    while (i < todosLosProductos.size()) {
      string cat = todosLosProductos[i].categoria;
      if (!cat.empty()) {
        bool existe = false;
        size_t cIdx = 0;
        while (cIdx < categorias.size() && !existe) {
          if (categorias[cIdx] == cat) {
            existe = true;
          }
          cIdx++;
        }
        if (!existe) {
          categorias.push_back(cat);
        }
      }
      i++;
    }

    size_t s1 = 0;
    while (s1 < categorias.size()) {
      size_t s2 = s1 + 1;
      while (s2 < categorias.size()) {
        if (categorias[s1] > categorias[s2]) {
          string tmp = categorias[s1];
          categorias[s1] = categorias[s2];
          categorias[s2] = tmp;
        }
        s2++;
      }
      s1++;
    }

    cout << "  0. [TODAS LAS CATEGORIAS]\n";
    size_t c = 0;
    while (c < categorias.size()) {
      cout << "  " << (c + 1) << ". " << categorias[c] << "\n";
      c++;
    }
    cout << "\n";
    int opc = leerEntero(
        "  Seleccione una categoria [0-" + to_string(categorias.size()) + "]: ",
        0, static_cast<int>(categorias.size()));
    if (opc == 0) {
      filtro.categoria = "Todos";
    } else {
      filtro.categoria = categorias[opc - 1];
    }
  }

  void seleccionarFiltroPeriodo(FiltroEstadistica &filtro, int anioRef) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== SELECCIONAR FILTRO POR PERIODO DE TIEMPO ===";
    cout << "\n\n";

    cout << "  Anio de referencia actual: " << anioRef << "\n\n";
    cout << "  1. Todos los anios (Todos los tiempos)\n";
    cout << "  2. Ultimo anio (" << anioRef << ")\n";
    cout << "  3. Ultimos 2 anios (" << (anioRef - 1) << " - " << anioRef
         << ")\n";
    cout << "  4. Ultimos 3 anios (" << (anioRef - 2) << " - " << anioRef
         << ")\n";
    cout << "  5. Ultimos 4 anios (" << (anioRef - 3) << " - " << anioRef
         << ")\n";
    cout << "  6. Ultimos 5 anios (" << (anioRef - 4) << " - " << anioRef
         << ")\n";
    cout << "  7. Periodo de tiempo manual (Ingresar anio inicial y anio final)\n\n";

    int opc = leerEntero("  Seleccione una opcion [1-7]: ", 1, 7);
    if (opc == 1) {
      filtro.modoTiempo = 0;
    } else if (opc == 2) {
      filtro.modoTiempo = 1;
    } else if (opc == 3) {
      filtro.modoTiempo = 2;
    } else if (opc == 4) {
      filtro.modoTiempo = 3;
    } else if (opc == 5) {
      filtro.modoTiempo = 4;
    } else if (opc == 6) {
      filtro.modoTiempo = 5;
    } else if (opc == 7) {
      filtro.modoTiempo = 6;
      cout << "\n";
      int anioIni =
          leerEntero("  Ingrese el anio inicial (ej: 2015): ", 1900, 2100);
      int anioFin =
          leerEntero("  Ingrese el anio final   (ej: 2026): ", 1900, 2100);
      if (anioIni > anioFin) {
        int tmp = anioIni;
        anioIni = anioFin;
        anioFin = tmp;
      }
      filtro.anioManualInicio = anioIni;
      filtro.anioManualFin = anioFin;
    }
  }

  void imprimirListadoProductosEstadistica(
      const string &tituloListado, const string &encabezadoEntidad,
      const vector<ItemEstadistica> &productos) {
    dibujarMarco();
    gotoxy(6, 5);
    cout << "=== " << tituloListado << " ===";
    cout << "\n\n";

    if (productos.empty()) {
      cout << "  [!] No se encontraron productos con los filtros seleccionados.\n\n";
      pausarDinamico();
    } else {
      cout << "  Total de productos unicos encontrados: " << productos.size()
           << "\n\n";

      const int LIMITE_PAGINA = 12;
      size_t i = 0;
      bool salirEsc = false;

      cout << "  +--------------------------------------------+--------------------------------+------+--------------------------+\n";
      cout << "  | " << left << setw(42) << "Nombre del producto" << " | "
           << left << setw(30) << encabezadoEntidad << " | "
           << right << setw(4) << "Anio" << " | "
           << left << setw(24) << "Subtipo" << " |\n";
      cout << "  +--------------------------------------------+--------------------------------+------+--------------------------+\n";

      while (i < productos.size() && !salirEsc) {
        string tit = productos[i].titulo;
        if (tit.size() > 42) {
          tit = tit.substr(0, 39) + "...";
        }

        string entidad = "";
        if (encabezadoEntidad == "Investigador") {
          entidad = productos[i].autorNombre;
        } else {
          entidad = productos[i].grupoNombre;
        }
        if (entidad.empty()) {
          entidad = "N/A";
        }
        if (entidad.size() > 30) {
          entidad = entidad.substr(0, 27) + "...";
        }

        string sub = productos[i].subtipo;
        if (sub.size() > 24) {
          sub = sub.substr(0, 21) + "...";
        }

        string anioTxt = to_string(productos[i].anio);
        if (productos[i].anio <= 1000) {
          anioTxt = "S/A";
        }

        cout << "  | " << left << setw(42) << tit << " | "
             << left << setw(30) << entidad << " | "
             << right << setw(4) << anioTxt << " | "
             << left << setw(24) << sub << " |\n";

        i++;

        if (i % LIMITE_PAGINA == 0 && i < productos.size()) {
          cout << "  +--------------------------------------------+--------------------------------+------+--------------------------+\n\n";
          bool continuar = esperarTeclaPaginacion(false);
          if (!continuar) {
            salirEsc = true;
          } else {
            dibujarMarco();
            gotoxy(6, 5);
            cout << "=== " << tituloListado << " (Continuacion) ===";
            cout << "\n\n";
            cout << "  +--------------------------------------------+--------------------------------+------+--------------------------+\n";
            cout << "  | " << left << setw(42) << "Nombre del producto" << " | "
                 << left << setw(30) << encabezadoEntidad << " | "
                 << right << setw(4) << "Anio" << " | "
                 << left << setw(24) << "Subtipo" << " |\n";
            cout << "  +--------------------------------------------+--------------------------------+------+--------------------------+\n";
          }
        }
      }

      if (!salirEsc) {
        cout << "  +--------------------------------------------+--------------------------------+------+--------------------------+\n\n";
        esperarTeclaPaginacion(true);
      }
    }
  }

  void menuEstadisticasInvestigadores(FiltroEstadistica filtroInicial) {
    vector<Investigador *> todosInvs;
    NodoInvestigador *act = listasInv.getCabeza();
    while (act != NULL) {
      if (act->investigador != NULL) {
        todosInvs.push_back(act->investigador);
      }
      act = act->sig;
    }

    if (todosInvs.empty()) {
      dibujarMarco();
      gotoxy(12, 6);
      cout << "No hay investigadores registrados en el sistema.";
      pausar();
    } else {
      bool salirModulo = false;
      vector<Investigador *> invsSeleccionados;

      while (!salirModulo) {
        if (invsSeleccionados.empty()) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "=== ESTADISTICA DE LOS INVESTIGADORES ===";
          cout << "\n\n";
          cout << "  Investigadores disponibles en el sistema:\n\n";
          size_t idx = 0;
          while (idx < todosInvs.size()) {
            cout << "  " << (idx + 1) << ". " << todosInvs[idx]->nombre
                 << " (RH: " << todosInvs[idx]->codigoRh << ")\n";
            idx++;
          }
          cout << "\n";
          cout << "  Ingrese el numero de un investigador o varios separados por coma (ej: 1, 3 o 'T' para todos)\n";
          string selStr =
              leerLineaTexto("  Seleccion (0 para cancelar): ", true);

          if (selStr == "0" || selStr == "c" || selStr == "C") {
            salirModulo = true;
          } else {
            bool esTodos = false;
            if (selStr == "t" || selStr == "T" || selStr == "todos" ||
                selStr == "TODOS") {
              esTodos = true;
            }
            if (esTodos) {
              size_t k = 0;
              while (k < todosInvs.size()) {
                invsSeleccionados.push_back(todosInvs[k]);
                k++;
              }
            } else {
              vector<int> nums = parsearSeleccionIndices(
                  selStr, static_cast<int>(todosInvs.size()));
              size_t nIdx = 0;
              while (nIdx < nums.size()) {
                invsSeleccionados.push_back(todosInvs[nums[nIdx] - 1]);
                nIdx++;
              }
            }

            if (invsSeleccionados.empty()) {
              cout << "  [!] Seleccion no valida. Debe ingresar al menos un numero valido.\n";
              pausarDinamico();
            }
          }
        }

        if (!salirModulo && !invsSeleccionados.empty()) {
          vector<ItemEstadistica> prodsCrudos;
          size_t invI = 0;
          while (invI < invsSeleccionados.size()) {
            Investigador *inv = invsSeleccionados[invI];
            NodoProducto *actP = inv->productos;
            while (actP != NULL) {
              if (actP->producto != NULL) {
                ItemEstadistica item;
                item.titulo = actP->producto->titulo;
                item.anio = actP->producto->anio;
                item.categoria = actP->producto->categoria;
                if (item.categoria.empty()) {
                  item.categoria = actP->producto->tipoProducto;
                }
                if (item.categoria.empty()) {
                  item.categoria = "Sin categoria";
                }
                item.subtipo = normalizarSubtipoProducto(
                    actP->producto->subtipo, actP->producto->tipoProducto);
                item.autorNombre = inv->nombre;
                item.grupoNombre = "N/A";
                item.firma = generarFirmaProducto(item.titulo, item.anio);
                prodsCrudos.push_back(item);
              }
              actP = actP->sig;
            }
            invI++;
          }

          vector<ItemEstadistica> prodsUnicos =
              consolidarItemsUnicos(prodsCrudos);
          FiltroEstadistica filtro = filtroInicial;
          int anioRef = calcularAnioReferencia(prodsUnicos);

          bool salirPanel = false;
          while (!salirPanel) {
            vector<ItemEstadistica> filtrados;
            size_t u = 0;
            while (u < prodsUnicos.size()) {
              if (itemPasaFiltro(prodsUnicos[u], filtro, anioRef)) {
                filtrados.push_back(prodsUnicos[u]);
              }
              u++;
            }

            dibujarMarco();
            gotoxy(8, 5);
            if (invsSeleccionados.size() == 1) {
              cout << "=== ESTADISTICAS DE PRODUCCION DEL INVESTIGADOR SELECCIONADO ===";
              cout << "\n  Investigador : " << invsSeleccionados[0]->nombre
                   << " (RH: " << invsSeleccionados[0]->codigoRh << ")\n";
            } else {
              cout << "=== ESTADISTICAS DE PRODUCCION DE LOS INVESTIGADORES SELECCIONADOS ===";
              cout << "\n  Investigadores seleccionados: "
                   << invsSeleccionados.size() << " investigador(es)\n";
            }
            cout << "  Filtro Categoria            : " << filtro.categoria
                 << "\n";
            cout << "  Filtro Periodo              : "
                 << obtenerDescripcionPeriodo(filtro, anioRef) << "\n";
            cout << "  Total Productos Netos       : " << filtrados.size()
                 << "\n\n";

            mostrarTablasEstadisticas(filtrados, filtro);

            cout << "  1. Cambiar Filtro de Categoria\n";
            cout << "  2. Cambiar Filtro de Periodo de Tiempo\n";
            cout << "  3. Ver Listado de Productos\n";
            cout << "  4. Cambiar Seleccion de Investigadores\n";
            cout << "  5. Regresar a Estadisticas Generales\n\n";

            int opc = leerEntero("  Seleccione una opcion [1-5]: ", 1, 5);
            if (opc == 1) {
              seleccionarFiltroCategoria(filtro, prodsUnicos);
            } else if (opc == 2) {
              seleccionarFiltroPeriodo(filtro, anioRef);
            } else if (opc == 3) {
              imprimirListadoProductosEstadistica(
                  "LISTADO DE PRODUCTOS - INVESTIGADOR(ES)", "Investigador",
                  filtrados);
            } else if (opc == 4) {
              invsSeleccionados.clear();
              salirPanel = true;
            } else if (opc == 5) {
              salirPanel = true;
              salirModulo = true;
            }
          }
        }
      }
    }
  }

  void menuEstadisticasGrupos(FiltroEstadistica filtroInicial) {
    vector<NodoGrupo *> todosGrupos;
    NodoGrupo *act = multilistas.getCabeza();
    while (act != NULL) {
      if (act->grupo != NULL) {
        todosGrupos.push_back(act);
      }
      act = act->sig;
    }

    if (todosGrupos.empty()) {
      dibujarMarco();
      gotoxy(12, 6);
      cout << "No hay grupos de investigacion registrados en el sistema.";
      pausar();
    } else {
      bool salirModulo = false;
      vector<NodoGrupo *> gruposSeleccionados;

      while (!salirModulo) {
        if (gruposSeleccionados.empty()) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "=== ESTADISTICAS DE LOS GRUPOS DE INVESTIGACION ===";
          cout << "\n\n";
          cout << "  Grupos de investigacion disponibles en el sistema:\n\n";
          size_t idx = 0;
          while (idx < todosGrupos.size()) {
            cout << "  " << (idx + 1) << ". "
                 << todosGrupos[idx]->grupo->nombreGrupo << " ("
                 << todosGrupos[idx]->grupo->nroGrupo << ")\n";
            idx++;
          }
          cout << "\n";
          cout << "  Ingrese el numero de un grupo o varios separados por coma (ej: 1, 2 o 'T' para todos)\n";
          string selStr =
              leerLineaTexto("  Seleccion (0 para cancelar): ", true);

          if (selStr == "0" || selStr == "c" || selStr == "C") {
            salirModulo = true;
          } else {
            bool esTodos = false;
            if (selStr == "t" || selStr == "T" || selStr == "todos" ||
                selStr == "TODOS") {
              esTodos = true;
            }
            if (esTodos) {
              size_t k = 0;
              while (k < todosGrupos.size()) {
                gruposSeleccionados.push_back(todosGrupos[k]);
                k++;
              }
            } else {
              vector<int> nums = parsearSeleccionIndices(
                  selStr, static_cast<int>(todosGrupos.size()));
              size_t nIdx = 0;
              while (nIdx < nums.size()) {
                gruposSeleccionados.push_back(todosGrupos[nums[nIdx] - 1]);
                nIdx++;
              }
            }

            if (gruposSeleccionados.empty()) {
              cout << "  [!] Seleccion no valida. Debe ingresar al menos un numero valido.\n";
              pausarDinamico();
            }
          }
        }

        if (!salirModulo && !gruposSeleccionados.empty()) {
          vector<ItemEstadistica> prodsCrudos;
          size_t grpI = 0;
          while (grpI < gruposSeleccionados.size()) {
            NodoGrupo *nodoG = gruposSeleccionados[grpI];
            string nomG = nodoG->grupo->nombreGrupo;
            NodoProducto *actP = nodoG->hijoProductos;
            while (actP != NULL) {
              if (actP->producto != NULL) {
                ItemEstadistica item;
                item.titulo = actP->producto->titulo;
                item.anio = actP->producto->anio;
                item.categoria = actP->producto->categoria;
                if (item.categoria.empty()) {
                  item.categoria = actP->producto->tipoProducto;
                }
                if (item.categoria.empty()) {
                  item.categoria = "Sin categoria";
                }
                item.subtipo = normalizarSubtipoProducto(
                    actP->producto->subtipo, actP->producto->tipoProducto);
                if (!actP->producto->autores.empty()) {
                  item.autorNombre = actP->producto->autores[0];
                  if (actP->producto->autores.size() > 1) {
                    item.autorNombre += " y otros";
                  }
                } else {
                  item.autorNombre = "N/A";
                }
                item.grupoNombre = nomG;
                item.firma = generarFirmaProducto(item.titulo, item.anio);
                prodsCrudos.push_back(item);
              }
              actP = actP->sig;
            }
            grpI++;
          }

          vector<ItemEstadistica> prodsUnicos =
              consolidarItemsUnicos(prodsCrudos);
          FiltroEstadistica filtro = filtroInicial;
          int anioRef = calcularAnioReferencia(prodsUnicos);

          bool salirPanel = false;
          while (!salirPanel) {
            vector<ItemEstadistica> filtrados;
            size_t u = 0;
            while (u < prodsUnicos.size()) {
              if (itemPasaFiltro(prodsUnicos[u], filtro, anioRef)) {
                filtrados.push_back(prodsUnicos[u]);
              }
              u++;
            }

            dibujarMarco();
            gotoxy(8, 5);
            if (gruposSeleccionados.size() == 1) {
              cout << "=== ESTADISTICAS DE PRODUCCION DEL GRUPO SELECCIONADO ===";
              cout << "\n  Grupo : "
                   << gruposSeleccionados[0]->grupo->nombreGrupo << " ("
                   << gruposSeleccionados[0]->grupo->nroGrupo << ")\n";
            } else {
              cout << "=== ESTADISTICAS DE PRODUCCION DE LOS GRUPOS SELECCIONADOS ===";
              cout << "\n  Grupos seleccionados: " << gruposSeleccionados.size()
                   << " grupo(s)\n";
            }
            cout << "  Filtro Categoria     : " << filtro.categoria << "\n";
            cout << "  Filtro Periodo       : "
                 << obtenerDescripcionPeriodo(filtro, anioRef) << "\n";
            cout << "  Total Productos Netos: " << filtrados.size() << "\n\n";

            mostrarTablasEstadisticas(filtrados, filtro);

            cout << "  1. Cambiar Filtro de Categoria\n";
            cout << "  2. Cambiar Filtro de Periodo de Tiempo\n";
            cout << "  3. Ver Listado de Productos\n";
            cout << "  4. Cambiar Seleccion de Grupos\n";
            cout << "  5. Regresar a Estadisticas Generales\n\n";

            int opc = leerEntero("  Seleccione una opcion [1-5]: ", 1, 5);
            if (opc == 1) {
              seleccionarFiltroCategoria(filtro, prodsUnicos);
            } else if (opc == 2) {
              seleccionarFiltroPeriodo(filtro, anioRef);
            } else if (opc == 3) {
              imprimirListadoProductosEstadistica(
                  "LISTADO DE PRODUCTOS - GRUPO(S)", "Grupo", filtrados);
            } else if (opc == 4) {
              gruposSeleccionados.clear();
              salirPanel = true;
            } else if (opc == 5) {
              salirPanel = true;
              salirModulo = true;
            }
          }
        }
      }
    }
  }

  void menuEstadisticasGenerales() {
    vector<ItemEstadistica> prodsCrudos;

    NodoInvestigador *actInv = listasInv.getCabeza();
    while (actInv != NULL) {
      if (actInv->investigador != NULL) {
        string nomInv = actInv->investigador->nombre;
        NodoProducto *actP = actInv->investigador->productos;
        while (actP != NULL) {
          if (actP->producto != NULL) {
            ItemEstadistica item;
            item.titulo = actP->producto->titulo;
            item.anio = actP->producto->anio;
            item.categoria = actP->producto->categoria;
            if (item.categoria.empty()) {
              item.categoria = actP->producto->tipoProducto;
            }
            if (item.categoria.empty()) {
              item.categoria = "Sin categoria";
            }
            item.subtipo = normalizarSubtipoProducto(
                actP->producto->subtipo, actP->producto->tipoProducto);
            item.autorNombre = nomInv;
            item.grupoNombre = "N/A";
            item.firma = generarFirmaProducto(item.titulo, item.anio);
            prodsCrudos.push_back(item);
          }
          actP = actP->sig;
        }
      }
      actInv = actInv->sig;
    }

    NodoGrupo *actGrp = multilistas.getCabeza();
    while (actGrp != NULL) {
      if (actGrp->grupo != NULL) {
        string nomGrp = actGrp->grupo->nombreGrupo;
        NodoProducto *actPG = actGrp->hijoProductos;
        while (actPG != NULL) {
          if (actPG->producto != NULL) {
            ItemEstadistica item;
            item.titulo = actPG->producto->titulo;
            item.anio = actPG->producto->anio;
            item.categoria = actPG->producto->categoria;
            if (item.categoria.empty()) {
              item.categoria = actPG->producto->tipoProducto;
            }
            if (item.categoria.empty()) {
              item.categoria = "Sin categoria";
            }
            item.subtipo = normalizarSubtipoProducto(
                actPG->producto->subtipo, actPG->producto->tipoProducto);
            if (!actPG->producto->autores.empty()) {
              item.autorNombre = actPG->producto->autores[0];
              if (actPG->producto->autores.size() > 1) {
                item.autorNombre += " y otros";
              }
            } else {
              item.autorNombre = "N/A";
            }
            item.grupoNombre = nomGrp;
            item.firma = generarFirmaProducto(item.titulo, item.anio);
            prodsCrudos.push_back(item);
          }
          actPG = actPG->sig;
        }
      }
      actGrp = actGrp->sig;
    }

    vector<ItemEstadistica> prodsUnicos = consolidarItemsUnicos(prodsCrudos);
    int anioRef = calcularAnioReferencia(prodsUnicos);

    FiltroEstadistica filtro;
    filtro.categoria = "Todos";
    filtro.modoTiempo = 0;

    int subOpcion = 0;
    while (subOpcion != 7) {
      vector<ItemEstadistica> filtrados;
      size_t u = 0;
      while (u < prodsUnicos.size()) {
        if (itemPasaFiltro(prodsUnicos[u], filtro, anioRef)) {
          filtrados.push_back(prodsUnicos[u]);
        }
        u++;
      }

      dibujarMarco();
      gotoxy(8, 5);
      cout << "=== ESTADISTICAS GENERALES ===";
      gotoxy(8, 6);
      cout << "Visualizacion exploratoria general de la produccion cientifica";
      cout << "\n";
      cout << "  Total Investigadores Registrados : "
           << contarInvestigadoresTotales() << "\n";
      cout << "  Total Grupos Registrados         : "
           << contarGruposTotales() << "\n";
      cout << "  Filtro Categoria                : " << filtro.categoria
           << "\n";
      cout << "  Filtro Periodo                  : "
           << obtenerDescripcionPeriodo(filtro, anioRef) << "\n";
      cout << "  Total Productos Netos Filtrados : " << filtrados.size()
           << "\n\n";

      mostrarTablasEstadisticas(filtrados, filtro);

      cout << "  1. Cambiar Filtro de Categoria\n";
      cout << "  2. Cambiar Filtro de Periodo de Tiempo\n";
      cout << "  3. Estadistica de los Investigadores\n";
      cout << "  4. Estadisticas de los Grupos de Investigacion\n";
      cout << "  5. Ver Listado de Productos de Investigadores\n";
      cout << "  6. Ver Listado de Productos de Grupos\n";
      cout << "  7. Regresar al Menu de Reportes\n\n";

      subOpcion = leerEntero("  Seleccione una opcion [1-7]: ", 1, 7);

      if (subOpcion == 1) {
        seleccionarFiltroCategoria(filtro, prodsUnicos);
      } else if (subOpcion == 2) {
        seleccionarFiltroPeriodo(filtro, anioRef);
      } else if (subOpcion == 3) {
        menuEstadisticasInvestigadores(filtro);
      } else if (subOpcion == 4) {
        menuEstadisticasGrupos(filtro);
      } else if (subOpcion == 5) {
        vector<ItemEstadistica> listInv;
        size_t fIdx = 0;
        while (fIdx < filtrados.size()) {
          if (filtrados[fIdx].autorNombre != "N/A") {
            listInv.push_back(filtrados[fIdx]);
          }
          fIdx++;
        }
        imprimirListadoProductosEstadistica(
            "LISTADO DE PRODUCTOS DE INVESTIGADORES", "Investigador", listInv);
      } else if (subOpcion == 6) {
        vector<ItemEstadistica> listGrp;
        size_t fIdx = 0;
        while (fIdx < filtrados.size()) {
          if (filtrados[fIdx].grupoNombre != "N/A") {
            listGrp.push_back(filtrados[fIdx]);
          }
          fIdx++;
        }
        imprimirListadoProductosEstadistica(
            "LISTADO DE PRODUCTOS DE GRUPOS", "Grupo", listGrp);
      } else if (subOpcion == 7) {
        // Regresar de forma limpia
      }
    }
  }

  void menuReportesEstadisticos() {
    gestorProductos.consolidar(listasInv, multilistas);

    int subOpcion = 0;
    while (subOpcion != 5) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "--- REPORTES Y ANALISIS (PEA-i) ---";

      gotoxy(12, 7);
      cout << "Total Investigadores : " << contarInvestigadoresTotales();
      gotoxy(12, 8);
      cout << "Total Grupos         : " << contarGruposTotales();
      gotoxy(12, 9);
      cout << "Productos Brutos     : " << gestorProductos.obtenerTotalBruto();
      gotoxy(12, 10);
      cout << "Productos Unicos     : " << gestorProductos.obtenerTotalUnicos()
           << " (Netos reales)";
      gotoxy(12, 11);
      cout << "Duplicados/Compart.  : "
           << gestorProductos.obtenerTotalDuplicados()
           << " (Entre grupos e investigadores)";

      gotoxy(12, 13);
      cout << "1. Estadisticas de produccion";
      gotoxy(12, 14);
      cout << "2. Ver Listado Detallado de Productos Unicos";
      gotoxy(12, 15);
      cout << "3. Distribucion por Categoria de Producto";
      gotoxy(12, 16);
      cout << "4. Distribucion Temporal por Anio";
      gotoxy(12, 17);
      cout << "5. Regresar al Menu Principal";

      gotoxy(12, 19);
      cout << "Seleccione una opcion [1-5]: ";
      cin >> subOpcion;

      if (cin.fail()) {
        cin.clear();
        cin.ignore(10000, '\n');
        subOpcion = 0;
      } else {
        cin.ignore(10000, '\n');
      }

      if (subOpcion == 1) {
        menuEstadisticasGenerales();
      } else if (subOpcion == 2) {
        mostrarListadoProductosUnicos();
      } else if (subOpcion == 3) {
        mostrarDistribucionCategorias();
      } else if (subOpcion == 4) {
        mostrarDistribucionAnios();
      } else if (subOpcion == 5) {
        // Regresar de forma limpia
      } else {
        gotoxy(12, 21);
        cout << "Opcion no valida.";
        pausar();
      }
    }
  }

  // =========================================================
  // CARGAR INVESTIGADOR
  // =========================================================

  void cargarInvestigador() {

    dibujarMarco();

    gotoxy(15, 6);
    cout << "--- CARGAR INVESTIGADOR DESDE CvLAC ---";

    gotoxy(15, 8);
    cout << "Ingrese la URL:";

    gotoxy(15, 9);

    cin >> ws;

    string url;

    getline(cin, url);

    string urlValida;
    string errVal;
    if (!LectorArchivosYWeb::validarUrlMinciencias("investigador", url,
                                                   urlValida, errVal)) {
      gotoxy(15, 11);
      cout << "Error de validacion de URL:";
      if (errVal.find("Incompatibilidad") != string::npos) {
        gotoxy(15, 13);
        cout << "La URL ingresada corresponde a un grupo (GrupLAC).";
        gotoxy(15, 14);
        cout << "Utilice la opcion '2. Cargar Grupo (GrupLAC)'.";
      } else if (errVal.find("scienti.minciencias.gov.co") != string::npos) {
        gotoxy(15, 13);
        cout << "El enlace debe pertenecer al dominio oficial:";
        gotoxy(15, 14);
        cout << "scienti.minciencias.gov.co";
      } else {
        gotoxy(15, 13);
        cout << errVal;
      }
      pausar();
    } else {

      url = urlValida;

      // -----------------------------------------------------
      // LLAMAR AL LECTOR WEB
      // -----------------------------------------------------

      Investigador *investigador =

          lectorWeb.cargarInvestigadorDesdeWeb(url);

      // -----------------------------------------------------
      // ALMACENAR RESULTADO
      // -----------------------------------------------------

      if (investigador != NULL) {

        Investigador *existente = listasInv.buscarCoincidencia(investigador);
        if (existente != NULL) {

          fusionarInvestigador(existente, investigador);
          delete investigador;
          gestorProductos.consolidar(listasInv, multilistas);

          gotoxy(15, 15);
          cout << "El investigador ya existia. Se sincronizaron sus productos.";
          gotoxy(15, 16);
          cout << "Para guardar en disco use la opcion 5.";
        } else {

          listasInv.agregar(investigador);
          gestorProductos.consolidar(listasInv, multilistas);

          gotoxy(15, 15);
          cout << "Investigador cargado en memoria.";
          gotoxy(15, 16);
          cout << "Para guardar en disco use la opcion 5.";
        }
      } else {

        gotoxy(15, 15);
        cout << "No se pudo cargar el investigador.";
      }

      pausar();
    }
  }

  // =========================================================
  // CARGAR GRUPO
  // =========================================================

  void cargarGrupo() {

    dibujarMarco();

    gotoxy(15, 6);
    cout << "--- CARGAR GRUPO DESDE GrupLAC ---";

    gotoxy(15, 8);
    cout << "Ingrese la URL:";

    gotoxy(15, 9);

    cin >> ws;

    string url;

    getline(cin, url);

    string urlValida;
    string errVal;
    if (!LectorArchivosYWeb::validarUrlMinciencias("grupo", url, urlValida,
                                                   errVal)) {
      gotoxy(15, 11);
      cout << "Error de validacion de URL:";
      if (errVal.find("Incompatibilidad") != string::npos) {
        gotoxy(15, 13);
        cout << "La URL ingresada corresponde a un investigador (CvLAC).";
        gotoxy(15, 14);
        cout << "Utilice la opcion '1. Cargar Investigador (CvLAC)'.";
      } else if (errVal.find("scienti.minciencias.gov.co") != string::npos) {
        gotoxy(15, 13);
        cout << "El enlace debe pertenecer al dominio oficial:";
        gotoxy(15, 14);
        cout << "scienti.minciencias.gov.co";
      } else {
        gotoxy(15, 13);
        cout << errVal;
      }
      pausar();
    } else {

      url = urlValida;

      // -----------------------------------------------------
      // LLAMAR AL LECTOR WEB
      // -----------------------------------------------------

      GrupoInvestigacion *grupo = NULL;

      vector<Investigador *> integrantes;

      vector<ProductoInvestigacion *> productos;

      bool cargado =
          lectorWeb.cargarGrupoDesdeWeb(url, grupo, integrantes, productos);

      // -----------------------------------------------------
      // ALMACENAR RESULTADO
      // -----------------------------------------------------

      if (cargado && grupo != NULL) {

        if (multilistas.buscarGrupoCoincidencia(grupo) != NULL) {

          for (size_t i = 0; i < integrantes.size(); ++i) {

            delete integrantes[i];
          }

          for (size_t i = 0; i < productos.size(); ++i) {

            delete productos[i];
          }

          delete grupo;

          gotoxy(15, 15);
          cout << "El grupo ya se encuentra cargado.";
        } else {

          string numeroGrupo = grupo->nroGrupo;

          multilistas.agregarGrupo(grupo);

          for (size_t i = 0; i < integrantes.size(); ++i) {

            multilistas.agregarIntegrante(numeroGrupo, integrantes[i]);
          }

          for (size_t i = 0; i < productos.size(); ++i) {

            multilistas.agregarProducto(numeroGrupo, productos[i]);
          }

          integrantes.clear();
          productos.clear();
          gestorProductos.consolidar(listasInv, multilistas);

          gotoxy(15, 15);
          cout << "Grupo cargado en memoria.";
          gotoxy(15, 16);
          cout << "Para guardar en disco use la opcion 5.";
        }
      } else {

        gotoxy(15, 15);
        cout << "No se pudo cargar el grupo.";
      }

      pausar();
    }
  }

  // =========================================================
  // ESTADO DEL SCRAPER Y HISTORIAL DE CIERRE
  // =========================================================

  void mostrarEstadoScraper() {

    dibujarMarco();

    gotoxy(15, 5);
    cout << "--- ESTADO DEL SCRAPER Y CONTROL DE PROCESOS ---";

    string ruta = lectorWeb.getRutaScraper();
    gotoxy(15, 7);
    cout << "Ruta detectada : ";
    if (ruta.empty()) {
      cout << "No encontrado (PEA-i-Scraper.exe / PEA-i.exe)";
    } else {
      cout << ruta;
    }

    bool activo = lectorWeb.estaScraperActivo();
    gotoxy(15, 8);
    cout << "Estado proceso : ";
    if (activo) {
      cout << "EN EJECUCION (PID: " << lectorWeb.obtenerPidScraper() << ")";
    } else {
      cout << "DETENIDO / INACTIVO";
    }

    gotoxy(15, 10);
    cout << "Ultimo tipo de cierre registrado:";
    gotoxy(17, 11);
    cout << lectorWeb.obtenerUltimoTipoCierre();

    gotoxy(15, 13);
    cout << "Ultimos registros (scraper_cierre.log):";
    vector<string> logs = lectorWeb.obtenerUltimosRegistrosLog(3);
    int y = 14;
    for (size_t i = 0; i < logs.size() && y < 17; ++i) {
      gotoxy(17, y++);
      string texto = logs[i];
      if (texto.size() > 55) {
        texto = texto.substr(0, 52) + "...";
      }
      cout << texto;
    }

    gotoxy(15, 18);
    cout << "1. Detener scraper ahora  |  2. Regresar: ";
    int subOpcion = 0;
    cin >> subOpcion;

    if (cin.fail()) {
      cin.clear();
      cin.ignore(10000, '\n');
      subOpcion = 2;
    }

    if (subOpcion == 1) {
      lectorWeb.cerrarScraperNormal();
      gotoxy(15, 20);
      cout << "Scraper detenido con exito.";
      pausar();
    }
  }

  // =========================================================
  // CARGAR DESDE ARCHIVO PDF (CvLAC / GrupLAC / LOTES MIXTOS)
  // =========================================================

  void cargarDesdePdfConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "--- CARGAR DESDE ARCHIVO PDF (CvLAC / GrupLAC / Lotes) ---";

    gotoxy(12, 7);
    cout << "Arrastre y suelte el archivo PDF aqui o ingrese la ruta:";
    gotoxy(12, 8);
    cout << "(Ejemplo: C:\\datos\\investigadores.pdf)";
    gotoxy(12, 10);
    cout << "Ruta del archivo: ";

    cin >> ws;
    string entradaRuta;
    getline(cin, entradaRuta);

    string rutaLimpia = LectorArchivosYWeb::sanitizarRutaArchivo(entradaRuta);

    if (rutaLimpia.empty()) {
      gotoxy(12, 12);
      cout << "Error: No se ingreso ninguna ruta de archivo.";
      pausar();
    } else {
      string rutaMin = LectorArchivosYWeb::aMinusculasTexto(rutaLimpia);
      bool esPdf = false;
      if (rutaMin.size() >= 4) {
        if (rutaMin.substr(rutaMin.size() - 4) == ".pdf") {
          esPdf = true;
        }
      }

      if (!esPdf) {
        gotoxy(12, 12);
        cout << "Error: El archivo debe tener extension .pdf";
        gotoxy(12, 13);
        cout << "Ruta recibida: " << rutaLimpia;
        pausar();
      } else {
        ifstream archivoPrueba(rutaLimpia.c_str(), ios::binary);
        if (!archivoPrueba.is_open()) {
          gotoxy(12, 12);
          cout << "Error: No se puede abrir o no existe el archivo indicado.";
          gotoxy(12, 13);
          cout << "Ruta: " << rutaLimpia;
          pausar();
        } else {
          archivoPrueba.close();

          gotoxy(12, 12);
          cout << "Procesando documento con el extractor inteligente...";
          gotoxy(12, 13);
          cout << "Esto puede tardar unos segundos segun la longitud...";

          string respuesta;
          bool exitoHttp =
              lectorWeb.cargarDesdeArchivo("pdf", rutaLimpia, respuesta);

          if (!exitoHttp) {
            gotoxy(12, 15);
            cout << "Error en la comunicacion o procesamiento:";
            gotoxy(12, 16);
            string err = lectorWeb.getUltimoError();
            if (err.empty()) {
              err = "Fallo en el servicio extractor del scraper.";
            }
            if (err.size() > 55) {
              err = err.substr(0, 52) + "...";
            }
            cout << err;
            pausar();
          } else {
            vector<GrupoInvestigacion *> gruposNuevos;
            vector<vector<Investigador *>> integrantesNuevos;
            vector<vector<ProductoInvestigacion *>> productosNuevos;
            vector<Investigador *> investigadoresNuevos;

            bool parseoOk = lectorWeb.parsearLote(
                respuesta, gruposNuevos, integrantesNuevos, productosNuevos,
                investigadoresNuevos);

            if (!parseoOk) {
              gotoxy(12, 15);
              cout << "Error interpretando la respuesta del extractor:";
              gotoxy(12, 16);
              string err = lectorWeb.getUltimoError();
              if (err.empty()) {
                err =
                    "El archivo no contiene registros validos de MinCiencias.";
              }
              if (err.size() > 55) {
                err = err.substr(0, 52) + "...";
              }
              cout << err;
              pausar();
            } else {
              int agregadosInv = 0;
              int omitidosInv = 0;
              size_t idxInv = 0;
              while (idxInv < investigadoresNuevos.size()) {
                Investigador *inv = investigadoresNuevos[idxInv];
                if (inv != NULL) {
                  Investigador *existente = listasInv.buscarCoincidencia(inv);
                  if (existente != NULL) {
                    fusionarInvestigador(existente, inv);
                    delete inv;
                    investigadoresNuevos[idxInv] = NULL;
                    omitidosInv++;
                  } else {
                    listasInv.agregar(inv);
                    agregadosInv++;
                  }
                }
                idxInv++;
              }

              int agregadosGrupos = 0;
              int omitidosGrupos = 0;
              size_t idxGrp = 0;
              while (idxGrp < gruposNuevos.size()) {
                GrupoInvestigacion *grp = gruposNuevos[idxGrp];
                if (grp != NULL) {
                  if (multilistas.buscarGrupoCoincidencia(grp) != NULL) {
                    size_t k = 0;
                    while (k < integrantesNuevos[idxGrp].size()) {
                      delete integrantesNuevos[idxGrp][k];
                      integrantesNuevos[idxGrp][k] = NULL;
                      k++;
                    }
                    k = 0;
                    while (k < productosNuevos[idxGrp].size()) {
                      delete productosNuevos[idxGrp][k];
                      productosNuevos[idxGrp][k] = NULL;
                      k++;
                    }
                    delete grp;
                    gruposNuevos[idxGrp] = NULL;
                    omitidosGrupos++;
                  } else {
                    string numGrupo = grp->nroGrupo;
                    multilistas.agregarGrupo(grp);

                    size_t k = 0;
                    while (k < integrantesNuevos[idxGrp].size()) {
                      multilistas.agregarIntegrante(
                          numGrupo, integrantesNuevos[idxGrp][k]);
                      k++;
                    }

                    k = 0;
                    while (k < productosNuevos[idxGrp].size()) {
                      multilistas.agregarProducto(numGrupo,
                                                  productosNuevos[idxGrp][k]);
                      k++;
                    }
                    agregadosGrupos++;
                  }
                }
                idxGrp++;
              }

              // Consolidar productos unicos y control de duplicados
              gestorProductos.consolidar(listasInv, multilistas);

              dibujarMarco();
              gotoxy(12, 5);
              cout << "=== RESULTADO DE EXTRACCION INTELIGENTE (PDF) ===";

              gotoxy(12, 7);
              cout << "Investigadores procesados: "
                   << (agregadosInv + omitidosInv);
              gotoxy(14, 8);
              cout << "- Incorporados: " << agregadosInv
                   << "  |  Ya existentes: " << omitidosInv;

              gotoxy(12, 10);
              cout << "Grupos procesados       : "
                   << (agregadosGrupos + omitidosGrupos);
              gotoxy(14, 11);
              cout << "- Incorporados: " << agregadosGrupos
                   << "  |  Ya existentes: " << omitidosGrupos;

              gotoxy(12, 13);
              cout << "Catalogo consolidado    : "
                   << gestorProductos.obtenerTotalUnicos()
                   << " productos netos";
              gotoxy(14, 14);
              cout << "(Duplicados/compartidos detectados: "
                   << gestorProductos.obtenerTotalDuplicados() << ")";

              gotoxy(12, 16);
              cout << "Datos cargados en memoria. Para guardar en disco,";
              gotoxy(12, 17);
              cout << "utilice la opcion '5. Guardar Datos' del menu.";

              pausar();
            }
          }
        }
      }
    }
  }

  // =========================================================
  // CARGAR DESDE ARCHIVO CSV (CvLAC / GrupLAC / LOTES MIXTOS)
  // =========================================================

  void cargarDesdeCsvConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "--- CARGAR DESDE ARCHIVO CSV (CvLAC / GrupLAC / Lotes) ---";

    gotoxy(12, 7);
    cout << "Arrastre y suelte el archivo CSV aqui o ingrese la ruta:";
    gotoxy(12, 8);
    cout << "(Ejemplo: C:\\datos\\investigadores.csv)";
    gotoxy(12, 10);
    cout << "Ruta del archivo: ";

    cin >> ws;
    string entradaRuta;
    getline(cin, entradaRuta);

    string rutaLimpia = LectorArchivosYWeb::sanitizarRutaArchivo(entradaRuta);

    if (rutaLimpia.empty()) {
      gotoxy(12, 12);
      cout << "Error: No se ingreso ninguna ruta de archivo.";
      pausar();
    } else {
      string rutaMin = LectorArchivosYWeb::aMinusculasTexto(rutaLimpia);
      bool esCsv = false;
      if (rutaMin.size() >= 4) {
        if (rutaMin.substr(rutaMin.size() - 4) == ".csv") {
          esCsv = true;
        }
      }

      if (!esCsv) {
        gotoxy(12, 12);
        cout << "Error: El archivo debe tener extension .csv";
        gotoxy(12, 13);
        cout << "Ruta recibida: " << rutaLimpia;
        pausar();
      } else {
        ifstream archivoPrueba(rutaLimpia.c_str(), ios::binary);
        if (!archivoPrueba.is_open()) {
          gotoxy(12, 12);
          cout << "Error: No se puede abrir o no existe el archivo indicado.";
          gotoxy(12, 13);
          cout << "Ruta: " << rutaLimpia;
          pausar();
        } else {
          archivoPrueba.close();

          gotoxy(12, 12);
          cout << "Procesando archivo CSV con el extractor MinCiencias...";
          gotoxy(12, 13);
          cout << "Validando estructura tabular y consistencia de datos...";

          string respuesta;
          bool exitoHttp =
              lectorWeb.cargarDesdeArchivo("csv", rutaLimpia, respuesta);

          if (!exitoHttp) {
            gotoxy(12, 15);
            cout << "Error en la comunicacion o procesamiento:";
            gotoxy(12, 16);
            string err = lectorWeb.getUltimoError();
            if (err.empty()) {
              err = "Fallo en el servicio extractor del scraper.";
            }
            if (err.size() > 55) {
              err = err.substr(0, 52) + "...";
            }
            cout << err;
            pausar();
          } else {
            vector<GrupoInvestigacion *> gruposNuevos;
            vector<vector<Investigador *>> integrantesNuevos;
            vector<vector<ProductoInvestigacion *>> productosNuevos;
            vector<Investigador *> investigadoresNuevos;

            bool parseoOk = lectorWeb.parsearLote(
                respuesta, gruposNuevos, integrantesNuevos, productosNuevos,
                investigadoresNuevos);

            if (!parseoOk) {
              gotoxy(12, 15);
              cout << "Error interpretando la respuesta del extractor CSV:";
              gotoxy(12, 16);
              string err = lectorWeb.getUltimoError();
              if (err.empty()) {
                err = "El archivo CSV no contiene registros validos de "
                      "MinCiencias.";
              }
              if (err.size() > 55) {
                err = err.substr(0, 52) + "...";
              }
              cout << err;
              pausar();
            } else {
              int prodsInvDetectados = 0;
              int idiomasInvDetectados = 0;
              if (!investigadoresNuevos.empty()) {
                if (investigadoresNuevos[0] != NULL) {
                  prodsInvDetectados =
                      investigadoresNuevos[0]->contarProductos();
                  idiomasInvDetectados =
                      static_cast<int>(investigadoresNuevos[0]->idiomas.size());
                }
              }

              string liderGrpDetectado = "";
              if (!gruposNuevos.empty()) {
                if (gruposNuevos[0] != NULL) {
                  liderGrpDetectado = gruposNuevos[0]->lider;
                }
              }

              int agregadosInv = 0;
              int omitidosInv = 0;
              size_t idxInv = 0;
              while (idxInv < investigadoresNuevos.size()) {
                Investigador *inv = investigadoresNuevos[idxInv];
                if (inv != NULL) {
                  Investigador *existente = listasInv.buscarCoincidencia(inv);
                  if (existente != NULL) {
                    fusionarInvestigador(existente, inv);
                    delete inv;
                    investigadoresNuevos[idxInv] = NULL;
                    omitidosInv++;
                  } else {
                    listasInv.agregar(inv);
                    agregadosInv++;
                  }
                }
                idxInv++;
              }

              int agregadosGrupos = 0;
              int omitidosGrupos = 0;
              size_t idxGrp = 0;
              while (idxGrp < gruposNuevos.size()) {
                GrupoInvestigacion *grp = gruposNuevos[idxGrp];
                if (grp != NULL) {
                  if (multilistas.buscarGrupoCoincidencia(grp) != NULL) {
                    size_t k = 0;
                    while (k < integrantesNuevos[idxGrp].size()) {
                      delete integrantesNuevos[idxGrp][k];
                      integrantesNuevos[idxGrp][k] = NULL;
                      k++;
                    }
                    k = 0;
                    while (k < productosNuevos[idxGrp].size()) {
                      delete productosNuevos[idxGrp][k];
                      productosNuevos[idxGrp][k] = NULL;
                      k++;
                    }
                    delete grp;
                    gruposNuevos[idxGrp] = NULL;
                    omitidosGrupos++;
                  } else {
                    string numGrupo = grp->nroGrupo;
                    multilistas.agregarGrupo(grp);

                    size_t k = 0;
                    while (k < integrantesNuevos[idxGrp].size()) {
                      multilistas.agregarIntegrante(
                          numGrupo, integrantesNuevos[idxGrp][k]);
                      k++;
                    }

                    k = 0;
                    while (k < productosNuevos[idxGrp].size()) {
                      multilistas.agregarProducto(numGrupo,
                                                  productosNuevos[idxGrp][k]);
                      k++;
                    }
                    agregadosGrupos++;
                  }
                }
                idxGrp++;
              }

              // Consolidar productos unicos y control de duplicados
              gestorProductos.consolidar(listasInv, multilistas);

              dibujarMarco();
              gotoxy(12, 5);
              cout << "=== RESULTADO DE IMPORTACION CSV (MinCiencias) ===";

              gotoxy(12, 7);
              cout << "Investigadores procesados: "
                   << (agregadosInv + omitidosInv);
              gotoxy(14, 8);
              cout << "- Incorporados: " << agregadosInv
                   << "  |  Ya existentes: " << omitidosInv;

              if (agregadosInv > 0 || omitidosInv > 0) {
                gotoxy(14, 9);
                cout << "- Detalle: " << prodsInvDetectados << " productos, "
                     << idiomasInvDetectados << " idiomas";
              }

              gotoxy(12, 11);
              cout << "Grupos procesados       : "
                   << (agregadosGrupos + omitidosGrupos);
              gotoxy(14, 12);
              cout << "- Incorporados: " << agregadosGrupos
                   << "  |  Ya existentes: " << omitidosGrupos;

              if (agregadosGrupos > 0 || omitidosGrupos > 0) {
                gotoxy(14, 13);
                if (liderGrpDetectado.empty()) {
                  liderGrpDetectado = "No registrado";
                }
                if (liderGrpDetectado.size() > 28) {
                  liderGrpDetectado = liderGrpDetectado.substr(0, 25) + "...";
                }
                cout << "- Lider: " << liderGrpDetectado;
              }

              gotoxy(12, 15);
              cout << "Catalogo consolidado    : "
                   << gestorProductos.obtenerTotalUnicos()
                   << " productos netos";
              gotoxy(14, 16);
              cout << "(Duplicados/compartidos detectados: "
                   << gestorProductos.obtenerTotalDuplicados() << ")";

              gotoxy(12, 18);
              cout << "Datos cargados en memoria. Para guardar en disco,";
              gotoxy(12, 19);
              cout << "utilice la opcion '5. Guardar Datos' del menu.";

              pausar();
            }
          }
        }
      }
    }
  }

  // =========================================================
  // MENU CARGAR DATOS
  // =========================================================

  void menuCargarDatos() {

    int opcion = 0;

    while (opcion != 6) {

      dibujarMarco();

      gotoxy(15, 6);
      cout << "--- CARGAR DATOS ---";
      gotoxy(15, 8);
      cout << "1. Cargar Investigador desde Web (CvLAC)";
      gotoxy(15, 9);
      cout << "2. Cargar Grupo desde Web (GrupLAC)";
      gotoxy(15, 10);
      cout << "3. Cargar desde Archivo PDF (CvLAC / GrupLAC / Lotes)";
      gotoxy(15, 11);
      cout << "4. Cargar desde Archivo CSV (CvLAC / GrupLAC / Lotes)";
      gotoxy(15, 12);
      cout << "5. Estado y Registro de Cierre del Scraper";
      gotoxy(15, 13);
      cout << "6. Regresar";
      gotoxy(15, 15);
      cout << "Seleccione una opcion: ";

      cin >> opcion;

      if (cin.fail()) {
        cin.clear();
        cin.ignore(10000, '\n');
        opcion = 0;
      }

      if (opcion == 1) {
        cargarInvestigador();
      } else if (opcion == 2) {
        cargarGrupo();
      } else if (opcion == 3) {
        cargarDesdePdfConsola();
      } else if (opcion == 4) {
        cargarDesdeCsvConsola();
      } else if (opcion == 5) {
        mostrarEstadoScraper();
      } else if (opcion == 6) {
        // Regresar al menu anterior.
      } else {
        gotoxy(15, 17);
        cout << "Opcion no valida.";
        pausar();
      }
    }
  }

public:
  // =========================================================
  // PERSISTENCIA Y CARGA INICIAL
  // =========================================================

  bool existenArchivosPersistencia() const {
    return persistencia.existenArchivosPersistencia();
  }

  bool existeArchivoInvestigadores() const {
    return persistencia.existeArchivoInvestigadores();
  }

  bool existeArchivoGrupos() const {
    return persistencia.existeArchivoGrupos();
  }

  bool cargarPersistencia() {
    bool invOK = persistencia.cargarInvestigadores(listasInv);
    bool gruposOK = persistencia.cargarGrupos(multilistas);
    if (invOK && gruposOK) {
      gestorProductos.consolidar(listasInv, multilistas);
      return true;
    }
    listasInv.limpiar();
    multilistas.limpiar();
    return false;
  }

  void cargarDatosIniciales() {
    if (existenArchivosPersistencia()) {
      if (!cargarPersistencia()) {
        iniciarSemilla();
      }
    } else {
      iniciarSemilla();
    }
  }

  // =========================================================
  // SEMILLA DE PRUEBA
  // =========================================================

  void iniciarSemilla() {

    // -----------------------------------------------------
    // INVESTIGADOR
    // -----------------------------------------------------

    Investigador *inv =

        new Investigador("001", "Dr. Juan Perez", "jperez@upc.edu.co");

    listasInv.agregar(inv);

    // -----------------------------------------------------
    // GRUPO
    // -----------------------------------------------------

    GrupoInvestigacion *grupo =

        new GrupoInvestigacion("G8", "Grupo de Investigacion UPC");

    multilistas.agregarGrupo(grupo);

    // -----------------------------------------------------
    // INTEGRANTE DEL GRUPO
    // -----------------------------------------------------

    // Es una copia independiente.
    Investigador *integrante =

        new Investigador("001", "Dr. Juan Perez", "jperez@upc.edu.co");

    multilistas.agregarIntegrante("G8", integrante);

    // -----------------------------------------------------
    // PRODUCTO
    // -----------------------------------------------------

    ProductoInvestigacion *producto =

        new ProductoInvestigacion("P001",
                                  "Sistema de informacion para investigacion",
                                  "Articulo", true, 2025);

    multilistas.agregarProducto("G8", producto);
    gestorProductos.consolidar(listasInv, multilistas);
  }

  // =========================================================
  // METODOS AUXILIARES DE LECTURA Y CONSTRUCCION INTERACTIVA
  // =========================================================

  string leerLineaTexto(const string &indicacion, bool obligatorio) {
    string entrada = "";
    bool valido = false;
    while (!valido) {
      cout << indicacion;
      getline(cin, entrada);

      size_t ini = 0;
      while (ini < entrada.size() &&
             (entrada[ini] == ' ' || entrada[ini] == '\t' ||
              entrada[ini] == '\r')) {
        ini++;
      }
      size_t fin = entrada.size();
      while (fin > ini &&
             (entrada[fin - 1] == ' ' || entrada[fin - 1] == '\t' ||
              entrada[fin - 1] == '\r')) {
        fin--;
      }

      string limpio = "";
      if (fin > ini) {
        limpio = entrada.substr(ini, fin - ini);
      }

      if (!obligatorio) {
        entrada = limpio;
        valido = true;
      } else {
        if (!limpio.empty()) {
          entrada = limpio;
          valido = true;
        } else {
          cout << "  [!] Campo obligatorio. Por favor ingrese un valor.\n";
        }
      }
    }
    return entrada;
  }

  int leerEntero(const string &indicacion, int minVal, int maxVal) {
    int valor = minVal - 1;
    bool valido = false;
    while (!valido) {
      cout << indicacion;
      cin >> valor;
      if (cin.fail()) {
        cin.clear();
        cin.ignore(10000, '\n');
        cout << "  [!] Entrada numerica invalida. Debe ser un numero entre "
             << minVal << " y " << maxVal << ".\n";
      } else {
        cin.ignore(10000, '\n');
        if (valor >= minVal && valor <= maxVal) {
          valido = true;
        } else {
          cout << "  [!] Valor fuera de rango (" << minVal << " - " << maxVal
               << "). Intente nuevamente.\n";
        }
      }
    }
    return valor;
  }

  string valorOCadena(const string &val, const string &defecto) {
    if (val.empty()) {
      return defecto;
    }
    return val;
  }

  string leerLineaModificar(const string &indicacion, const string &valorActual,
                            bool obligatorio) {
    string entrada = "";
    bool valido = false;
    while (!valido) {
      if (!valorActual.empty()) {
        cout << indicacion << "\n";
        cout << "    [Valor actual: " << valorActual << "]\n";
        if (obligatorio) {
          cout << "    (Presione ENTER para conservar el valor actual): ";
        } else {
          cout << "    (Presione ENTER para conservar, '-' para borrar): ";
        }
      } else {
        cout << indicacion << "\n";
        cout << "    [Valor actual: (Vacio / No registrado)]\n";
        if (obligatorio) {
          cout << "    (Ingrese nuevo valor obligatorio): ";
        } else {
          cout << "    (Presione ENTER para omitir o ingrese nuevo valor): ";
        }
      }

      getline(cin, entrada);

      size_t ini = 0;
      while (ini < entrada.size() &&
             (entrada[ini] == ' ' || entrada[ini] == '\t' ||
              entrada[ini] == '\r')) {
        ini++;
      }
      size_t fin = entrada.size();
      while (fin > ini &&
             (entrada[fin - 1] == ' ' || entrada[fin - 1] == '\t' ||
              entrada[fin - 1] == '\r')) {
        fin--;
      }

      string limpio = "";
      if (fin > ini) {
        limpio = entrada.substr(ini, fin - ini);
      }

      if (limpio.empty()) {
        if (!valorActual.empty()) {
          entrada = valorActual;
          valido = true;
        } else {
          if (!obligatorio) {
            entrada = "";
            valido = true;
          } else {
            cout << "  [!] Campo obligatorio. Por favor ingrese un valor.\n";
          }
        }
      } else {
        if (limpio == "-" && !obligatorio) {
          entrada = "";
          valido = true;
        } else {
          entrada = limpio;
          valido = true;
        }
      }
    }
    return entrada;
  }

  void eliminarElementoColeccion(const string &nombreColeccion,
                                 vector<string> &coleccion) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== ELIMINAR " << nombreColeccion << " ===";
    cout << "\n\n";

    if (coleccion.empty()) {
      cout << "  [!] No hay elementos registrados en " << nombreColeccion
           << " para eliminar.\n\n";
      pausarDinamico();
    } else {
      cout << "  Elementos registrados:\n";
      size_t i = 0;
      while (i < coleccion.size()) {
        cout << "    " << (i + 1) << ". " << coleccion[i] << "\n";
        i++;
      }
      cout << "\n";
      string aviso = "  Seleccione el numero a eliminar [1-" +
                     to_string(coleccion.size()) + "] (0 para cancelar): ";
      int sel = leerEntero(aviso, 0, static_cast<int>(coleccion.size()));
      if (sel > 0) {
        string eliminado = coleccion[sel - 1];
        coleccion.erase(coleccion.begin() + (sel - 1));
        cout << "\n  [OK] '" << eliminado
             << "' ha sido eliminado exitosamente.\n\n";
        pausarDinamico();
      }
    }
  }

  Investigador *clonarInvestigador(const Investigador *orig) {
    Investigador *copia = NULL;
    if (orig != NULL) {
      copia = new Investigador(orig->codigoRh, orig->nombre, orig->correo,
                               orig->orcid, orig->institucion,
                               orig->departamento, orig->ciudad,
                               orig->categoriaInvestigador, orig->perfil);

      copia->nombreCitaciones = orig->nombreCitaciones;
      copia->nacionalidad = orig->nacionalidad;
      copia->sexo = orig->sexo;
      copia->estadoParEvaluador = orig->estadoParEvaluador;
      copia->researcherId = orig->researcherId;
      copia->autorIdScopus = orig->autorIdScopus;
      copia->googleScholar = orig->googleScholar;
      copia->researchGate = orig->researchGate;
      copia->academiaEdu = orig->academiaEdu;
      copia->mendeley = orig->mendeley;
      copia->linkedin = orig->linkedin;
      copia->repositorioInstitucional = orig->repositorioInstitucional;
      copia->idiomas = orig->idiomas;
      copia->areasConocimiento = orig->areasConocimiento;
      copia->lineasInvestigacion = orig->lineasInvestigacion;
      copia->formacionAcademica = orig->formacionAcademica;
      copia->experienciaProfesional = orig->experienciaProfesional;
      copia->gruposInvestigacion = orig->gruposInvestigacion;
      copia->semilleros = orig->semilleros;
      copia->proyectos = orig->proyectos;
      copia->reconocimientos = orig->reconocimientos;
      copia->activo = orig->activo;

      NodoProducto *actP = orig->productos;
      while (actP != NULL) {
        if (actP->producto != NULL) {
          ProductoInvestigacion *prodCopia =
              new ProductoInvestigacion(*(actP->producto));
          copia->agregarProducto(prodCopia);
        }
        actP = actP->sig;
      }
    }
    return copia;
  }

  string seleccionarCategoriaProducto() {
    cout << "\n  --- CATEGORIAS DISPONIBLES DE PRODUCTOS ---\n";
    cout << "   1. Articulo\n";
    cout << "   2. Capitulos de libro\n";
    cout << "   3. Capitulos de libro publicados\n";
    cout << "   4. Informes de investigacion\n";
    cout << "   5. Libros de divulgacion y/o Compilacion\n";
    cout << "   6. Libros de formacion\n";
    cout << "   7. Libros publicados\n";
    cout << "   8. Manuales y Guias Especializadas\n";
    cout << "   9. Otra publicacion divulgativa\n";
    cout << "  10. Otros articulos publicados\n";
    cout << "  11. Softwares\n";
    cout << "  12. Otra categoria (personalizada)\n";
    int opCat =
        leerEntero("  Seleccione el numero de categoria [1-12]: ", 1, 12);
    string categoriaSeleccionada = "";
    if (opCat == 1) {
      categoriaSeleccionada = "Articulo";
    } else if (opCat == 2) {
      categoriaSeleccionada = "Capitulos de libro";
    } else if (opCat == 3) {
      categoriaSeleccionada = "Capitulos de libro publicados";
    } else if (opCat == 4) {
      categoriaSeleccionada = "Informes de investigacion";
    } else if (opCat == 5) {
      categoriaSeleccionada =
          "Libros de divulgacion y/o Compilacion de divulgacion";
    } else if (opCat == 6) {
      categoriaSeleccionada = "Libros de formacion";
    } else if (opCat == 7) {
      categoriaSeleccionada = "Libros publicados";
    } else if (opCat == 8) {
      categoriaSeleccionada = "Manuales y Guias Especializadas";
    } else if (opCat == 9) {
      categoriaSeleccionada = "Otra publicacion divulgativa";
    } else if (opCat == 10) {
      categoriaSeleccionada = "Otros articulos publicados";
    } else if (opCat == 11) {
      categoriaSeleccionada = "Softwares";
    } else if (opCat == 12) {
      categoriaSeleccionada = leerLineaTexto(
          "  Ingrese el nombre de la categoria personalizada: ", true);
    }
    return categoriaSeleccionada;
  }

  ProductoInvestigacion *
  crearProductoInteractivo(const string &idSugerido,
                           const string &autorPredeterminado) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== REGISTRO DE PRODUCTO DE INVESTIGACION ===";
    cout << "\n\n";

    string idProd = "";
    if (!idSugerido.empty()) {
      cout << "  ID sugerido para el producto: " << idSugerido << "\n";
      cout << "  1. Usar ID sugerido\n";
      cout << "  2. Ingresar ID personalizado\n";
      int opId = leerEntero("  Seleccione opcion [1-2]: ", 1, 2);
      if (opId == 1) {
        idProd = idSugerido;
      } else {
        idProd =
            leerLineaTexto("  Ingrese ID personalizado del producto: ", true);
      }
    } else {
      idProd = leerLineaTexto("  Ingrese ID del producto: ", true);
    }

    string titulo =
        leerLineaTexto("  Titulo del producto (obligatorio): ", true);
    string categoria = seleccionarCategoriaProducto();

    cout << "\n";
    string subtipo =
        leerLineaTexto("  Subcategoria / Subtipo (variable, ingresado por "
                       "usuario, ej: Articulo A1, Software web, etc.): ",
                       false);
    if (subtipo.empty()) {
      subtipo = categoria;
    }

    int anio =
        leerEntero("  Anio de creacion / publicacion (ej: 2024): ", 1900, 2100);

    cout << "\n  ¿Producto validado por MinCiencias?\n";
    cout << "  1. Si\n";
    cout << "  2. No\n";
    int opVal = leerEntero("  Seleccione [1-2]: ", 1, 2);
    bool validado = false;
    if (opVal == 1) {
      validado = true;
    }

    cout << "\n  ¿Desea ingresar datos adicionales (DOI, ISBN, Revista, "
            "Editorial)?\n";
    cout << "  1. Si\n";
    cout << "  2. Omitir\n";
    int opExt = leerEntero("  Seleccione [1-2]: ", 1, 2);
    string doi = "";
    string isbn = "";
    string revista = "";
    string editorial = "";
    if (opExt == 1) {
      doi = leerLineaTexto("  DOI (opcional): ", false);
      isbn = leerLineaTexto("  ISBN (opcional): ", false);
      revista = leerLineaTexto("  Revista (opcional): ", false);
      editorial = leerLineaTexto("  Editorial (opcional): ", false);
    }

    ProductoInvestigacion *nuevoProd = new ProductoInvestigacion(
        idProd, titulo, categoria, validado, anio, categoria, subtipo, doi,
        isbn, revista, editorial);

    if (!autorPredeterminado.empty()) {
      nuevoProd->autores.push_back(autorPredeterminado);
    }

    cout << "\n  ¿Desea registrar autores adicionales para este producto?\n";
    cout << "  1. Si\n";
    cout << "  2. Omitir\n";
    int opAut = leerEntero("  Seleccione [1-2]: ", 1, 2);
    if (opAut == 1) {
      bool agregandoAutores = true;
      while (agregandoAutores) {
        string autor = leerLineaTexto(
            "  Nombre del autor adicional (Enter para finalizar autores): ",
            false);
        if (!autor.empty()) {
          nuevoProd->autores.push_back(autor);
        } else {
          agregandoAutores = false;
        }
      }
    }

    cout << "\n  [OK] Producto registrado temporalmente para esta entidad.\n";
    pausar();
    return nuevoProd;
  }

  // =========================================================
  // GESTION DE INVESTIGADORES: AGREGAR (CREATE) Y LISTAR
  // =========================================================

  void listarInvestigadores() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== LISTADO DE INVESTIGADORES REGISTRADOS ===";

    NodoInvestigador *act = listasInv.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay investigadores registrados en el sistema.";
    } else {
      int y = 7;
      int n = 1;
      while (act != NULL && y < 19) {
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->investigador->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->investigador->nombre
             << " (" << act->investigador->codigoRh << ") ["
             << act->investigador->contarProductos() << " prods]";
        y++;
        n++;
        act = act->sig;
      }
      if (act != NULL) {
        gotoxy(12, 19);
        cout << "... y mas investigadores registrados en el catalogo.";
      }
    }
    pausar();
  }

  void agregarInvestigador() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== AGREGAR INVESTIGADOR ===";
    gotoxy(12, 7);
    cout << "Paso 1: Datos Basicos Obligatorios";
    cout << "\n\n";

    string codigoRh = "";
    bool codigoValido = false;
    while (!codigoValido) {
      codigoRh = leerLineaTexto(
          "  Codigo RH / Identificador unico (obligatorio): ", true);
      Investigador *existente = listasInv.buscar(codigoRh);
      if (existente != NULL) {
        cout << "  [!] Ya existe un investigador con el codigo '" << codigoRh
             << "': " << existente->nombre << ".\n";
        cout << "  Por favor ingrese un codigo identificador diferente.\n";
      } else {
        codigoValido = true;
      }
    }

    string nombre = leerLineaTexto(
        "  Nombre completo del investigador (obligatorio): ", true);
    string correo =
        leerLineaTexto("  Correo electronico (obligatorio): ", true);
    string sexo = leerLineaTexto("  Sexo (obligatorio): ", true);
    string nacionalidad =
        leerLineaTexto("  Nacionalidad (obligatorio): ", true);
    string departamento =
        leerLineaTexto("  Departamento (obligatorio): ", true);
    string ciudad = leerLineaTexto("  Ciudad (obligatorio): ", true);

    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== AGREGAR INVESTIGADOR ===";
    gotoxy(12, 7);
    cout << "Paso 2: Datos Complementarios Opcionales (Institucion, Redes, "
            "etc.)";
    gotoxy(12, 9);
    cout << "1. Ingresar datos complementarios opcionales";
    gotoxy(12, 10);
    cout << "2. Omitir y continuar al siguiente paso";
    gotoxy(12, 12);
    int opcBasicos = leerEntero("Seleccione opcion [1-2]: ", 1, 2);

    string institucion = "";
    string categoriaInvestigador = "";
    string perfil = "";
    string nombreCitaciones = "";
    string estadoParEvaluador = "";
    string orcid = "";
    string researcherId = "";
    string autorIdScopus = "";
    string googleScholar = "";
    string researchGate = "";
    string academiaEdu = "";
    string mendeley = "";
    string linkedin = "";
    string repositorio = "";

    if (opcBasicos == 1) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== DATOS COMPLEMENTARIOS (OPCIONALES) ===";
      cout << "\n  (Presione ENTER en cualquier campo que desee omitir)\n\n";
      institucion = leerLineaTexto("  Institucion: ", false);
      categoriaInvestigador = leerLineaTexto(
          "  Categoria (Junior, Asociado, Senior, Sin categoria): ", false);
      perfil = leerLineaTexto("  Perfil profesional / Resumen: ", false);
      nombreCitaciones = leerLineaTexto("  Nombre en citaciones: ", false);
      estadoParEvaluador =
          leerLineaTexto("  Estado par evaluador (Si / No): ", false);

      cout << "\n  --- REDES E IDENTIFICADORES ACADEMICOS (OPCIONALES) ---\n";
      orcid = leerLineaTexto("  ORCID: ", false);
      researcherId = leerLineaTexto("  Researcher ID: ", false);
      autorIdScopus = leerLineaTexto("  Autor ID Scopus: ", false);
      googleScholar = leerLineaTexto("  Google Scholar URL: ", false);
      researchGate = leerLineaTexto("  ResearchGate URL: ", false);
      academiaEdu = leerLineaTexto("  Academia.edu URL: ", false);
      mendeley = leerLineaTexto("  Mendeley URL: ", false);
      linkedin = leerLineaTexto("  LinkedIn URL: ", false);
      repositorio = leerLineaTexto("  Repositorio Institucional URL: ", false);
    }

    Investigador *nuevoInv =
        new Investigador(codigoRh, nombre, correo, orcid, institucion,
                         departamento, ciudad, categoriaInvestigador, perfil);

    nuevoInv->nombreCitaciones = nombreCitaciones;
    nuevoInv->nacionalidad = nacionalidad;
    nuevoInv->sexo = sexo;
    nuevoInv->estadoParEvaluador = estadoParEvaluador;
    nuevoInv->researcherId = researcherId;
    nuevoInv->autorIdScopus = autorIdScopus;
    nuevoInv->googleScholar = googleScholar;
    nuevoInv->researchGate = researchGate;
    nuevoInv->academiaEdu = academiaEdu;
    nuevoInv->mendeley = mendeley;
    nuevoInv->linkedin = linkedin;
    nuevoInv->repositorioInstitucional = repositorio;

    // Submenú de datos adicionales (opcionales):
    bool continuarMenu = true;
    bool cancelarTodo = false;
    while (continuarMenu) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== CAMPOS ADICIONALES DEL INVESTIGADOR (OPCIONALES) ===";
      gotoxy(12, 7);
      cout << "Investigador: " << nuevoInv->nombre << " (" << nuevoInv->codigoRh
           << ")";

      gotoxy(12, 9);
      cout << "Estado actual de campos registrados:";
      gotoxy(14, 10);
      cout << "- Productos           : " << nuevoInv->contarProductos();
      gotoxy(14, 11);
      cout << "- Formacion Academica : " << nuevoInv->formacionAcademica.size();
      gotoxy(14, 12);
      cout << "- Experiencia Prof.   : "
           << nuevoInv->experienciaProfesional.size();
      gotoxy(14, 13);
      cout << "- Lineas Investigacion: "
           << nuevoInv->lineasInvestigacion.size();
      gotoxy(50, 10);
      cout << "- Proyectos      : " << nuevoInv->proyectos.size();
      gotoxy(50, 11);
      cout << "- Areas Conoc.   : " << nuevoInv->areasConocimiento.size();
      gotoxy(50, 12);
      cout << "- Reconocimientos: " << nuevoInv->reconocimientos.size();
      gotoxy(50, 13);
      cout << "- Idiomas        : " << nuevoInv->idiomas.size();

      gotoxy(12, 15);
      cout << "1. Agregar Producto de Investigacion";
      gotoxy(12, 16);
      cout << "2. Agregar Formacion Academica";
      gotoxy(12, 17);
      cout << "3. Agregar Experiencia Profesional";
      gotoxy(12, 18);
      cout << "4. Agregar Linea de Investigacion";
      gotoxy(50, 15);
      cout << "5. Agregar Proyecto";
      gotoxy(50, 16);
      cout << "6. Agregar Area de Conocimiento";
      gotoxy(50, 17);
      cout << "7. Agregar Reconocimiento";
      gotoxy(50, 18);
      cout << "8. Agregar Idioma";
      gotoxy(12, 20);
      cout << "9. Finalizar y Guardar Investigador (Omitir restantes)";
      gotoxy(12, 21);
      cout << "0. Cancelar Registro y Descartar";
      gotoxy(12, 23);
      int subOpc = leerEntero("Seleccione una opcion [0-9]: ", 0, 9);

      if (subOpc == 1) {
        stringstream ssId;
        ssId << "INV_" << nuevoInv->codigoRh << "_P"
             << (nuevoInv->contarProductos() + 1);
        ProductoInvestigacion *p =
            crearProductoInteractivo(ssId.str(), nuevoInv->nombre);
        nuevoInv->agregarProducto(p);
      } else if (subOpc == 2) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- AGREGAR FORMACION ACADEMICA ---";
        cout << "\n\n";
        string form = leerLineaTexto("  Descripcion de la formacion (ej: "
                                     "Pregrado en Ingenieria de Sistemas): ",
                                     true);
        nuevoInv->formacionAcademica.push_back(form);
        cout << "\n  [OK] Formacion academica agregada.\n";
        pausar();
      } else if (subOpc == 3) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- AGREGAR EXPERIENCIA PROFESIONAL ---";
        cout << "\n\n";
        string exp = leerLineaTexto("  Descripcion de la experiencia (ej: "
                                    "Docente Catedratico UPC 2020-2025): ",
                                    true);
        nuevoInv->experienciaProfesional.push_back(exp);
        cout << "\n  [OK] Experiencia profesional agregada.\n";
        pausar();
      } else if (subOpc == 4) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- AGREGAR LINEA DE INVESTIGACION ---";
        cout << "\n\n";
        string lin =
            leerLineaTexto("  Nombre de la linea de investigacion: ", true);
        nuevoInv->lineasInvestigacion.push_back(lin);
        cout << "\n  [OK] Linea de investigacion agregada.\n";
        pausar();
      } else if (subOpc == 5) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- AGREGAR PROYECTO ---";
        cout << "\n\n";
        string proy =
            leerLineaTexto("  Nombre / Descripcion del proyecto: ", true);
        nuevoInv->proyectos.push_back(proy);
        cout << "\n  [OK] Proyecto agregado.\n";
        pausar();
      } else if (subOpc == 6) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- AGREGAR AREA DE CONOCIMIENTO ---";
        cout << "\n\n";
        string area =
            leerLineaTexto("  Nombre del area de conocimiento: ", true);
        nuevoInv->areasConocimiento.push_back(area);
        cout << "\n  [OK] Area de conocimiento agregada.\n";
        pausar();
      } else if (subOpc == 7) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- AGREGAR RECONOCIMIENTO ---";
        cout << "\n\n";
        string rec = leerLineaTexto(
            "  Descripcion del reconocimiento o distincion: ", true);
        nuevoInv->reconocimientos.push_back(rec);
        cout << "\n  [OK] Reconocimiento agregado.\n";
        pausar();
      } else if (subOpc == 8) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- AGREGAR IDIOMA ---";
        cout << "\n\n";
        string idi = leerLineaTexto(
            "  Nombre del idioma (ej: Espanol, Ingles, Frances): ", true);
        nuevoInv->idiomas.push_back(idi);
        cout << "\n  [OK] Idioma agregado.\n";
        pausar();
      } else if (subOpc == 9) {
        continuarMenu = false;
      } else if (subOpc == 0) {
        continuarMenu = false;
        cancelarTodo = true;
      }
    }

    if (cancelarTodo) {
      delete nuevoInv;
      dibujarMarco();
      gotoxy(12, 8);
      cout << "Operacion cancelada. El nuevo investigador no fue registrado.";
      pausar();
    } else {
      listasInv.agregar(nuevoInv);
      gestorProductos.consolidar(listasInv, multilistas);

      dibujarMarco();
      gotoxy(12, 6);
      cout << "=== INVESTIGADOR REGISTRADO CON EXITO ===";
      gotoxy(12, 8);
      cout << "Investigador: " << nuevoInv->nombre << " (" << nuevoInv->codigoRh
           << ")";
      gotoxy(12, 10);
      cout << "Incorporado exitosamente a la lista en memoria.";
      gotoxy(12, 12);
      cout << "Catalogo consolidado: " << gestorProductos.obtenerTotalUnicos()
           << " productos netos unicos.";
      gotoxy(12, 14);
      cout << "Para guardar permanentemente en el archivo de texto plano,";
      gotoxy(12, 15);
      cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
              "principal.";
      pausar();
    }
  }

  void eliminarProductoInvestigador(Investigador *inv) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== ELIMINAR PRODUCTO DEL INVESTIGADOR ===";
    cout << "\n\n";

    if (inv->productos == NULL || inv->contarProductos() == 0) {
      cout << "  [!] El investigador no tiene productos asociados para "
              "eliminar.\n\n";
      pausarDinamico();
    } else {
      cout << "  Productos asociados al investigador:\n";
      vector<NodoProducto *> nodos;
      NodoProducto *act = inv->productos;
      int num = 1;
      while (act != NULL) {
        if (act->producto != NULL) {
          nodos.push_back(act);
          cout << "    " << num << ". [" << act->producto->idProducto << "] "
               << act->producto->titulo << " (" << act->producto->categoria
               << ", " << act->producto->anio << ")\n";
          num++;
        }
        act = act->sig;
      }
      cout << "\n";
      string aviso = "  Seleccione el numero de producto a eliminar [1-" +
                     to_string(nodos.size()) + "] (0 para cancelar): ";
      int sel = leerEntero(aviso, 0, static_cast<int>(nodos.size()));
      if (sel > 0) {
        NodoProducto *aEliminar = nodos[sel - 1];
        string tituloEliminado = "";
        if (aEliminar->producto != NULL) {
          tituloEliminado = aEliminar->producto->titulo;
        }

        NodoProducto *anterior = NULL;
        NodoProducto *actual = inv->productos;
        bool eliminado = false;
        while (actual != NULL && !eliminado) {
          if (actual == aEliminar) {
            if (anterior == NULL) {
              inv->productos = actual->sig;
            } else {
              anterior->sig = actual->sig;
            }
            actual->sig = NULL;
            delete actual;
            eliminado = true;
          } else {
            anterior = actual;
            actual = actual->sig;
          }
        }

        if (eliminado) {
          cout << "\n  [OK] Producto '" << tituloEliminado
               << "' eliminado exitosamente del investigador.\n\n";
          gestorProductos.consolidar(listasInv, multilistas);
        }
        pausarDinamico();
      }
    }
  }

  void modificarInvestigador(Investigador *inv) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== MODIFICAR INVESTIGADOR ===";
    gotoxy(12, 7);
    cout << "Paso 1: Modificacion de Datos Basicos Obligatorios";
    cout << "\n\n";

    string codigoAnterior = inv->codigoRh;
    string nuevoCodigo = codigoAnterior;
    bool codigoValido = false;
    while (!codigoValido) {
      string ingCod = leerLineaModificar("  Codigo RH / Identificador unico",
                                         codigoAnterior, true);
      if (ingCod == codigoAnterior) {
        codigoValido = true;
        nuevoCodigo = ingCod;
      } else {
        Investigador *existente = listasInv.buscar(ingCod);
        if (existente != NULL) {
          cout << "  [!] Ya existe otro investigador con el codigo '" << ingCod
               << "': " << existente->nombre << ".\n";
          cout << "  Por favor ingrese un codigo identificador diferente.\n";
        } else {
          codigoValido = true;
          nuevoCodigo = ingCod;
        }
      }
    }
    inv->codigoRh = nuevoCodigo;

    inv->nombre = leerLineaModificar("  Nombre completo del investigador",
                                     inv->nombre, true);
    inv->correo = leerLineaModificar("  Correo electronico", inv->correo, true);
    inv->sexo = leerLineaModificar("  Sexo", inv->sexo, true);
    inv->nacionalidad =
        leerLineaModificar("  Nacionalidad", inv->nacionalidad, true);
    inv->departamento =
        leerLineaModificar("  Departamento", inv->departamento, true);
    inv->ciudad = leerLineaModificar("  Ciudad", inv->ciudad, true);

    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== MODIFICAR INVESTIGADOR ===";
    gotoxy(12, 7);
    cout << "Paso 2: Datos Complementarios Opcionales (Institucion, Redes, "
            "etc.)";
    gotoxy(12, 9);
    cout << "1. Modificar datos complementarios opcionales";
    gotoxy(12, 10);
    cout << "2. Conservar actuales y continuar al siguiente paso";
    gotoxy(12, 12);
    int opcComp = leerEntero("Seleccione opcion [1-2]: ", 1, 2);

    if (opcComp == 1) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== MODIFICAR DATOS COMPLEMENTARIOS ===";
      cout << "\n\n";
      inv->institucion =
          leerLineaModificar("  Institucion", inv->institucion, false);
      inv->categoriaInvestigador = leerLineaModificar(
          "  Categoria (Junior, Asociado, Senior, Sin categoria)",
          inv->categoriaInvestigador, false);
      inv->perfil = leerLineaModificar("  Perfil profesional / Resumen",
                                       inv->perfil, false);
      inv->nombreCitaciones = leerLineaModificar("  Nombre en citaciones",
                                                 inv->nombreCitaciones, false);
      inv->estadoParEvaluador = leerLineaModificar(
          "  Estado par evaluador (Si / No)", inv->estadoParEvaluador, false);

      cout << "\n  --- REDES E IDENTIFICADORES ACADEMICOS ---\n\n";
      inv->orcid = leerLineaModificar("  ORCID", inv->orcid, false);
      inv->researcherId =
          leerLineaModificar("  Researcher ID", inv->researcherId, false);
      inv->autorIdScopus =
          leerLineaModificar("  Autor ID Scopus", inv->autorIdScopus, false);
      inv->googleScholar =
          leerLineaModificar("  Google Scholar URL", inv->googleScholar, false);
      inv->researchGate =
          leerLineaModificar("  ResearchGate URL", inv->researchGate, false);
      inv->academiaEdu =
          leerLineaModificar("  Academia.edu URL", inv->academiaEdu, false);
      inv->mendeley =
          leerLineaModificar("  Mendeley URL", inv->mendeley, false);
      inv->linkedin =
          leerLineaModificar("  LinkedIn URL", inv->linkedin, false);
      inv->repositorioInstitucional =
          leerLineaModificar("  Repositorio Institucional URL",
                             inv->repositorioInstitucional, false);
    }

    // Paso 3: Submenú de datos adicionales (Agregar y Eliminar elementos
    // específicos)
    bool continuarMenu = true;
    while (continuarMenu) {
      dibujarMarco();
      gotoxy(10, 5);
      cout << "=== MODIFICAR ELEMENTOS Y COLECCIONES (INVESTIGADOR) ===";
      gotoxy(10, 6);
      cout << "Investigador: " << inv->nombre << " (" << inv->codigoRh << ")";

      gotoxy(10, 8);
      cout << "Estado actual de campos registrados:";
      gotoxy(12, 9);
      cout << "- Productos           : " << inv->contarProductos();
      gotoxy(12, 10);
      cout << "- Formacion Academica : " << inv->formacionAcademica.size();
      gotoxy(12, 11);
      cout << "- Experiencia Prof.   : " << inv->experienciaProfesional.size();
      gotoxy(12, 12);
      cout << "- Lineas Investigacion: " << inv->lineasInvestigacion.size();
      gotoxy(46, 9);
      cout << "- Proyectos      : " << inv->proyectos.size();
      gotoxy(46, 10);
      cout << "- Areas Conoc.   : " << inv->areasConocimiento.size();
      gotoxy(46, 11);
      cout << "- Reconocimientos: " << inv->reconocimientos.size();
      gotoxy(46, 12);
      cout << "- Idiomas        : " << inv->idiomas.size();

      gotoxy(10, 14);
      cout << "1. Gestionar Productos de Investigacion (Agregar / Eliminar)";
      gotoxy(10, 15);
      cout << "2. Gestionar Formacion Academica (Agregar / Eliminar)";
      gotoxy(10, 16);
      cout << "3. Gestionar Experiencia Profesional (Agregar / Eliminar)";
      gotoxy(10, 17);
      cout << "4. Gestionar Lineas de Investigacion (Agregar / Eliminar)";
      gotoxy(10, 18);
      cout << "5. Gestionar Proyectos (Agregar / Eliminar)";
      gotoxy(10, 19);
      cout << "6. Gestionar Areas de Conocimiento (Agregar / Eliminar)";
      gotoxy(10, 20);
      cout << "7. Gestionar Reconocimientos (Agregar / Eliminar)";
      gotoxy(10, 21);
      cout << "8. Gestionar Idiomas (Agregar / Eliminar)";
      gotoxy(10, 22);
      cout << "9. Finalizar y Guardar Modificaciones";
      gotoxy(10, 23);
      int subOpc = leerEntero("Seleccione una opcion [1-9]: ", 1, 9);

      if (subOpc == 1) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- GESTION DE PRODUCTOS DE INVESTIGACION ---";
        gotoxy(12, 7);
        cout << "Productos actuales: " << inv->contarProductos();
        gotoxy(12, 9);
        cout << "1. Agregar Producto";
        gotoxy(12, 10);
        cout << "2. Eliminar Producto";
        gotoxy(12, 11);
        cout << "0. Regresar";
        gotoxy(12, 13);
        int opcProd = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
        if (opcProd == 1) {
          stringstream ssId;
          ssId << "INV_" << inv->codigoRh << "_P"
               << (inv->contarProductos() + 1);
          ProductoInvestigacion *p =
              crearProductoInteractivo(ssId.str(), inv->nombre);
          inv->agregarProducto(p);
          gestorProductos.consolidar(listasInv, multilistas);
        } else if (opcProd == 2) {
          eliminarProductoInvestigador(inv);
        }
      } else if (subOpc == 2) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- GESTION DE FORMACION ACADEMICA ---";
        gotoxy(12, 7);
        cout << "Registros actuales: " << inv->formacionAcademica.size();
        gotoxy(12, 9);
        cout << "1. Agregar Formacion Academica";
        gotoxy(12, 10);
        cout << "2. Eliminar Formacion Academica";
        gotoxy(12, 11);
        cout << "0. Regresar";
        gotoxy(12, 13);
        int opcForm = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
        if (opcForm == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR FORMACION ACADEMICA ---";
          cout << "\n\n";
          string form = leerLineaTexto("  Descripcion de la formacion (ej: "
                                       "Pregrado en Ingenieria de Sistemas): ",
                                       true);
          inv->formacionAcademica.push_back(form);
          cout << "\n  [OK] Formacion academica agregada.\n";
          pausar();
        } else if (opcForm == 2) {
          eliminarElementoColeccion("FORMACION ACADEMICA",
                                    inv->formacionAcademica);
        }
      } else if (subOpc == 3) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- GESTION DE EXPERIENCIA PROFESIONAL ---";
        gotoxy(12, 7);
        cout << "Registros actuales: " << inv->experienciaProfesional.size();
        gotoxy(12, 9);
        cout << "1. Agregar Experiencia Profesional";
        gotoxy(12, 10);
        cout << "2. Eliminar Experiencia Profesional";
        gotoxy(12, 11);
        cout << "0. Regresar";
        gotoxy(12, 13);
        int opcExp = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
        if (opcExp == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR EXPERIENCIA PROFESIONAL ---";
          cout << "\n\n";
          string exp = leerLineaTexto("  Descripcion de la experiencia (ej: "
                                      "Docente Catedratico UPC 2020-2025): ",
                                      true);
          inv->experienciaProfesional.push_back(exp);
          cout << "\n  [OK] Experiencia profesional agregada.\n";
          pausar();
        } else if (opcExp == 2) {
          eliminarElementoColeccion("EXPERIENCIA PROFESIONAL",
                                    inv->experienciaProfesional);
        }
      } else if (subOpc == 4) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- GESTION DE LINEAS DE INVESTIGACION ---";
        gotoxy(12, 7);
        cout << "Registros actuales: " << inv->lineasInvestigacion.size();
        gotoxy(12, 9);
        cout << "1. Agregar Linea de Investigacion";
        gotoxy(12, 10);
        cout << "2. Eliminar Linea de Investigacion";
        gotoxy(12, 11);
        cout << "0. Regresar";
        gotoxy(12, 13);
        int opcLin = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
        if (opcLin == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR LINEA DE INVESTIGACION ---";
          cout << "\n\n";
          string lin =
              leerLineaTexto("  Nombre de la linea de investigacion: ", true);
          inv->lineasInvestigacion.push_back(lin);
          cout << "\n  [OK] Linea de investigacion agregada.\n";
          pausar();
        } else if (opcLin == 2) {
          eliminarElementoColeccion("LINEAS DE INVESTIGACION",
                                    inv->lineasInvestigacion);
        }
      } else if (subOpc == 5) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- GESTION DE PROYECTOS ---";
        gotoxy(12, 7);
        cout << "Registros actuales: " << inv->proyectos.size();
        gotoxy(12, 9);
        cout << "1. Agregar Proyecto";
        gotoxy(12, 10);
        cout << "2. Eliminar Proyecto";
        gotoxy(12, 11);
        cout << "0. Regresar";
        gotoxy(12, 13);
        int opcProy = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
        if (opcProy == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR PROYECTO ---";
          cout << "\n\n";
          string proy =
              leerLineaTexto("  Nombre / Descripcion del proyecto: ", true);
          inv->proyectos.push_back(proy);
          cout << "\n  [OK] Proyecto agregado.\n";
          pausar();
        } else if (opcProy == 2) {
          eliminarElementoColeccion("PROYECTOS", inv->proyectos);
        }
      } else if (subOpc == 6) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- GESTION DE AREAS DE CONOCIMIENTO ---";
        gotoxy(12, 7);
        cout << "Registros actuales: " << inv->areasConocimiento.size();
        gotoxy(12, 9);
        cout << "1. Agregar Area de Conocimiento";
        gotoxy(12, 10);
        cout << "2. Eliminar Area de Conocimiento";
        gotoxy(12, 11);
        cout << "0. Regresar";
        gotoxy(12, 13);
        int opcArea = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
        if (opcArea == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR AREA DE CONOCIMIENTO ---";
          cout << "\n\n";
          string area =
              leerLineaTexto("  Nombre del area de conocimiento: ", true);
          inv->areasConocimiento.push_back(area);
          cout << "\n  [OK] Area de conocimiento agregada.\n";
          pausar();
        } else if (opcArea == 2) {
          eliminarElementoColeccion("AREAS DE CONOCIMIENTO",
                                    inv->areasConocimiento);
        }
      } else if (subOpc == 7) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- GESTION DE RECONOCIMIENTOS ---";
        gotoxy(12, 7);
        cout << "Registros actuales: " << inv->reconocimientos.size();
        gotoxy(12, 9);
        cout << "1. Agregar Reconocimiento";
        gotoxy(12, 10);
        cout << "2. Eliminar Reconocimiento";
        gotoxy(12, 11);
        cout << "0. Regresar";
        gotoxy(12, 13);
        int opcRec = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
        if (opcRec == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR RECONOCIMIENTO ---";
          cout << "\n\n";
          string rec = leerLineaTexto(
              "  Descripcion del reconocimiento o distincion: ", true);
          inv->reconocimientos.push_back(rec);
          cout << "\n  [OK] Reconocimiento agregado.\n";
          pausar();
        } else if (opcRec == 2) {
          eliminarElementoColeccion("RECONOCIMIENTOS", inv->reconocimientos);
        }
      } else if (subOpc == 8) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- GESTION DE IDIOMAS ---";
        gotoxy(12, 7);
        cout << "Registros actuales: " << inv->idiomas.size();
        gotoxy(12, 9);
        cout << "1. Agregar Idioma";
        gotoxy(12, 10);
        cout << "2. Eliminar Idioma";
        gotoxy(12, 11);
        cout << "0. Regresar";
        gotoxy(12, 13);
        int opcIdi = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
        if (opcIdi == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR IDIOMA ---";
          cout << "\n\n";
          string idi = leerLineaTexto(
              "  Nombre del idioma (ej: Espanol, Ingles, Frances): ", true);
          inv->idiomas.push_back(idi);
          cout << "\n  [OK] Idioma agregado.\n";
          pausar();
        } else if (opcIdi == 2) {
          eliminarElementoColeccion("IDIOMAS", inv->idiomas);
        }
      } else if (subOpc == 9) {
        continuarMenu = false;
      }
    }

    gestorProductos.consolidar(listasInv, multilistas);

    dibujarMarco();
    gotoxy(12, 6);
    cout << "=== INVESTIGADOR MODIFICADO CON EXITO ===";
    gotoxy(12, 8);
    cout << "Investigador: " << inv->nombre << " (" << inv->codigoRh << ")";
    gotoxy(12, 10);
    cout << "Datos actualizados exitosamente en la memoria del sistema.";
    gotoxy(12, 12);
    cout << "Catalogo consolidado: " << gestorProductos.obtenerTotalUnicos()
         << " productos netos unicos.";
    gotoxy(12, 14);
    cout << "Para guardar permanentemente en el archivo de texto plano,";
    gotoxy(12, 15);
    cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
            "principal.";
    pausar();
  }

  void modificarInvestigadorConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== MODIFICAR INVESTIGADOR ===";

    NodoInvestigador *act = listasInv.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay investigadores registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Investigadores disponibles para modificar:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->investigador->codigoRh);
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->investigador->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->investigador->nombre
             << " (" << act->investigador->codigoRh << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->investigador->codigoRh);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el codigo RH a "
                         "modificar (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit(entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        Investigador *inv = listasInv.buscar(codigoSel);
        if (inv != NULL) {
          modificarInvestigador(inv);
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "No se encontro ningun investigador con el codigo/numero: "
               << entrada;
          pausar();
        }
      }
    }
  }

  void eliminarInvestigadorConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== ELIMINAR INVESTIGADOR (DELETE) ===";

    NodoInvestigador *act = listasInv.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay investigadores registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Investigadores disponibles para eliminar:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->investigador->codigoRh);
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->investigador->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->investigador->nombre
             << " (" << act->investigador->codigoRh << ") ["
             << act->investigador->contarProductos() << " prods]";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->investigador->codigoRh);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el codigo RH a "
                         "eliminar (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit(entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        Investigador *inv = listasInv.buscar(codigoSel);
        if (inv != NULL) {
          string nombreInv = inv->nombre;
          string codigoInv = inv->codigoRh;
          int prods = inv->contarProductos();

          dibujarMarco();
          gotoxy(12, 6);
          cout << "=== CONFIRMACION DE ELIMINACION DE INVESTIGADOR ===";
          gotoxy(12, 8);
          cout << "Investigador a eliminar  : " << nombreInv << " ("
               << codigoInv << ")";
          gotoxy(12, 9);
          cout << "Total productos asociados: " << prods;
          gotoxy(12, 11);
          cout << "[!] ADVERTENCIA: Esta accion eliminara permanentemente";
          gotoxy(12, 12);
          cout << "    al investigador y todos sus datos asociados.";
          gotoxy(12, 14);
          cout << "1. Confirmar eliminacion definitiva";
          gotoxy(12, 15);
          cout << "2. Cancelar operacion";
          gotoxy(12, 17);
          int opcConf = leerEntero("Seleccione opcion [1-2]: ", 1, 2);

          if (opcConf == 1) {
            bool eliminado = listasInv.eliminar(codigoInv);
            if (eliminado) {
              NodoGrupo *gAct = multilistas.getCabeza();
              while (gAct != NULL) {
                NodoInvestigador *antI = NULL;
                NodoInvestigador *curI = gAct->hijoIntegrantes;
                bool found = false;
                while (curI != NULL && !found) {
                  if (curI->investigador != NULL &&
                      curI->investigador->codigoRh == codigoInv) {
                    if (antI == NULL) {
                      gAct->hijoIntegrantes = curI->sig;
                    } else {
                      antI->sig = curI->sig;
                    }
                    if (curI->sig != NULL) {
                      curI->sig->ant = antI;
                    }
                    curI->sig = NULL;
                    curI->ant = NULL;
                    delete curI;
                    found = true;
                  } else {
                    antI = curI;
                    curI = curI->sig;
                  }
                }
                gAct = gAct->sig;
              }

              gestorProductos.consolidar(listasInv, multilistas);

              dibujarMarco();
              gotoxy(12, 6);
              cout << "=== INVESTIGADOR ELIMINADO CON EXITO (DELETE) ===";
              gotoxy(12, 8);
              cout << "Investigador: " << nombreInv << " (" << codigoInv << ")";
              gotoxy(12, 10);
              cout << "Eliminado completamente de la memoria del sistema.";
              gotoxy(12, 12);
              cout << "Catalogo consolidado actualizado: "
                   << gestorProductos.obtenerTotalUnicos()
                   << " productos netos unicos.";
              gotoxy(12, 14);
              cout << "Para guardar permanentemente en el archivo de texto plano,";
              gotoxy(12, 15);
              cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
                      "principal.";
              pausar();
            } else {
              dibujarMarco();
              gotoxy(12, 8);
              cout << "Error al intentar eliminar el investigador.";
              pausar();
            }
          } else {
            dibujarMarco();
            gotoxy(12, 8);
            cout << "Operacion cancelada. El investigador no fue eliminado.";
            pausar();
          }
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "No se encontro ningun investigador con el codigo/numero: "
               << entrada;
          pausar();
        }
      }
    }
  }

  void alternarEstadoInvestigadorConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== ACTIVAR / DESACTIVAR INVESTIGADOR ===";

    NodoInvestigador *act = listasInv.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay investigadores registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Investigadores registrados:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->investigador->codigoRh);
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->investigador->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->investigador->nombre
             << " (" << act->investigador->codigoRh << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->investigador->codigoRh);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el codigo RH del "
                         "investigador (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit(entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        Investigador *inv = listasInv.buscar(codigoSel);
        dibujarMarco();
        if (inv != NULL) {
          listasInv.alternarEstado(codigoSel);
          gotoxy(12, 7);
          cout << "=== CAMBIO DE ESTADO REALIZADO ===";
          gotoxy(12, 9);
          cout << "Investigador : " << inv->nombre;
          gotoxy(12, 10);
          cout << "Codigo RH    : " << inv->codigoRh;
          gotoxy(12, 11);
          if (inv->activo) {
            cout << "Nuevo Estado : ACTIVO (Habilitado en el sistema)";
          } else {
            cout << "Nuevo Estado : INACTIVO (Deshabilitado en el sistema)";
          }
          gotoxy(12, 13);
          cout << "Para guardar permanentemente en el archivo de texto plano,";
          gotoxy(12, 14);
          cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
                  "principal.";
        } else {
          gotoxy(12, 8);
          cout << "No se encontro ningun investigador con el codigo/numero: "
               << entrada;
        }
        pausar();
      }
    }
  }

  void mostrarInfoBasicaInvestigador(Investigador *inv) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== INFORMACION BASICA DEL INVESTIGADOR ===";
    cout << "\n\n";

    string estadoTxt = "ACTIVO (Habilitado en el sistema)";
    if (!inv->activo) {
      estadoTxt = "INACTIVO (Deshabilitado en el sistema)";
    }

    cout << "  Nombre Completo          : "
         << valorOCadena(inv->nombre, "No registrado") << "\n";
    cout << "  Codigo RH                : "
         << valorOCadena(inv->codigoRh, "No registrado") << "\n";
    cout << "  Estado en el Sistema     : " << estadoTxt << "\n";
    cout << "  Correo Electronico       : "
         << valorOCadena(inv->correo, "No registrado") << "\n";
    cout << "  Categoria MinCiencias    : "
         << valorOCadena(inv->categoriaInvestigador, "No registrada") << "\n";
    cout << "  Institucion Principal    : "
         << valorOCadena(inv->institucion, "No registrada") << "\n";
    cout << "  Ubicacion Geografica     : "
         << valorOCadena(inv->departamento, "N/D") << " - "
         << valorOCadena(inv->ciudad, "N/D") << "\n";
    cout << "  Nacionalidad             : "
         << valorOCadena(inv->nacionalidad, "No registrada") << "\n";
    cout << "  Sexo                     : "
         << valorOCadena(inv->sexo, "No registrado") << "\n";
    cout << "  Estado Par Evaluador     : "
         << valorOCadena(inv->estadoParEvaluador, "No registrado") << "\n";
    cout << "  Nombre en Citaciones     : "
         << valorOCadena(inv->nombreCitaciones, "No registrado") << "\n";
    cout << "  ORCID                    : "
         << valorOCadena(inv->orcid, "No registrado") << "\n";
    cout << "  Perfil / Biografia       : "
         << valorOCadena(inv->perfil, "No registrado") << "\n";

    cout << "\n  --- IDENTIFICADORES Y ENLACES ACADEMICOS ---\n";
    cout << "  ResearcherID             : "
         << valorOCadena(inv->researcherId, "No registrado") << "\n";
    cout << "  Scopus Author ID         : "
         << valorOCadena(inv->autorIdScopus, "No registrado") << "\n";
    cout << "  Google Scholar           : "
         << valorOCadena(inv->googleScholar, "No registrado") << "\n";
    cout << "  ResearchGate             : "
         << valorOCadena(inv->researchGate, "No registrado") << "\n";
    cout << "  Academia.edu             : "
         << valorOCadena(inv->academiaEdu, "No registrado") << "\n";
    cout << "  Mendeley                 : "
         << valorOCadena(inv->mendeley, "No registrado") << "\n";
    cout << "  LinkedIn                 : "
         << valorOCadena(inv->linkedin, "No registrado") << "\n";
    cout << "  Repositorio Institucional: "
         << valorOCadena(inv->repositorioInstitucional, "No registrado")
         << "\n\n";

    pausarDinamico();
  }

  void mostrarListaColeccion(const string &titulo,
                             const vector<string> &elementos,
                             const string &nombreSeccion) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== " << titulo << " ===";
    cout << "\n\n";

    if (elementos.empty()) {
      cout << "  [!] No hay datos registrados para mostrar en " << nombreSeccion
           << ".\n\n";
    } else {
      cout << "  Total de registros encontrados: " << elementos.size()
           << "\n\n";
      size_t i = 0;
      bool salirEsc = false;
      while (i < elementos.size() && !salirEsc) {
        cout << "  " << (i + 1) << ". " << elementos[i] << "\n";
        i++;
        if (i % 12 == 0 && i < elementos.size()) {
          cout << "\n";
          bool continua = esperarTeclaPaginacion(false);
          if (!continua) {
            salirEsc = true;
          } else {
            dibujarMarco();
            gotoxy(12, 5);
            cout << "=== " << titulo << " (Continuacion) ===";
            cout << "\n\n";
          }
        }
      }
      cout << "\n";
    }
    pausarDinamico();
  }

  void mostrarProductosPorCategoriaInvestigador(Investigador *inv) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== LISTA DE PRODUCTOS POR CATEGORIAS ===";
    cout << "\n\n";

    if (inv->productos == NULL || inv->contarProductos() == 0) {
      cout << "  [!] No hay datos registrados para mostrar en productos (el "
              "investigador no posee productos asociados).\n\n";
      pausarDinamico();
    } else {
      vector<string> categorias;
      NodoProducto *actP = inv->productos;
      while (actP != NULL) {
        if (actP->producto != NULL) {
          string cat = actP->producto->categoria;
          if (cat.empty()) {
            cat = "Sin categoria";
          }
          bool yaExiste = false;
          size_t cIdx = 0;
          while (cIdx < categorias.size() && !yaExiste) {
            if (categorias[cIdx] == cat) {
              yaExiste = true;
            }
            cIdx++;
          }
          if (!yaExiste) {
            categorias.push_back(cat);
          }
        }
        actP = actP->sig;
      }

      cout << "  Investigador             : " << inv->nombre << " ("
           << inv->codigoRh << ")\n";
      cout << "  Total global de productos: " << inv->contarProductos() << "\n";
      cout << "  Categorias representadas : " << categorias.size() << "\n\n";

      size_t c = 0;
      int lineasPantalla = 6;
      const int LIMITE_LINEAS = 18;
      bool salirEsc = false;

      while (c < categorias.size() && !salirEsc) {
        string catActual = categorias[c];

        if (lineasPantalla + 3 > LIMITE_LINEAS) {
          cout << "\n";
          bool continua = esperarTeclaPaginacion(false);
          if (!continua) {
            salirEsc = true;
          } else {
            dibujarMarco();
            gotoxy(12, 5);
            cout << "=== LISTA DE PRODUCTOS POR CATEGORIAS (Continuacion) ===";
            cout << "\n\n";
            lineasPantalla = 0;
          }
        }

        if (!salirEsc) {
          cout << "  "
                  "============================================================"
                  "\n";
          cout << "  CATEGORIA: " << catActual << "\n";
          cout << "  "
                  "============================================================"
                  "\n";
          lineasPantalla += 3;

          NodoProducto *pCurr = inv->productos;
          int numProdEnCat = 1;
          while (pCurr != NULL && !salirEsc) {
            if (pCurr->producto != NULL) {
              string pCat = pCurr->producto->categoria;
              if (pCat.empty()) {
                pCat = "Sin categoria";
              }
              if (pCat == catActual) {
                ProductoInvestigacion *p = pCurr->producto;

                int lineasItem = 3;
                if (!p->doi.empty()) {
                  lineasItem++;
                }
                if (!p->isbn.empty()) {
                  lineasItem++;
                }
                if (!p->revista.empty()) {
                  lineasItem++;
                }
                if (!p->editorial.empty()) {
                  lineasItem++;
                }
                if (!p->autores.empty()) {
                  lineasItem++;
                }

                if (lineasPantalla + lineasItem > LIMITE_LINEAS) {
                  cout << "\n";
                  bool continua = esperarTeclaPaginacion(false);
                  if (!continua) {
                    salirEsc = true;
                  } else {
                    dibujarMarco();
                    gotoxy(12, 5);
                    cout << "=== PRODUCTOS (Continuacion) - Categoria: "
                         << catActual << " ===";
                    cout << "\n\n";
                    lineasPantalla = 0;
                  }
                }

                if (!salirEsc) {
                  cout << "   " << numProdEnCat << ". [" << p->idProducto
                       << "] " << p->titulo << "\n";
                  cout << "      Anio: " << p->anio;
                  if (!p->subtipo.empty()) {
                    cout << " | Subtipo: " << p->subtipo;
                  }
                  if (p->validado) {
                    cout << " | MinCiencias: VALIDADO";
                  } else {
                    cout << " | MinCiencias: NO VALIDADO";
                  }
                  cout << "\n";
                  if (!p->doi.empty()) {
                    cout << "      DOI: " << p->doi << "\n";
                  }
                  if (!p->isbn.empty()) {
                    cout << "      ISBN: " << p->isbn << "\n";
                  }
                  if (!p->revista.empty()) {
                    cout << "      Revista: " << p->revista << "\n";
                  }
                  if (!p->editorial.empty()) {
                    cout << "      Editorial: " << p->editorial << "\n";
                  }
                  if (!p->autores.empty()) {
                    cout << "      Autores: ";
                    size_t aIdx = 0;
                    while (aIdx < p->autores.size()) {
                      cout << p->autores[aIdx];
                      if (aIdx + 1 < p->autores.size()) {
                        cout << ", ";
                      }
                      aIdx++;
                    }
                    cout << "\n";
                  }
                  cout << "\n";
                  lineasPantalla += lineasItem;
                  numProdEnCat++;
                }
              }
            }
            pCurr = pCurr->sig;
          }
          c++;
        }
      }

      if (!salirEsc) {
        cout << "\n";
        esperarTeclaPaginacion(true);
      }
    }
  }

  void mostrarProduccionPorAnioInvestigador(Investigador *inv) {
    if (inv == NULL) {
      dibujarMarco();
      gotoxy(12, 6);
      cout << "Investigador no valido.";
      pausar();
    } else {
      bool salir = false;
      while (!salir) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "=== LISTA DE PRODUCCION POR ANIO (INVESTIGADOR) ===";
        cout << "\n\n";
        cout << "  Investigador: " << inv->nombre << " (" << inv->codigoRh
             << ")\n";
        cout << "  Total productos asociados: " << inv->contarProductos()
             << "\n\n";

        if (inv->productos == NULL || inv->contarProductos() == 0) {
          cout << "  [!] El investigador no tiene productos registrados.\n\n";
          pausarDinamico();
          salir = true;
        } else {
          vector<int> anios;
          vector<int> conteos;

          NodoProducto *actP = inv->productos;
          while (actP != NULL) {
            if (actP->producto != NULL) {
              int anio = actP->producto->anio;
              bool yaExiste = false;
              size_t aIdx = 0;
              while (aIdx < anios.size() && !yaExiste) {
                if (anios[aIdx] == anio) {
                  yaExiste = true;
                  conteos[aIdx]++;
                }
                aIdx++;
              }
              if (!yaExiste) {
                anios.push_back(anio);
                conteos.push_back(1);
              }
            }
            actP = actP->sig;
          }

          size_t s1 = 0;
          while (s1 < anios.size()) {
            size_t s2 = s1 + 1;
            while (s2 < anios.size()) {
              if (anios[s1] > anios[s2]) {
                int tA = anios[s1];
                anios[s1] = anios[s2];
                anios[s2] = tA;
                int tC = conteos[s1];
                conteos[s1] = conteos[s2];
                conteos[s2] = tC;
              }
              s2++;
            }
            s1++;
          }

          cout << "  +--------+-----------------------+\n";
          cout << "  |  Anio  | Cantidad de Productos |\n";
          cout << "  +--------+-----------------------+\n";
          size_t idx = 0;
          int totalProd = 0;
          while (idx < anios.size()) {
            string anioTxt = to_string(anios[idx]);
            if (anios[idx] <= 1000) {
              anioTxt = "Sin anio";
            }
            cout << "  | " << right << setw(6) << anioTxt << " | "
                 << right << setw(21) << conteos[idx] << " |\n";
            totalProd += conteos[idx];
            idx++;
          }
          cout << "  +--------+-----------------------+\n";
          cout << "  | TOTAL  | " << right << setw(21) << totalProd << " |\n";
          cout << "  +--------+-----------------------+\n\n";

          cout << "  1. Consultar cantidad de productos en un periodo de tiempo especifico (Rango de anios)\n";
          cout << "  2. Regresar\n\n";
          int opc = leerEntero("  Seleccione una opcion [1-2]: ", 1, 2);

          if (opc == 1) {
            cout << "\n";
            int aIni = leerEntero("  Ingrese anio inicial: ", 1900, 2100);
            int aFin = leerEntero("  Ingrese anio final  : ", 1900, 2100);
            if (aIni > aFin) {
              int t = aIni;
              aIni = aFin;
              aFin = t;
            }

            int conteoPeriodo = 0;
            vector<int> aniosP;
            vector<int> conteosP;

            size_t cIdx = 0;
            while (cIdx < anios.size()) {
              if (anios[cIdx] >= aIni && anios[cIdx] <= aFin) {
                aniosP.push_back(anios[cIdx]);
                conteosP.push_back(conteos[cIdx]);
                conteoPeriodo += conteos[cIdx];
              }
              cIdx++;
            }

            cout << "\n  ==============================================================\n";
            cout << "  CONTEO TOTAL EN EL PERIODO ESPECIFICADO\n";
            cout << "  Periodo consultado           : " << aIni << " - " << aFin
                 << "\n";
            cout << "  Total de productos publicados: " << conteoPeriodo
                 << " producto(s)\n";
            cout << "  ==============================================================\n\n";

            if (aniosP.empty()) {
              cout << "  No se registraron productos publicados dentro del periodo "
                   << aIni << " - " << aFin << ".\n\n";
            } else {
              cout << "  Detalle de produccion dentro del periodo:\n";
              cout << "  +--------+-----------------------+\n";
              cout << "  |  Anio  | Cantidad de Productos |\n";
              cout << "  +--------+-----------------------+\n";
              size_t p = 0;
              while (p < aniosP.size()) {
                cout << "  | " << right << setw(6) << aniosP[p] << " | "
                     << right << setw(21) << conteosP[p] << " |\n";
                p++;
              }
              cout << "  +--------+-----------------------+\n";
              cout << "  | TOTAL  | " << right << setw(21) << conteoPeriodo
                   << " |\n";
              cout << "  +--------+-----------------------+\n\n";
            }
            pausarDinamico();
          } else if (opc == 2) {
            salir = true;
          }
        }
      }
    }
  }

  void menuDetalleInvestigador(Investigador *inv) {
    int subOpcion = 0;
    while (subOpcion != 13) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== CONSULTA DETALLADA DE INVESTIGADOR ===";
      gotoxy(12, 6);
      cout << "Investigador: " << inv->nombre << " (" << inv->codigoRh << ")";
      gotoxy(14, 8);
      cout << "1. Informacion Basica";
      gotoxy(14, 9);
      cout << "2. Lista de Productos por Categorias";
      gotoxy(14, 10);
      cout << "3. Lista de Produccion por Anio";
      gotoxy(14, 11);
      cout << "4. Formacion Academica";
      gotoxy(14, 12);
      cout << "5. Experiencia Profesional";
      gotoxy(14, 13);
      cout << "6. Lineas de Investigacion";
      gotoxy(14, 14);
      cout << "7. Proyectos";
      gotoxy(14, 15);
      cout << "8. Areas de Conocimiento";
      gotoxy(14, 16);
      cout << "9. Reconocimientos";
      gotoxy(14, 17);
      cout << "10. Idiomas";
      gotoxy(14, 18);
      cout << "11. Modificar Investigador";
      gotoxy(14, 19);
      cout << "12. Eliminar Investigador";
      gotoxy(14, 20);
      cout << "13. Regresar";
      gotoxy(14, 22);
      cout << "Seleccione una opcion [1-13]: ";

      cin >> subOpcion;
      if (cin.fail()) {
        cin.clear();
        cin.ignore(10000, '\n');
        subOpcion = 0;
      } else {
        cin.ignore(10000, '\n');
      }

      if (subOpcion == 1) {
        mostrarInfoBasicaInvestigador(inv);
      } else if (subOpcion == 2) {
        mostrarProductosPorCategoriaInvestigador(inv);
      } else if (subOpcion == 3) {
        mostrarProduccionPorAnioInvestigador(inv);
      } else if (subOpcion == 4) {
        mostrarListaColeccion("FORMACION ACADEMICA", inv->formacionAcademica,
                              "formacion academica");
      } else if (subOpcion == 5) {
        mostrarListaColeccion("EXPERIENCIA PROFESIONAL",
                              inv->experienciaProfesional,
                              "experiencia profesional");
      } else if (subOpcion == 6) {
        mostrarListaColeccion("LINEAS DE INVESTIGACION",
                              inv->lineasInvestigacion,
                              "lineas de investigacion");
      } else if (subOpcion == 7) {
        mostrarListaColeccion("PROYECTOS DE INVESTIGACION", inv->proyectos,
                              "proyectos");
      } else if (subOpcion == 8) {
        mostrarListaColeccion("AREAS DE CONOCIMIENTO", inv->areasConocimiento,
                              "areas de conocimiento");
      } else if (subOpcion == 9) {
        mostrarListaColeccion("RECONOCIMIENTOS Y PREMIOS", inv->reconocimientos,
                              "reconocimientos");
      } else if (subOpcion == 10) {
        mostrarListaColeccion("IDIOMAS", inv->idiomas, "idiomas");
      } else if (subOpcion == 11) {
        modificarInvestigador(inv);
      } else if (subOpcion == 12) {
        string nombreInv = inv->nombre;
        string codigoInv = inv->codigoRh;
        int prods = inv->contarProductos();

        dibujarMarco();
        gotoxy(12, 6);
        cout << "=== CONFIRMACION DE ELIMINACION DE INVESTIGADOR ===";
        gotoxy(12, 8);
        cout << "Investigador a eliminar  : " << nombreInv << " ("
             << codigoInv << ")";
        gotoxy(12, 9);
        cout << "Total productos asociados: " << prods;
        gotoxy(12, 11);
        cout << "[!] ADVERTENCIA: Esta accion eliminara permanentemente";
        gotoxy(12, 12);
        cout << "    al investigador y todos sus datos asociados.";
        gotoxy(12, 14);
        cout << "1. Confirmar eliminacion definitiva";
        gotoxy(12, 15);
        cout << "2. Cancelar operacion";
        gotoxy(12, 17);
        int opcConf = leerEntero("Seleccione opcion [1-2]: ", 1, 2);

        if (opcConf == 1) {
          bool eliminado = listasInv.eliminar(codigoInv);
          if (eliminado) {
            NodoGrupo *gAct = multilistas.getCabeza();
            while (gAct != NULL) {
              NodoInvestigador *antI = NULL;
              NodoInvestigador *curI = gAct->hijoIntegrantes;
              bool found = false;
              while (curI != NULL && !found) {
                if (curI->investigador != NULL &&
                    curI->investigador->codigoRh == codigoInv) {
                  if (antI == NULL) {
                    gAct->hijoIntegrantes = curI->sig;
                  } else {
                    antI->sig = curI->sig;
                  }
                  if (curI->sig != NULL) {
                    curI->sig->ant = antI;
                  }
                  curI->sig = NULL;
                  curI->ant = NULL;
                  delete curI;
                  found = true;
                } else {
                  antI = curI;
                  curI = curI->sig;
                }
              }
              gAct = gAct->sig;
            }

            gestorProductos.consolidar(listasInv, multilistas);

            dibujarMarco();
            gotoxy(12, 6);
            cout << "=== INVESTIGADOR ELIMINADO CON EXITO (DELETE) ===";
            gotoxy(12, 8);
            cout << "Investigador: " << nombreInv << " (" << codigoInv << ")";
            gotoxy(12, 10);
            cout << "Eliminado completamente de la memoria del sistema.";
            gotoxy(12, 12);
            cout << "Catalogo consolidado actualizado: "
                 << gestorProductos.obtenerTotalUnicos()
                 << " productos netos unicos.";
            gotoxy(12, 14);
            cout << "Para guardar permanentemente en el archivo de texto plano,";
            gotoxy(12, 15);
            cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
                    "principal.";
            pausar();
            subOpcion = 13;
          } else {
            dibujarMarco();
            gotoxy(12, 8);
            cout << "Error al intentar eliminar el investigador.";
            pausar();
          }
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "Operacion cancelada. El investigador no fue eliminado.";
          pausar();
        }
      } else if (subOpcion == 13) {
        // Regresar
      } else {
        gotoxy(14, 23);
        cout << "Opcion no valida.";
        pausar();
      }
    }
  }

  void consultarInvestigadorConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== CONSULTAR INVESTIGADOR (READ) ===";

    NodoInvestigador *act = listasInv.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay investigadores registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Investigadores disponibles para consulta:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->investigador->codigoRh);
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->investigador->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->investigador->nombre
             << " (" << act->investigador->codigoRh << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->investigador->codigoRh);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el codigo RH a "
                         "consultar (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit(entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        Investigador *inv = listasInv.buscar(codigoSel);
        if (inv != NULL) {
          menuDetalleInvestigador(inv);
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "No se encontro ningun investigador con el codigo/numero: "
               << entrada;
          pausar();
        }
      }
    }
  }

  void consultarProduccionPorAnioInvestigadorConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== CONSULTAR PRODUCCION POR ANIO - INVESTIGADOR ===";

    NodoInvestigador *act = listasInv.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay investigadores registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Investigadores disponibles para consulta:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->investigador->codigoRh);
        gotoxy(12, y);
        cout << n << ". " << act->investigador->nombre << " ("
             << act->investigador->codigoRh << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->investigador->codigoRh);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el codigo RH a "
                         "consultar (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit((unsigned char)entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        Investigador *inv = listasInv.buscar(codigoSel);
        if (inv != NULL) {
          mostrarProduccionPorAnioInvestigador(inv);
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "No se encontro ningun investigador con el codigo/numero: "
               << entrada;
          pausar();
        }
      }
    }
  }

  void menuGestionInvestigadores() {
    int opcion = 0;
    while (opcion != 8) {
      dibujarMarco();
      gotoxy(15, 6);
      cout << "--- GESTION DE INVESTIGADORES ---";
      gotoxy(15, 8);
      cout << "1. Listar Investigadores";
      gotoxy(15, 9);
      cout << "2. Consultar Investigador";
      gotoxy(15, 10);
      cout << "3. Consultar Produccion por Anio";
      gotoxy(15, 11);
      cout << "4. Crear / Agregar Investigador";
      gotoxy(15, 12);
      cout << "5. Modificar Investigador";
      gotoxy(15, 13);
      cout << "6. Eliminar Investigador";
      gotoxy(15, 14);
      cout << "7. Activar / Desactivar Investigador";
      gotoxy(15, 15);
      cout << "8. Regresar al Menu Principal";
      gotoxy(15, 17);
      cout << "Seleccione una opcion [1-8]: ";

      cin >> opcion;
      if (cin.fail()) {
        cin.clear();
        cin.ignore(10000, '\n');
        opcion = 0;
      } else {
        cin.ignore(10000, '\n');
      }

      if (opcion == 1) {
        listarInvestigadores();
      } else if (opcion == 2) {
        consultarInvestigadorConsola();
      } else if (opcion == 3) {
        consultarProduccionPorAnioInvestigadorConsola();
      } else if (opcion == 4) {
        agregarInvestigador();
      } else if (opcion == 5) {
        modificarInvestigadorConsola();
      } else if (opcion == 6) {
        eliminarInvestigadorConsola();
      } else if (opcion == 7) {
        alternarEstadoInvestigadorConsola();
      } else if (opcion == 8) {
        // Regresar al menu principal
      } else {
        gotoxy(15, 19);
        cout << "Opcion no valida.";
        pausar();
      }
    }
  }

  // =========================================================
  // GESTION DE GRUPOS: CREAR Y LISTAR
  // =========================================================

  void listarGrupos() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== LISTADO DE GRUPOS DE INVESTIGACION ===";

    NodoGrupo *act = multilistas.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay grupos de investigacion registrados en el sistema.";
    } else {
      int y = 7;
      int n = 1;
      while (act != NULL && y < 19) {
        gotoxy(12, y);
        string lid = act->grupo->lider;
        if (lid.empty()) {
          lid = "Sin lider";
        }
        if (lid.size() > 20) {
          lid = lid.substr(0, 17) + "..";
        }
        string estadoTxt = "[ACTIVO]";
        if (!act->grupo->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->grupo->nombreGrupo << " ("
             << act->grupo->nroGrupo << ") [Lider: " << lid << "]";
        y++;
        n++;
        act = act->sig;
      }
      if (act != NULL) {
        gotoxy(12, 19);
        cout << "... y mas grupos registrados en el catalogo.";
      }
    }
    pausar();
  }

  void crearGrupo() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== CREAR GRUPO DE INVESTIGACION ===";
    gotoxy(12, 7);
    cout << "Paso 1: Informacion Basica Obligatoria";
    cout << "\n\n";

    string nroGrupo = "";
    bool grupoValido = false;
    while (!grupoValido) {
      nroGrupo = leerLineaTexto(
          "  Numero / Codigo de identificacion del grupo (obligatorio): ",
          true);
      NodoGrupo *existente = multilistas.buscarGrupo(nroGrupo);
      if (existente != NULL) {
        cout << "  [!] Ya existe un grupo con el identificador '" << nroGrupo
             << "': " << existente->grupo->nombreGrupo << ".\n";
        cout << "  Por favor ingrese un codigo identificador diferente.\n";
      } else {
        grupoValido = true;
      }
    }

    string nombreGrupo = leerLineaTexto(
        "  Nombre del grupo de investigacion (obligatorio): ", true);
    string lider = leerLineaTexto(
        "  Nombre completo del lider del grupo (obligatorio): ", true);
    string anioFormacion =
        leerLineaTexto("  Anio de formacion (ej: 2005) (obligatorio): ", true);
    string departamento =
        leerLineaTexto("  Departamento (ej: CESAR) (obligatorio): ", true);
    string ciudad =
        leerLineaTexto("  Ciudad (ej: VALLEDUPAR) (obligatorio): ", true);
    string email = leerLineaTexto(
        "  Correo electronico / Email del grupo (obligatorio): ", true);
    string institucion =
        leerLineaTexto("  Institucion que avala (ej: UNIVERSIDAD POPULAR DEL "
                       "CESAR) (obligatorio): ",
                       true);
    string planTrabajo = leerLineaTexto(
        "  Plan estrategico / Plan de trabajo institucional (obligatorio): ",
        true);

    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== CREAR GRUPO DE INVESTIGACION ===";
    gotoxy(12, 7);
    cout << "Paso 2: Informacion Descriptiva Complementaria (Opcional)";
    gotoxy(12, 9);
    cout << "1. Ingresar informacion descriptiva (clasificacion, area, web, "
            "objetivos)";
    gotoxy(12, 10);
    cout << "2. Omitir y continuar al registro de integrantes";
    gotoxy(12, 12);
    int opcOpcionales = leerEntero("Seleccione opcion [1-2]: ", 1, 2);

    string clasificacion = "";
    string areaConocimiento = "";
    string paginaWeb = "";
    string objetivos = "";
    string estadoArte = "";
    string retos = "";
    string vision = "";

    if (opcOpcionales == 1) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== INFORMACION DESCRIPTIVA (OPCIONAL) ===";
      cout << "\n  (Presione ENTER en cualquier campo que desee dejar "
              "vacio)\n\n";
      clasificacion = leerLineaTexto(
          "  Clasificacion (ej: A1, A, B, C, Reconocido): ", false);
      areaConocimiento = leerLineaTexto("  Area de conocimiento: ", false);
      paginaWeb = leerLineaTexto("  Pagina Web del grupo: ", false);
      objetivos = leerLineaTexto("  Objetivos del grupo: ", false);
      estadoArte = leerLineaTexto("  Estado del arte: ", false);
      retos = leerLineaTexto("  Retos del grupo: ", false);
      vision = leerLineaTexto("  Vision del grupo: ", false);
    }

    GrupoInvestigacion *nuevoGrupo = new GrupoInvestigacion(
        nroGrupo, nombreGrupo, anioFormacion, departamento, ciudad, lider, "",
        paginaWeb, email, clasificacion, areaConocimiento, "", "", planTrabajo,
        estadoArte, objetivos, retos, vision);

    nuevoGrupo->instituciones.push_back(institucion);
    if (!planTrabajo.empty()) {
      nuevoGrupo->instituciones.push_back("Plan Estrategico");
      nuevoGrupo->instituciones.push_back("Plan de trabajo: " + planTrabajo);
    }

    // Paso 3: Integrantes (MÍNIMO 2 OBLIGATORIOS)
    vector<Investigador *> integrantesGrupo;
    bool cancelarGrupo = false;
    bool integrantesCompletos = false;

    while (!integrantesCompletos && !cancelarGrupo) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== REGISTRO DE INTEGRANTES (OBLIGATORIO: MINIMO 2) ===";
      gotoxy(12, 7);
      cout << "Grupo: " << nuevoGrupo->nombreGrupo << " ("
           << nuevoGrupo->nroGrupo << ")";
      gotoxy(12, 8);
      cout << "Integrantes actuales registrados: " << integrantesGrupo.size()
           << " / 2 requeridos";

      int yPos = 10;
      size_t idxInt = 0;
      while (idxInt < integrantesGrupo.size() && yPos < 15) {
        gotoxy(14, yPos);
        cout << (idxInt + 1) << ". " << integrantesGrupo[idxInt]->nombre << " ("
             << integrantesGrupo[idxInt]->codigoRh << ")";
        yPos++;
        idxInt++;
      }

      gotoxy(12, 16);
      cout << "1. Vincular investigador existente en el sistema";
      gotoxy(12, 17);
      cout << "2. Registrar nuevo investigador integrante";
      if (integrantesGrupo.size() >= 2) {
        gotoxy(12, 18);
        cout
            << "3. Continuar al siguiente paso (Integrantes minimos cumplidos)";
      }
      gotoxy(12, 19);
      cout << "0. Cancelar creacion del grupo";

      int maxOpcInt = 2;
      if (integrantesGrupo.size() >= 2) {
        maxOpcInt = 3;
      }
      gotoxy(12, 21);
      int opcInt = leerEntero("Seleccione opcion: ", 0, maxOpcInt);

      if (opcInt == 1) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- VINCULAR INVESTIGADOR EXISTENTE ---";
        vector<Investigador *> disponibles;
        NodoInvestigador *nInv = listasInv.getCabeza();
        while (nInv != NULL) {
          if (nInv->investigador != NULL) {
            disponibles.push_back(nInv->investigador);
          }
          nInv = nInv->sig;
        }

        if (disponibles.empty()) {
          gotoxy(12, 8);
          cout
              << "No hay investigadores registrados previamente en el sistema.";
          pausar();
        } else {
          int yD = 7;
          size_t d = 0;
          while (d < disponibles.size() && yD < 18) {
            gotoxy(12, yD);
            cout << (d + 1) << ". " << disponibles[d]->nombre << " ("
                 << disponibles[d]->codigoRh << ")";
            yD++;
            d++;
          }
          gotoxy(12, 19);
          int selInv = leerEntero("Seleccione numero de investigador [1-" +
                                      to_string(disponibles.size()) +
                                      "] (0 para volver): ",
                                  0, static_cast<int>(disponibles.size()));
          if (selInv > 0) {
            Investigador *elegido = disponibles[selInv - 1];
            bool yaEsta = false;
            size_t c = 0;
            while (c < integrantesGrupo.size() && !yaEsta) {
              if (integrantesGrupo[c]->codigoRh == elegido->codigoRh) {
                yaEsta = true;
              }
              c++;
            }
            if (yaEsta) {
              cout << "\n  [!] El investigador ya esta vinculado a este "
                      "grupo.\n";
              pausar();
            } else {
              Investigador *copiaIntegrante = clonarInvestigador(elegido);
              integrantesGrupo.push_back(copiaIntegrante);
              cout << "\n  [OK] Investigador vinculado exitosamente como "
                      "integrante.\n";
              pausar();
            }
          }
        }
      } else if (opcInt == 2) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "--- REGISTRAR NUEVO INTEGRANTE PARA EL GRUPO ---";
        cout << "\n\n";
        string codInt = "";
        bool codOk = false;
        while (!codOk) {
          codInt = leerLineaTexto(
              "  Codigo RH / Identificador del integrante: ", true);
          bool enGrupo = false;
          size_t gCheck = 0;
          while (gCheck < integrantesGrupo.size() && !enGrupo) {
            if (integrantesGrupo[gCheck]->codigoRh == codInt) {
              enGrupo = true;
            }
            gCheck++;
          }
          if (enGrupo) {
            cout << "  [!] Este codigo ya fue agregado como integrante de este "
                    "grupo.\n";
          } else {
            codOk = true;
          }
        }
        string nomInt =
            leerLineaTexto("  Nombre completo del integrante: ", true);
        string corInt =
            leerLineaTexto("  Correo electronico del integrante: ", true);
        string instInt = leerLineaTexto(
            "  Institucion (opcional, Enter para omitir): ", false);

        Investigador *nuevoIntegrante =
            new Investigador(codInt, nomInt, corInt, "", instInt);
        integrantesGrupo.push_back(nuevoIntegrante);
        cout << "\n  [OK] Integrante registrado para el grupo.\n";
        pausar();
      } else if (opcInt == 3 && integrantesGrupo.size() >= 2) {
        integrantesCompletos = true;
      } else if (opcInt == 0) {
        cancelarGrupo = true;
      }
    }

    if (cancelarGrupo) {
      delete nuevoGrupo;
      size_t iDel = 0;
      while (iDel < integrantesGrupo.size()) {
        delete integrantesGrupo[iDel];
        iDel++;
      }
      dibujarMarco();
      gotoxy(12, 8);
      cout << "Creacion del grupo cancelada. Ningun dato fue guardado.";
      pausar();
    } else {
      // Paso 4: Menú de Datos Adicionales (Opcionales para Grupo: Productos,
      // Líneas de Investigación, etc.)
      vector<ProductoInvestigacion *> productosGrupo;
      bool continuarMenuGrupo = true;
      bool descartarFinal = false;

      while (continuarMenuGrupo) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "=== DATOS ADICIONALES DEL GRUPO (OPCIONALES) ===";
        gotoxy(12, 7);
        cout << "Grupo: " << nuevoGrupo->nombreGrupo << " ("
             << nuevoGrupo->nroGrupo << ")";

        gotoxy(12, 9);
        cout << "Resumen de elementos registrados:";
        gotoxy(14, 10);
        cout << "- Integrantes vinculados : " << integrantesGrupo.size()
             << " (Cumple minimo 2)";
        gotoxy(14, 11);
        cout << "- Lineas de Investigacion: "
             << nuevoGrupo->lineasInvestigacion.size();
        gotoxy(14, 12);
        cout << "- Productos del Grupo    : " << productosGrupo.size();

        gotoxy(12, 14);
        cout << "1. Agregar Linea de Investigacion (Opcional)";
        gotoxy(12, 15);
        cout << "2. Agregar Producto de Investigacion del Grupo (Opcional)";
        gotoxy(12, 16);
        cout << "3. Agregar Integrante Adicional (Opcional)";
        gotoxy(12, 17);
        cout << "4. Finalizar y Guardar Grupo (Omitir restantes)";
        gotoxy(12, 18);
        cout << "0. Cancelar y Descartar Creacion";
        gotoxy(12, 20);
        int subOpcG = leerEntero("Seleccione opcion [0-4]: ", 0, 4);

        if (subOpcG == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR LINEA DE INVESTIGACION AL GRUPO ---";
          cout << "\n\n";
          string linG =
              leerLineaTexto("  Nombre de la linea de investigacion: ", true);
          nuevoGrupo->lineasInvestigacion.push_back(linG);
          cout << "\n  [OK] Linea de investigacion agregada al grupo.\n";
          pausar();
        } else if (subOpcG == 2) {
          stringstream ssId;
          ssId << "G" << nuevoGrupo->nroGrupo << "_P"
               << (productosGrupo.size() + 1);
          ProductoInvestigacion *pGrp =
              crearProductoInteractivo(ssId.str(), nuevoGrupo->lider);
          productosGrupo.push_back(pGrp);
        } else if (subOpcG == 3) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- AGREGAR INTEGRANTE ADICIONAL ---";
          gotoxy(12, 7);
          cout << "1. Vincular investigador existente";
          gotoxy(12, 8);
          cout << "2. Registrar nuevo investigador integrante";
          gotoxy(12, 9);
          cout << "0. Regresar";
          gotoxy(12, 11);
          int opcExtraInt = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
          if (opcExtraInt == 1) {
            vector<Investigador *> disponibles;
            NodoInvestigador *nInv = listasInv.getCabeza();
            while (nInv != NULL) {
              if (nInv->investigador != NULL) {
                disponibles.push_back(nInv->investigador);
              }
              nInv = nInv->sig;
            }
            if (disponibles.empty()) {
              cout << "\n  No hay mas investigadores en el sistema.\n";
              pausar();
            } else {
              int yD = 13;
              size_t d = 0;
              while (d < disponibles.size() && yD < 19) {
                gotoxy(14, yD);
                cout << (d + 1) << ". " << disponibles[d]->nombre << " ("
                     << disponibles[d]->codigoRh << ")";
                yD++;
                d++;
              }
              gotoxy(12, 20);
              int selInv = leerEntero("Seleccione numero de investigador [1-" +
                                          to_string(disponibles.size()) +
                                          "] (0 para cancelar): ",
                                      0, static_cast<int>(disponibles.size()));
              if (selInv > 0) {
                Investigador *elegido = disponibles[selInv - 1];
                bool yaEsta = false;
                size_t c = 0;
                while (c < integrantesGrupo.size() && !yaEsta) {
                  if (integrantesGrupo[c]->codigoRh == elegido->codigoRh) {
                    yaEsta = true;
                  }
                  c++;
                }
                if (yaEsta) {
                  cout << "\n  [!] El investigador ya esta vinculado a este "
                          "grupo.\n";
                  pausar();
                } else {
                  Investigador *copiaIntegrante = clonarInvestigador(elegido);
                  integrantesGrupo.push_back(copiaIntegrante);
                  cout << "\n  [OK] Integrante vinculado con exito.\n";
                  pausar();
                }
              }
            }
          } else if (opcExtraInt == 2) {
            string codInt = leerLineaTexto(
                "  Codigo RH / Identificador del integrante: ", true);
            string nomInt =
                leerLineaTexto("  Nombre completo del integrante: ", true);
            string corInt =
                leerLineaTexto("  Correo electronico del integrante: ", true);
            Investigador *nuevoIntegrante =
                new Investigador(codInt, nomInt, corInt);
            integrantesGrupo.push_back(nuevoIntegrante);
            cout << "\n  [OK] Integrante agregado.\n";
            pausar();
          }
        } else if (subOpcG == 4) {
          continuarMenuGrupo = false;
        } else if (subOpcG == 0) {
          continuarMenuGrupo = false;
          descartarFinal = true;
        }
      }

      if (descartarFinal) {
        delete nuevoGrupo;
        size_t iDel = 0;
        while (iDel < integrantesGrupo.size()) {
          delete integrantesGrupo[iDel];
          iDel++;
        }
        size_t pDel = 0;
        while (pDel < productosGrupo.size()) {
          delete productosGrupo[pDel];
          pDel++;
        }
        dibujarMarco();
        gotoxy(12, 8);
        cout << "Creacion del grupo cancelada. Los datos fueron descartados.";
        pausar();
      } else {
        string nGrupoId = nuevoGrupo->nroGrupo;
        multilistas.agregarGrupo(nuevoGrupo);

        size_t iAdd = 0;
        while (iAdd < integrantesGrupo.size()) {
          multilistas.agregarIntegrante(nGrupoId, integrantesGrupo[iAdd]);
          iAdd++;
        }

        size_t pAdd = 0;
        while (pAdd < productosGrupo.size()) {
          multilistas.agregarProducto(nGrupoId, productosGrupo[pAdd]);
          pAdd++;
        }

        gestorProductos.consolidar(listasInv, multilistas);

        dibujarMarco();
        gotoxy(12, 6);
        cout << "=== GRUPO DE INVESTIGACION CREADO CON EXITO ===";
        gotoxy(12, 8);
        cout << "Grupo        : " << nuevoGrupo->nombreGrupo << " ("
             << nuevoGrupo->nroGrupo << ")";
        gotoxy(12, 9);
        cout << "Lider        : " << nuevoGrupo->lider;
        gotoxy(12, 10);
        cout << "Integrantes  : " << integrantesGrupo.size() << " registrados";
        gotoxy(12, 11);
        cout << "Productos    : " << productosGrupo.size() << " registrados";
        gotoxy(12, 13);
        cout << "Catalogo consolidado: " << gestorProductos.obtenerTotalUnicos()
             << " productos netos unicos.";
        gotoxy(12, 15);
        cout << "Para guardar permanentemente en el archivo 'grupos.txt',";
        gotoxy(12, 16);
        cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
                "principal.";
        pausar();
      }
    }
  }

  void eliminarProductoGrupo(NodoGrupo *nodoG) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== ELIMINAR PRODUCTO DEL GRUPO ===";
    cout << "\n\n";

    if (nodoG == NULL || nodoG->hijoProductos == NULL) {
      cout
          << "  [!] El grupo no tiene productos registrados para eliminar.\n\n";
      pausarDinamico();
    } else {
      cout << "  Productos asociados al grupo:\n";
      vector<NodoProducto *> nodos;
      NodoProducto *act = nodoG->hijoProductos;
      int num = 1;
      while (act != NULL) {
        if (act->producto != NULL) {
          nodos.push_back(act);
          cout << "    " << num << ". [" << act->producto->idProducto << "] "
               << act->producto->titulo << " (" << act->producto->categoria
               << ", " << act->producto->anio << ")\n";
          num++;
        }
        act = act->sig;
      }
      cout << "\n";
      string aviso = "  Seleccione el numero de producto a eliminar [1-" +
                     to_string(nodos.size()) + "] (0 para cancelar): ";
      int sel = leerEntero(aviso, 0, static_cast<int>(nodos.size()));
      if (sel > 0) {
        NodoProducto *aEliminar = nodos[sel - 1];
        string tituloEliminado = "";
        if (aEliminar->producto != NULL) {
          tituloEliminado = aEliminar->producto->titulo;
        }

        NodoProducto *anterior = NULL;
        NodoProducto *actual = nodoG->hijoProductos;
        bool eliminado = false;
        while (actual != NULL && !eliminado) {
          if (actual == aEliminar) {
            if (anterior == NULL) {
              nodoG->hijoProductos = actual->sig;
            } else {
              anterior->sig = actual->sig;
            }
            actual->sig = NULL;
            delete actual;
            eliminado = true;
          } else {
            anterior = actual;
            actual = actual->sig;
          }
        }

        if (eliminado) {
          cout << "\n  [OK] Producto '" << tituloEliminado
               << "' eliminado exitosamente del grupo.\n\n";
          gestorProductos.consolidar(listasInv, multilistas);
        }
        pausarDinamico();
      }
    }
  }

  void eliminarIntegranteGrupo(NodoGrupo *nodoG) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== ELIMINAR INTEGRANTE DEL GRUPO ===";
    cout << "\n\n";

    if (nodoG == NULL || nodoG->hijoIntegrantes == NULL) {
      cout << "  [!] El grupo no tiene integrantes vinculados para "
              "eliminar.\n\n";
      pausarDinamico();
    } else {
      vector<NodoInvestigador *> nodos;
      NodoInvestigador *act = nodoG->hijoIntegrantes;
      int num = 1;
      while (act != NULL) {
        if (act->investigador != NULL) {
          nodos.push_back(act);
          cout << "    " << num << ". " << act->investigador->nombre << " ("
               << act->investigador->codigoRh << ")\n";
          num++;
        }
        act = act->sig;
      }
      cout << "\n";
      if (nodos.size() <= 2) {
        cout << "  [!] Advertencia: El grupo cuenta con " << nodos.size()
             << " integrantes (minimo 2 requeridos por MinCiencias).\n";
        cout << "      Si elimina un integrante, se recomienda vincular otro "
                "nuevo.\n\n";
      }

      string aviso = "  Seleccione el numero de integrante a eliminar [1-" +
                     to_string(nodos.size()) + "] (0 para cancelar): ";
      int sel = leerEntero(aviso, 0, static_cast<int>(nodos.size()));
      if (sel > 0) {
        NodoInvestigador *aEliminar = nodos[sel - 1];
        string nombreEliminado = "";
        if (aEliminar->investigador != NULL) {
          nombreEliminado = aEliminar->investigador->nombre;
        }

        if (aEliminar->ant != NULL) {
          aEliminar->ant->sig = aEliminar->sig;
        } else {
          nodoG->hijoIntegrantes = aEliminar->sig;
        }
        if (aEliminar->sig != NULL) {
          aEliminar->sig->ant = aEliminar->ant;
        }
        aEliminar->sig = NULL;
        aEliminar->ant = NULL;
        delete aEliminar;

        cout << "\n  [OK] Integrante '" << nombreEliminado
             << "' desvinculado y eliminado del grupo con exito.\n\n";
        gestorProductos.consolidar(listasInv, multilistas);
        pausarDinamico();
      }
    }
  }

  void modificarGrupo(NodoGrupo *nodoG) {
    if (nodoG != NULL && nodoG->grupo != NULL) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== MODIFICAR GRUPO DE INVESTIGACION ===";
      gotoxy(12, 7);
      cout << "Paso 1: Modificacion de Informacion Basica Obligatoria";
      cout << "\n\n";

      string numAnterior = nodoG->grupo->nroGrupo;
      string nuevoNum = numAnterior;
      bool numValido = false;
      while (!numValido) {
        string ingNum = leerLineaModificar(
            "  Numero / Codigo identificador del grupo", numAnterior, true);
        if (ingNum == numAnterior) {
          numValido = true;
          nuevoNum = ingNum;
        } else {
          NodoGrupo *existente = multilistas.buscarGrupo(ingNum);
          if (existente != NULL) {
            cout << "  [!] Ya existe otro grupo con el identificador '"
                 << ingNum << "': " << existente->grupo->nombreGrupo << ".\n";
            cout << "  Por favor ingrese un codigo identificador diferente.\n";
          } else {
            numValido = true;
            nuevoNum = ingNum;
          }
        }
      }
      nodoG->grupo->nroGrupo = nuevoNum;

      nodoG->grupo->nombreGrupo =
          leerLineaModificar("  Nombre del grupo de investigacion",
                             nodoG->grupo->nombreGrupo, true);
      nodoG->grupo->lider = leerLineaModificar(
          "  Nombre completo del lider del grupo", nodoG->grupo->lider, true);
      nodoG->grupo->anioFormacion = leerLineaModificar(
          "  Anio de formacion (ej: 2005)", nodoG->grupo->anioFormacion, true);
      nodoG->grupo->departamento = leerLineaModificar(
          "  Departamento (ej: CESAR)", nodoG->grupo->departamento, true);
      nodoG->grupo->ciudad = leerLineaModificar("  Ciudad (ej: VALLEDUPAR)",
                                                nodoG->grupo->ciudad, true);
      nodoG->grupo->email = leerLineaModificar(
          "  Correo electronico / Email del grupo", nodoG->grupo->email, true);

      string instActual = "";
      if (!nodoG->grupo->instituciones.empty()) {
        instActual = nodoG->grupo->instituciones[0];
      }
      string nuevaInst =
          leerLineaModificar("  Institucion que avala", instActual, true);
      if (!nodoG->grupo->instituciones.empty()) {
        nodoG->grupo->instituciones[0] = nuevaInst;
      } else {
        nodoG->grupo->instituciones.push_back(nuevaInst);
      }

      nodoG->grupo->planEstrategico = leerLineaModificar(
          "  Plan estrategico / Plan de trabajo institucional",
          nodoG->grupo->planEstrategico, true);

      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== MODIFICAR GRUPO DE INVESTIGACION ===";
      gotoxy(12, 7);
      cout << "Paso 2: Informacion Descriptiva Complementaria (Opcional)";
      gotoxy(12, 9);
      cout << "1. Modificar informacion descriptiva (clasificacion, area, web, "
              "objetivos)";
      gotoxy(12, 10);
      cout << "2. Conservar actual y continuar a la gestion de colecciones";
      gotoxy(12, 12);
      int opcDescr = leerEntero("Seleccione opcion [1-2]: ", 1, 2);

      if (opcDescr == 1) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "=== MODIFICAR INFORMACION DESCRIPTIVA ===";
        cout << "\n\n";
        nodoG->grupo->clasificacion =
            leerLineaModificar("  Clasificacion (ej: A1, A, B, C, Reconocido)",
                               nodoG->grupo->clasificacion, false);
        nodoG->grupo->areaConocimiento = leerLineaModificar(
            "  Area de conocimiento", nodoG->grupo->areaConocimiento, false);
        nodoG->grupo->paginaWeb = leerLineaModificar(
            "  Pagina Web del grupo", nodoG->grupo->paginaWeb, false);
        nodoG->grupo->objetivos = leerLineaModificar(
            "  Objetivos del grupo", nodoG->grupo->objetivos, false);
        nodoG->grupo->estadoArte = leerLineaModificar(
            "  Estado del arte", nodoG->grupo->estadoArte, false);
        nodoG->grupo->retos =
            leerLineaModificar("  Retos del grupo", nodoG->grupo->retos, false);
        nodoG->grupo->vision = leerLineaModificar("  Vision del grupo",
                                                  nodoG->grupo->vision, false);
      }

      // Paso 3: Gestión de Colecciones del Grupo (Integrantes, Productos,
      // Líneas, Instituciones)
      bool continuarMenuGrupo = true;
      while (continuarMenuGrupo) {
        int totalIntegrantes = 0;
        NodoInvestigador *nInt = nodoG->hijoIntegrantes;
        while (nInt != NULL) {
          totalIntegrantes++;
          nInt = nInt->sig;
        }

        int totalProductosGrupo = 0;
        NodoProducto *nP = nodoG->hijoProductos;
        while (nP != NULL) {
          totalProductosGrupo++;
          nP = nP->sig;
        }

        dibujarMarco();
        gotoxy(12, 5);
        cout << "=== MODIFICAR ELEMENTOS Y COLECCIONES (GRUPO) ===";
        gotoxy(12, 6);
        cout << "Grupo: " << nodoG->grupo->nombreGrupo << " ("
             << nodoG->grupo->nroGrupo << ")";

        gotoxy(12, 8);
        cout << "Resumen de elementos registrados:";
        gotoxy(14, 9);
        cout << "- Integrantes vinculados : " << totalIntegrantes;
        if (totalIntegrantes >= 2) {
          cout << " (Cumple minimo 2)";
        } else {
          cout << " [!] Menos de 2 requeridos";
        }
        gotoxy(14, 10);
        cout << "- Productos del Grupo    : " << totalProductosGrupo;
        gotoxy(14, 11);
        cout << "- Lineas de Investigacion: "
             << nodoG->grupo->lineasInvestigacion.size();
        gotoxy(14, 12);
        cout << "- Instituciones          : "
             << nodoG->grupo->instituciones.size();

        gotoxy(12, 14);
        cout << "1. Gestionar Integrantes (Agregar / Eliminar / Listar)";
        gotoxy(12, 15);
        cout
            << "2. Gestionar Productos del Grupo (Agregar / Eliminar / Listar)";
        gotoxy(12, 16);
        cout << "3. Gestionar Lineas de Investigacion (Agregar / Eliminar)";
        gotoxy(12, 17);
        cout << "4. Gestionar Instituciones Vinculadas (Agregar / Eliminar)";
        gotoxy(12, 18);
        cout << "5. Finalizar y Guardar Modificaciones";
        gotoxy(12, 20);
        int subOpcG = leerEntero("Seleccione opcion [1-5]: ", 1, 5);

        if (subOpcG == 1) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- GESTION DE INTEGRANTES DEL GRUPO ---";
          gotoxy(12, 7);
          cout << "Integrantes actuales: " << totalIntegrantes;
          gotoxy(12, 9);
          cout << "1. Vincular investigador existente en el sistema";
          gotoxy(12, 10);
          cout << "2. Registrar nuevo investigador integrante";
          gotoxy(12, 11);
          cout << "3. Eliminar integrante del grupo";
          gotoxy(12, 12);
          cout << "0. Regresar";
          gotoxy(12, 14);
          int opcInt = leerEntero("Seleccione opcion [0-3]: ", 0, 3);
          if (opcInt == 1) {
            dibujarMarco();
            gotoxy(12, 5);
            cout << "--- VINCULAR INVESTIGADOR EXISTENTE ---";
            vector<Investigador *> disponibles;
            NodoInvestigador *nInvDisp = listasInv.getCabeza();
            while (nInvDisp != NULL) {
              if (nInvDisp->investigador != NULL) {
                disponibles.push_back(nInvDisp->investigador);
              }
              nInvDisp = nInvDisp->sig;
            }
            if (disponibles.empty()) {
              gotoxy(12, 8);
              cout << "No hay investigadores registrados previamente en el "
                      "sistema.\n";
              pausar();
            } else {
              int yD = 7;
              size_t d = 0;
              while (d < disponibles.size() && yD < 18) {
                gotoxy(12, yD);
                cout << (d + 1) << ". " << disponibles[d]->nombre << " ("
                     << disponibles[d]->codigoRh << ")";
                yD++;
                d++;
              }
              gotoxy(12, 19);
              string avisoDisp = "Seleccione numero de investigador [1-" +
                                 to_string(disponibles.size()) +
                                 "] (0 para volver): ";
              int selInv = leerEntero(avisoDisp, 0,
                                      static_cast<int>(disponibles.size()));
              if (selInv > 0) {
                Investigador *elegido = disponibles[selInv - 1];
                bool yaEsta = false;
                NodoInvestigador *curInt = nodoG->hijoIntegrantes;
                while (curInt != NULL && !yaEsta) {
                  if (curInt->investigador != NULL &&
                      curInt->investigador->codigoRh == elegido->codigoRh) {
                    yaEsta = true;
                  }
                  curInt = curInt->sig;
                }
                if (yaEsta) {
                  cout << "\n  [!] El investigador ya esta vinculado a este "
                          "grupo.\n";
                  pausar();
                } else {
                  Investigador *copiaIntegrante = clonarInvestigador(elegido);
                  multilistas.agregarIntegrante(nodoG->grupo->nroGrupo,
                                                copiaIntegrante);
                  cout << "\n  [OK] Investigador vinculado exitosamente al "
                          "grupo.\n";
                  gestorProductos.consolidar(listasInv, multilistas);
                  pausar();
                }
              }
            }
          } else if (opcInt == 2) {
            dibujarMarco();
            gotoxy(12, 5);
            cout << "--- REGISTRAR NUEVO INTEGRANTE PARA EL GRUPO ---";
            cout << "\n\n";
            string codInt = "";
            bool codOk = false;
            while (!codOk) {
              codInt = leerLineaTexto(
                  "  Codigo RH / Identificador del integrante: ", true);
              bool enGrupo = false;
              NodoInvestigador *chkInt = nodoG->hijoIntegrantes;
              while (chkInt != NULL && !enGrupo) {
                if (chkInt->investigador != NULL &&
                    chkInt->investigador->codigoRh == codInt) {
                  enGrupo = true;
                }
                chkInt = chkInt->sig;
              }
              if (enGrupo) {
                cout << "  [!] Este codigo ya pertenece a un integrante de "
                        "este grupo.\n";
              } else {
                codOk = true;
              }
            }
            string nomInt =
                leerLineaTexto("  Nombre completo del integrante: ", true);
            string corInt =
                leerLineaTexto("  Correo electronico del integrante: ", true);
            string instInt = leerLineaTexto(
                "  Institucion (opcional, Enter para omitir): ", false);
            Investigador *nuevoIntegrante =
                new Investigador(codInt, nomInt, corInt, "", instInt);
            multilistas.agregarIntegrante(nodoG->grupo->nroGrupo,
                                          nuevoIntegrante);
            cout << "\n  [OK] Integrante agregado exitosamente al grupo.\n";
            gestorProductos.consolidar(listasInv, multilistas);
            pausar();
          } else if (opcInt == 3) {
            eliminarIntegranteGrupo(nodoG);
          }
        } else if (subOpcG == 2) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- GESTION DE PRODUCTOS DEL GRUPO ---";
          gotoxy(12, 7);
          cout << "Productos actuales: " << totalProductosGrupo;
          gotoxy(12, 9);
          cout << "1. Agregar Producto al Grupo";
          gotoxy(12, 10);
          cout << "2. Eliminar Producto del Grupo";
          gotoxy(12, 11);
          cout << "0. Regresar";
          gotoxy(12, 13);
          int opcProdG = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
          if (opcProdG == 1) {
            stringstream ssId;
            ssId << "G" << nodoG->grupo->nroGrupo << "_P"
                 << (totalProductosGrupo + 1);
            ProductoInvestigacion *pGrp =
                crearProductoInteractivo(ssId.str(), nodoG->grupo->lider);
            multilistas.agregarProducto(nodoG->grupo->nroGrupo, pGrp);
            gestorProductos.consolidar(listasInv, multilistas);
          } else if (opcProdG == 2) {
            eliminarProductoGrupo(nodoG);
          }
        } else if (subOpcG == 3) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- GESTION DE LINEAS DE INVESTIGACION ---";
          gotoxy(12, 7);
          cout << "Registros actuales: "
               << nodoG->grupo->lineasInvestigacion.size();
          gotoxy(12, 9);
          cout << "1. Agregar Linea de Investigacion";
          gotoxy(12, 10);
          cout << "2. Eliminar Linea de Investigacion";
          gotoxy(12, 11);
          cout << "0. Regresar";
          gotoxy(12, 13);
          int opcLinG = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
          if (opcLinG == 1) {
            dibujarMarco();
            gotoxy(12, 5);
            cout << "--- AGREGAR LINEA DE INVESTIGACION AL GRUPO ---";
            cout << "\n\n";
            string linG =
                leerLineaTexto("  Nombre de la linea de investigacion: ", true);
            nodoG->grupo->lineasInvestigacion.push_back(linG);
            cout << "\n  [OK] Linea de investigacion agregada al grupo.\n";
            pausar();
          } else if (opcLinG == 2) {
            eliminarElementoColeccion("LINEAS DE INVESTIGACION",
                                      nodoG->grupo->lineasInvestigacion);
          }
        } else if (subOpcG == 4) {
          dibujarMarco();
          gotoxy(12, 5);
          cout << "--- GESTION DE INSTITUCIONES VINCULADAS ---";
          gotoxy(12, 7);
          cout << "Registros actuales: " << nodoG->grupo->instituciones.size();
          gotoxy(12, 9);
          cout << "1. Agregar Institucion";
          gotoxy(12, 10);
          cout << "2. Eliminar Institucion";
          gotoxy(12, 11);
          cout << "0. Regresar";
          gotoxy(12, 13);
          int opcInstG = leerEntero("Seleccione opcion [0-2]: ", 0, 2);
          if (opcInstG == 1) {
            dibujarMarco();
            gotoxy(12, 5);
            cout << "--- AGREGAR INSTITUCION VINCULADA ---";
            cout << "\n\n";
            string instG = leerLineaTexto("  Nombre de la institucion: ", true);
            nodoG->grupo->instituciones.push_back(instG);
            cout << "\n  [OK] Institucion agregada al grupo.\n";
            pausar();
          } else if (opcInstG == 2) {
            eliminarElementoColeccion("INSTITUCIONES",
                                      nodoG->grupo->instituciones);
          }
        } else if (subOpcG == 5) {
          continuarMenuGrupo = false;
        }
      }

      gestorProductos.consolidar(listasInv, multilistas);

      dibujarMarco();
      gotoxy(12, 6);
      cout << "=== GRUPO DE INVESTIGACION MODIFICADO CON EXITO ===";
      gotoxy(12, 8);
      cout << "Grupo        : " << nodoG->grupo->nombreGrupo << " ("
           << nodoG->grupo->nroGrupo << ")";
      gotoxy(12, 9);
      cout << "Lider        : " << nodoG->grupo->lider;
      gotoxy(12, 11);
      cout << "Datos actualizados exitosamente en la memoria del sistema.";
      gotoxy(12, 13);
      cout << "Catalogo consolidado: " << gestorProductos.obtenerTotalUnicos()
           << " productos netos unicos.";
      gotoxy(12, 15);
      cout << "Para guardar permanentemente en el archivo 'grupos.txt',";
      gotoxy(12, 16);
      cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
              "principal.";
      pausar();
    }
  }

  void modificarGrupoConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== MODIFICAR GRUPO DE INVESTIGACION ===";

    NodoGrupo *act = multilistas.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay grupos de investigacion registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Grupos disponibles para modificar:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->grupo->nroGrupo);
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->grupo->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->grupo->nombreGrupo << " ("
             << act->grupo->nroGrupo << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->grupo->nroGrupo);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el ID/codigo del "
                         "grupo a modificar (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit(entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        NodoGrupo *nodoG = multilistas.buscarGrupo(codigoSel);
        if (nodoG != NULL && nodoG->grupo != NULL) {
          modificarGrupo(nodoG);
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "No se encontro ningun grupo con el codigo/numero: "
               << entrada;
          pausar();
        }
      }
    }
  }

  void eliminarGrupoConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== ELIMINAR GRUPO DE INVESTIGACION (DELETE) ===";

    NodoGrupo *act = multilistas.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay grupos de investigacion registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Grupos disponibles para eliminar:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->grupo->nroGrupo);
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->grupo->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->grupo->nombreGrupo << " ("
             << act->grupo->nroGrupo << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->grupo->nroGrupo);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el ID/codigo del "
                         "grupo a eliminar (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit(entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        NodoGrupo *nodoG = multilistas.buscarGrupo(codigoSel);
        if (nodoG != NULL && nodoG->grupo != NULL) {
          string nombreGrupo = nodoG->grupo->nombreGrupo;
          string idGrupo = nodoG->grupo->nroGrupo;
          string liderGrupo = nodoG->grupo->lider;

          dibujarMarco();
          gotoxy(12, 6);
          cout << "=== CONFIRMACION DE ELIMINACION DE GRUPO ===";
          gotoxy(12, 8);
          cout << "Grupo a eliminar         : " << nombreGrupo << " ("
               << idGrupo << ")";
          gotoxy(12, 9);
          cout << "Lider del grupo          : " << liderGrupo;
          gotoxy(12, 11);
          cout << "[!] ADVERTENCIA: Esta accion eliminara permanentemente el grupo,";
          gotoxy(12, 12);
          cout << "    sus integrantes asociados y todos sus productos registrados.";
          gotoxy(12, 14);
          cout << "1. Confirmar eliminacion definitiva";
          gotoxy(12, 15);
          cout << "2. Cancelar operacion";
          gotoxy(12, 17);
          int opcConf = leerEntero("Seleccione opcion [1-2]: ", 1, 2);

          if (opcConf == 1) {
            bool eliminado = multilistas.eliminarGrupo(idGrupo);
            if (eliminado) {
              gestorProductos.consolidar(listasInv, multilistas);

              dibujarMarco();
              gotoxy(12, 6);
              cout << "=== GRUPO ELIMINADO CON EXITO (DELETE) ===";
              gotoxy(12, 8);
              cout << "Grupo: " << nombreGrupo << " (" << idGrupo << ")";
              gotoxy(12, 10);
              cout << "Eliminado completamente de la memoria del sistema.";
              gotoxy(12, 12);
              cout << "Catalogo consolidado actualizado: "
                   << gestorProductos.obtenerTotalUnicos()
                   << " productos netos unicos.";
              gotoxy(12, 14);
              cout << "Para guardar permanentemente en el archivo 'grupos.txt',";
              gotoxy(12, 15);
              cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
                      "principal.";
              pausar();
            } else {
              dibujarMarco();
              gotoxy(12, 8);
              cout << "Error al intentar eliminar el grupo.";
              pausar();
            }
          } else {
            dibujarMarco();
            gotoxy(12, 8);
            cout << "Operacion cancelada. El grupo no fue eliminado.";
            pausar();
          }
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "No se encontro ningun grupo con el codigo/numero: "
               << entrada;
          pausar();
        }
      }
    }
  }

  void alternarEstadoGrupoConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== ACTIVAR / DESACTIVAR GRUPO DE INVESTIGACION ===";

    NodoGrupo *act = multilistas.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay grupos de investigacion registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Grupos de investigacion registrados:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->grupo->nroGrupo);
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->grupo->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->grupo->nombreGrupo << " ("
             << act->grupo->nroGrupo << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->grupo->nroGrupo);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada = leerLineaTexto("  Ingrese el numero de lista o el "
                                      "ID/codigo del grupo (0 para cancelar): ",
                                      false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit(entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        NodoGrupo *nodoG = multilistas.buscarGrupo(codigoSel);
        dibujarMarco();
        if (nodoG != NULL && nodoG->grupo != NULL) {
          multilistas.alternarEstadoGrupo(codigoSel);
          gotoxy(12, 7);
          cout << "=== CAMBIO DE ESTADO REALIZADO ===";
          gotoxy(12, 9);
          cout << "Grupo        : " << nodoG->grupo->nombreGrupo;
          gotoxy(12, 10);
          cout << "Codigo / ID  : " << nodoG->grupo->nroGrupo;
          gotoxy(12, 11);
          if (nodoG->grupo->activo) {
            cout << "Nuevo Estado : ACTIVO (Habilitado en el sistema)";
          } else {
            cout << "Nuevo Estado : INACTIVO (Deshabilitado en el sistema)";
          }
          gotoxy(12, 13);
          cout << "Para guardar permanentemente en el archivo 'grupos.txt',";
          gotoxy(12, 14);
          cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
                  "principal.";
        } else {
          gotoxy(12, 8);
          cout << "No se encontro ningun grupo con el codigo/numero: "
               << entrada;
        }
        pausar();
      }
    }
  }

  void mostrarInfoBasicaGrupo(GrupoInvestigacion *grupo) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== INFORMACION BASICA DEL GRUPO DE INVESTIGACION ===";
    cout << "\n\n";

    string estadoTxt = "ACTIVO (Habilitado en el sistema)";
    if (!grupo->activo) {
      estadoTxt = "INACTIVO (Deshabilitado en el sistema)";
    }

    cout << "  Nombre del Grupo         : "
         << valorOCadena(grupo->nombreGrupo, "No registrado") << "\n";
    cout << "  Codigo / ID del Grupo    : "
         << valorOCadena(grupo->nroGrupo, "No registrado") << "\n";
    cout << "  Estado en el Sistema     : " << estadoTxt << "\n";
    cout << "  Lider del Grupo          : "
         << valorOCadena(grupo->lider, "Sin lider registrado") << "\n";
    cout << "  Anio de Formacion        : "
         << valorOCadena(grupo->anioFormacion, "No registrado") << "\n";
    cout << "  Ubicacion Geografica     : "
         << valorOCadena(grupo->departamento, "N/D") << " - "
         << valorOCadena(grupo->ciudad, "N/D") << "\n";
    cout << "  Clasificacion MinCiencias: "
         << valorOCadena(grupo->clasificacion, "No clasificado") << "\n";
    cout << "  Area de Conocimiento     : "
         << valorOCadena(grupo->areaConocimiento, "No registrada") << "\n";
    cout << "  Programa Nacional CTeI   : "
         << valorOCadena(grupo->programaNacionalCti, "No registrado") << "\n";
    if (!grupo->programaNacionalCtiSecundario.empty()) {
      cout << "  Programa CTeI Secundario : "
           << grupo->programaNacionalCtiSecundario << "\n";
    }
    cout << "  Informacion Certificada  : "
         << valorOCadena(grupo->informacionCertificada, "No") << "\n";
    cout << "  Correo Electronico       : "
         << valorOCadena(grupo->email, "No registrado") << "\n";
    cout << "  Pagina Web               : "
         << valorOCadena(grupo->paginaWeb, "No registrada") << "\n";

    cout << "\n  --- INFORMACION DESCRIPTIVA DEL GRUPO ---\n";
    cout << "  Plan Estrategico         : "
         << valorOCadena(grupo->planEstrategico, "No registrado") << "\n";
    cout << "  Estado del Arte          : "
         << valorOCadena(grupo->estadoArte, "No registrado") << "\n";
    cout << "  Objetivos                : "
         << valorOCadena(grupo->objetivos, "No registrados") << "\n";
    cout << "  Retos                    : "
         << valorOCadena(grupo->retos, "No registrados") << "\n";
    cout << "  Vision                   : "
         << valorOCadena(grupo->vision, "No registrada") << "\n\n";

    pausarDinamico();
  }

  void mostrarInstitucionesGrupo(GrupoInvestigacion *grupo) {
    mostrarListaColeccion("INSTITUCIONES VINCULADAS AL GRUPO",
                          grupo->instituciones, "instituciones vinculadas");
  }

  void mostrarLineasInvestigacionGrupo(GrupoInvestigacion *grupo) {
    mostrarListaColeccion("LINEAS DE INVESTIGACION DEL GRUPO",
                          grupo->lineasInvestigacion,
                          "lineas de investigacion");
  }

  void mostrarIntegrantesGrupo(NodoGrupo *nodoG) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== INTEGRANTES DEL GRUPO DE INVESTIGACION ===";
    cout << "\n\n";

    if (nodoG == NULL || nodoG->hijoIntegrantes == NULL) {
      cout << "  [!] No hay datos registrados para mostrar en integrantes del "
              "grupo.\n\n";
    } else {
      cout << "  Grupo: " << nodoG->grupo->nombreGrupo << " ("
           << nodoG->grupo->nroGrupo << ")\n\n";
      NodoInvestigador *act = nodoG->hijoIntegrantes;
      int n = 1;
      int conteoPausa = 0;
      bool salirEsc = false;
      while (act != NULL && !salirEsc) {
        if (act->investigador != NULL) {
          Investigador *inv = act->investigador;
          string estadoTxt = "[ACTIVO]";
          if (!inv->activo) {
            estadoTxt = "[INACTIVO]";
          }
          cout << "  " << n << ". " << estadoTxt << " " << inv->nombre << "\n";
          cout << "     Codigo RH / ID: "
               << valorOCadena(inv->codigoRh, "Sin ID");
          if (!inv->categoriaInvestigador.empty()) {
            cout << " | Categoria: " << inv->categoriaInvestigador;
          }
          cout << " | Productos aportados: " << inv->contarProductos() << "\n";
          if (!inv->institucion.empty()) {
            cout << "     Institucion   : " << inv->institucion << "\n";
          }
          cout << "\n";
          n++;
          conteoPausa++;

          if (conteoPausa % 4 == 0 && act->sig != NULL) {
            cout << "\n";
            bool continua = esperarTeclaPaginacion(false);
            if (!continua) {
              salirEsc = true;
            } else {
              dibujarMarco();
              gotoxy(12, 5);
              cout << "=== INTEGRANTES DEL GRUPO (Continuacion) ===";
              cout << "\n\n";
            }
          }
        }
        act = act->sig;
      }
    }
    pausarDinamico();
  }

  void mostrarProductosPorCategoriaGrupo(NodoGrupo *nodoG) {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== PRODUCTOS DEL GRUPO POR CATEGORIA ===";
    cout << "\n\n";

    if (nodoG == NULL || nodoG->hijoProductos == NULL) {
      cout << "  [!] No hay datos registrados para mostrar en productos del "
              "grupo.\n\n";
      pausarDinamico();
    } else {
      vector<string> categorias;
      NodoProducto *actP = nodoG->hijoProductos;
      int totalProds = 0;
      while (actP != NULL) {
        if (actP->producto != NULL) {
          totalProds++;
          string cat = actP->producto->categoria;
          if (cat.empty()) {
            cat = "Sin categoria";
          }
          bool yaExiste = false;
          size_t cIdx = 0;
          while (cIdx < categorias.size() && !yaExiste) {
            if (categorias[cIdx] == cat) {
              yaExiste = true;
            }
            cIdx++;
          }
          if (!yaExiste) {
            categorias.push_back(cat);
          }
        }
        actP = actP->sig;
      }

      cout << "  Grupo                    : " << nodoG->grupo->nombreGrupo
           << " (" << nodoG->grupo->nroGrupo << ")\n";
      cout << "  Total global de productos: " << totalProds << "\n";
      cout << "  Categorias representadas : " << categorias.size() << "\n\n";

      size_t c = 0;
      int lineasPantalla = 6;
      const int LIMITE_LINEAS = 18;
      bool salirEsc = false;

      while (c < categorias.size() && !salirEsc) {
        string catActual = categorias[c];

        if (lineasPantalla + 3 > LIMITE_LINEAS) {
          cout << "\n";
          bool continua = esperarTeclaPaginacion(false);
          if (!continua) {
            salirEsc = true;
          } else {
            dibujarMarco();
            gotoxy(12, 5);
            cout << "=== PRODUCTOS DEL GRUPO (Continuacion) ===";
            cout << "\n\n";
            lineasPantalla = 0;
          }
        }

        if (!salirEsc) {
          cout << "  "
                  "============================================================"
                  "\n";
          cout << "  CATEGORIA: " << catActual << "\n";
          cout << "  "
                  "============================================================"
                  "\n";
          lineasPantalla += 3;

          NodoProducto *pCurr = nodoG->hijoProductos;
          int numProdEnCat = 1;
          while (pCurr != NULL && !salirEsc) {
            if (pCurr->producto != NULL) {
              string pCat = pCurr->producto->categoria;
              if (pCat.empty()) {
                pCat = "Sin categoria";
              }
              if (pCat == catActual) {
                ProductoInvestigacion *p = pCurr->producto;

                int lineasItem = 3;
                if (!p->doi.empty()) {
                  lineasItem++;
                }
                if (!p->isbn.empty()) {
                  lineasItem++;
                }
                if (!p->revista.empty()) {
                  lineasItem++;
                }
                if (!p->editorial.empty()) {
                  lineasItem++;
                }
                if (!p->autores.empty()) {
                  lineasItem++;
                }

                if (lineasPantalla + lineasItem > LIMITE_LINEAS) {
                  cout << "\n";
                  bool continua = esperarTeclaPaginacion(false);
                  if (!continua) {
                    salirEsc = true;
                  } else {
                    dibujarMarco();
                    gotoxy(12, 5);
                    cout << "=== PRODUCTOS DEL GRUPO (Continuacion) - "
                            "Categoria: "
                         << catActual << " ===";
                    cout << "\n\n";
                    lineasPantalla = 0;
                  }
                }

                if (!salirEsc) {
                  cout << "   " << numProdEnCat << ". [" << p->idProducto
                       << "] " << p->titulo << "\n";
                  cout << "      Anio: " << p->anio;
                  if (!p->subtipo.empty()) {
                    cout << " | Subtipo: " << p->subtipo;
                  }
                  if (p->validado) {
                    cout << " | MinCiencias: VALIDADO";
                  } else {
                    cout << " | MinCiencias: NO VALIDADO";
                  }
                  cout << "\n";
                  if (!p->doi.empty()) {
                    cout << "      DOI: " << p->doi << "\n";
                  }
                  if (!p->isbn.empty()) {
                    cout << "      ISBN: " << p->isbn << "\n";
                  }
                  if (!p->revista.empty()) {
                    cout << "      Revista: " << p->revista << "\n";
                  }
                  if (!p->editorial.empty()) {
                    cout << "      Editorial: " << p->editorial << "\n";
                  }
                  if (!p->autores.empty()) {
                    cout << "      Autores: ";
                    size_t aIdx = 0;
                    while (aIdx < p->autores.size()) {
                      cout << p->autores[aIdx];
                      if (aIdx + 1 < p->autores.size()) {
                        cout << ", ";
                      }
                      aIdx++;
                    }
                    cout << "\n";
                  }
                  cout << "\n";
                  lineasPantalla += lineasItem;
                  numProdEnCat++;
                }
              }
            }
            pCurr = pCurr->sig;
          }
          c++;
        }
      }

      if (!salirEsc) {
        cout << "\n";
        esperarTeclaPaginacion(true);
      }
    }
  }

  void mostrarProduccionPorAnioGrupo(NodoGrupo *nodoG) {
    if (nodoG == NULL || nodoG->grupo == NULL) {
      dibujarMarco();
      gotoxy(12, 6);
      cout << "Grupo no valido.";
      pausar();
    } else {
      bool salir = false;
      while (!salir) {
        dibujarMarco();
        gotoxy(12, 5);
        cout << "=== LISTA DE PRODUCCION POR ANIO (GRUPO) ===";
        cout << "\n\n";
        cout << "  Grupo: " << nodoG->grupo->nombreGrupo << " ("
             << nodoG->grupo->nroGrupo << ")\n\n";

        if (nodoG->hijoProductos == NULL) {
          cout << "  [!] El grupo no tiene productos registrados.\n\n";
          pausarDinamico();
          salir = true;
        } else {
          vector<int> anios;
          vector<int> conteos;

          NodoProducto *actP = nodoG->hijoProductos;
          while (actP != NULL) {
            if (actP->producto != NULL) {
              int anio = actP->producto->anio;
              bool yaExiste = false;
              size_t aIdx = 0;
              while (aIdx < anios.size() && !yaExiste) {
                if (anios[aIdx] == anio) {
                  yaExiste = true;
                  conteos[aIdx]++;
                }
                aIdx++;
              }
              if (!yaExiste) {
                anios.push_back(anio);
                conteos.push_back(1);
              }
            }
            actP = actP->sig;
          }

          size_t s1 = 0;
          while (s1 < anios.size()) {
            size_t s2 = s1 + 1;
            while (s2 < anios.size()) {
              if (anios[s1] > anios[s2]) {
                int tA = anios[s1];
                anios[s1] = anios[s2];
                anios[s2] = tA;
                int tC = conteos[s1];
                conteos[s1] = conteos[s2];
                conteos[s2] = tC;
              }
              s2++;
            }
            s1++;
          }

          cout << "  +--------+-----------------------+\n";
          cout << "  |  Anio  | Cantidad de Productos |\n";
          cout << "  +--------+-----------------------+\n";
          size_t idx = 0;
          int totalProd = 0;
          while (idx < anios.size()) {
            string anioTxt = to_string(anios[idx]);
            if (anios[idx] <= 1000) {
              anioTxt = "Sin anio";
            }
            cout << "  | " << right << setw(6) << anioTxt << " | "
                 << right << setw(21) << conteos[idx] << " |\n";
            totalProd += conteos[idx];
            idx++;
          }
          cout << "  +--------+-----------------------+\n";
          cout << "  | TOTAL  | " << right << setw(21) << totalProd << " |\n";
          cout << "  +--------+-----------------------+\n\n";

          cout << "  1. Consultar cantidad de productos en un periodo de tiempo especifico (Rango de anios)\n";
          cout << "  2. Regresar\n\n";
          int opc = leerEntero("  Seleccione una opcion [1-2]: ", 1, 2);

          if (opc == 1) {
            cout << "\n";
            int aIni = leerEntero("  Ingrese anio inicial: ", 1900, 2100);
            int aFin = leerEntero("  Ingrese anio final  : ", 1900, 2100);
            if (aIni > aFin) {
              int t = aIni;
              aIni = aFin;
              aFin = t;
            }

            int conteoPeriodo = 0;
            vector<int> aniosP;
            vector<int> conteosP;

            size_t cIdx = 0;
            while (cIdx < anios.size()) {
              if (anios[cIdx] >= aIni && anios[cIdx] <= aFin) {
                aniosP.push_back(anios[cIdx]);
                conteosP.push_back(conteos[cIdx]);
                conteoPeriodo += conteos[cIdx];
              }
              cIdx++;
            }

            cout << "\n  ==============================================================\n";
            cout << "  CONTEO TOTAL EN EL PERIODO ESPECIFICADO\n";
            cout << "  Periodo consultado           : " << aIni << " - " << aFin
                 << "\n";
            cout << "  Total de productos publicados: " << conteoPeriodo
                 << " producto(s)\n";
            cout << "  ==============================================================\n\n";

            if (aniosP.empty()) {
              cout << "  No se registraron productos publicados dentro del periodo "
                   << aIni << " - " << aFin << ".\n\n";
            } else {
              cout << "  Detalle de produccion dentro del periodo:\n";
              cout << "  +--------+-----------------------+\n";
              cout << "  |  Anio  | Cantidad de Productos |\n";
              cout << "  +--------+-----------------------+\n";
              size_t p = 0;
              while (p < aniosP.size()) {
                cout << "  | " << right << setw(6) << aniosP[p] << " | "
                     << right << setw(21) << conteosP[p] << " |\n";
                p++;
              }
              cout << "  +--------+-----------------------+\n";
              cout << "  | TOTAL  | " << right << setw(21) << conteoPeriodo
                   << " |\n";
              cout << "  +--------+-----------------------+\n\n";
            }
            pausarDinamico();
          } else if (opc == 2) {
            salir = true;
          }
        }
      }
    }
  }

  void menuDetalleGrupo(NodoGrupo *nodoG) {
    int subOpcion = 0;
    while (subOpcion != 9) {
      dibujarMarco();
      gotoxy(12, 5);
      cout << "=== CONSULTA DETALLADA DE GRUPO DE INVESTIGACION ===";
      gotoxy(12, 6);
      cout << "Grupo: " << nodoG->grupo->nombreGrupo << " ("
           << nodoG->grupo->nroGrupo << ")";
      gotoxy(14, 8);
      cout << "1. Informacion Basica del Grupo";
      gotoxy(14, 9);
      cout << "2. Instituciones Vinculadas";
      gotoxy(14, 10);
      cout << "3. Lista de Integrantes";
      gotoxy(14, 11);
      cout << "4. Productos por Categoria";
      gotoxy(14, 12);
      cout << "5. Lista de Produccion por Anio";
      gotoxy(14, 13);
      cout << "6. Lineas de Investigacion";
      gotoxy(14, 14);
      cout << "7. Modificar Grupo";
      gotoxy(14, 15);
      cout << "8. Eliminar Grupo";
      gotoxy(14, 16);
      cout << "9. Regresar";
      gotoxy(14, 18);
      cout << "Seleccione una opcion [1-9]: ";

      cin >> subOpcion;
      if (cin.fail()) {
        cin.clear();
        cin.ignore(10000, '\n');
        subOpcion = 0;
      } else {
        cin.ignore(10000, '\n');
      }

      if (subOpcion == 1) {
        mostrarInfoBasicaGrupo(nodoG->grupo);
      } else if (subOpcion == 2) {
        mostrarInstitucionesGrupo(nodoG->grupo);
      } else if (subOpcion == 3) {
        mostrarIntegrantesGrupo(nodoG);
      } else if (subOpcion == 4) {
        mostrarProductosPorCategoriaGrupo(nodoG);
      } else if (subOpcion == 5) {
        mostrarProduccionPorAnioGrupo(nodoG);
      } else if (subOpcion == 6) {
        mostrarLineasInvestigacionGrupo(nodoG->grupo);
      } else if (subOpcion == 7) {
        modificarGrupo(nodoG);
      } else if (subOpcion == 8) {
        string nombreGrupo = nodoG->grupo->nombreGrupo;
        string idGrupo = nodoG->grupo->nroGrupo;
        string liderGrupo = nodoG->grupo->lider;

        dibujarMarco();
        gotoxy(12, 6);
        cout << "=== CONFIRMACION DE ELIMINACION DE GRUPO ===";
        gotoxy(12, 8);
        cout << "Grupo a eliminar         : " << nombreGrupo << " ("
             << idGrupo << ")";
        gotoxy(12, 9);
        cout << "Lider del grupo          : " << liderGrupo;
        gotoxy(12, 11);
        cout << "[!] ADVERTENCIA: Esta accion eliminara permanentemente el grupo,";
        gotoxy(12, 12);
        cout << "    sus integrantes asociados y todos sus productos registrados.";
        gotoxy(12, 14);
        cout << "1. Confirmar eliminacion definitiva";
        gotoxy(12, 15);
        cout << "2. Cancelar operacion";
        gotoxy(12, 17);
        int opcConf = leerEntero("Seleccione opcion [1-2]: ", 1, 2);

        if (opcConf == 1) {
          bool eliminado = multilistas.eliminarGrupo(idGrupo);
          if (eliminado) {
            gestorProductos.consolidar(listasInv, multilistas);

            dibujarMarco();
            gotoxy(12, 6);
            cout << "=== GRUPO ELIMINADO CON EXITO (DELETE) ===";
            gotoxy(12, 8);
            cout << "Grupo: " << nombreGrupo << " (" << idGrupo << ")";
            gotoxy(12, 10);
            cout << "Eliminado completamente de la memoria del sistema.";
            gotoxy(12, 12);
            cout << "Catalogo consolidado actualizado: "
                 << gestorProductos.obtenerTotalUnicos()
                 << " productos netos unicos.";
            gotoxy(12, 14);
            cout << "Para guardar permanentemente en el archivo 'grupos.txt',";
            gotoxy(12, 15);
            cout << "recuerde utilizar la opcion '5. Guardar Datos' en el menu "
                    "principal.";
            pausar();
            subOpcion = 9;
          } else {
            dibujarMarco();
            gotoxy(12, 8);
            cout << "Error al intentar eliminar el grupo.";
            pausar();
          }
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "Operacion cancelada. El grupo no fue eliminado.";
          pausar();
        }
      } else if (subOpcion == 9) {
        // Regresar
      } else {
        gotoxy(14, 20);
        cout << "Opcion no valida.";
        pausar();
      }
    }
  }

  void consultarGrupoConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== CONSULTAR GRUPO DE INVESTIGACION (READ) ===";

    NodoGrupo *act = multilistas.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay grupos de investigacion registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Grupos disponibles para consulta:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->grupo->nroGrupo);
        gotoxy(12, y);
        string estadoTxt = "[ACTIVO]";
        if (!act->grupo->activo) {
          estadoTxt = "[INACTIVO]";
        }
        cout << n << ". " << estadoTxt << " " << act->grupo->nombreGrupo << " ("
             << act->grupo->nroGrupo << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->grupo->nroGrupo);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el ID/codigo del "
                         "grupo a consultar (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit(entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        NodoGrupo *nodoG = multilistas.buscarGrupo(codigoSel);
        if (nodoG != NULL && nodoG->grupo != NULL) {
          menuDetalleGrupo(nodoG);
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "No se encontro ningun grupo con el codigo/numero: "
               << entrada;
          pausar();
        }
      }
    }
  }

  void consultarProduccionPorAnioGrupoConsola() {
    dibujarMarco();
    gotoxy(12, 5);
    cout << "=== CONSULTAR PRODUCCION POR ANIO - GRUPO ===";

    NodoGrupo *act = multilistas.getCabeza();
    if (act == NULL) {
      gotoxy(12, 8);
      cout << "No hay grupos de investigacion registrados en el sistema.";
      pausar();
    } else {
      gotoxy(12, 7);
      cout << "Grupos disponibles para consulta:";
      int y = 9;
      int n = 1;
      vector<string> codigos;
      while (act != NULL && y < 19) {
        codigos.push_back(act->grupo->nroGrupo);
        gotoxy(12, y);
        cout << n << ". " << act->grupo->nombreGrupo << " ("
             << act->grupo->nroGrupo << ")";
        y++;
        n++;
        act = act->sig;
      }
      while (act != NULL) {
        codigos.push_back(act->grupo->nroGrupo);
        act = act->sig;
      }

      cout << "\n\n";
      string entrada =
          leerLineaTexto("  Ingrese el numero de lista o el ID/codigo del "
                         "grupo a consultar (0 para cancelar): ",
                         false);

      if (!entrada.empty() && entrada != "0") {
        string codigoSel = "";
        bool esNum = true;
        size_t idxCh = 0;
        while (idxCh < entrada.size()) {
          if (!isdigit((unsigned char)entrada[idxCh])) {
            esNum = false;
          }
          idxCh++;
        }

        if (esNum) {
          int numSel = atoi(entrada.c_str());
          if (numSel >= 1 && numSel <= (int)codigos.size()) {
            codigoSel = codigos[numSel - 1];
          }
        }

        if (codigoSel.empty()) {
          codigoSel = entrada;
        }

        NodoGrupo *nodoG = multilistas.buscarGrupo(codigoSel);
        if (nodoG != NULL && nodoG->grupo != NULL) {
          mostrarProduccionPorAnioGrupo(nodoG);
        } else {
          dibujarMarco();
          gotoxy(12, 8);
          cout << "No se encontro ningun grupo con el codigo/numero: "
               << entrada;
          pausar();
        }
      }
    }
  }

  void menuGestionGrupos() {
    int opcion = 0;
    while (opcion != 8) {
      dibujarMarco();
      gotoxy(15, 6);
      cout << "--- GESTION DE GRUPOS ---";
      gotoxy(15, 8);
      cout << "1. Listar Grupos";
      gotoxy(15, 9);
      cout << "2. Consultar Grupo";
      gotoxy(15, 10);
      cout << "3. Consultar Produccion por Anio";
      gotoxy(15, 11);
      cout << "4. Crear Grupo";
      gotoxy(15, 12);
      cout << "5. Modificar Grupo";
      gotoxy(15, 13);
      cout << "6. Eliminar Grupo";
      gotoxy(15, 14);
      cout << "7. Activar / Desactivar Grupo";
      gotoxy(15, 15);
      cout << "8. Regresar al Menu Principal";
      gotoxy(15, 17);
      cout << "Seleccione una opcion [1-8]: ";

      cin >> opcion;
      if (cin.fail()) {
        cin.clear();
        cin.ignore(10000, '\n');
        opcion = 0;
      } else {
        cin.ignore(10000, '\n');
      }

      if (opcion == 1) {
        listarGrupos();
      } else if (opcion == 2) {
        consultarGrupoConsola();
      } else if (opcion == 3) {
        consultarProduccionPorAnioGrupoConsola();
      } else if (opcion == 4) {
        crearGrupo();
      } else if (opcion == 5) {
        modificarGrupoConsola();
      } else if (opcion == 6) {
        eliminarGrupoConsola();
      } else if (opcion == 7) {
        alternarEstadoGrupoConsola();
      } else if (opcion == 8) {
        // Regresar al menu principal
      } else {
        gotoxy(15, 19);
        cout << "Opcion no valida.";
        pausar();
      }
    }
  }

  // =========================================================
  // MENU PRINCIPAL
  // =========================================================

  void menuPrincipal() {

    int opcion = 0;

    while (opcion != 6) {

      dibujarMarco();

      gotoxy(15, 6);
      cout << "1. Gestionar Investigadores";
      gotoxy(15, 7);
      cout << "2. Gestionar Grupos";
      gotoxy(15, 8);
      cout << "3. Reportes y Analisis";
      gotoxy(15, 9);
      cout << "4. Cargar Datos";
      gotoxy(15, 10);
      cout << "5. Guardar Datos";
      gotoxy(15, 11);
      cout << "6. Salir";
      gotoxy(15, 13);
      cout << "Seleccione una opcion: ";

      cin >> opcion;

      if (cin.fail()) {
        cin.clear();
        cin.ignore(10000, '\n');
        opcion = 0;
      } else {
        cin.ignore(10000, '\n');
      }

      if (opcion == 1) {

        // =================================================
        // SUBMENU GESTIONAR INVESTIGADORES
        // =================================================

        menuGestionInvestigadores();

      } else if (opcion == 2) {

        // =================================================
        // SUBMENU GESTIONAR GRUPOS
        // =================================================

        menuGestionGrupos();
      } else if (opcion == 3) {

        // =================================================
        // REPORTES ANALITICOS Y GESTION DE PRODUCTOS UNICOS
        // =================================================

        menuReportesEstadisticos();
      } else if (opcion == 4) {

        // =================================================
        // CARGAR DATOS
        // =================================================

        menuCargarDatos();
      } else if (opcion == 5) {

        // =================================================
        // GUARDAR DATOS
        // =================================================

        dibujarMarco();
        gotoxy(15, 6);
        cout << "--- GUARDAR DATOS ---";

        bool investigadoresOK = persistencia.guardarInvestigadores(listasInv);

        bool gruposOK = persistencia.guardarGrupos(multilistas);

        gotoxy(15, 9);

        if (investigadoresOK && gruposOK) {

          cout << "Todos los datos fueron "
               << "guardados correctamente.";
        } else {

          cout << "Ocurrio un error al guardar "
               << "los datos.";
        }

        pausar();
      } else if (opcion == 6) {

        // =================================================
        // SALIR
        // =================================================

        dibujarMarco();
        gotoxy(15, 8);
        cout << "--- SALIDA DEL SISTEMA ---";
        gotoxy(15, 10);
        cout << "Tipo de salida: Cierre normal desde menu principal.";
        gotoxy(15, 12);
        cout << "Deteniendo proceso scraper (si esta activo)...";
        lectorWeb.cerrarScraperNormal();
        gotoxy(15, 14);
        cout << "Servicios finalizados con exito.";
        gotoxy(15, 16);
        cout << "Saliendo del sistema...";
        Sleep(800);
      } else {

        // =================================================
        // OPCION INVALIDA
        // =================================================

        gotoxy(15, 14);
        cout << "Opcion no valida.";
        pausar();
      }
    }
  }
};

// =========================================================================
// FUNCION PRINCIPAL
// =========================================================================

int main() {

#ifdef _WIN32

  SetConsoleOutputCP(CP_UTF8);

  LectorArchivosYWeb::registrarManejadorConsola();

#endif

  MotorConsolaC motor;

  // ---------------------------------------------------------
  // CARGA DE DATOS INICIAL
  // ---------------------------------------------------------
  // Si existen los archivos de persistencia (investigadores.txt y
  // grupos.txt), se lee la informacion contenida en ellos.
  // De lo contrario, se carga la semilla normal como habitualmente.
  // ---------------------------------------------------------

  if (motor.existenArchivosPersistencia()) {
    if (!motor.cargarPersistencia()) {
      motor.iniciarSemilla();
    }
  } else {
    motor.iniciarSemilla();
  }

  // ---------------------------------------------------------
  // INICIAR MENU
  // ---------------------------------------------------------

  motor.menuPrincipal();

  return 0;
}
