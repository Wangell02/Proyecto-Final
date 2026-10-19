# PLAN DE IMPLEMENTACIÓN: PROCESAMIENTO INTELIGENTE DE ARCHIVOS (PDF Y CSV) Y SISTEMA DE CONTROL DE PRODUCTOS DUPLICADOS

**Proyecto:** PEA-i (Programa Estadístico de Análisis de Investigación)  
**Módulos Afectados:** `DLDD-MAFF-JDLA.cpp` y `DLDD-MAFF-JDLA.py`  
**Objetivo General:**  
1. **Fase Previa (COMPLETADA):** Implementación en C++ del sistema de detección, consolidación y control de productos duplicados idéntico al que ya opera en Python (`canonical_key(titulo), anio`), permitiendo que el aplicativo de consola relacione productos compartidos entre grupos e investigadores sin duplicar métricas en estadísticas ni en reportes.  
2. **Etapa 1 (COMPLETADA):** Procesamiento y extracción inteligente desde archivos PDF (CvLAC, GrupLAC y lotes mixtos).  
3. **Etapa 2 (COMPLETADA):** Procesamiento y extracción inteligente desde archivos CSV y formatos planos/estructurados.

---

## 1. Análisis Técnico del Control de Productos Duplicados

### 1.1. El Mecanismo Existente en Python (`DLDD-MAFF-JDLA.py`)

En el aplicativo de Python existen tres puntos críticos donde se controla la duplicidad de productos:

1. **En el Scraper de Grupos (`WebScraper._find_group_products`):**
   Desduplica internamente los productos del grupo usando:
   `key = (clean_text(product.titulo).casefold(), int(product.anio or 0))`
2. **En el Servicio Global de Estadísticas (`ApplicationService.statistics`):**
   Recolecta todos los productos de todos los investigadores y todos los grupos, unificándolos bajo la firma canónica:
   `key = (canonical_key(titulo), anio)`
3. **En el Módulo Gráfico de Estadísticas (`PEAApp.build_statistics`):**
   Construye un diccionario `unique_products_dict` indexado por `key = (canonical_key(titulo), anio)` que no solo desduplica, sino que **fusiona los metadatos contextuales**: si el producto fue cargado desde un investigador y luego aparece en un grupo (o viceversa), preserva tanto `_grupo_nombre` como `_autor_nombre`, garantizando que en el conteo estadístico global solo cuente como 1 producto único.

### 1.2. Implementación Realizada en C++ (`DLDD-MAFF-JDLA.cpp`)

Se implementaron con éxito los componentes de deduplicación en C++:
- **`canonicalKey(const string &texto)`:** Normalización canónica ASCII insensible a mayúsculas, signos y tildes UTF-8 en español (á, é, í, ó, ú, ñ).
- **`generarFirmaProducto(const string &titulo, int anio)`:** Generador determinista de clave de producto (`canonicalKey(titulo) + "#" + anio`).
- **`GestorProductosUnicos`:** Estructura que recorre en una sola pasada los investigadores independientes, los grupos propios y los integrantes de cada grupo, consolidando productos bajo firmas únicas, registrando sus apariciones y complementando metadatos.
- **`menuReportesEstadisticos()`:** Submenú interactivo en la Opción 3 de la consola para inspeccionar productos brutos, productos netos únicos, duplicados compartidos, distribución por categorías y distribución por año.

---

## 2. El Sistema Inteligente de 4 Capas (Compatibilidad con Productos Duplicados y Lotes)

```
┌────────────────────────────────────────────────────────────────────────┐
│ CAPA 1: GUARDIÁN DE IDENTIDAD INSTITUCIONAL (MINCIENCIAS GATEKEEPER)   │
│ Valida que el documento sea de investigación MinCiencias y no basura.  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CAPA 2: PARTICIONADOR Y DETECTOR POLIMÓRFICO DE LOTES                  │
│ Identifica fronteras de entidades y relaciones grupo-investigador.     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CAPA 3: NORMALIZADOR DINÁMICO DE ESQUEMAS Y LIMPIEZA DE PRODUCTOS      │
│ Aísla títulos puros (sin prefijos) y años normalizados de 4 dígitos.   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CAPA 4: MOTOR DE RESOLUCIÓN DE PRODUCTOS DUPLICADOS Y FUSIÓN RELACIONAL│
│ Aplica canonical_key(titulo)+anio; vincula a múltiples padres y unifica│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Estructura General del Plan de Implementación (3 Fases)

```
==========================================================================
FASE PREVIA: SISTEMA DE CONTROL DE PRODUCTOS DUPLICADOS EN C++ [COMPLETADA]
==========================================================================
  [x] P.1: Función de normalización canónica de cadenas en C++ (canonicalKey C++).
  [x] P.2: Generador de firmas únicas de productos: (titulo_normalizado, anio).
  [x] P.3: Clase GestorProductosUnicos en C++ para deduplicación global.
  [x] P.4: Función unificada de conteo y obtención de productos sin duplicados.
  [x] P.5: Vinculación con estadísticas y reportes de consola en C++.

==========================================================================
ETAPA 1: PROCESAMIENTO DE ARCHIVOS PDF (CvLAC, GrupLAC Y LOTES MIXTOS) [COMPLETADA]
==========================================================================
  [x] 1.1: Módulo Lector de Texto PDF con Segmentación de Páginas y Secciones.
  [x] 1.2: Motor de Partición Polimórfica (CvLAC único, GrupLAC único o Compilados).
  [x] 1.3: Extracción Heurística de Colecciones y Producción con Firma Canónica.
  [x] 1.4: Actualización de GUI Python (Panel de resumen individual y de lote).
  [x] 1.5: Actualización de Consola C++ (Drag & Drop + Ingesta por lote a Multilistas).
  [x] 1.6: Pruebas con PDFs individuales, múltiples y mixtos.

==========================================================================
ETAPA 2: PROCESAMIENTO DE ARCHIVOS CSV (TABLAS SIMPLES, MULTI-REGISTRO Y MIXTAS)
==========================================================================
  [ ] 2.1: Detector de Dialectos, Delimitadores (, ; \t) y Codificaciones.
  [ ] 2.2: Particionador de Filas y Enrutador de Esquemas (Investigador vs Grupo).
  [ ] 2.3: Mapeo Flexible por Alias y Ensamble con Resolución de Duplicados.
  [ ] 2.4: Actualización de GUI Python (Integración CSV con soporte de lotes).
  [ ] 2.5: Actualización de Consola C++ (Drag & Drop CSV + Ingesta por lote).
  [ ] 2.6: Pruebas con CSV de 1 entidad, múltiples entidades y mixtos.
==========================================================================
```

---

## 4. Matriz de Cumplimiento Estricto de Reglas de Programación

| Restricción | Motivo | Técnica Aplicada en la Implementación |
|---|---|---|
| **Sin `break`** | Ruptura abrupta | Banderas booleanas en la condición del ciclo: `while (i < cat.size() && !encontrado) { ... }` |
| **Sin `continue`** | Salto incondicional | Bloques condicionales explícitos anidados: `if (!existe) { ... }` |
| **Sin `switch`** | Tablas de salto | Árboles jerárquicos estructurados con `if`, `else if` y `else` (o `elif` en Python) |
| **Sin Operadores Ternarios** | Concisión en una línea | Asignaciones explícitas en bloques `if-else` de varias líneas |
| **Sin `return` en funciones `void`** | Retorno prematuro | Flujo secuencial natural hasta el fin del bloque sin sentencias `return` intermedias |
