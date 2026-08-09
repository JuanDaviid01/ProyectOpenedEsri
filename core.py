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
from functools import wraps
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

def es_posgrado(programa):
    prog_norm = normalizar_texto(programa)
    return "especializac" in prog_norm or "maestri" in prog_norm

def obtener_semestre_actual():
    ahora = datetime.now()
    semestre = 1 if ahora.month <= 6 else 2
    return f"{ahora.year}-{semestre}"

def obtener_semestre_fecha(fecha_str):
    if not fecha_str or str(fecha_str).strip() in ["N/A", "n/a", ""]:
        return None
    iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(fecha_str).strip())
    if iso_match:
        anio, mes_num, _ = iso_match.groups()
        semestre = 1 if int(mes_num) <= 6 else 2
        return f"{anio}-{semestre}"
    
    patron_anio = re.search(r"\b(20\d{2})\b", str(fecha_str))
    if patron_anio:
        anio = patron_anio.group(1)
        meses_dict = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
            "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
        }
        for nombre_mes, mes_idx in meses_dict.items():
            if nombre_mes in str(fecha_str).lower():
                semestre = 1 if mes_idx <= 6 else 2
                return f"{anio}-{semestre}"
    return None

def validar_vigencia_semestre_cert(fecha_str, curso_nombre):
    semestre_actual = obtener_semestre_actual()
    semestre_cert = obtener_semestre_fecha(fecha_str)
    if semestre_cert and semestre_cert != semestre_actual:
        return False, f"El certificado del curso '{curso_nombre}' no corresponde al semestre actual ({semestre_actual}). Semestre detectado: {semestre_cert}."
    return True, ""

app = Flask(__name__)
app.secret_key = "opened-esri-secret-2025"
app.config["SESSION_PERMANENT"] = False
CORS(app)

USUARIOS_FILE = Path(__file__).resolve().parent / "usuarios.json"
PROGRAMAS_FILE = Path(__file__).resolve().parent / "config_programas.json"

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

def cargar_programas_config():
    if not PROGRAMAS_FILE.exists():
        return {"programas": []}
    with open(PROGRAMAS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"programas": []}

def guardar_programas_config(data):
    with open(PROGRAMAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def obtener_programas_mapeados():
    data = cargar_programas_config()
    mapa_codigos = {}
    mapa_creditos_materia = {}
    mapa_proveedores = {}
    for prog in data.get("programas", []):
        p_norm = normalizar_texto(prog["nombre"])
        mapa_proveedores[p_norm] = prog.get("proveedores_permitidos", "ambos")
        electivas_map = {}
        creditos_map = {}
        for ele in prog.get("electivas", []):
            e_norm = normalizar_texto(ele["nombre"])
            electivas_map[e_norm] = ele.get("codigo", "")
            creditos_map[e_norm] = int(ele.get("creditos", prog.get("creditos_unidad", 3)))
        mapa_codigos[p_norm] = electivas_map
        mapa_creditos_materia[p_norm] = creditos_map
    return mapa_codigos, mapa_creditos_materia, mapa_proveedores

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("usuario") or session.get("rol") != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"error": "Acceso restringido a Administradores de la Facultad."}), 403
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated_function


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

    estado = usuario.get("estado", "aprobado")
    if estado == "pendiente":
        return jsonify({"error": "Su cuenta está pendiente de aprobación por el Administrador de la Facultad."}), 403
    if estado == "rechazado":
        return jsonify({"error": "Su cuenta ha sido inhabilitada por el Administrador."}), 403

    session["usuario"] = username
    session["nombre"] = usuario["nombre"]
    session["rol"] = usuario.get("rol", "operador")
    return jsonify({"ok": True, "nombre": usuario["nombre"], "rol": session["rol"]})

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

    es_primer_usuario = (len(usuarios) == 0) or (username in ["admin", "juandaviiid"])
    rol_inicial = "admin" if es_primer_usuario else "operador"
    estado_inicial = "aprobado" if es_primer_usuario else "pendiente"

    usuarios[username] = {
        "nombre": nombre,
        "password_hash": generate_password_hash(password),
        "rol": rol_inicial,
        "estado": estado_inicial,
        "fecha_registro": datetime.now().isoformat()
    }
    guardar_usuarios(usuarios)

    return jsonify({"ok": True, "registrado": True, "estado": estado_inicial})

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
    es_admin = (session.get("rol") == "admin")
    resp = make_response(render_template("index.html", nombre_usuario=session["nombre"], es_admin=es_admin))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/admin")
