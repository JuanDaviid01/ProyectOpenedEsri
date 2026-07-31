import os
import io
import re
import json
import tempfile
import locale
import unicodedata
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for, make_response
from flask_cors import CORS
from services import extractor_pdf, generador_doc
from services.resolucion_excel import obtener_y_registrar_resolucion

def normalizar_texto(texto):
    if not texto:
        return ""
    texto_nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in texto_nfkd if not unicodedata.combining(c)]).lower().strip()

CODIGOS_ASIGNATURAS = {
    # 1. Sistemas y Telecomunicaciones Presencial
    "ingenieria en sistemas y telecomunicaciones presencial": {
        "electiva i": "C5808002",
        "electiva ii": "C5909002",
    },
    # 2. Sistemas y Telecomunicaciones Virtual
    "ingenieria en sistemas y telecomunicaciones virtual": {
        "electiva i": "CV050036",
        "electiva ii": "CV050039",
    },
    # 3. Analítica de datos presencial
    "ingenieria en analitica de datos presencial": {
        "electiva i": "IA030606",
        "electiva ii": "IA030707",
        "electiva iii": "IA030807",
    },
    # 4. Analítica de datos virtual
    "ingenieria en analitica de datos virtual": {
        "electiva i": "10410606",
        "electiva ii": "10410706",
        "electiva iii": "10410805",
    },
    # 5. Logística presencial
    "ingenieria logistica presencial": {
        "electiva i": "IL020403",
        "electiva ii": "IL020603",
        "electiva iii": "IL020703",
        "electiva iv": "IL020803",
    },
    # 6. Logística virtual
    "ingenieria logistica virtual": {
        "electiva i": "10310403",
        "electiva ii": "10310603",
        "electiva iii": "10310704",
        "electiva iv": "10310803",
    },
    # 7. Seguridad de la información presencial
    "ingenieria en seguridad de la informacion presencial": {
        "electiva i": "IS040606",
        "electiva ii": "IS040804",
    },
    # 8. Seguridad de la información virtual
    "ingenieria en seguridad de la informacion virtual": {
        "electiva i": "10510606",
        "electiva ii": "10510804",
    },
    # 9. Industrial
    "ingenieria industrial": {
        "electiva i": "10710405",
        "electiva ii": "10710503",
    },
    # 10. Especialización en SIG
    "especializacion en sistemas de informacion geografica": {
        "electiva i": "83060204",
        "electiva ii": "83060207",
    },
    # 11. Maestría en TIG
    "maestria en tecnologias de la informacion geografica": {
        "electiva i": "M8040106",
        "electiva ii": "M8040206",
    },
    # 12. Maestría en Educación y transformación digital
    "maestria en educacion y transformacion digital": {
        "electiva i": "M1510102",
        "electiva ii": "M1510103",
        "electiva iii": "M1510204",
        "electiva iv": "M1510303",
    }
}

app = Flask(__name__)
app.secret_key = "opened-esri-secret-2025"
app.config["SESSION_PERMANENT"] = False
CORS(app)

USUARIOS_FILE = Path(__file__).resolve().parent / "usuarios.json"

def cargar_usuarios():
    if not USUARIOS_FILE.exists():
        return {}
    with open(USUARIOS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def guardar_usuarios(usuarios):
    with open(USUARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)

# ==========================================
# LOGIN / REGISTRO / LOGOUT
# ==========================================
@app.route("/login", methods=["GET"])
def login_page():
    session.clear()
    resp = make_response(render_template("login.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Usuario y contraseña son obligatorios."}), 400

    usuarios = cargar_usuarios()
    usuario = usuarios.get(username)

    if not usuario or not check_password_hash(usuario["password_hash"], password):
        return jsonify({"error": "Usuario o contraseña incorrectos."}), 401

    session["usuario"] = username
    session["nombre"] = usuario["nombre"]
    return jsonify({"ok": True, "nombre": usuario["nombre"]})

@app.route("/api/registro", methods=["POST"])
def api_registro():
    data = request.get_json()
    username = (data.get("username") or "").strip().lower()
    nombre = (data.get("nombre") or "").strip()
    password = data.get("password") or ""
    confirmar = data.get("confirmar") or ""

    if not all([username, nombre, password, confirmar]):
        return jsonify({"error": "Todos los campos son obligatorios."}), 400

    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres."}), 400

    if password != confirmar:
        return jsonify({"error": "Las contraseñas no coinciden."}), 400

    usuarios = cargar_usuarios()

    if username in usuarios:
        return jsonify({"error": "Ese nombre de usuario ya existe."}), 409

    usuarios[username] = {
        "nombre": nombre,
        "password_hash": generate_password_hash(password)
    }
    guardar_usuarios(usuarios)

    return jsonify({"ok": True, "registrado": True})

@app.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect(url_for("login_page")))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/")
def index():
    return redirect(url_for("login_page"))

