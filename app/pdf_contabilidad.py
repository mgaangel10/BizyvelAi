from fpdf import FPDF
from datetime import datetime
from typing import Dict

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Informe Contable - Bizyvel", ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, 'C')

def generar_pdf_contabilidad(resumen: Dict, nombre_archivo: str, analisis_ia: str = ""):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 12)

    pdf.cell(0, 10, f"Ingresos: {resumen['ingresos']:.2f} EUR", ln=True)
    pdf.cell(0, 10, f"Gastos: {resumen['gastos']:.2f} EUR", ln=True)
    pdf.cell(0, 10, f"Beneficio Neto: {resumen['beneficio_neto']:.2f} EUR", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Gastos por Categoría:", ln=True)
    pdf.set_font("Arial", "", 12)
    for cat, monto in resumen['por_categoria'].items():
        pdf.cell(0, 10, f"- {cat.capitalize()}: {monto:.2f} EUR", ln=True)

    if resumen['alertas']:
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Alertas:", ln=True)
        pdf.set_font("Arial", "", 12)
        for alerta in resumen['alertas']:
            texto_alerta = alerta.replace("⚠️", "ALERTA:").replace("€", "EUR")
            pdf.multi_cell(0, 10, texto_alerta)

    if analisis_ia:
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Análisis de IA:", ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, analisis_ia)

    pdf.output(nombre_archivo)
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Informe BizyBel - Análisis Contable de Inteligencia Artificial", ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, "Generado automáticamente por IA", 0, 0, 'C')

def generar_pdf_ia(contenido: str, nombre_archivo: str):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, contenido)
    pdf.output(nombre_archivo)