@admin_required
def admin_page():
    resp = make_response(render_template("admin.html", nombre_usuario=session["nombre"]))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/api/programas", methods=["GET"])
def api_obtener_programas():
    config_data = cargar_programas_config()
    return jsonify(config_data)

@app.route("/api/admin/usuarios", methods=["GET"])
@admin_required
def api_admin_listar_usuarios():
    usuarios = cargar_usuarios()
    res = {}
    for k, v in usuarios.items():
        res[k] = {
            "nombre": v.get("nombre", ""),
            "rol": v.get("rol", "operador"),
            "estado": v.get("estado", "aprobado"),
            "fecha_registro": v.get("fecha_registro", "")
        }
    return jsonify(res)

@app.route("/api/admin/usuarios/estado", methods=["POST"])
@admin_required
def api_admin_usuario_estado():
    data = request.get_json() or {}
    target_user = (data.get("username") or "").strip().lower()
    nuevo_estado = (data.get("estado") or "").strip().lower()

    if not target_user or nuevo_estado not in ["aprobado", "pendiente", "rechazado"]:
        return jsonify({"error": "Parámetros inválidos."}), 400

    usuarios = cargar_usuarios()
    if target_user not in usuarios:
        return jsonify({"error": "Usuario no encontrado."}), 404

    usuarios[target_user]["estado"] = nuevo_estado
    guardar_usuarios(usuarios)
    return jsonify({"ok": True})

@app.route("/api/admin/usuarios/rol", methods=["POST"])
@admin_required
def api_admin_usuario_rol():
    data = request.get_json() or {}
    target_user = (data.get("username") or "").strip().lower()
    nuevo_rol = (data.get("rol") or "").strip().lower()

    if not target_user or nuevo_rol not in ["admin", "operador"]:
        return jsonify({"error": "Parámetros inválidos."}), 400

    usuarios = cargar_usuarios()
    if target_user not in usuarios:
        return jsonify({"error": "Usuario no encontrado."}), 404

    usuarios[target_user]["rol"] = nuevo_rol
    guardar_usuarios(usuarios)
    return jsonify({"ok": True})

@app.route("/api/admin/usuarios/<username>", methods=["DELETE"])
@admin_required
def api_admin_eliminar_usuario(username):
    target_user = username.strip().lower()
    if target_user == session.get("usuario"):
        return jsonify({"error": "No puede eliminar su propia cuenta de administrador en sesión."}), 400

    usuarios = cargar_usuarios()
    if target_user not in usuarios:
        return jsonify({"error": "Usuario no encontrado."}), 404

    del usuarios[target_user]
    guardar_usuarios(usuarios)
    return jsonify({"ok": True})

