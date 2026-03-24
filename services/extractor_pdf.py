# En services/extractor_pdf.py
import fitz
import re

def extraer_info_opened(archivo_stream):
    try:
        # Context manager para liberar recursos de memoria en I/O
        with fitz.open(stream=archivo_stream, filetype="pdf") as doc:
            texto = "".join(pagina.get_text("text") for pagina in doc)

        texto_limpio = re.sub(r"\s+", " ", texto)

        patrones = {
            "estudiante": r"(?i)constar que:\s*(.*?)\s*estudiante",
            "curso": r"(?i)Mooc:\s*(.*?)\s*con una nota",
            "nota": r"(?i)nota final de[:\s]+(\d[.,]\d{1,2})",
            "fecha": r"(\d{1,2}\s+días\s+del\s+mes\s+de\s+\w+\s+del\s+\d{4})"
        }

        resultados = {}
        for llave, regex in patrones.items():
            match = re.search(regex, texto_limpio)
            if match:
                resultados[llave] = match.group(1).strip()
            elif llave == "nota":
                candidatos = re.findall(r"\b[0-5][.,]\d{1,2}\b", texto_limpio)
                resultados[llave] = candidatos[0] if candidatos else "N/A"
            else:
                resultados[llave] = "N/A"

        return resultados

    except Exception as e:
        return {"error": str(e)}

def extraer_info_esri(archivo_stream):
    try:
        # Función aislada: lista para futuras mutaciones de parsing (ej. lectura de tablas/coordenadas)
        with fitz.open(stream=archivo_stream, filetype="pdf") as doc:
            texto = "".join(pagina.get_text("text") for pagina in doc)

        texto_limpio = re.sub(r"\s+", " ", texto)

        patrones = {
            "estudiante": r"(?i)constar que:\s*(.*?)\s*estudiante",
            "curso": r"(?i)Mooc:\s*(.*?)\s*con una nota",
            "nota": r"(?i)nota final de[:\s]+(\d[.,]\d{1,2})",
            "fecha": r"(\d{1,2}\s+días\s+del\s+mes\s+de\s+\w+\s+del\s+\d{4})"
        }

        resultados = {}
        for llave, regex in patrones.items():
            match = re.search(regex, texto_limpio)
            if match:
                resultados[llave] = match.group(1).strip()
            elif llave == "nota":
                candidatos = re.findall(r"\b[0-5][.,]\d{1,2}\b", texto_limpio)
                resultados[llave] = candidatos[0] if candidatos else "N/A"
            else:
                resultados[llave] = "N/A"

        return resultados

    except Exception as e:
        return {"error": str(e)}

def ejecutar_extractor(archivo_stream, tipo_certificado):
    """
    Dispatcher (Enrutador). Delega el stream a la estrategia de parsing correspondiente.
    """
    parsers = {
        "opened": extraer_info_opened,
        "esri": extraer_info_esri
    }
    
    # Sanitización de entrada y asignación de puntero a función
    extractor = parsers.get(tipo_certificado.strip().lower())
    
    if not extractor:
        return {"error": f"Parser no implementado para el tipo de certificado: '{tipo_certificado}'"}
        
    return extractor(archivo_stream)