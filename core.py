import fitz
import re
import sys
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
 
def extraer_info_certificado_Opened(archivo_stream):
    try:
        # Leer desde memoria, no desde disco
        doc = fitz.open(stream=archivo_stream, filetype="pdf")
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

def extraer_info_certificado_Esri(ruta_pdf):
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

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/api/extraer', methods=['POST'])
def procesar_certificado():
    try:
        # Validar si el request contiene archivos (multipart/form-data)
        if 'archivos' not in request.files:
            return jsonify({"error": "No se encontraron archivos en la petición."}), 400

        archivos = request.files.getlist('archivos')
        tipo_cert = request.form.get('tipo') # El tipo ahora viene en el form-data

        if not tipo_cert:
            return jsonify({"error": "Se requiere especificar el 'tipo' (opened o esri)."}), 400

        resultados_globales = []

        for archivo in archivos:
            archivo_stream = archivo.read()
            
            if tipo_cert.lower() == 'opened':
                resultado = extraer_info_certificado_Opened(archivo_stream)
            elif tipo_cert.lower() == 'esri':
                resultado = extraer_info_certificado_Esri(archivo_stream)
            else:
                return jsonify({"error": f"Tipo de parser '{tipo_cert}' no implementado."}), 400

            # Validar error interno de la función
            if "error" in resultado:
                return jsonify({"error": f"Error procesando {archivo.filename}: {resultado['error']}"}), 500

            # Inyectar el nombre del archivo para mapear en el frontend
            resultado['nombre_archivo'] = archivo.filename
            resultados_globales.append(resultado)

        return jsonify(resultados_globales), 200

    except Exception as e:
        return jsonify({"error": f"Excepción en servidor: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)