@app.route("/api/admin/programas", methods=["POST"])
@admin_required
def api_admin_guardar_programa():
    data = request.get_json() or {}
    prog_id = (data.get("id") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    nivel = (data.get("nivel") or "pregrado").strip().lower()
    creditos_unidad = int(data.get("creditos_unidad", 3))
    electivas = data.get("electivas", [])

    if not nombre or not electivas:
        return jsonify({"error": "Nombre del programa y al menos una electiva son requeridos."}), 400

    config_data = cargar_programas_config()
    programas = config_data.get("programas", [])

    index_existente = -1
    for idx, p in enumerate(programas):
        if p["id"] == prog_id or normalizar_texto(p["nombre"]) == normalizar_texto(nombre):
            index_existente = idx
            break

    nuevo_programa = {
        "id": prog_id if prog_id else f"prog_{int(datetime.now().timestamp())}",
        "nombre": nombre,
        "nivel": nivel,
        "creditos_unidad": creditos_unidad,
        "electivas": electivas
    }

    if index_existente >= 0:
        programas[index_existente] = nuevo_programa
    else:
        programas.append(nuevo_programa)

    config_data["programas"] = programas
    guardar_programas_config(config_data)
    return jsonify({"ok": True})

@app.route("/api/admin/programas/<prog_id>", methods=["DELETE"])
@admin_required
def api_admin_eliminar_programa(prog_id):
    config_data = cargar_programas_config()
    programas = config_data.get("programas", [])

    programas_filtrados = [p for p in programas if p["id"] != prog_id]
    if len(programas_filtrados) == len(programas):
        return jsonify({"error": "Programa no encontrado."}), 404

    config_data["programas"] = programas_filtrados
    guardar_programas_config(config_data)
    return jsonify({"ok": True})


@app.route("/api/extraer", methods=["POST"])
def procesar_certificado():
    if not session.get("usuario"):
        return jsonify({"error": "No autenticado."}), 401
    try:
        if "archivos" not in request.files:
            return jsonify({"error": "No se encontraron archivos en la petición."}), 400

        archivos = request.files.getlist("archivos")
        tipo_certificado = request.form.get("tipo_certificado", "").strip().lower()
        programa_destino = request.form.get("programa_destino", "").strip()

        if not tipo_certificado:
            return jsonify({"error": "Se requiere especificar el tipo_certificado (opened o esri)."}), 400

        mapa_codigos_dyn, mapa_creditos_dyn, mapa_proveedores_dyn = obtener_programas_mapeados()
        prog_norm = normalizar_texto(programa_destino)
        prov_permitido = mapa_proveedores_dyn.get(prog_norm, "ambos")

        if prov_permitido == "opened" and tipo_certificado == "esri":
            return jsonify({"error": f"El programa '{programa_destino}' no permite certificados de ESRI (solo permite Opened)."}), 400
        if prov_permitido == "esri" and tipo_certificado == "opened":
            return jsonify({"error": f"El programa '{programa_destino}' no permite certificados de Opened (solo permite ESRI)."}), 400

        cursos_vistos = set()
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

            # Validación de duplicados por nombre de curso
            curso_nombre = str(resultado.get("curso", "")).strip().lower()
            if curso_nombre and curso_nombre != "n/a":
                if curso_nombre in cursos_vistos:
                    return jsonify({
                        "error": f"Se detectó el certificado del curso '{resultado.get('curso')}' duplicado en el mismo lote."
                    }), 400
                cursos_vistos.add(curso_nombre)

            resultado["nombre_archivo"] = archivo.filename
            resultados_globales.append(resultado)

        if not resultados_globales:
            return jsonify({"error": "No se enviaron archivos válidos para procesar."}), 400

        # Validar nota mínima aprobatoria (>= 3.0) para certificados cuantitativos Opened
        if tipo_certificado == "opened":
            for res in resultados_globales:
                nota_raw = str(res.get("nota", "0.0")).strip()
                try:
                    nota_val = float(nota_raw.replace(",", "."))
                    if nota_val < 3.0:
                        return jsonify({
                            "error": f"El certificado del curso '{res.get('curso')}' no cumple con la nota mínima de aprobación (3.0). Nota obtenida: {nota_val:.1f}."
                        }), 400
                except ValueError:
                    if nota_raw.lower() not in ["aprobado", "aprobada"]:
                        return jsonify({
                            "error": f"El certificado del curso '{res.get('curso')}' no registra una nota aprobatoria válida."
                        }), 400

        # =========================================================================
        # === DESCOMENTAR EL SIGUIENTE BLOQUE PARA ACTIVAR EN PRODUCCIÓN LA VALIDACION DE FECHA
        # =========================================================================
        # for res in resultados_globales:
        #     es_vigente, msg_vigencia = validar_vigencia_semestre_cert(res.get("fecha"), res.get("curso"))
        #     if not es_vigente:
        #         return jsonify({"error": msg_vigencia}), 400
        # =========================================================================

        return jsonify(resultados_globales), 200

    except Exception as e:
        return jsonify({"error": f"Excepción en servidor: {str(e)}"}), 500


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

        # Validar duplicados de cursos en los resultados recibidos
        cursos_vistos = set()
        for res in resultados:
            c_nombre = str(res.get("curso", "")).strip().lower()
            if c_nombre and c_nombre != "n/a":
                if c_nombre in cursos_vistos:
                    return jsonify({
                        "error": f"Se detectó el certificado del curso '{res.get('curso')}' duplicado en el mismo lote."
                    }), 400
                cursos_vistos.add(c_nombre)

        # Parseo de materias a homologar (única o selección múltiple)
        materias_raw = request.form.get("materia_homologar", "Electiva I").strip()
        materias_lista = []
        if materias_raw.startswith("["):
            try:
                materias_lista = json.loads(materias_raw)
            except json.JSONDecodeError:
                materias_lista = [materias_raw]
        else:
            materias_lista = [m.strip() for m in materias_raw.split(",") if m.strip()]

        if not materias_lista:
            materias_lista = ["Electiva I"]

        mapa_codigos_dyn, mapa_creditos_dyn, mapa_proveedores_dyn = obtener_programas_mapeados()
        prog_norm = normalizar_texto(programa_destino)
        prov_permitido = mapa_proveedores_dyn.get(prog_norm, "ambos")

        if prov_permitido == "opened" and tipo_certificado == "esri":
            return jsonify({"error": f"El programa '{programa_destino}' no permite certificados de ESRI (solo permite Opened)."}), 400
        if prov_permitido == "esri" and tipo_certificado == "opened":
            return jsonify({"error": f"El programa '{programa_destino}' no permite certificados de Opened (solo permite ESRI)."}), 400

        creditos_map_prog = mapa_creditos_dyn.get(prog_norm, {})
        num_materias = len(materias_lista)

        if tipo_certificado == "esri":
            certificados_esperados = num_materias * 2
        else:
            certificados_esperados = sum(creditos_map_prog.get(normalizar_texto(m), 3) for m in materias_lista)

        if len(resultados) != certificados_esperados:
            if tipo_certificado == "esri":
                msg_err = f"Ha seleccionado {num_materias} materia(s) con ESRI (se requieren 2 certificados por materia, total {certificados_esperados}). Se recibieron {len(resultados)}."
            else:
                msg_err = f"Ha seleccionado {num_materias} materia(s) con Opened (total {certificados_esperados} crédito(s) / certificado(s) requeridos). Se recibieron {len(resultados)}."
            return jsonify({"error": msg_err}), 400

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


        nombre_estudiante_manual = request.form.get("nombre_estudiante_manual", "").strip()

        if tipo_certificado == "esri" and nombre_estudiante_manual:
            nombre_estudiante = nombre_estudiante_manual.upper()
        else:
            nombre_estudiante = str(primer_resultado.get("estudiante", "")).strip().upper()

        if not nombre_estudiante or nombre_estudiante == "N/A":
            nombre_estudiante = "SIN NOMBRE"

        # Mapeo de códigos de asignatura y certificados por cada materia seleccionada
        materias_mapeadas = []
        mapa_prog = mapa_codigos_dyn.get(prog_norm, {})

        curr_idx = 0
        for idx, mat_nombre in enumerate(materias_lista):
            mat_norm = normalizar_texto(mat_nombre)
            codigo_asig = mapa_prog.get(mat_norm, "C5909002")
            c_num = 2 if tipo_certificado == "esri" else creditos_map_prog.get(mat_norm, 3)

            certs_subgrupo = resultados[curr_idx:curr_idx + c_num]
            curr_idx += c_num

            materias_mapeadas.append({
                "materia": mat_nombre,
                "codigo_asignatura": codigo_asig,
                "creditos": c_num,
                "certificados": certs_subgrupo
            })

        # Mapeo retrocompatible para la resolución
        materia_homologar = materias_lista[0] if materias_lista else "Electiva I"
        codigo_asignatura = materias_mapeadas[0]["codigo_asignatura"] if materias_mapeadas else "C5909002"
        total_creditos_num = sum(m["creditos"] for m in materias_mapeadas)
        creditos_asignados = str(total_creditos_num)

        datos = {
            "fecha_resolucion": fecha_actual,
            "nombre_estudiante": nombre_estudiante,
            "codigo_estudiante": codigo_estudiante,
            "documento_estudiante": codigo_estudiante,
            "programa": programa_destino,
            "materias_homologadas": materias_mapeadas,
            "materia_homologar": ", ".join(materias_lista),
            "codigo_asignatura": codigo_asignatura,
            "creditos": creditos_asignados,
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)