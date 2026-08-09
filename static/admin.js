
document.addEventListener('DOMContentLoaded', () => {
    cargarUsuariosAdmin();
    cargarProgramasAdmin();
});

function cambiarSeccion(seccion) {
    document.getElementById('sec-usuarios').style.display = (seccion === 'usuarios') ? 'block' : 'none';
    document.getElementById('sec-programas').style.display = (seccion === 'programas') ? 'block' : 'none';

    document.getElementById('tab-btn-usuarios').classList.toggle('activo', seccion === 'usuarios');
    document.getElementById('tab-btn-programas').classList.toggle('activo', seccion === 'programas');
}


async function cargarUsuariosAdmin() {
    try {
        const res = await fetch('/api/admin/usuarios');
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'Error al cargar usuarios');
        }
        const usuarios = await res.json();
        renderizarTablaUsuarios(usuarios);
    } catch (error) {
        console.error('Error usuarios:', error);
        mostrarToast(error.message, 'Error Admin', 'error');
    }
}

function renderizarTablaUsuarios(usuarios) {
    const tbody = document.getElementById('tbody-usuarios');
    tbody.innerHTML = '';

    let pendientesCount = 0;

    const lista = Object.keys(usuarios).map(k => ({
        username: k,
        ...usuarios[k]
    }));

    if (lista.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">No hay usuarios registrados.</td></tr>';
        document.getElementById('badge-pendientes-count').textContent = '0';
        return;
    }

    lista.forEach(u => {
        if (u.estado === 'pendiente') pendientesCount++;

        const tr = document.createElement('tr');

        const badgeEstado = u.estado === 'aprobado'
            ? '<span class="status-badge status-aprobado">Aprobado</span>'
            : (u.estado === 'pendiente'
                ? '<span class="status-badge status-pendiente">Pendiente</span>'
                : '<span class="status-badge status-rechazado">Inhabilitado</span>');

        const badgeRol = u.rol === 'admin'
            ? '<span class="role-badge role-admin">Administrador</span>'
            : '<span class="role-badge">Operador</span>';

        let acciones = '';
        if (u.estado === 'pendiente') {
            acciones += `<button class="btn-accion-sm btn-aprobar" onclick="cambiarEstadoUsuario('${u.username}', 'aprobado')">Aprobar</button>`;
            acciones += `<button class="btn-accion-sm btn-rechazar" onclick="cambiarEstadoUsuario('${u.username}', 'rechazado')">Rechazar</button>`;
        } else if (u.estado === 'aprobado') {
            acciones += `<button class="btn-accion-sm btn-rechazar" onclick="cambiarEstadoUsuario('${u.username}', 'rechazado')">Inhabilitar</button>`;
        } else {
            acciones += `<button class="btn-accion-sm btn-aprobar" onclick="cambiarEstadoUsuario('${u.username}', 'aprobado')">Re-Activar</button>`;
        }

        if (u.rol !== 'admin') {
            acciones += `<button class="btn-accion-sm" style="background:#0284c7; color:white;" onclick="cambiarRolUsuario('${u.username}', 'admin')">Hacer Admin</button>`;
        } else {
            acciones += `<button class="btn-accion-sm" style="background:#64748b; color:white;" onclick="cambiarRolUsuario('${u.username}', 'operador')">Hacer Operador</button>`;
        }

        acciones += `<button class="btn-accion-sm btn-eliminar-usr" onclick="eliminarUsuario('${u.username}')">Eliminar</button>`;

        tr.innerHTML = `
            <td><strong>${u.username}</strong></td>
            <td>${u.nombre}</td>
            <td>${badgeRol}</td>
            <td>${badgeEstado}</td>
            <td>${acciones}</td>
        `;

        tbody.appendChild(tr);
    });

    const badgeEl = document.getElementById('badge-pendientes-count');
    badgeEl.textContent = pendientesCount;
    badgeEl.style.display = (pendientesCount > 0) ? 'inline-block' : 'none';
}

