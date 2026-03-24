import os
import io
import re
import json
import fitz
import tempfile
import locale
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from services import extractor_pdf, generador_doc

app = Flask(__name__)
CORS(app)

ARCHIVO_CONTADOR = "contador_resolucion.txt"

def obtener_siguiente_resolucion(base_inicial=1048):
    """
    Lee el archivo local, incrementa el contador y lo sobrescribe.
    """
    # Si el archivo no existe, lo crea con la base inicial
    if not os.path.exists(ARCHIVO_CONTADOR):
        with open(ARCHIVO_CONTADOR, "w") as f:
            f.write(str(base_inicial))
        return str(base_inicial)
    
    # Lee el valor actual
    with open(ARCHIVO_CONTADOR, "r") as f:
        actual = int(f.read().strip())
    
    # Incrementa
    siguiente = actual + 1
    
    # Sobrescribe con el nuevo valor
    with open(ARCHIVO_CONTADOR, "w") as f:
        f.write(str(siguiente))
        
    return str(siguiente)


@app.route("/")
def index():
    return render_template("index.html")
@app.route("/api/extraer", methods=["POST"])
def procesar_certificado():
    try:
        if "archivos" not in request.files:
            return jsonify({"error": "No se encontraron archivos en la petición."}), 400

        archivos = request.files.getlist("archivos")
        tipo_certificado = request.form.get("tipo_certificado", "").strip().lower()

        if not tipo_certificado:
            return jsonify({"error": "Se requiere especificar el tipo_certificado (opened o esri)."}), 400

        resultados_globales = []
        for archivo in archivos:
            # Validación de payload vacío
            if archivo.filename == '':
                continue

            archivo_stream = archivo.read()

            # Delegación al dispatcher (Patrón Strategy)
            resultado = extractor_pdf.ejecutar_extractor(archivo_stream, tipo_certificado)

            # Manejo de errores propagados desde el servicio
            if "error" in resultado:
                return jsonify({
                    "error": f"Error procesando {archivo.filename}: {resultado['error']}"
                }), 400 # Cambiado a 400 (Bad Request) si el parser no existe

            resultado["nombre_archivo"] = archivo.filename
            resultados_globales.append(resultado)

        if not resultados_globales:
            return jsonify({"error": "No se enviaron archivos válidos para procesar."}), 400

        return jsonify(resultados_globales), 200

    except Exception as e:
        return jsonify({"error": f"Excepción en servidor: {str(e)}"}), 500

@app.route("/api/generar-resolucion-final", methods=["POST"])
def generar_resolucion_final():
    try:
        if "archivos" not in request.files:
            return jsonify({"error": "No se encontraron archivos para anexar."}), 400

        archivos = request.files.getlist("archivos")
        codigo_estudiante = request.form.get("codigo_estudiante", "").strip()
        tipo_certificado = request.form.get("tipo_certificado", "").strip().lower()
        resultados_json = request.form.get("resultados", "")

        if not all([codigo_estudiante, tipo_certificado, resultados_json]):
            return jsonify({"error": "Faltan parámetros obligatorios en el form-data."}), 400

        resultados = json.loads(resultados_json)
        if not resultados:
            return jsonify({"error": "La lista de resultados está vacía."}), 400

        primer_resultado = resultados[0]
        fecha_extraida = primer_resultado.get("fecha", "")

        patron_fecha = re.search(r"(\d{1,2})\s+días\s+del\s+mes\s+de\s+(\w+)\s+del\s+(\d{4})", fecha_extraida, re.IGNORECASE)
        dia_constancia, mes_constancia, anio_constancia = patron_fecha.groups() if patron_fecha else ("", "", "")

        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8') 
        fecha_actual = datetime.now().strftime("%d de %B de %Y")

        numero_resolucion = obtener_siguiente_resolucion()

        # Payload de negocio
        datos = {
            "numero_resolucion": numero_resolucion,
            "fecha_resolucion": fecha_actual,
            "nombre_estudiante": primer_resultado.get("estudiante", "N/A"),
            "codigo_estudiante": codigo_estudiante,
            "documento_estudiante": codigo_estudiante,
            "programa": "Ingeniería de Sistemas y Telecomunicaciones",
            "numero_resolucion_derogada": "1090",
            "fecha_resolucion_derogada": fecha_actual,
            "nombre_curso": primer_resultado.get("curso", "N/A"),
            "nota_curso": primer_resultado.get("nota", "N/A"),
            "dia_constancia": dia_constancia,
            "mes_constancia": mes_constancia,
            "anio_constancia": anio_constancia,
        }

        cursos = [{
            "periodo": "2025-2",
            "asignatura_opened": item.get("curso", "N/A"),
            "nota": item.get("nota", "N/A"),
            "nota_definitiva": item.get("nota", "N/A"),
            "asignatura_homologada": "ELECTIVA II",
            "codigo_asignatura": "C5909002",
            "creditos": "3"
        } for item in resultados]

        # Context Manager para I/O
        with tempfile.TemporaryDirectory() as carpeta_temp:
            ruta_temp = Path(carpeta_temp)
            nombre_docx = f"Resolucion_{codigo_estudiante}_FINAL.docx"
            
            # 1. Descarga de buffers PDF al FS temporal
            rutas_pdfs_anexos = []
            for archivo in archivos:
                ruta_destino = ruta_temp / secure_filename(archivo.filename)
                archivo.save(ruta_destino)
                if ruta_destino.suffix.lower() == ".pdf":
                    rutas_pdfs_anexos.append(str(ruta_destino))
                else:
                    return jsonify({"error": f"Archivo no admitido: {archivo.filename}"}), 400

            # 2. Pipeline Word (Genera el DOCX e incrusta las imágenes de los PDFs internamente)
            ruta_docx_final = generador_doc.generar_resolucion_word(
                datos, cursos, str(ruta_temp), nombre_docx, rutas_pdfs_anexos
            )

            # 3. Volcado a RAM para liberar lock del FS
            with open(ruta_docx_final, "rb") as f_in:
                docx_buffer = io.BytesIO(f_in.read())

        # 4. Envío binario desde memoria
        return send_file(
            docx_buffer, 
            as_attachment=True, 
            download_name=nombre_docx,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        return jsonify({"error": f"Error generando resolución final: {str(e)}"}), 500
@app.route("/descargar")
def descargar_archivo():
    ruta = request.args.get("ruta")

    if not ruta or not os.path.exists(ruta):
        return "Archivo no encontrado", 404

    return send_file(ruta, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)