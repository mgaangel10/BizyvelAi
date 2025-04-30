import datetime
import json
import os

from openai import OpenAI
from .ventas_fake import obtener_venta_por_id  # Usa el punto si estás en /app

from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def analizar_mensaje_factura(texto: str) -> dict:
    prompt = f"""
Eres un asistente inteligente que interpreta mensajes para generar facturas.

Del siguiente mensaje:
\"\"\"{texto}\"\"\"

Extrae y devuelve un JSON con los siguientes campos:
- cliente
- email
- fecha (opcional, formato YYYY-MM-DD)
- productos (lista de objetos con: nombre, cantidad, precio)
- NombreEmpresa (opcional)
- cid (opcional)

Ejemplo de salida esperada:
{{
  "cliente": "Juan Pérez",
  "email": "juanp@gmail.com",
  "fecha": "2025-05-15",
  "productos": [
    {{"nombre": "zapatillas", "cantidad": 2, "precio": 50}},
    {{"nombre": "sudadera", "cantidad": 1, "precio": 40}}
  ],
  "NombreEmpresa": "Sportify S.A.",
  "cid": "C-00123"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        datos = json.loads(response.choices[0].message.content)

        # Valores por defecto si faltan
        datos["NombreEmpresa"] = datos.get("NombreEmpresa", "Bizyvel S.A.")
        datos["cid"] = datos.get("cid", "C-987654")
        datos["fecha"] = datos.get("fecha", datetime.now().strftime("%Y-%m-%d"))
        datos["productos"] = datos.get("productos", [])

        return datos

    except Exception as e:
        print("❌ Error al analizar el mensaje:", e)
        return {}

def analizar_archivo_contabilidad(resumen: dict) -> str:
    print("📊 Analizando contabilidad con IA...")

    prompt = f"""
    Aquí tienes un resumen contable de un negocio:

    Ingresos: {resumen['ingresos']} EUR
    Gastos: {resumen['gastos']} EUR
    Beneficio neto: {resumen['beneficio_neto']} EUR
    Gastos por categoría: {resumen['por_categoria']}
    Alertas: {resumen['alertas']}

    Como asistente contable, analiza estos datos y genera recomendaciones concretas:
    - ¿Qué observas?
    - ¿Qué decisiones sugerirías?
    - ¿Dónde puede ahorrar el negocio?
    - ¿Alguna inversión o estrategia recomendada?
    """

    respuesta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    resultado = respuesta.choices[0].message.content
    print("✅ Análisis IA generado:", resultado)

    return resultado


