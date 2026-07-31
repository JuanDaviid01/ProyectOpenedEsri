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

// MAPEO DE ELECTIVAS DISPONIBLES POR PROGRAMA
const ELECTIVAS_POR_PROGRAMA = {
    "Ingeniería en Sistemas y Telecomunicaciones Presencial": ["Electiva I", "Electiva II"],
    "Ingeniería en Sistemas y Telecomunicaciones Virtual": ["Electiva I", "Electiva II"],
    "Ingeniería en analítica de datos presencial": ["Electiva I", "Electiva II", "Electiva III"],
    "Ingeniería en analítica de datos virtual": ["Electiva I", "Electiva II", "Electiva III"],
    "Ingeniería Logística Presencial": ["Electiva I", "Electiva II", "Electiva III", "Electiva IV"],
    "Ingeniería Logística Virtual": ["Electiva I", "Electiva II", "Electiva III", "Electiva IV"],
    "Ingeniería en Seguridad de la Información Presencial": ["Electiva I", "Electiva II"],
    "Ingeniería en Seguridad de la Información Virtual": ["Electiva I", "Electiva II"],
    "Ingeniería Industrial": ["Electiva I", "Electiva II"],
    "Especialización en Sistemas de información geográfica": ["Electiva I", "Electiva II"],
    "Maestría en Tecnologías de la información geográfica": ["Electiva I", "Electiva II"],
    "Maestría en Educación y transformación digital": ["Electiva I", "Electiva II", "Electiva III", "Electiva IV"]
};

// Segmentador tipo de nota
document.querySelectorAll('#tipo_nota .seg-opcion').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('#tipo_nota .seg-opcion').forEach(b => b.classList.remove('activo'));
        btn.classList.add('activo');
        document.getElementById('tipo_nota_valor').value = btn.dataset.valor;
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
const selectPrograma = document.getElementById('programa_destino');
const selectMateria = document.getElementById('materia_homologar');

// Función para actualizar dinámicamente las materias a homologar según el programa
function actualizarOpcionesElectivas() {
    const programaSeleccionado = selectPrograma.value;
    selectMateria.innerHTML = '';

    if (!programaSeleccionado || !ELECTIVAS_POR_PROGRAMA[programaSeleccionado]) {
        selectMateria.disabled = true;
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Seleccione primero un programa';
        opt.disabled = true;
        opt.selected = true;
        selectMateria.appendChild(opt);
        return;
    }

    selectMateria.disabled = false;
    const defaultOpt = document.createElement('option');
    defaultOpt.value = '';
    defaultOpt.textContent = 'Seleccionar materia';
    defaultOpt.disabled = true;
    defaultOpt.selected = true;
    selectMateria.appendChild(defaultOpt);

    const electivasDisponibles = ELECTIVAS_POR_PROGRAMA[programaSeleccionado];
    electivasDisponibles.forEach(electiva => {
        const opt = document.createElement('option');
        opt.value = electiva;
        opt.textContent = electiva;
        selectMateria.appendChild(opt);
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
        
        // Resetear validación
        invalidarValidacion(false);
    }
});

// Eventos de cambios en campos del formulario
selectPrograma.addEventListener('change', () => {
    actualizarOpcionesElectivas();
    invalidarValidacion(false);
});

selectMateria.addEventListener('change', () => {
    invalidarValidacion(false);
});

selectTipo.addEventListener('change', () => {
    invalidarValidacion(false);
});

// Cargar archivos en memoria
inputArchivos.addEventListener('change', () => {
    Array.from(inputArchivos.files).forEach(archivo => {
        archivosEnMemoria.push(archivo);
    });

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

// Validar documentos
btnValidar.addEventListener('click', async () => {
    const codigoEstudiante = inputCodigo.value.trim();
    if (!codigoEstudiante) {
        mostrarToast("Ingrese el código del estudiante.", "Código Requerido", "error");
        return;
    }

    if (archivosEnMemoria.length < 1) {
        mostrarToast("Cargue al menos 1 certificado para realizar la validación.", "Archivos Requeridos", "error");
        return;
    }

    if (!selectTipo.value) {
        mostrarToast("Seleccione el proveedor del certificado.", "Proveedor Requerido", "error");
        return;
    }

    const formData = new FormData();

    archivosEnMemoria.forEach(archivo => {
        formData.append('archivos', archivo);
    });

    formData.append('tipo_certificado', selectTipo.value);

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

        estudianteValidado = {
            codigo: codigoEstudiante,
            nombre: (datosCrudos[0].estudiante || '').trim(),
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
    if (archivosEnMemoria.length < 1) {
        mostrarToast("Cargue al menos 1 certificado para este proceso.", "Archivos Requeridos", "error");
        return;
    }
    if (!selectTipo.value) {
        mostrarToast("Seleccione el proveedor del certificado.", "Proveedor Requerido", "error");
        return;
    }

    if (!selectPrograma.value) {
        mostrarToast("Seleccione el programa de destino.", "Programa Requerido", "error");
        return;
    }

    if (!selectMateria.value) {
        mostrarToast("Seleccione la materia a homologar.", "Materia Requerida", "error");
        return;
    }

    try {
        mostrarToast("Generando documento de resolución final con anexos...", "Procesando", "info", 3000);

        const formData = new FormData();
        formData.append("codigo_estudiante", estudianteValidado.codigo);
        formData.append("tipo_certificado", selectTipo.value);
        formData.append("programa_destino", selectPrograma.value);
        formData.append("materia_homologar", selectMateria.value);
        formData.append("tipo_nota", document.getElementById('tipo_nota_valor').value);
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