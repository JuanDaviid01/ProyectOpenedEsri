# En services/extractor_pdf.py
# pyrefly: ignore [missing-import]
import fitz
import re
from datetime import datetime
import re

MESES_ES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, 
            "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}

def normalizar_fecha(fecha_raw, formato_origen):
    try:
        if formato_origen == "opened":
            match = re.search(r"(\d{1,2})\s+días\s+del\s+mes\s+de\s+(\w+)\s+del\s+(\d{4})", fecha_raw, re.IGNORECASE)
            if match:
                dia, mes_str, anio = match.groups()
                mes = MESES_ES.get(mes_str.lower(), 1)
                return f"{anio}-{mes:02d}-{int(dia):02d}"
                
        elif formato_origen == "esri":
            # Parsea strings tipo "March 9, 2026"
            dt = datetime.strptime(fecha_raw.strip(), "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
            
    except Exception:
        pass
    return fecha_raw

def extraer_info_opened(archivo_stream):
    try:
        with fitz.open(stream=archivo_stream, filetype="pdf") as doc:
            texto = "".join(pagina.get_text("text") for pagina in doc)

        texto_limpio = re.sub(r"\s+", " ", texto.replace('\xa0', ' '))

        resultados = {}

        # Extracción determinística por subcadenas para eludir fallos del autómata regex
        if "constar que:" in texto_limpio and "estudiante" in texto_limpio:
            bloque_posterior = texto_limpio.split("constar que:")[1]
            nombre_crudo = bloque_posterior.split("estudiante")[0]
            resultados["estudiante"] = nombre_crudo.strip(" :,-_")
        else:
            resultados["estudiante"] = "N/A"

        patrones = {
            "curso": r"(?i)Mooc:\s*(.*?)\s*con una nota",
            "nota": r"(?i)nota final de[:\s]+(\d+(?:[.,]\d{1,2})?)",
            "fecha": r"(\d{1,2}\s+días\s+del\s+mes\s+de\s+\w+\s+del\s+\d{4})"
        }

        for llave, regex in patrones.items():
            match = re.search(regex, texto_limpio)
            if match:
                resultados[llave] = match.group(1).strip()
            elif llave == "nota":
                candidatos = re.findall(r"\b[0-5](?:[.,]\d{1,2})?\b", texto_limpio)
                resultados[llave] = candidatos[0] if candidatos else "N/A"
            else:
                resultados[llave] = "N/A"
                
            if llave == "nota" and resultados[llave] != "N/A":
                try:
                    valor = float(resultados[llave].replace(',', '.'))
                    resultados[llave] = f"{valor:.2f}"
                except ValueError:
                    continue

        if resultados.get("fecha") != "N/A":
            resultados["fecha"] = normalizar_fecha(resultados["fecha"], "opened")
            
        return resultados

    except Exception as e:
        return {"error": str(e)}

def extraer_info_esri(archivo_stream):
    try:
        with fitz.open(stream=archivo_stream, filetype="pdf") as doc:
            texto = "".join(pagina.get_text("text") for pagina in doc)

        # Reemplazar espacios duros y caracteres no mapeados (ej: U+FFFD -> Ñ)
        texto_limpio = texto.replace('\xa0', ' ').replace('\ufffd', 'Ñ')
        resultados = {}

        # 1. ESTUDIANTE
        patron_estudiante = r"(?i)(?:recognizes|certifies)\s+that\s*\n?\s*(.*?)\s*\n?\s*(?:has\s+attended|has\s+successfully\s+completed|has\s+completed)"
        match_est = re.search(patron_estudiante, texto_limpio, re.DOTALL)
        if match_est:
            nombre = match_est.group(1).replace('\n', ' ').strip(" :,-_")
            resultados["estudiante"] = re.sub(r"\s+", " ", nombre).upper()
        else:
            resultados["estudiante"] = "N/A"

        # 2. CURSO
        patron_curso = r"(?i)(?:has\s+attended|has\s+completed)\s+(?:the\s+)?(?:web\s+|training\s+|instructor-led\s+)?course\s*\n?\s*(.*?)\s*\n?\s*(?=\d+\s*(?:hour|minute|day|hr|min)|Completed|Issued|Date|\Z)"
        match_cur = re.search(patron_curso, texto_limpio, re.DOTALL)
        if match_cur:
            curso_nombre = match_cur.group(1).replace('\n', ' ').strip(" :,-_")
            resultados["curso"] = re.sub(r"\s+", " ", curso_nombre)
        else:
            resultados["curso"] = "N/A"

        # 3. FECHA
        patron_fecha = r"(?i)(?:Completed|Issued)\s+on\s+([a-zA-Z]+\s+\d{1,2},\s+\d{4})"
        match_fec = re.search(patron_fecha, texto_limpio)
        if match_fec:
            fecha_raw = match_fec.group(1).strip()
            resultados["fecha"] = normalizar_fecha(fecha_raw, "esri")
        else:
            resultados["fecha"] = "N/A"

        # 4. NOTA (Aprobación cualitativa para certificados ESRI)
        resultados["nota"] = "Aprobado"

        return resultados

    except Exception as e:
        return {"error": str(e)}

def ejecutar_extractor(archivo_stream, tipo_certificado):
    parsers = {
        "opened": extraer_info_opened,
        "esri": extraer_info_esri
    }
    
    extractor = parsers.get(tipo_certificado.strip().lower())
    
    if not extractor:
        return {"error": f"Parser no implementado para el tipo de certificado: '{tipo_certificado}'"}
        
    return extractor(archivo_stream)