@app.route("/app")
def app_page():
    if not session.get("usuario"):
        return redirect(url_for("login_page"))
    resp = make_response(render_template("index.html", nombre_usuario=session["nombre"]))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

# ==========================================
# EXTRAER INFO DE CERTIFICADOS
# ==========================================
@app.route("/api/extraer", methods=["POST"])
def procesar_certificado():
    if not session.get("usuario"):
        return jsonify({"error": "No autenticado."}), 401
    try:
        if "archivos" not in request.files:
            return jsonify({"error": "No se encontraron archivos en la petición."}), 400

        archivos = request.files.getlist("archivos")
        tipo_certificado = request.form.get("tipo_certificado", "").strip().lower()

        if not tipo_certificado:
            return jsonify({"error": "Se requiere especificar el tipo_certificado (opened o esri)."}), 400

        resultados_globales = []
        for archivo in archivos:
            if archivo.filename == '':
                continue

            archivo_stream = archivo.read()
            resultado = extractor_pdf.ejecutar_extractor(archivo_stream, tipo_certificado)

            if "error" in resultado:
                return jsonify({"error": f"Error procesando {archivo.filename}: {resultado['error']}"}), 400

            # Validación de integridad del certificado
            if resultado.get("estudiante") == "N/A" or resultado.get("curso") == "N/A":
                return jsonify({
                    "error": f"El archivo '{archivo.filename}' no es un certificado válido de {tipo_certificado.upper()} o es ilegible."
                }), 400

            resultado["nombre_archivo"] = archivo.filename
            resultados_globales.append(resultado)

        if not resultados_globales:
            return jsonify({"error": "No se enviaron archivos válidos para procesar."}), 400

        return jsonify(resultados_globales), 200

    except Exception as e:
        return jsonify({"error": f"Excepción en servidor: {str(e)}"}), 500

