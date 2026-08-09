// SISTEMA DE NOTIFICACIONES TOAST
function mostrarToast(mensaje, titulo = '', tipo = 'info', duracion = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${tipo}`;

    const iconos = {
        exito: '✓',
        error: '✕',
        info: 'ℹ',
        advertencia: '⚠'
    };
    const icono = iconos[tipo] || 'ℹ';

    toast.innerHTML = `
        <span class="toast-icono">${icono}</span>
        <div class="toast-contenido">
            ${titulo ? `<div class="toast-titulo">${titulo}</div>` : ''}
            <div>${mensaje}</div>
        </div>
        <button class="toast-cerrar" type="button">✕</button>
    `;

    container.appendChild(toast);

    const btnCerrar = toast.querySelector('.toast-cerrar');
    btnCerrar.onclick = () => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    };

    if (duracion > 0) {
        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.add('fade-out');
                setTimeout(() => toast.remove(), 300);
            }
        }, duracion);
    }
}

let ELECTIVAS_POR_PROGRAMA = {
    "Ingeniería en Sistemas y Telecomunicaciones": ["Electiva I", "Electiva II"],
    "Ingeniería de Sistemas (Virtual)": ["Electiva I", "Electiva II"],
    "Ingeniería en Analítica de Datos (Presencial)": ["Electiva I", "Electiva II", "Electiva III"],
    "Ingeniería en Analítica de Datos (Virtual)": ["Electiva I", "Electiva II", "Electiva III"],
    "Ingeniería Logística (Presencial)": ["Electiva I", "Electiva II", "Electiva III", "Electiva IV"],
    "Ingeniería Logística (Virtual)": ["Electiva I", "Electiva II", "Electiva III", "Electiva IV"],
    "Ingeniería en Seguridad de la Información (Presencial)": ["Electiva I", "Electiva II"],
    "Ingeniería en Seguridad de la Información (Virtual)": ["Electiva I", "Electiva II"],
    "Ingeniería Industrial": ["Electiva I", "Electiva II"],
    "Especialización en Sistemas de Información Geográfica (Presencial)": ["Electiva I", "Electiva II"],
    "Especialización en Sistemas de Información Geográfica (Virtual)": ["Electiva I", "Electiva II"],
    "Maestría en Tecnologías de la Información Geográfica (Presencial)": ["Electiva I", "Electiva II"],
    "Maestría en Tecnologías de la Información Geográfica (Virtual)": ["Electiva I", "Electiva II"],
    "Maestría en Educación y Transformación Digital": ["Electiva I", "Electiva II", "Electiva III", "Electiva IV"]
};

const btnCuantitativa = document.querySelector('#tipo_nota .seg-opcion[data-valor="cuantitativa"]');
const btnCualitativa = document.querySelector('#tipo_nota .seg-opcion[data-valor="cualitativa"]');
const inputTipoNotaValor = document.getElementById('tipo_nota_valor');

// Segmentador tipo de nota
document.querySelectorAll('#tipo_nota .seg-opcion').forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.disabled || btn.classList.contains('deshabilitado')) return;

        document.querySelectorAll('#tipo_nota .seg-opcion').forEach(b => b.classList.remove('activo'));
        btn.classList.add('activo');
        inputTipoNotaValor.value = btn.dataset.valor;
        invalidarValidacion(false);
    });
});

let estudianteValidado = null;
let archivosEnMemoria = [];
const inputArchivos = document.getElementById('archivos');
const listaArchivos = document.querySelector('.lista-archivos');
const btnValidar = document.getElementById('btn-validar');
const btnGenerar = document.getElementById('btn-generar');
const inputCodigo = document.getElementById('codigo_estudiante');
const selectTipo = document.getElementById('tipo_certificado');
const optEsri = selectTipo ? selectTipo.querySelector('option[value="esri"]') : null;
const selectPrograma = document.getElementById('programa_destino');
const contenedorMaterias = document.getElementById('contenedor_materias');
const grupoNombreManual = document.getElementById('grupo_nombre_manual');
const inputNombreManual = document.getElementById('nombre_estudiante_manual');

function obtenerMateriasSeleccionadas() {
    if (!contenedorMaterias) return [];
    const checkboxes = contenedorMaterias.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

// Función para actualizar dinámicamente las materias a homologar según el programa
function actualizarOpcionesElectivas() {
    const programaSeleccionado = selectPrograma.value;
    contenedorMaterias.innerHTML = '';

    if (!programaSeleccionado || !ELECTIVAS_POR_PROGRAMA[programaSeleccionado]) {
        contenedorMaterias.innerHTML = '<span class="placeholder-materias">Seleccione primero un programa</span>';
        return;
    }

    const electivasDisponibles = ELECTIVAS_POR_PROGRAMA[programaSeleccionado];
    electivasDisponibles.forEach((electiva, idx) => {
        const label = document.createElement('label');
        label.className = 'materia-checkbox-label';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'materias_homologar';
        checkbox.value = electiva;
        if (idx === 0) {
            checkbox.checked = true;
            label.classList.add('seleccionado');
        }

        checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
                label.classList.add('seleccionado');
            } else {
                label.classList.remove('seleccionado');
            }
            invalidarValidacion(false);
        });

        const span = document.createElement('span');
        span.textContent = electiva;

        label.appendChild(checkbox);
        label.appendChild(span);
        contenedorMaterias.appendChild(label);
    });
}

// Resetear estado de validación y deshabilitar botón de generar
function invalidarValidacion(notificar = true) {
    if (estudianteValidado) {
        estudianteValidado = null;
        if (notificar) {
            mostrarToast("Al realizar cambios en el formulario, debe volver a validar los documentos.", "Atención", "advertencia");
        }
    }
    btnGenerar.disabled = true;
}

// Resetear formulario completo (al cambiar código de estudiante)
let codigoPrevio = (inputCodigo.value || '').trim();

inputCodigo.addEventListener('input', () => {
    const codigoActual = inputCodigo.value.trim();
    if (codigoActual !== codigoPrevio) {
        codigoPrevio = codigoActual;
        
        // Resetear archivos
        archivosEnMemoria = [];
        inputArchivos.value = '';
        renderizarLista();
        
        // Resetear selects
        selectPrograma.value = '';
        actualizarOpcionesElectivas();
        selectTipo.value = '';
        if (optEsri) optEsri.disabled = false;

        // Resetear nombre manual ESRI
        if (inputNombreManual) inputNombreManual.value = '';
        if (grupoNombreManual) grupoNombreManual.style.display = 'none';

        // Resetear tipo de nota
        document.querySelectorAll('#tipo_nota .seg-opcion').forEach(b => {
            b.classList.remove('activo');
            b.disabled = false;
            b.classList.remove('deshabilitado');
        });
        inputTipoNotaValor.value = '';
        
        // Resetear validación
        invalidarValidacion(false);
    }
});

function actualizarComportamientoTipoNota() {
    const proveedor = selectTipo.value;

    if (proveedor === 'esri') {
        btnCuantitativa.disabled = true;
        btnCuantitativa.classList.remove('activo');
        btnCuantitativa.classList.add('deshabilitado');

        btnCualitativa.disabled = false;
        btnCualitativa.classList.remove('deshabilitado');
        btnCualitativa.classList.add('activo');
        inputTipoNotaValor.value = 'cualitativa';

        if (grupoNombreManual) {
            grupoNombreManual.style.display = 'block';
        }
    } else {
        btnCuantitativa.disabled = false;
        btnCuantitativa.classList.remove('deshabilitado');

        btnCualitativa.disabled = false;
        btnCualitativa.classList.remove('deshabilitado');

        if (grupoNombreManual) {
            grupoNombreManual.style.display = 'none';
        }
        if (inputNombreManual) {
            inputNombreManual.value = '';
        }
    }
}

function actualizarOpcionesProveedor() {
    const programa = selectPrograma.value;
    const optOpened = selectTipo ? selectTipo.querySelector('option[value="opened"]') : null;

    if (!programa) {
        if (optEsri) optEsri.disabled = false;
        if (optOpened) optOpened.disabled = false;
        return;
    }

    const provPermitido = PROVEEDORES_PERMITIDOS_POR_PROGRAMA[programa] || (esPosgrado(programa) ? 'ambos' : 'opened');

    if (provPermitido === 'opened') {
        if (optEsri) optEsri.disabled = true;
        if (optOpened) optOpened.disabled = false;
        selectTipo.value = 'opened';
        actualizarComportamientoTipoNota();
    } else if (provPermitido === 'esri') {
        if (optEsri) optEsri.disabled = false;
        if (optOpened) optOpened.disabled = true;
        selectTipo.value = 'esri';
        actualizarComportamientoTipoNota();
    } else {
        if (optEsri) optEsri.disabled = false;
        if (optOpened) optOpened.disabled = false;
    }
}

selectPrograma.addEventListener('change', () => {
    actualizarOpcionesElectivas();
    actualizarOpcionesProveedor();
    invalidarValidacion(false);
});

selectTipo.addEventListener('change', () => {
    actualizarComportamientoTipoNota();
    invalidarValidacion(false);
});

// Cargar archivos en memoria
inputArchivos.addEventListener('change', () => {
    const nuevosArchivos = Array.from(inputArchivos.files);
    let duplicadosDetectados = [];

    nuevosArchivos.forEach(archivoNuevo => {
        const yaExiste = archivosEnMemoria.some(a =>
            a.name === archivoNuevo.name && a.size === archivoNuevo.size
        );
        if (yaExiste) {
            duplicadosDetectados.push(archivoNuevo.name);
        } else {
            archivosEnMemoria.push(archivoNuevo);
        }
    });

    if (duplicadosDetectados.length > 0) {
        mostrarToast(`No se agregaron archivos duplicados (${duplicadosDetectados.join(', ')}). Cargue certificados diferentes.`, "Archivo Duplicado", "advertencia");
    }

    inputArchivos.value = '';
    renderizarLista();
    invalidarValidacion(true);
});

function renderizarLista() {
    listaArchivos.innerHTML = '';

    if (archivosEnMemoria.length === 0) {
        listaArchivos.innerHTML = '<div class="archivo-item">No hay archivos cargados</div>';
        return;
    }

    archivosEnMemoria.forEach((archivo, index) => {
        const nodoArchivo = document.createElement('div');
        nodoArchivo.className = 'archivo-item';
        nodoArchivo.style.display = 'flex';
        nodoArchivo.style.justifyContent = 'space-between';
        nodoArchivo.style.alignItems = 'center';
        nodoArchivo.style.marginBottom = '5px';

        const textoArchivo = document.createElement('span');
        textoArchivo.textContent = `${archivo.name} (${(archivo.size / 1024).toFixed(2)} KB)`;

        const btnEliminar = document.createElement('button');
        btnEliminar.type = 'button';
        btnEliminar.innerHTML = '✕';
        btnEliminar.style.color = 'red';
        btnEliminar.style.background = 'none';
        btnEliminar.style.border = 'none';
        btnEliminar.style.cursor = 'pointer';
        btnEliminar.style.fontWeight = 'bold';

        btnEliminar.onclick = () => eliminarArchivo(index);

        nodoArchivo.appendChild(textoArchivo);
        nodoArchivo.appendChild(btnEliminar);
        listaArchivos.appendChild(nodoArchivo);
    });
}

function eliminarArchivo(index) {
    archivosEnMemoria.splice(index, 1);
    invalidarValidacion(true);
    renderizarLista();
}

function esPosgrado(programa) {
    const progNorm = (programa || '').toLowerCase();
    return progNorm.includes('especializac') || progNorm.includes('maestri');
}

let CREDITOS_POR_PROGRAMA = {
    "Ingeniería en Sistemas y Telecomunicaciones": 3,
    "Ingeniería de Sistemas (Virtual)": 3,
    "Ingeniería en Analítica de Datos (Presencial)": 2,
    "Ingeniería en Analítica de Datos (Virtual)": 2,
    "Ingeniería Logística (Presencial)": 3,
    "Ingeniería Logística (Virtual)": 3,
    "Ingeniería en Seguridad de la Información (Presencial)": 3,
    "Ingeniería en Seguridad de la Información (Virtual)": 3,
    "Ingeniería Industrial": 2,
    "Especialización en Sistemas de Información Geográfica (Presencial)": 3,
    "Especialización en Sistemas de Información Geográfica (Virtual)": 3,
    "Maestría en Tecnologías de la Información Geográfica (Presencial)": 3,
    "Maestría en Tecnologías de la Información Geográfica (Virtual)": 3,
    "Maestría en Educación y Transformación Digital": 2
};

let PROVEEDORES_PERMITIDOS_POR_PROGRAMA = {};
let CREDITOS_POR_ELECTIVA = {};

async function cargarCatalogosDinamicos() {
    if (!selectPrograma) return;
    try {
        const res = await fetch('/api/programas');
        if (!res.ok) return;
        const data = await res.json();
        const programas = data.programas || [];

        if (programas.length > 0) {
            const valPrevio = selectPrograma.value;
            selectPrograma.innerHTML = '<option value="" selected disabled>Seleccionar programa</option>';

            programas.forEach(p => {
                const electivasNombres = (p.electivas || []).map(e => e.nombre);
                ELECTIVAS_POR_PROGRAMA[p.nombre] = electivasNombres;
                CREDITOS_POR_PROGRAMA[p.nombre] = p.creditos_unidad || 3;
                PROVEEDORES_PERMITIDOS_POR_PROGRAMA[p.nombre] = p.proveedores_permitidos || (p.nivel === 'posgrado' ? 'ambos' : 'opened');

                (p.electivas || []).forEach(e => {
                    CREDITOS_POR_ELECTIVA[`${p.nombre}_${e.nombre}`] = e.creditos || p.creditos_unidad || 3;
                });

                const opt = document.createElement('option');
                opt.value = p.nombre;
                opt.textContent = p.nombre;
                selectPrograma.appendChild(opt);
            });

            if (valPrevio && ELECTIVAS_POR_PROGRAMA[valPrevio]) {
                selectPrograma.value = valPrevio;
            }
        }
    } catch (e) {
        console.warn('Catálogo dinámico no disponible, usando local:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    cargarCatalogosDinamicos();
});

function calcularCertificadosEsperados(programa, tipoCertificado) {
    const materias = obtenerMateriasSeleccionadas();
    if (materias.length === 0) return 0;

    if (tipoCertificado === 'esri') {
        return materias.length * 2;
    }
    let totalCreditos = 0;
    materias.forEach(m => {
        const c = CREDITOS_POR_ELECTIVA[`${programa}_${m}`] || CREDITOS_POR_PROGRAMA[programa] || 3;
        totalCreditos += c;
    });
    return totalCreditos;
}

// Validar documentos
btnValidar.addEventListener('click', async () => {
    const codigoEstudiante = inputCodigo.value.trim();
    if (!codigoEstudiante) {
        mostrarToast("Ingrese el código del estudiante.", "Código Requerido", "error");
        return;
    }

    if (!selectPrograma.value) {
        mostrarToast("Seleccione el programa de destino antes de validar.", "Programa Requerido", "error");
        return;
    }

    const materiasSeleccionadas = obtenerMateriasSeleccionadas();
    if (materiasSeleccionadas.length === 0) {
        mostrarToast("Seleccione al menos una materia a homologar.", "Materia Requerida", "error");
        return;
    }

    if (!selectTipo.value) {
        mostrarToast("Seleccione el proveedor del certificado.", "Proveedor Requerido", "error");
        return;
    }

    if (!inputTipoNotaValor.value) {
        mostrarToast("Seleccione el tipo de nota (Cuantitativa o Cualitativa).", "Tipo de Nota Requerido", "error");
        return;
    }

    // Validar restricción de proveedor (ESRI solo para Posgrados)
    if (selectTipo.value === 'esri' && !esPosgrado(selectPrograma.value)) {
        mostrarToast("Los certificados de ESRI solo están permitidos para programas de Posgrado (Especializaciones y Maestrías).", "Proveedor No Permitido", "error");
        return;
    }

    // Validar número exacto acumulado de certificados
    const esperados = calcularCertificadosEsperados(selectPrograma.value, selectTipo.value);
    if (archivosEnMemoria.length !== esperados) {
        if (selectTipo.value === 'esri') {
            mostrarToast(`Ha seleccionado ${materiasSeleccionadas.length} materia(s) en posgrado con ESRI (se requieren 2 certificados por materia, total ${esperados}). Ha cargado ${archivosEnMemoria.length}.`, "Cantidad de Certificados Incorrecta", "error");
        } else {
            const creditosUnidad = CREDITOS_POR_PROGRAMA[selectPrograma.value] || 3;
            mostrarToast(`Ha seleccionado ${materiasSeleccionadas.length} materia(s) de ${creditosUnidad} crédito(s) cada una (total ${esperados} certificados para Opened). Ha cargado ${archivosEnMemoria.length}.`, "Cantidad de Certificados Incorrecta", "error");
        }
        return;
    }

    const formData = new FormData();

    archivosEnMemoria.forEach(archivo => {
        formData.append('archivos', archivo);
    });

    formData.append('tipo_certificado', selectTipo.value);
    formData.append('programa_destino', selectPrograma.value);
    formData.append('materias_homologar', JSON.stringify(materiasSeleccionadas));

    try {
        mostrarToast("Analizando y validando certificados cargados...", "Validando", "info", 2000);

        const response = await fetch('/api/extraer', {
            method: 'POST',
            body: formData
        });

        const datosCrudos = await response.json();

        if (!response.ok) {
            throw new Error(datosCrudos.error || `HTTP Status: ${response.status}`);
        }

        if (!Array.isArray(datosCrudos) || datosCrudos.length === 0) {
            throw new Error("No se obtuvo información válida de los certificados.");
        }

        const nombreReferencia = (datosCrudos[0].estudiante || '').trim().toLowerCase();

        const nombresInconsistentes = datosCrudos.some(cert =>
            (cert.estudiante || '').trim().toLowerCase() !== nombreReferencia
        );

        if (nombresInconsistentes) {
            estudianteValidado = null;
            btnGenerar.disabled = true;
            mostrarToast("Se detectaron certificados pertenecientes a diferentes estudiantes en el mismo lote.", "Error de Validación", "error");
            return;
        }

        // Validación de cursos duplicados en el lote
        const cursosVistos = new Set();
        let cursoDuplicado = null;

        for (const cert of datosCrudos) {
            const cursoKey = (cert.curso || '').trim().toLowerCase();
            if (cursoKey && cursoKey !== 'n/a') {
                if (cursosVistos.has(cursoKey)) {
                    cursoDuplicado = cert.curso;
                    break;
                }
                cursosVistos.add(cursoKey);
            }
        }

        if (cursoDuplicado) {
            estudianteValidado = null;
            btnGenerar.disabled = true;
            mostrarToast(`Se detectó el certificado del curso "${cursoDuplicado}" duplicado en el mismo lote. Adjunte certificados de cursos diferentes.`, "Certificado Duplicado", "error");
            return;
        }

        // Validación de nota mínima aprobatoria (>= 3.0) para Opened
        if (selectTipo.value === 'opened') {
            for (const cert of datosCrudos) {
                const notaVal = parseFloat(String(cert.nota || '0').replace(',', '.'));
                if (!isNaN(notaVal) && notaVal < 3.0) {
                    estudianteValidado = null;
                    btnGenerar.disabled = true;
                    mostrarToast(`El certificado del curso "${cert.curso}" no cumple con la nota mínima de aprobación (3.0). Nota obtenida: ${notaVal.toFixed(1)}.`, "Nota Insuficiente", "error");
                    return;
                }
            }
        }

        // =========================================================================
        // === DESCOMENTAR EL SIGUIENTE BLOQUE PARA ACTIVAR EN PRODUCCIÓN LA    ===
        // === VALIDACIÓN DE VIGENCIA DE CERTIFICADOS DEL SEMESTRE ACTUAL EN JS ===
        // =========================================================================
        /*
        const ahora = new Date();
        const semestreActual = `${ahora.getFullYear()}-${ahora.getMonth() + 1 <= 6 ? 1 : 2}`;
        for (const cert of datosCrudos) {
            if (cert.fecha && cert.fecha !== 'N/A') {
                const partes = cert.fecha.split('-');
                if (partes.length >= 2) {
                    const anioCert = partes[0];
                    const mesCert = parseInt(partes[1], 10);
                    const semCert = `${anioCert}-${mesCert <= 6 ? 1 : 2}`;
                    if (semCert !== semestreActual) {
                        estudianteValidado = null;
                        btnGenerar.disabled = true;
                        mostrarToast(`El certificado del curso "${cert.curso}" no corresponde al semestre actual (${semestreActual}). Semestre certificado: ${semCert}.`, "Certificado Vencido", "error");
                        return;
                    }
                }
            }
        }
        */
        // =========================================================================

        const nombreManual = (inputNombreManual && inputNombreManual.value) ? inputNombreManual.value.trim() : '';
        const nombreFinal = (selectTipo.value === 'esri' && nombreManual) ? nombreManual : (datosCrudos[0].estudiante || '').trim();

        estudianteValidado = {
            codigo: codigoEstudiante,
            nombre: nombreFinal,
            certificados: datosCrudos.map(cert => ({
                estudiante: cert.estudiante || "N/A",
                curso: cert.curso || "N/A",
                nota: cert.nota || "N/A",
                fecha: cert.fecha || "N/A",
                archivo: cert.nombre_archivo || "N/A"
            }))
        };

        btnGenerar.disabled = false;
        mostrarToast(`Documentos de <strong>${estudianteValidado.nombre}</strong> validados correctamente. Ya puede generar la resolución.`, "Validación Exitosa", "exito", 5000);

    } catch (error) {
        console.error("Error en validación:", error);
        estudianteValidado = null;
        btnGenerar.disabled = true;
        mostrarToast(error.message, "Error al Validar", "error", 5000);
    }
});

// Generar resolución final + anexos
btnGenerar.addEventListener('click', async () => {
    if (!estudianteValidado) {
        mostrarToast("Primero debe validar los documentos antes de generar la resolución.", "Validación Requerida", "advertencia");
        return;
    }
    if (!selectPrograma.value) {
        mostrarToast("Seleccione el programa de destino.", "Programa Requerido", "error");
        return;
    }

    const materiasSeleccionadas = obtenerMateriasSeleccionadas();
    if (materiasSeleccionadas.length === 0) {
        mostrarToast("Seleccione al menos una materia a homologar.", "Materia Requerida", "error");
        return;
    }

    if (!selectTipo.value) {
        mostrarToast("Seleccione el proveedor del certificado.", "Proveedor Requerido", "error");
        return;
    }

    if (!inputTipoNotaValor.value) {
        mostrarToast("Seleccione el tipo de nota (Cuantitativa o Cualitativa).", "Tipo de Nota Requerido", "error");
        return;
    }

    // Validar restricción de proveedor (ESRI solo para Posgrados)
    if (selectTipo.value === 'esri' && !esPosgrado(selectPrograma.value)) {
        mostrarToast("Los certificados de ESRI solo están permitidos para programas de Posgrado (Especializaciones y Maestrías).", "Proveedor No Permitido", "error");
        return;
    }

    // Validar cantidad esperada acumulada
    const esperados = calcularCertificadosEsperados(selectPrograma.value, selectTipo.value);
    if (archivosEnMemoria.length !== esperados) {
        if (selectTipo.value === 'esri') {
            mostrarToast(`Ha seleccionado ${materiasSeleccionadas.length} materia(s) en posgrado con ESRI (se requieren 2 certificados por materia, total ${esperados}). Ha cargado ${archivosEnMemoria.length}.`, "Cantidad de Certificados Incorrecta", "error");
        } else {
            const creditosUnidad = CREDITOS_POR_PROGRAMA[selectPrograma.value] || 3;
            mostrarToast(`Ha seleccionado ${materiasSeleccionadas.length} materia(s) de ${creditosUnidad} crédito(s) cada una (total ${esperados} certificados para Opened). Ha cargado ${archivosEnMemoria.length}.`, "Cantidad de Certificados Incorrecta", "error");
        }
        return;
    }

    try {
        mostrarToast("Generando documento de resolución final con anexos...", "Procesando", "info", 3000);

        const formData = new FormData();
        const nombreManual = (inputNombreManual && inputNombreManual.value) ? inputNombreManual.value.trim() : '';

        formData.append("codigo_estudiante", estudianteValidado.codigo);
        formData.append("tipo_certificado", selectTipo.value);
        formData.append("programa_destino", selectPrograma.value);
        formData.append("materia_homologar", JSON.stringify(materiasSeleccionadas));
        formData.append("tipo_nota", document.getElementById('tipo_nota_valor').value);
        formData.append("nombre_estudiante_manual", nombreManual);
        formData.append(
            "resultados",
            JSON.stringify(estudianteValidado.certificados)
        );

        archivosEnMemoria.forEach(archivo => {
            formData.append("archivos", archivo);
        });

        const response = await fetch('/api/generar-resolucion-final', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP Status: ${response.status}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = `Resolucion_${estudianteValidado.codigo}_FINAL.docx`;

        document.body.appendChild(link);
        link.click();

        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        mostrarToast("Resolución final generada y descargada correctamente.", "Descarga Completada", "exito", 5000);

    } catch (error) {
        console.error("Error generando resolución final:", error);
        mostrarToast(error.message, "Error al Generar", "error", 6000);
    }
});