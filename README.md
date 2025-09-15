# Benchmark: Evaluador de LLMs (ARC + Mazes) con Django y LM Studio

> **Stack**: Python 3.12.5 · Django 5.2 · HTMX (polling) · LM Studio (API OpenAI-compatible)  
> **Objetivo**: Evaluar modelos de lenguaje locales (vía LM Studio) contra dos dominios:
> 1) **ARC-AGI** (train/evaluation), y 2) **Mazes** (laberintos TXT → JSON), con métricas, vistas de detalle y ejecución en lote (incl. ejecución *live* con progreso).

---

## Tabla de contenidos

- [Visión general](#visión-general)
- [Arquitectura](#arquitectura)
  - [Estructura de carpetas](#estructura-de-carpetas)
  - [Apps y responsabilidades](#apps-y-responsabilidades)
  - [Flujo de datos](#flujo-de-datos)
- [Instalación](#instalación)
  - [Requisitos](#requisitos)
  - [Setup del entorno](#setup-del-entorno)
  - [Variables y ajustes](#variables-y-ajustes)
- [Datos](#datos)
  - [ARC](#arc)
  - [Mazes](#mazes)
- [Uso](#uso)
  - [LM Studio: cargar modelo y API](#lm-studio-cargar-modelo-y-api)
  - [Interfaz web](#interfaz-web)
    - [Inicio](#inicio)
    - [ARC](#arc-1)
    - [Mazes](#mazes-1)
  - [Ejecución en lote (live)](#ejecución-en-lote-live)
- [Métricas](#métricas)
  - [ARC](#arc-2)
  - [Mazes](#mazes-2)
- [Prompts y parsing](#prompts-y-parsing)
- [Rendimiento y contexto](#rendimiento-y-contexto)
- [Resolución de problemas](#resolución-de-problemas)
- [Extensiones sugeridas](#extensiones-sugeridas)
- [Licencia](#licencia)

---

## Visión general

Este proyecto es un **banco de pruebas** para evaluar LLMs (cargados localmente en **LM Studio**) en dos dominios:

- **ARC-AGI**: se construye un *few-shot* leave-one-out (K=1) por par *train[i]* y se evalúa la salida del modelo contra el *expected grid* con métricas de exactitud a nivel de celda y exact match.  
- **Mazes**: convierte laberintos **TXT → JSON**, detecta `start/goal`, normaliza la codificación (1=libre/0=pared), y le pide al LLM una secuencia **UDLR**. Se simula, se computa el mejor camino (BFS) y se reporta *success/efficiency/steps*. La vista de evaluación **pinta la ruta** devuelta por el modelo como overlay.

Incluye además un **módulo de ejecuciones** (*runs*) para lanzar evaluación completa (dataset entero) en *background* (thread) con **progreso live** (HTMX polling).

---

## Arquitectura

### Estructura de carpetas

```
benchmark/
├── config/                     # urls y settings del proyecto Django
├── evaluations/
│   ├── core/
│   │   └── lmstudio.py         # cliente HTTP a LM Studio (OpenAI-like)
│   ├── arc/
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── metrics.py
│   │   └── services/
│   │       └── arc.py
│   ├── maze/
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── metrics.py
│   │   └── services/
│   │       └── maze.py
│   ├── runs/
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py
│   └── templates/
│       ├── base.html
│       ├── arc/
│       ├── maze/
│       └── runs/
├── static/
│   ├── css/app.css
│   └── img/favicon.ico
├── data/
│   ├── arcagi2/
│   │   ├── train/
│   │   └── evaluation/
│   ├── maze_converted/
│   ├── maze/
│   ├── perfect/
│   └── imperfect/
├── manage.py
└── requirements.txt
```

### Apps y responsabilidades

- **core.lmstudio**: cliente HTTP a LM Studio.  
- **arc**: carga JSONs de ARC, construye prompts y parsea matrices.  
- **maze**: conversión TXT→JSON, BFS, prompts y parsing de movimientos.  
- **runs**: persistencia y vistas live de ejecuciones.

---

## Instalación

### Requisitos

- Python 3.12.5  
- Django 5.2  
- LM Studio

### Setup del entorno

```bash
python manage.py runserver
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations
python manage.py makemigrations evaluations  

Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Include *.pyc,*.pyo | Remove-Item -Force

export PYTHONDONTWRITEBYTECODE=1
```

### Variables y ajustes

En `settings.py`:

```python
LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
STATIC_URL = "static/"
STATICFILES_DIRS = [ BASE_DIR / "static" ]
```

---

## Datos

- **ARC**: JSONs en `data/arcagi2/train/` y `evaluation/`.  
- **Mazes**: TXT en `data/maze/`, convertidos a JSON en `data/maze_converted/`.

---

## Uso

### LM Studio

Carga un modelo (ej. *Qwen2.5-7B-Instruct-1M*) y activa **Start Server**.

### Interfaz web

- **Inicio**: `/`  
- **ARC**: `/arc/` → detalle, evaluar, dataset live.  
- **Mazes**: `/maze/` → herramientas TXT→JSON, detalle con preview y evaluación con ruta overlay.  
- **Runs**: `/run/<id>/` → progreso live.

---

## Métricas

- **ARC**: exact match, cell accuracy, latencia.  
- **Mazes**: success, efficiency, pasos, shortest path.

---

## Resolución de problemas

- `NoReverseMatch`: asegura `app_name` en urls y `namespace`.  
- `favicon.ico` cae en maze: sirve favicon desde `/static/`.  
- `no such table`: ejecutar `python manage.py migrate`.  
- `Trying to keep ... tokens`: usar modelo con ventana larga o RLE.

---

## Licencia

### ARC Dataset

https://arcprize.org/arc-agi/2/

### Mazes Dataset

https://www.kaggle.com/datasets/mexwell/maze-dataset