async function cambiarEstadoUsuario(username, nuevoEstado) {
    try {
        const res = await fetch('/api/admin/usuarios/estado', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, estado: nuevoEstado })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        mostrarToast(`Estado de ${username} actualizado a ${nuevoEstado}.`, 'Usuario Actualizado', 'exito');
        cargarUsuariosAdmin();
    } catch (error) {
        mostrarToast(error.message, 'Error', 'error');
    }
}

async function cambiarRolUsuario(username, nuevoRol) {
    try {
        const res = await fetch('/api/admin/usuarios/rol', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, rol: nuevoRol })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        mostrarToast(`Rol de ${username} cambiado a ${nuevoRol}.`, 'Usuario Actualizado', 'exito');
        cargarUsuariosAdmin();
    } catch (error) {
        mostrarToast(error.message, 'Error', 'error');
    }
}

async function eliminarUsuario(username) {
    if (!confirm(`¿Está seguro de que desea eliminar permanentemente al usuario '${username}'?`)) return;

    try {
        const res = await fetch(`/api/admin/usuarios/${username}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        mostrarToast(`Usuario ${username} eliminado correctamente.`, 'Usuario Eliminado', 'info');
        cargarUsuariosAdmin();
    } catch (error) {
        mostrarToast(error.message, 'Error', 'error');
    }
}


let catalogProgramasGlobal = [];

async function cargarProgramasAdmin() {
    try {
        const res = await fetch('/api/programas');
        if (!res.ok) throw new Error('Error al cargar programas');
        const data = await res.json();
        catalogProgramasGlobal = data.programas || [];
        renderizarGridProgramas(catalogProgramasGlobal);
    } catch (error) {
        console.error('Error programas:', error);
        mostrarToast(error.message, 'Error Catálogo', 'error');
    }
}

function renderizarGridProgramas(programas) {
    const grid = document.getElementById('grid-programas');
    grid.innerHTML = '';

    if (programas.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 30px; color: #64748b;">No hay programas registrados en el catálogo.</div>';
        return;
    }

    programas.forEach(p => {
        const item = document.createElement('div');
        item.className = 'card-programa-item';

        let electivasHtml = '';
        (p.electivas || []).forEach(e => {
            electivasHtml += `
                <div class="electiva-row">
                    <span>${e.nombre} (${e.creditos || 3} cr.)</span>
                    <span class="code-tag">${e.codigo}</span>
                </div>
            `;
        });

        const provTag = p.proveedores_permitidos === 'opened'
            ? 'Solo Opened'
            : (p.proveedores_permitidos === 'esri' ? 'Solo ESRI' : 'Opened y ESRI');

        item.innerHTML = `
            <div class="prog-title">${p.nombre}</div>
            <div class="prog-meta">
                <span>Nivel: <strong>${(p.nivel || 'pregrado').toUpperCase()}</strong></span>
                <span>Proveedores: <strong>${provTag}</strong></span>
            </div>
            <div class="electivas-mini-list">
                <div style="font-size: 11px; font-weight: bold; color: #94a3b8; margin-bottom: 4px; text-transform: uppercase;">Electivas, Créditos y Códigos</div>
                ${electivasHtml || '<div style="font-size: 12px; color: #94a3b8;">Sin electivas configuradas</div>'}
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 15px;">
                <button class="btn-accion-sm" style="background:#0284c7; color:white;" onclick="editarPrograma('${p.id}')">Editar</button>
                <button class="btn-accion-sm btn-eliminar-usr" onclick="eliminarPrograma('${p.id}', '${p.nombre}')">Eliminar</button>
            </div>
        `;

        grid.appendChild(item);
    });
}

function abrirModalPrograma() {
    document.getElementById('modal-prog-titulo').textContent = 'Agregar Nuevo Programa';
    document.getElementById('prog-id').value = '';
    document.getElementById('prog-nombre').value = '';
    document.getElementById('prog-nivel').value = 'pregrado';
    document.getElementById('prog-proveedores').value = 'opened';

    const cont = document.getElementById('contenedor-electivas-form');
    cont.innerHTML = '';
    agregarFilaElectivaForm('Electiva I', '', 3);
    agregarFilaElectivaForm('Electiva II', '', 3);

    document.getElementById('modal-programa').style.display = 'flex';
}

function cerrarModalPrograma() {
    document.getElementById('modal-programa').style.display = 'none';
}

function agregarFilaElectivaForm(nombre = '', codigo = '', creditos = 3) {
    const cont = document.getElementById('contenedor-electivas-form');
    const div = document.createElement('div');
    div.className = 'fila-electiva-form';
    div.style.display = 'flex';
    div.style.gap = '8px';
    div.style.marginBottom = '8px';
    div.style.alignItems = 'center';

    div.innerHTML = `
        <input type="text" placeholder="Electiva (ej: Electiva I)" value="${nombre}" required style="flex: 2; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px;">
        <input type="number" placeholder="Créditos" value="${creditos}" min="1" max="10" required style="width: 75px; padding: 8px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px;">
        <input type="text" placeholder="Código (ej: C5808002)" value="${codigo}" required style="flex: 2; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px;">
        <button type="button" onclick="this.parentElement.remove()" style="background: #fee2e2; color: #b91c1c; border: none; padding: 6px 10px; border-radius: 6px; cursor: pointer; font-weight: bold;">Eliminar</button>
    `;
    cont.appendChild(div);
}

function editarPrograma(progId) {
    const p = catalogProgramasGlobal.find(x => x.id === progId);
    if (!p) return;

    document.getElementById('modal-prog-titulo').textContent = 'Editar Programa Académico';
    document.getElementById('prog-id').value = p.id;
    document.getElementById('prog-nombre').value = p.nombre;
    document.getElementById('prog-nivel').value = p.nivel || 'pregrado';
    document.getElementById('prog-proveedores').value = p.proveedores_permitidos || 'ambos';

    const cont = document.getElementById('contenedor-electivas-form');
    cont.innerHTML = '';

    (p.electivas || []).forEach(e => {
        agregarFilaElectivaForm(e.nombre, e.codigo, e.creditos || p.creditos_unidad || 3);
    });

    document.getElementById('modal-programa').style.display = 'flex';
}

async function guardarPrograma(e) {
    e.preventDefault();

    const progId = document.getElementById('prog-id').value.trim();
    const nombre = document.getElementById('prog-nombre').value.trim();
    const nivel = document.getElementById('prog-nivel').value;
    const proveedores_permitidos = document.getElementById('prog-proveedores').value;

    const filas = document.querySelectorAll('.fila-electiva-form');
    const electivas = [];

    filas.forEach(f => {
        const inputs = f.querySelectorAll('input');
        const eNombre = inputs[0].value.trim();
        const eCreditos = intVal(inputs[1].value, 3);
        const eCodigo = inputs[2].value.trim();
        if (eNombre && eCodigo) {
            electivas.push({ nombre: eNombre, creditos: eCreditos, codigo: eCodigo });
        }
    });

    if (electivas.length === 0) {
        mostrarToast('Agregue al menos una electiva con sus créditos y código.', 'Electivas Requeridas', 'error');
        return;
    }

    const payload = {
        id: progId || `prog_${Date.now()}`,
        nombre,
        nivel,
        proveedores_permitidos,
        creditos_unidad: electivas[0] ? electivas[0].creditos : 3,
        electivas
    };

    try {
        const res = await fetch('/api/admin/programas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        mostrarToast(`Programa '${nombre}' guardado correctamente.`, 'Catálogo Actualizado', 'exito');
        cerrarModalPrograma();
        cargarProgramasAdmin();
    } catch (error) {
        mostrarToast(error.message, 'Error al Guardar', 'error');
    }
}

function intVal(val, def = 3) {
    const parsed = parseInt(val, 10);
    return isNaN(parsed) ? def : parsed;
}

async function eliminarPrograma(progId, nombre) {
    if (!confirm(`¿Está seguro de eliminar el programa '${nombre}' del catálogo?`)) return;

    try {
        const res = await fetch(`/api/admin/programas/${progId}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        mostrarToast(`Programa '${nombre}' eliminado del catálogo.`, 'Catálogo Actualizado', 'info');
        cargarProgramasAdmin();
    } catch (error) {
        mostrarToast(error.message, 'Error', 'error');
    }
}
