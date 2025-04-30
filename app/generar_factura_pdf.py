from fpdf import FPDF
from datetime import datetime
import os

# Ruta al logo
base_dir = os.path.dirname(os.path.abspath(__file__))
ruta_logo = os.path.join(base_dir, "../logo/img.png")

class PDF(FPDF):
    def header(self):
        # Logo si existe
        if os.path.exists(ruta_logo):
            self.image(ruta_logo, 10, 8, 33)

        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Bizyvel - Tu negocio inteligente", ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, 'C')


def crear_factura_pdf(data: dict, destino):
    from app.generar_factura_pdf import PDF  # asegúrate de usar TU clase, no FPDF directa



    pdf = PDF()
    pdf.add_page()

    # Título
    pdf.set_font("Arial", "B", 16)
    numero_factura = data.get("numeroFactura", "SIN-NUMERO")
    pdf.cell(0, 10, f"Factura Nº {numero_factura}", ln=True, align="C")
    pdf.ln(5)

    # Datos de cabecera
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Empresa: {data.get('nombreEmpresa', 'Empresa desconocida')}", ln=True)
    pdf.cell(0, 10, f"CID: {data.get('cid', 'N/A')}", ln=True)
    pdf.cell(0, 10, f"Albarán Nº: {data.get('numeroAlbaran', '---')}", ln=True)

    fecha = data.get("ventaDto", {}).get("fecha", datetime.today().strftime("%Y-%m-%d"))
    pdf.cell(0, 10, f"Fecha: {fecha}", ln=True)
    pdf.cell(0, 10, f"Cliente: {data.get('cliente', 'Sin nombre')}", ln=True)
    pdf.ln(10)

    # Tabla de productos
    productos = data.get("ventaDto", {}).get("detalleVentas", [])

    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(80, 10, "Producto", 1, 0, "C", fill=True)
    pdf.cell(30, 10, "Cantidad", 1, 0, "C", fill=True)
    pdf.cell(40, 10, "Precio", 1, 0, "C", fill=True)
    pdf.cell(40, 10, "Total", 1, 1, "C", fill=True)

    pdf.set_font("Arial", "", 12)
    for p in productos:
        nombre = p.get("nombreProducto", "Producto")
        cantidad = p.get("cantida", 0)
        precio = p.get("precioProducto", 0)
        total = cantidad * precio
        pdf.cell(80, 10, nombre, 1)
        pdf.cell(30, 10, str(cantidad), 1, 0, "C")
        pdf.cell(40, 10, f"${precio:.2f}", 1, 0, "R")
        pdf.cell(40, 10, f"${total:.2f}", 1, 1, "R")

    # Totales
    subtotal = data.get("subtotal", 0)
    impuestos = data.get("impuestos", 0)
    total = data.get("total", subtotal + impuestos)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(150, 10, "Subtotal", 0)
    pdf.cell(40, 10, f"${subtotal:.2f}", 0, 1, "R")
    pdf.cell(150, 10, "Impuestos", 0)
    pdf.cell(40, 10, f"${impuestos:.2f}", 0, 1, "R")
    pdf.cell(150, 10, "TOTAL", 0)
    pdf.cell(40, 10, f"${total:.2f}", 0, 1, "R")

    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, "Gracias por tu compra.", ln=True, align="C")

    # Guardar o enviar
    if isinstance(destino, str):
        pdf.output(destino)
        print(f"✅ Factura guardada en archivo: {destino}")
    else:
        # 🔥 Solución para BytesIO
        pdf_bytes = pdf.output(dest='S').encode('latin1')  # 'S' = return as string
        destino.write(pdf_bytes)
        print("✅ Factura escrita en memoria para enviar por red")


class PDFCierre(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Informe de Cierre Mensual - IA", ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, 'C')

def generar_pdf_cierre_ia(analisis: str, nombre_archivo: str):
    pdf = PDFCierre()
    pdf.add_page()
    pdf.set_font("Arial", "", 12)

    lineas = analisis.split('\n')
    for linea in lineas:
        pdf.multi_cell(0, 10, linea)

    pdf.output(nombre_archivo)

class PDFTextoIA(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Informe Inteligente - Bizyvel", ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, 'C')

def generar_pdf_texto_ia(texto: str, nombre_archivo: str):
    texto = texto.encode('ascii', 'ignore').decode()  # Quita emojis y caracteres especiales
    pdf = PDFTextoIA()
    pdf.add_page()
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, texto)
    pdf.output(nombre_archivo)

import re

import pandas as pd
import io

def extraer_correos_desde_excel(contenido_excel: bytes) -> list[str]:
    df = pd.read_excel(io.BytesIO(contenido_excel))

    # Asegurarnos de que hay una columna con emails (puede llamarse 'correo' o similar)
    posibles_columnas = ["correo", "correos", "email", "emails"]
    columna_email = next((col for col in df.columns if col.lower() in posibles_columnas), None)

    if not columna_email:
        raise ValueError("No se encontró una columna de correos en el archivo.")

    # Limpiamos nulos y espacios
    lista_correos = df[columna_email].dropna().astype(str).str.strip().tolist()

    return lista_correos
