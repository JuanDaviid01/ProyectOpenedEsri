// Variable global refactorizada a un objeto estructurado
let estudianteValidado = null;
let archivosEnMemoria = [];

const inputArchivos = document.getElementById('archivos');
const listaArchivos = document.querySelector('.lista-archivos');
const btnValidar = document.querySelector('.btn-principal');
const inputCodigo = document.getElementById('codigo_estudiante'); // 1. Referencia al código

// 1. Acumular archivos en memoria y renderizar
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
    archivosEnMemoria.forEach((archivo) => {
        const nodoArchivo = document.createElement('div');
        nodoArchivo.className = 'archivo-item';
        nodoArchivo.textContent = `${archivo.name} (${(archivo.size / 1024).toFixed(2)} KB)`;
        listaArchivos.appendChild(nodoArchivo);
    });
}

// 2. Request asíncrono y lógica de validación
btnValidar.addEventListener('click', async () => {
    const codigoEstudiante = inputCodigo.value.trim();

    // Validación de pre-condiciones en el DOM
    if (!codigoEstudiante) {
        alert("Error: Ingrese el código del estudiante.");
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

    const tipoSeleccionado = document.getElementById('tipo_certificado').value;
    formData.append('tipo', tipoSeleccionado);

    try {
        const response = await fetch('http://localhost:5000/api/extraer', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP Status: ${response.status}`);
        }

        const datosCrudos = await response.json();

        // 3. Validación de integridad del estudiante (Homologación de nombres)
        const nombreReferencia = datosCrudos[0].estudiante.trim().toLowerCase();

        const nombresInconsistentes = datosCrudos.some(cert =>
            cert.estudiante.trim().toLowerCase() !== nombreReferencia
        );

        if (nombresInconsistentes) {
            alert("Error crítico: Se detectaron certificados pertenecientes a diferentes estudiantes en el mismo lote.");
            return; // Aborta la operación, no guarda en memoria
        }

        // 4. Transformación a estructura de datos relacional (1:N)
        estudianteValidado = {
            codigo: codigoEstudiante,
            nombre: datosCrudos[0].estudiante.trim(),
            certificados: datosCrudos.map(cert => ({
                curso: cert.curso,
                nota: cert.nota,
                fecha: cert.fecha,
                archivo: cert.nombre_archivo
            }))
        };

        console.log("Validación estricta superada. Estructura de datos generada:", estudianteValidado);
        alert("Documentos validados correctamente. Listo para generar resolución.");

    } catch (error) {
        console.error("Excepción XHR/Fetch:", error);
        alert("Error procesando la petición. Verifique stack trace en consola.");
    }
});