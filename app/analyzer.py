import pandas as pd
import io
from datetime import datetime

def analizar_archivo(nombre_archivo: str, contenido: bytes) -> dict:
    if nombre_archivo.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(contenido))
        return analizar_excel(df)
    else:
        return {"error": "Formato no soportado aún"}

def analizar_excel(df: pd.DataFrame) -> dict:
    if "fecha" not in df.columns or "total" not in df.columns:
        return {"error": "Faltan columnas necesarias"}

    df["fecha"] = pd.to_datetime(df["fecha"])
    df["mes"] = df["fecha"].dt.to_period("M")

    ventas_por_mes = {
        str(mes): float(total)
        for mes, total in df.groupby("mes")["total"].sum().items()
    }

    producto_top = df["producto"].value_counts().idxmax()

    recomendaciones = []
    valores = list(ventas_por_mes.values())
    if len(valores) >= 2 and valores[-1] < valores[-2]:
        recomendaciones.append("Las ventas bajaron este mes. ¿Quieres lanzar una promoción?")
    else:
        recomendaciones.append("Las ventas se mantuvieron o subieron.")

    return {
        "ventas_por_mes": ventas_por_mes,
        "producto_mas_vendido": producto_top,
        "recomendaciones": recomendaciones
    }