# ==========================================
# GENERAR RESOLUCIÓN FINAL
# ==========================================
@app.route("/api/generar-resolucion-final", methods=["POST"])
def generar_resolucion_final():
    if not session.get("usuario"):
        return jsonify({"error": "No autenticado."}), 401

    try:
        if "archivos" not in request.files:
            return jsonify({"error": "No se encontraron archivos para anexar."}), 400

        archivos = request.files.getlist("archivos")
        codigo_estudiante = request.form.get("codigo_estudiante", "").strip()
        tipo_certificado = request.form.get("tipo_certificado", "").strip().lower()
        resultados_json = request.form.get("resultados", "")
        programa_destino = request.form.get("programa_destino", "").strip()
        materia_homologar = request.form.get("materia_homologar", "Electiva I").strip()
        tipo_nota = request.form.get("tipo_nota", "cuantitativa").strip().lower()
        responsable_resolucion = session["nombre"]

        if not all([codigo_estudiante, tipo_certificado, resultados_json, programa_destino, materia_homologar, responsable_resolucion]):
            return jsonify({"error": "Faltan parámetros obligatorios en el form-data."}), 400

        MESES_NOMBRE = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
            7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }

        resultados = json.loads(resultados_json)
        if not resultados:
            return jsonify({"error": "La lista de resultados está vacía."}), 400
        if len(resultados) < 1:
            return jsonify({
                "error": "Se requiere al menos 1 certificado válido para homologar."
            }), 400

        primer_resultado = resultados[0]
        fecha_extraida = primer_resultado.get("fecha", "")

        dia_constancia, mes_constancia, anio_constancia = "", "", ""
        if fecha_extraida:
            iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", fecha_extraida.strip())
            if iso_match:
                anio, mes_num, dia = iso_match.groups()
                dia_constancia = str(int(dia))
                mes_constancia = MESES_NOMBRE.get(int(mes_num), "")
                anio_constancia = anio
            else:
                patron_fecha = re.search(r"(\d{1,2})\s+días\s+del\s+mes\s+de\s+(\w+)\s+del\s+(\d{4})", fecha_extraida, re.IGNORECASE)
                if patron_fecha:
                    dia_constancia, mes_constancia, anio_constancia = patron_fecha.groups()

        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8') 
        except:
            pass
        fecha_actual = datetime.now().strftime("%d de %B de %Y")

        # =============================
        # CÁLCULO DE PROMEDIO Y NOTA DEFINITIVA
        # =============================
        notas_num = []
        for item in resultados:
            nota_str = item.get("nota", "0.0")
            try:
                val = float(nota_str.replace(",", "."))
                notas_num.append(val)
            except ValueError:
                # Si es un certificado de Esri u otro cualitativo (ej: "Aprobado")
                if nota_str.lower() in ["aprobado", "aprobada"]:
                    notas_num.append(5.0)
                else:
                    notas_num.append(0.0)

        promedio = sum(notas_num) / len(notas_num) if notas_num else 0.0

        if tipo_nota == "cuantitativa":
            nota_definitiva = f"{promedio:.1f}"
        else:
            # Nota cualitativa
            if promedio >= 3.0:
                nota_definitiva = "9.5"
            else:
                nota_definitiva = "0.0"

        # =============================
        # NORMALIZACIÓN DEL NOMBRE DEL ESTUDIANTE
        # =============================
        nombre_estudiante = str(primer_resultado.get("estudiante", "")).strip().upper()
        if not nombre_estudiante or nombre_estudiante == "N/A":
            nombre_estudiante = "SIN NOMBRE"

        mapa_creditos = {
            # Sistemas y Telecomunicaciones
            "ingeniería en sistemas y telecomunicaciones presencial": "3",
            "ingenieria en sistemas y telecomunicaciones virtual": "3",
            # Analítica de Datos
            "ingeniería en analítica de datos presencial": "2",
            "ingenieria en analitica de datos virtual": "2",
            # Logística
            "ingeniería logística presencial": "3",
            "ingenieria logistica virtual": "3",
            # Seguridad de la Información
            "ingeniería en seguridad de la información presencial": "3",
            "ingenieria en seguridad de la informacion virtual": "3",
            # Industrial
            "ingeniería industrial": "2",
            # Postgrados SIG (por defecto 3 créditos, editable)
            "especialización en sistemas de información geográfica": "3",
            "maestría en tecnologías de la información geográfica": "3",
            # Maestría Educación
            "maestría en educación y transformación digital": "2"
        }
        creditos_asignados = mapa_creditos.get(programa_destino.lower().strip(), "3")

        datos = {
            "fecha_resolucion": fecha_actual,
            "nombre_estudiante": nombre_estudiante,
            "codigo_estudiante": codigo_estudiante,
            "documento_estudiante": codigo_estudiante,
            "programa": programa_destino,
            "nombre_curso": primer_resultado.get("curso", "N/A"),
            "nota_curso": primer_resultado.get("nota", "N/A"),
            "dia_constancia": dia_constancia,
            "mes_constancia": mes_constancia,
            "anio_constancia": anio_constancia,
            "responsable": responsable_resolucion
        }

        #  Registro en Excel FCI y cálculo de consecutivo
        numero_resolucion = obtener_y_registrar_resolucion(datos, usuario=responsable_resolucion)
        datos["numero_resolucion"] = numero_resolucion

        # Obtener código de asignatura dinámico según el programa y la electiva seleccionada
        prog_norm = normalizar_texto(programa_destino)
        mat_norm = normalizar_texto(materia_homologar)

        mapa_prog = CODIGOS_ASIGNATURAS.get(prog_norm, {})
        codigo_asignatura = mapa_prog.get(mat_norm, "C5909002")

        cursos = [{
            "periodo": "2025-2",
            "asignatura_opened": item.get("curso", "N/A"),
            "nota": item.get("nota", "N/A"),
            "nota_definitiva": nota_definitiva,
            "asignatura_homologada": materia_homologar.upper(),
            "codigo_asignatura": codigo_asignatura,
            "creditos": creditos_asignados
        } for item in resultados]

        with tempfile.TemporaryDirectory() as carpeta_temp:
            ruta_temp = Path(carpeta_temp)
            nombre_docx = f"Resolucion_{numero_resolucion}_{codigo_estudiante}.docx"
            
            rutas_pdfs_anexos = []
            for archivo in archivos:
                ruta_destino = ruta_temp / secure_filename(archivo.filename)
                archivo.save(ruta_destino)
                if ruta_destino.suffix.lower() == ".pdf":
                    rutas_pdfs_anexos.append(str(ruta_destino))
                else:
                    return jsonify({"error": f"Archivo no admitido: {archivo.filename}"}), 400

            if tipo_certificado == "esri":
                ruta_docx_final = generador_doc.generar_resolucion_esri(
                    datos, cursos, str(ruta_temp), nombre_docx, rutas_pdfs_anexos
                )
            else:
                ruta_docx_final = generador_doc.generar_resolucion_opened(
                    datos, cursos, str(ruta_temp), nombre_docx, rutas_pdfs_anexos
                )

            with open(ruta_docx_final, "rb") as f_in:
                docx_buffer = io.BytesIO(f_in.read())

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