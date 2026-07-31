# Opened ESRI - Sistema de Homologación de Electivas

**Universidad de Manizales — Facultad de Ciencias e Ingeniería**  
**Autores:** Juan David Gomez Vallejo & Diana Milena Giraldo Valencia

---

## Visión General del Proyecto

**Opened ESRI** es una solución integral basada en software para la automatización del proceso de **homologación de asignaturas electivas** para los programas de pregrado y posgrado de la Universidad de Manizales.

El sistema procesa certificados digitales emitidos por las plataformas **Opened** y **ESRI**, extrae la información relevante de forma determinística mediante procesamiento de documentos PDF, realiza la homologación de créditos y códigos de asignaturas según el programa académico de destino, actualiza el histórico oficial en Excel y genera la resolución administrativa en formato Word (`.docx`) lista para expedición, anexando los soportes digitales rasterizados en alta resolución.

---

## Características Principales

- **Soporte Multi-Proveedor (Opened & ESRI):** Extracción automatizada adaptada a la estructura de certificados de ambas plataformas.
- **Asignación Dinámica de Códigos y Créditos:** Matriz de programas y electivas (*Electiva I*, *Electiva II*, *Electiva III*, *Electiva IV*) que mapea automáticamente los códigos institucionales de asignatura y los créditos correspondientes.
- **Validación Determinística de Seguridad:** Verificación de integridad de nombres de estudiantes por lote para evitar homologaciones cruzadas.
- **Generación Automática de Documentos Word (`.docx`):** Plantillas institucionales personalizadas (`resolucionlimpia.docx` y `resolucionlimpiaEsri.docx`) con tablas dinámicas combinadas (*merge*) y renderizado de anexos PDF a imágenes PNG.
- **Control de Consecutivos en Excel:** Lectura y escritura asíncrona del historial oficial en `FCI & RESOLUCIONES 2025.xlsx`.
- **Interfaz UI/UX Moderna:** Notificaciones flotantes tipo Toast (sin popups emergentes molestos), filtrado dinámico de electivas por programa, botón de acción protegido por validación y auto-reset de formulario.

---

## Tecnologías Utilizadas

### Backend
- **Python 3.12**
- **Flask**: Framework web para la arquitectura API REST y control de sesión.
- **PyMuPDF (`fitz`)**: Extracción de texto PDF y rasterización de páginas a imágenes PNG (150 DPI).
- **`python-docx`**: Inyección de variables, manipulación de tablas Word y adición de anexos.
- **`openpyxl`**: Lectura y registro histórico de consecutivos en libros de cálculo Excel (`.xlsx`).
- **Werkzeug**: Encriptación de contraseñas (`scrypt`) y manejo seguro de archivos subidos.

### Frontend
- **HTML5 & Vanilla CSS3**: Estilos adaptativos, variables CSS, notificaciones Toast y segmentador táctil.
- **Vanilla JavaScript (ES6+)**: Consumo de API mediante `fetch`, manipulación dinámica del DOM, gestión de archivos en memoria sin librerías pesadas.

---

## Estructura del Proyecto

```text
ProyectOpenedEsri/
│
├── core.py                        # Servidor Flask y controladores de API / rutas
├── requirements.txt               # Lista de dependencias del proyecto
├── README.md                      # Documentación principal del repositorio
├── usuarios.json                  # Registro seguro de usuarios y contraseñas (hash)
├── contador_resolucion.txt        # Registro auxiliar de conteo
│
├── services/                      # Módulos de servicios y lógica de negocio
│   ├── extractor_pdf.py           # Parsers PDF para Opened y ESRI
│   ├── generador_doc.py           # Generador de resoluciones Word y rasterizado de anexos
│   └── resolucion_excel.py        # Gestión de consecutivos e historial en Excel
│
├── documentos/                    # Plantillas y libros institucionales
│   ├── resolucionlimpia.docx      # Plantilla Word para homologaciones Opened
│   ├── resolucionlimpiaEsri.docx  # Plantilla Word para homologaciones ESRI
│   ├── FCI & RESOLUCIONES 2025.xlsx # Libro Excel de control histórico
│   ├── certificadosOpened/        # Certificados PDF de prueba (Opened)
│   └── certificadosESRI/          # Certificados PDF de prueba (ESRI)
│
├── static/                        # Archivos estáticos de la interfaz web
│   ├── app.js                     # Lógica cliente (Toast, AJAX, formulario dinámico)
│   ├── estilos.css                # Hoja de estilos general y notificaciones
│   ├── logoum.png                 # Logo Universidad de Manizales
│   ├── opened.png                 # Logo Opened
│   └── banner.png                 # Banner superior
│
└── templates/                     # Plantillas HTML
    ├── login.html                 # Pantalla de autenticación y registro
    ├── index.html                 # Panel principal de gestión de homologaciones
    └── resolucion.html            # Vista preliminar HTML de resoluciones
```

---

## Matriz de Asignaturas y Códigos

El sistema asocia automáticamente la materia a homologar y el programa universitario con su respectivo código institucional de asignatura:

| Programa de Destino | Electiva I | Electiva II | Electiva III | Electiva IV |
| :--- | :---: | :---: | :---: | :---: |
| **Ingeniería en Sistemas y Telecomunicaciones Presencial** | `C5808002` | `C5909002` | — | — |
| **Ingeniería en Sistemas y Telecomunicaciones Virtual** | `CV050036` | `CV050039` | — | — |
| **Ingeniería en Analítica de Datos Presencial** | `IA030606` | `IA030707` | `IA030807` | — |
| **Ingeniería en Analítica de Datos Virtual** | `10410606` | `10410706` | `10410805` | — |
| **Ingeniería Logística Presencial** | `IL020403` | `IL020603` | `IL020703` | `IL020803` |
| **Ingeniería Logística Virtual** | `10310403` | `10310603` | `10310704` | `10310803` |
| **Ingeniería en Seguridad de la Información Presencial** | `IS040606` | `IS040804` | — | — |
| **Ingeniería en Seguridad de la Información Virtual** | `10510606` | `10510804` | — | — |
| **Ingeniería Industrial** | `10710405` | `10710503` | — | — |
| **Especialización en Sistemas de Información Geográfica** | `83060204` | `83060207` | — | — |
| **Maestría en Tecnologías de la Información Geográfica** | `M8040106` | `M8040206` | — | — |
| **Maestría en Educación y Transformación Digital** | `M1510102` | `M1510103` | `M1510204` | `M1510303` |

---

## Instalación y Despliegue

### Requisitos Previos
- Python 3.10 o superior.

### Pasos de Instalación
1. Clonar el repositorio:
   ```bash
   git clone "link"
   cd ProyectOpenedEsri
   ```
2. Activar el entorno virtual:
   ```bash
   # En Windows:
   .\venv\Scripts\activate
   ```
3. Instalar las dependencias requeridas:
   ```bash
   pip install -r requirements.txt
   ```
4. Iniciar la aplicación web:
   ```bash
   python core.py
   ```
5. Acceder a la interfaz desde un navegador web en: `http://localhost:5000`

---

## Créditos y Licencia

Desarrollado para la **Universidad de Manizales**.  
- **Autores:** Juan David Gomez Vallejo & Diana Milena Giraldo Valencia.
