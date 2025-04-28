import io
from fastapi import HTTPException
from .pdf_contabilidad import generar_pdf_contabilidad

from fastapi import APIRouter, UploadFile, File
from app.analyzer import analizar_archivo
from datetime import datetime
import os
import pandas as pd

router = APIRouter()

@router.post("/analizar/")
async def recibir_archivo(file: UploadFile = File(...)):
    contenido = await file.read()
    nombre = file.filename
    resultado = analizar_archivo(nombre, contenido)
    return {"resultado": resultado}


