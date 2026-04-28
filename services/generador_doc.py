import re
import fitz  # PyMuPDF para rasterización
from pathlib import Path
from docx import Document
from docx.shared import Inches

def obtener_ruta_base():
    return Path(__file__).resolve().parent.parent

def cargar_plantilla():
    ruta = obtener_ruta_base() / "documentos" / "resolucionlimpia.docx"
    if not ruta.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {ruta}")
    return Document(ruta)

def reemplazar_texto_en_parrafo(paragraph, reemplazos):
    if paragraph.text.strip():
        for key in reemplazos:
            if key in paragraph.text:
                print(f"DEBUG: Clave '{key}' detectada en párrafo: '{paragraph.text[:50]}...'")

    for variable, valor in reemplazos.items():
        patron = r"\{\{\s*" + re.escape(variable) + r"\s*\}\}"
        
        match = re.search(patron, paragraph.text)
        if match:
            # print(f"DEBUG: Match exitoso para '{variable}'. Ejecutando reemplazo con '{valor}'")
            paragraph.text = re.sub(patron, str(valor), paragraph.text)

def reemplazar_texto_en_documento(doc, reemplazos):
    for p in doc.paragraphs:
        reemplazar_texto_en_parrafo(p, reemplazos)

    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                for p in c.paragraphs:
                    reemplazar_texto_en_parrafo(p, reemplazos)

    for s in doc.sections:
        for h in [s.header, s.footer]:
            for p in h.paragraphs:
                reemplazar_texto_en_parrafo(p, reemplazos)
            for t in h.tables:
                for r in t.rows:
                    for c in r.cells:
                        for p in c.paragraphs:
                            reemplazar_texto_en_parrafo(p, reemplazos)

def limpiar_filas_tabla(tabla, fila_inicial=2):
    while len(tabla.rows) > fila_inicial:
        tabla._tbl.remove(tabla.rows[-1]._tr)

def llenar_tabla_cursos(doc, cursos):
    if not doc.tables:
        return

    tabla = doc.tables[0]
    limpiar_filas_tabla(tabla, fila_inicial=2)
    for curso in cursos:
        fila = tabla.add_row().cells
        fila[0].text = str(curso.get("periodo", ""))
        fila[1].text = str(curso.get("asignatura_opened", ""))
        fila[2].text = str(curso.get("nota", ""))
        fila[3].text = str(curso.get("nota_definitiva", ""))
        fila[4].text = str(curso.get("asignatura_homologada", ""))
        fila[5].text = str(curso.get("codigo_asignatura", ""))
        fila[6].text = str(curso.get("creditos", ""))

def generar_resolucion_word(datos, cursos, carpeta_salida, nombre_salida, rutas_pdfs_anexos):
    doc = cargar_plantilla()
    
    # 1. Inyección de payload de negocio
    reemplazar_texto_en_documento(doc, datos)
    llenar_tabla_cursos(doc, cursos)

    # 2. Rasterización de anexos PDF a PNG y anexado al DOM del DOCX
    for ruta_pdf in rutas_pdfs_anexos:
        pdf_doc = fitz.open(ruta_pdf)
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            
            ruta_img_temp = Path(carpeta_salida) / f"temp_{Path(ruta_pdf).stem}_{page_num}.png"
            pix.save(str(ruta_img_temp))
            
            doc.add_page_break()
            doc.add_picture(str(ruta_img_temp), width=Inches(6.5))
            
        pdf_doc.close()

    # 3. Guardado final
    ruta_docx = Path(carpeta_salida) / nombre_salida
    doc.save(ruta_docx)

    return str(ruta_docx)