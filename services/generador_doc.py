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
    if not paragraph.text.strip():
        return

    texto_original = paragraph.text
    texto_nuevo = texto_original

    for variable, valor in reemplazos.items():
        patron = r"\{\{\s*" + re.escape(variable) + r"\s*\}\}"
        texto_nuevo = re.sub(patron, str(valor), texto_nuevo)

    if texto_nuevo != texto_original:
        paragraph.text = texto_nuevo

def reemplazar_texto_en_documento(doc, reemplazos):
    for paragraph in doc.paragraphs:
        reemplazar_texto_en_parrafo(paragraph, reemplazos)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    reemplazar_texto_en_parrafo(paragraph, reemplazos)

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