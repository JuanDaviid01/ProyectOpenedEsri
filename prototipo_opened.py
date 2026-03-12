import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pdfplumber
import re
import random
from datetime import datetime
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


# almacenar estudiantes cargados
estudiantes = {}

def generar_pdf(nombre, cedula, cursos, creditos, radicado):

    os.makedirs("RADICADOS", exist_ok=True)

    archivo = f"RADICADOS/radicado_{cedula}.pdf"

    c = canvas.Canvas(archivo, pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(150, 750, "UNIVERSIDAD DE MANIZALES")

    c.setFont("Helvetica", 12)
    c.drawString(180, 720, "Sistema de Homologación de Electivas")

    c.drawString(100, 680, f"Radicado: {radicado}")
    c.drawString(100, 660, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")

    c.drawString(100, 620, f"Nombre: {nombre}")
    c.drawString(100, 600, f"Cédula: {cedula}")

    c.drawString(100, 560, "Cursos certificados:")

    y = 540
    for curso in cursos:
        c.drawString(120, y, f"- {curso}")
        y -= 20

    c.drawString(100, 480, f"Créditos obtenidos: {creditos}")

    if creditos >= 2:
        estado = "Cumple con los requisitos para homologar la asignatura electiva."
    else:
        estado = "No cumple con los créditos requeridos."

    c.drawString(100, 450, estado)

    c.save()


def extraer_datos(pdf):

    texto = ""

    with pdfplumber.open(pdf) as pdf_file:
        for page in pdf_file.pages:
            contenido = page.extract_text()
            if contenido:
                texto += contenido

    nombre_match = re.search(r'CERTIFICAN QUE:\s*(.*?)\s*Con Cédula', texto)
    cedula_match = re.search(r'Cédula de ciudadanía\s*(\d+)', texto)
    curso_match = re.search(r'curso\s*\n*(.*?)\n*Con una duración', texto, re.DOTALL)

    nombre = nombre_match.group(1) if nombre_match else "No encontrado"
    cedula = cedula_match.group(1) if cedula_match else "No encontrado"
    curso = curso_match.group(1) if curso_match else "No encontrado"

    return nombre, cedula, curso


def generar_radicado():

    numero = random.randint(1000, 9999)
    año = datetime.now().year

    return f"HOM-{año}-{numero}"


def cargar_pdfs():

    archivos = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])

    for pdf in archivos:

        nombre, cedula, curso = extraer_datos(pdf)

        if cedula not in estudiantes:

            estudiantes[cedula] = {
                "nombre": nombre,
                "cursos": [],
                "creditos": 0
            }

        estudiantes[cedula]["cursos"].append(curso)
        estudiantes[cedula]["creditos"] += 1

        tabla.insert("", "end", values=(nombre, cedula, curso, 1))


def generar_radicados():

    for cedula, datos in estudiantes.items():

        if datos["creditos"] >= 2:

            radicado = generar_radicado()

            generar_pdf(
                datos["nombre"],
                cedula,
                datos["cursos"],
                datos["creditos"],
                radicado
            )

            messagebox.showinfo(
                "Radicado generado",
                f"Radicado {radicado} generado para {datos['nombre']}"
            )

        else:

            messagebox.showwarning(
                "Créditos insuficientes",
                f"{datos['nombre']} no cumple con los créditos requeridos"
            )


# INTERFAZ

ventana = tk.Tk()
ventana.title("Sistema de Radicación de Certificados")
ventana.geometry("900x500")


boton_cargar = tk.Button(
    ventana,
    text="Seleccionar Certificados",
    command=cargar_pdfs
)

boton_cargar.pack(pady=10)


boton_radicado = tk.Button(
    ventana,
    text="Generar Radicado",
    command=generar_radicados,
    bg="green",
    fg="white"
)

boton_radicado.pack(pady=10)


tabla = ttk.Treeview(
    ventana,
    columns=("Nombre", "Documento", "Curso", "Créditos"),
    show="headings"
)

tabla.heading("Nombre", text="Nombre")
tabla.heading("Documento", text="Documento")
tabla.heading("Curso", text="Curso")
tabla.heading("Créditos", text="Créditos")

tabla.pack(fill="both", expand=True)


ventana.mainloop()