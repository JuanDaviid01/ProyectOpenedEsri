import fitz
import re
import sys
import json

def extraer_info_certificado_Opened(ruta_pdf):
    try:
        doc = fitz.open(ruta_pdf)
        # Extraemos texto de todas las páginas
        texto = ""
        for pagina in doc:
            texto += pagina.get_text("text")
        
        # Normalización técnica: eliminamos saltos de línea y espacios redundantes
        texto_limpio = re.sub(r'\s+', ' ', texto)

        # Diccionario de patrones optimizados
        patrones = {
            # Busca lo que hay entre "constar que:" y "estudiante"
            "estudiante": r"(?i)constar que:\s*(.*?)\s*estudiante",
            # Busca lo que hay entre "Mooc:" y "con una nota"
            "curso": r"(?i)Mooc:\s*(.*?)\s*con una nota",
            # Tu regex perfecto para la nota
            "nota": r"(?i)nota final de[:\s]+(\d[.,]\d{1,2})",
            # Busca el formato de fecha al final de la frase de entrega
            "fecha": r"(\d{1,2}\s+días\s+del\s+mes\s+de\s+\w+\s+del\s+\d{4})"
        }

        resultados = {}
        for llave, regex in patrones.items():
            match = re.search(regex, texto_limpio)
            if match:
                resultados[llave] = match.group(1).strip()
            else:
                # Fallback específico para la nota si el regex principal falla
                if llave == "nota":
                    candidatos = re.findall(r"\b[0-5][.,]\d{1,2}\b", texto_limpio)
                    resultados[llave] = candidatos[0] if candidatos else "N/A"
                else:
                    resultados[llave] = "N/A"

        return resultados

    except Exception as e:
        return {"error": str(e)}



if __name__ == "__main__":
    if len(sys.argv) > 1:
        data = extraer_info_certificado_Opened(sys.argv[1])
        # Impresión limpia en formato JSON
        print(json.dumps(data, indent=4, ensure_ascii=False))
    else:
        print("Error: Proporciona la ruta del PDF.")

















# ya extrae las notas de los certificados de Opened tengo que hacer otra funcion para los certificados de Esri
# tengo que guardar los datos en variables para hacer comprobaciones de fecha, curso etc...
# con diana tengo que gestionar el llamado a las funciones apra que se ejecuten desde la interfaz que ella esta diseñando
# https://gemini.google.com/app/687588a7b4006c90?is_sa=1&is_sa=1&android-min-version=301356232&ios-min-version=322.0&campaign_id=bkws&pt=9008&mt=8&ct=p-growth-sem-bkws&gad_campaignid=21991937965