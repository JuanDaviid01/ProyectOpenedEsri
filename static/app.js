let estudianteValidado = null;
let archivosEnMemoria = [];
const inputArchivos = document.getElementById('archivos');
const listaArchivos = document.querySelector('.lista-archivos');
const btnValidar = document.getElementById('btn-validar');
const btnGenerar = document.getElementById('btn-generar');
const inputCodigo = document.getElementById('codigo_estudiante');
const selectTipo = document.getElementById('tipo_certificado');

// Cargar archivos en memoria
inputArchivos.addEventListener('change', () => {
    Array.from(inputArchivos.files).forEach(archivo => {
        archivosEnMemoria.push(archivo);
    });

    inputArchivos.value = '';
    renderizarLista();
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
        // Flexbox inline para separar nombre y botón
        nodoArchivo.style.display = 'flex';
        nodoArchivo.style.justifyContent = 'space-between';
        nodoArchivo.style.alignItems = 'center';
        nodoArchivo.style.marginBottom = '5px';

        const textoArchivo = document.createElement('span');
        textoArchivo.textContent = `${archivo.name} (${(archivo.size / 1024).toFixed(2)} KB)`;

        // Botón de eliminación con inyección de evento en el callback
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
    // Mutación del array de estado
    archivosEnMemoria.splice(index, 1);

    // Invalida el estado de la validación anterior por seguridad transaccional
    if (estudianteValidado) {
        estudianteValidado = null;
        alert("Atención: Al modificar los archivos, debe volver a Validar los Documentos.");
    }

    // Renderizado reactivo
    renderizarLista();
}

// Validar documentos
btnValidar.addEventListener('click', async () => {
    const codigoEstudiante = inputCodigo.value.trim();
    if (archivosEnMemoria.length < 3) {
        alert("Error: La normativa exige un mínimo de 3 certificados para este proceso.");
        return;
    }
    if (!codigoEstudiante) {
        alert("Error: Ingrese el código del estudiante.");
        return;
    }

    if (!selectTipo.value) {
        alert("Error: Seleccione el proveedor del certificado.");
        return;
    }

    if (archivosEnMemoria.length === 0) {
        alert("Error: Cargue al menos un documento.");
        return;
    }

    const formData = new FormData();

    archivosEnMemoria.forEach(archivo => {
        formData.append('archivos', archivo);
    });

    formData.append('tipo_certificado', selectTipo.value);

    try {
        const response = await fetch('http://localhost:5000/api/extraer', {
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
            alert("Error crítico: Se detectaron certificados pertenecientes a diferentes estudiantes en el mismo lote.");
            return;
        }

        estudianteValidado = {
            codigo: codigoEstudiante,
            nombre: (datosCrudos[0].estudiante || '').trim(),
            certificados: datosCrudos.map(cert => ({
                curso: cert.curso || "N/A",
                nota: cert.nota || "N/A",
                fecha: cert.fecha || "N/A",
                archivo: cert.nombre_archivo || "N/A"
            }))
        };

        console.log("Validación superada:", estudianteValidado);
        alert("Documentos validados correctamente. Listo para generar resolución.");

    } catch (error) {
        console.error("Error en validación:", error);
        estudianteValidado = null;
        alert(`Error procesando la petición: ${error.message}`);
    }
});

// Generar resolución final + anexos
btnGenerar.addEventListener('click', async () => {
    // 1. Validaciones de estado
    if (!estudianteValidado) {
        alert("Primero debe validar los documentos antes de generar la resolución.");
        return;
    }
    if (archivosEnMemoria.length < 3) {
        alert("Error: La normativa exige un mínimo de 3 certificados para este proceso.");
        return;
    }
    if (!selectTipo.value) {
        alert("Seleccione el proveedor del certificado.");
        return;
    }

    if (archivosEnMemoria.length === 0) {
        alert("No hay archivos cargados para anexar.");
        return;
    }

    try {
        // 2. Instanciación e hidratación del payload multipart
        const formData = new FormData();
        formData.append("codigo_estudiante", estudianteValidado.codigo);
        formData.append("tipo_certificado", selectTipo.value);
        formData.append(
            "resultados",
            JSON.stringify(estudianteValidado.certificados)
        );

        archivosEnMemoria.forEach(archivo => {
            formData.append("archivos", archivo);
        });

        // 3. Petición POST al backend
        const response = await fetch('http://localhost:5000/api/generar-resolucion-final', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            // Manejo de errores controlados por la API
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP Status: ${response.status}`);
        }

        // 4. Manejo del I/O binario y descarga
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = `Resolucion_${estudianteValidado.codigo}_FINAL.docx`;

        document.body.appendChild(link);
        link.click();

        // Garbage collection
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        alert("Resolución final generada y descargada correctamente.");

    } catch (error) {
        console.error("Error generando resolución final:", error);
        alert(`Ocurrió un error al generar la resolución final: ${error.message}`);
    }
});