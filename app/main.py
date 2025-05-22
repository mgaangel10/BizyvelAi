import io
from typing import Optional

import fitz
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Path
from starlette.responses import StreamingResponse

from .FacturaRequest import VerFactura


from openai import OpenAI
from pydantic import BaseModel
from .factura_parser import analizar_mensaje_factura, analizar_archivo_contabilidad
from .generar_factura_pdf import crear_factura_pdf
from .pdf_contabilidad import generar_pdf_contabilidad
from .enviar_factura import enviar_factura_email
from .analaizar_excel import analizar_archivo
from .generar_factura_pdf import generar_pdf_cierre_ia
from .generar_factura_pdf import generar_pdf_texto_ia
from .generar_factura_pdf import extraer_correos_desde_excel
from .enviar_factura import enviar_promocion_email
from io import BytesIO

from .pdf_contabilidad import generar_pdf_ia
import os
from app.routes import router
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bizyvel IA - Facturación y Análisis")

# 👇 Primero configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O la URL de tu frontend si quieres más seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 👇 Luego incluir las rutas
app.include_router(router)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
class Mensaje(BaseModel):
    mensaje: str

@app.post("/factura")
async def generar_factura_factura(request: VerFactura):
    try:


        datos = request.dict()

        nombre_pdf = f"factura_{datos['numeroFactura']}.pdf"

        # Puedes pasar todos los datos como están al generador de PDF
        crear_factura_pdf(datos, nombre_pdf)

        # (opcional) Si tienes el email del cliente o un campo aparte
        # enviar_factura_email(datos.get("clienteEmail"), nombre_pdf)

        return {
            "estado": "ok",
            "cliente": datos["cliente"],
            "archivo": nombre_pdf
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/factura/pdf")
async def generar_factura_pdf(request: VerFactura):
    buffer = BytesIO()
    crear_factura_pdf(request.dict(), buffer)
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=factura_{request.numeroFactura}.pdf"
    })



@app.post("/contabilidad/analisis")
async def analizar_contabilidad(file: UploadFile = File(...)):
    try:
        print("📥 Leyendo archivo Excel...")
        contenido = await file.read()
        df = pd.read_excel(io.BytesIO(contenido))
        print("✅ Excel leído correctamente")

        columnas_requeridas = {"fecha", "tipo", "categoria", "descripcion", "monto"}
        if not columnas_requeridas.issubset(df.columns):
            print("❌ Columnas faltantes:", df.columns)
            raise HTTPException(status_code=400, detail="Faltan columnas requeridas")

        print("🧮 Convirtiendo montos a numérico...")
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

        print("💰 Calculando ingresos y gastos...")
        ingresos = float(df[df["tipo"] == "ingreso"]["monto"].sum())
        gastos = float(df[df["tipo"] == "gasto"]["monto"].sum())
        beneficio = ingresos - gastos
        print(f"🔢 Ingresos: {ingresos}, Gastos: {gastos}, Beneficio: {beneficio}")

        print("📊 Agrupando por categoría...")
        por_categoria = df[df["tipo"] == "gasto"].groupby("categoria")["monto"].sum().to_dict()
        por_categoria = {str(k): float(v) for k, v in por_categoria.items()}
        print("📂 Gastos por categoría:", por_categoria)

        alertas = []
        if por_categoria.get("comida", 0.0) > 100:
            alertas.append("⚠️ Los gastos en comida superan los 100€")

        resumen = {
            "ingresos": round(ingresos, 2),
            "gastos": round(gastos, 2),
            "beneficio_neto": round(beneficio, 2),
            "por_categoria": por_categoria,
            "alertas": alertas
        }
        print("🧾 Resumen contable generado:", resumen)

        nombre_pdf = f"informe_contable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        print("📄 Generando PDF:", nombre_pdf)
        generar_pdf_contabilidad(resumen, nombre_pdf)
        print("✅ PDF generado correctamente")

        from starlette.responses import JSONResponse
        return JSONResponse(content={
            "resumen": resumen,
            "pdf_generado": nombre_pdf
        })

    except Exception as e:
        print("🔥 ERROR en analizar_contabilidad:", e)
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/contabilidad/ia-analisis")
async def analizar_excel_con_ia(file: UploadFile = File(...)):
    try:
        contenido = await file.read()

        # 📥 Leer Excel o PDF
        if file.filename.endswith(".pdf"):
            texto = extraer_texto_pdf(contenido)  # 👈 asegúrate de tener este método implementado
        elif file.filename.endswith(".xlsx") or file.filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contenido))
            texto = df.to_csv(index=False, sep='|')  # separador claro
        else:
            raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Usa .xlsx o .pdf")

        # 📤 Enviar a la IA
        prompt = f"""
Actúas como un CONTABLE EXPERTO y ASESOR FINANCIERO de confianza. Vas a recibir un listado de movimientos contables de un negocio real, incluyendo ingresos, gastos, fechas, categorías y descripciones. Necesito que hagas una contabilidad real, no un simple resumen.

Concretamente, realiza lo siguiente:

1. Cálculo del balance general del mes (total ingresos, total gastos, beneficio neto).
2. Análisis de flujo de caja si es posible (entrada vs salida por semanas).
3. Identificación de gastos innecesarios o excesivos, con propuesta de optimización.
4. Revisión de pagos pendientes o cobros atrasados si hay fechas futuras o vencidas.
5. Comparativa entre ingresos y gastos por categoría.
6. Sugerencias prácticas contables para mejorar la salud financiera del negocio.
7. Evaluación de rentabilidad del mes, si es positivo o negativo, y por qué.
8. Notifica si hay errores contables, duplicados, o entradas sospechosas.

Datos contables:
{texto}
"""

        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        contenido_ia = respuesta.choices[0].message.content

        # 🧾 Generar PDF con la respuesta de la IA
        nombre_pdf = f"analisis_contable_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        generar_pdf_ia(contenido_ia, nombre_pdf)

        return {
            "estado": "ok",
            "analisis_ia": contenido_ia,
            "pdf_generado": nombre_pdf
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Utilidad para extraer texto de PDFs
def extraer_texto_pdf(bytes_pdf):
    texto = ""
    with fitz.open(stream=bytes_pdf, filetype="pdf") as doc:
        for pagina in doc:
            texto += pagina.get_text()
    return texto
@app.post("/cierre-mensual/ia")
async def cierre_mensual_ia(file: UploadFile = File(...)):
    try:
        contenido = await file.read()

        extension = file.filename.split(".")[-1].lower()
        texto_extraido = ""

        if extension in ["xlsx", "xls"]:
            print("📥 Procesando Excel...")
            df = pd.read_excel(io.BytesIO(contenido))
            if not {"fecha", "tipo", "categoria", "descripcion", "monto"}.issubset(df.columns):
                raise HTTPException(status_code=400, detail="Columnas requeridas: fecha, tipo, categoria, descripcion, monto")
            texto_extraido = df.to_csv(index=False)

        elif extension == "pdf":
            print("📥 Procesando PDF...")
            with fitz.open(stream=contenido, filetype="pdf") as doc:
                texto_extraido = "\n".join([page.get_text() for page in doc])
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado. Solo .xlsx o .pdf")

        # 🔍 Prompt a la IA
        prompt = f"""
Eres un asesor contable experto. Analiza los datos de este archivo del mes completo y genera un informe profesional de cierre mensual con:
- Tendencias de ingresos y gastos
- Anomalías encontradas
- Recomendaciones para el siguiente mes
- Resumen ejecutivo

Datos:
{texto_extraido}
"""

        print("🧠 Enviando a OpenAI...")
        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        contenido_ia = respuesta.choices[0].message.content.strip()
        print("✅ Análisis recibido")

        # 📄 Crear PDF con el análisis
        nombre_pdf = f"cierre_mensual_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        generar_pdf_cierre_ia(contenido_ia, nombre_pdf)

        return {
            "estado": "ok",
            "analisis_ia": contenido_ia,
            "pdf_generado": nombre_pdf
        }

    except Exception as e:
        print("🔥 ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/facturas/ia-seguimiento")
async def seguimiento_facturas(file: UploadFile = File(...)):
    try:
        contenido = await file.read()

        # Leer Excel o extraer texto de PDF
        if file.filename.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(contenido))
            texto = "\n".join([page.extract_text() for page in reader.pages])
            texto_entrada = f"Contenido de PDF de facturas:\n{texto}"
        else:
            df = pd.read_excel(io.BytesIO(contenido))
            texto_entrada = df.to_csv(index=False)

        # Construimos el prompt
        prompt = f"""
Eres una IA experta en contabilidad y gestión de facturas.
A continuación tienes un listado de facturas (emitidas o recibidas).
Analiza y genera un informe claro con:

1. Facturas pendientes de cobro o pago.
2. Facturas con errores o inconsistencias (duplicadas, totales incorrectos).
3. Facturas con vencimiento esta semana.
4. Proveedores que estén cobrando más de lo habitual.
5. Recomendaciones.

Datos:
{texto_entrada}
"""

        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        analisis = respuesta.choices[0].message.content

        # Generamos PDF con el análisis
        nombre_pdf = f"informe_facturas_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        generar_pdf_texto_ia(analisis, nombre_pdf)

        return {
            "estado": "ok",
            "analisis_ia": analisis,
            "pdf_generado": nombre_pdf
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/campania/promocion")
async def enviar_promocion(
    mensaje: str = Form(...),
    archivo: UploadFile = File(...),
    nombre: str = Form("Miguel Ángel"),
    empresa: str = Form("Bizyvel")
):
    try:
        contenido = await archivo.read()

        # Leer correos válidamente
        if archivo.filename.endswith(".xlsx") or archivo.filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contenido))

            # Validar columna
            columnas_validas = [col.lower() for col in df.columns]
            if not any(c in columnas_validas for c in ["email", "correo", "correos"]):
                raise HTTPException(status_code=400, detail="El Excel debe tener una columna llamada 'email' o 'correo'")

            # Extraer correos limpiando espacios
            nombre_col = next(col for col in df.columns if col.lower() in ["email", "correo", "correos"])
            correos = df[nombre_col].dropna().astype(str).str.strip().tolist()

        else:
            raise HTTPException(status_code=400, detail="Solo se permite Excel (.xlsx o .xls)")

        # ✅ GENERAR CONTENIDO DEL CORREO CON IA
        prompt = f"""
        Eres un experto en redacción de correos promocionales. Crea un mensaje persuasivo y profesional para los clientes con esta instrucción:

        {mensaje}

        El mensaje debe ser corto, amigable y directo.
        """
        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        texto_email = respuesta.choices[0].message.content

        # 🧠 Reemplazar los placeholders por nombre y empresa reales
        texto_email = texto_email.replace("[Tu nombre]", nombre).replace("[Tu empresa]", empresa)

        # ✅ Enviar correos
        enviados = 0
        for email in correos:
            try:
                enviar_promocion_email(email, texto_email)
                enviados += 1
            except Exception as err:
                print(f"❌ Error al enviar a {email}: {err}")

        return {
            "estado": "ok",
            "emails_enviados": enviados,
            "mensaje_generado": texto_email
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PreguntaFiscal(BaseModel):
    pregunta: str
@app.post("/fiscal/consulta")
async def consulta_fiscal(pregunta: PreguntaFiscal):
    try:
        prompt = f"Eres un asesor fiscal profesional. Responde de forma clara y profesional la siguiente consulta:\n\n{pregunta.pregunta}"

        respuesta = client.chat.completions.create(
            model="gpt-4",  # si no tienes GPT-4 pon "gpt-3.5-turbo"
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        return {
            "accion": "consulta_fiscal",
            "tipo": "respuesta_ia",
            "datos": {
                "productos": []
            },
            "response": respuesta.choices[0].message.content.strip()
        }


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/asistente/accion/{idNegocio}")
async def asistente_ia_accion(
    idNegocio: str = Path(...),
    mensaje: Optional[str] = Form(None),
    archivo: Optional[UploadFile] = File(None),
    nombre: str = Form("Miguel Ángel"),
    empresa: str = Form("Bizyvel"),
    authorization: Optional[str] = Header(None)  # 👈 Aquí recogemos el token que llega

):
    try:
        texto_archivo = ""
        df = None
        contenido = None

        if archivo:
            contenido = await archivo.read()
            if archivo.filename.endswith(".pdf"):
                with fitz.open(stream=contenido, filetype="pdf") as doc:
                    texto_archivo = "\n".join([page.get_text() for page in doc])
            elif archivo.filename.endswith(".xlsx") or archivo.filename.endswith(".xls"):
                df = pd.read_excel(io.BytesIO(contenido))
                texto_archivo = df.to_csv(index=False)

        prompt = f"""
        Actúas como un asistente inteligente para un software de gestión de negocios.

        Tu tarea es analizar el mensaje del usuario y decidir **qué acción ejecutar** entre las siguientes:

        - crear_factura → cuando el usuario pida generar una factura o presupuesto.
        - analisis_ia → cuando suba un archivo con ingresos/gastos y pida un análisis contable o resumen financiero.
        - cierre_mensual → cuando suba un archivo del mes y quiera un cierre contable mensual.
        - seguimiento_facturas → cuando quiera saber el estado de sus facturas (pendientes, vencidas, duplicadas...).
        - enviar_promocion → cuando quiera enviar una campaña o promoción a varios clientes.
        - consulta_fiscal → cuando haga una pregunta fiscal o tributaria (IVA, IRPF, deducciones...).
        - spring → cuando el mensaje esté relacionado con productos, ventas, stock, o cualquier funcionalidad avanzada que tú no puedas procesar.

        ❗ Si el mensaje **no encaja claramente** en ninguna de las anteriores, responde con `spring`.

        👉 Devuelve **solo**:
        1. La acción (una palabra, exactamente como está en la lista).
        2. Una línea breve explicando por qué la elegiste.

        Texto del usuario:
        {mensaje if mensaje else ""}

        Contenido del archivo:
        {texto_archivo[:1000]}
        """

        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        decision = respuesta.choices[0].message.content.strip()
        accion = decision.split("\n")[0].replace("Acción:", "").strip()
        if accion == "spring":
            headers = {
                "Authorization": authorization,  # 👈 Token del frontend
                "accept": "application/json"
            }

            # Construimos el body con el mensaje (como lo espera Spring Boot)
            payload = {
                "pregunta": mensaje
            }

            # 👇 METEMOS el ID directamente en la URL
            spring_url = f"https://celeraai-backend.onrender.com/usuario/generarRecomendaciones/{idNegocio}"

            response = requests.post(spring_url, json=payload, headers=headers)
            return response.json()


        elif accion == "crear_factura":
            datos = analizar_mensaje_factura(mensaje)
            datos["NombreEmpresa"] = empresa
            datos["cid"] = "C-987654"
            datos["numeroAlbaran"] = 1203
            datos["numeroFactura"] = f"F-{datetime.now().strftime('%Y%m%d')}-001"
            subtotal = sum(p.get("cantidad", 0) * p.get("precio", 0) for p in datos.get("productos", []))
            datos["subtotal"] = subtotal
            datos["impuestos"] = round(subtotal * 0.21, 2)
            datos["total"] = round(subtotal + datos["impuestos"], 2)
            nombre_pdf = f"factura_{datos['numeroFactura']}.pdf"
            crear_factura_pdf(datos, nombre_pdf)
            enviar_factura_email(datos["email"], nombre_pdf)
            return {"accion": "crear_factura", "cliente": datos["cliente"], "archivo": nombre_pdf}



        elif accion == "analisis_ia":
            texto = df.to_csv(index=False, sep='|') if df is not None else texto_archivo
            prompt_ia = f"""
            Eres un contable experto. Haz un análisis real de estos movimientos contables (ingresos, gastos, fechas, categorías...):

            {texto}
            """
            respuesta_ia = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt_ia}],
                temperature=0.4
            )
            analisis = respuesta_ia.choices[0].message.content.strip()
            nombre_pdf = f"analisis_contable_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            generar_pdf_ia(analisis, nombre_pdf)
            return {"accion": "analisis_ia", "analisis": analisis, "pdf": nombre_pdf}

        elif accion == "cierre_mensual":
            texto = df.to_csv(index=False) if df is not None else texto_archivo
            prompt_cierre = f"""
            Eres un asesor contable. Analiza este mes completo y genera un informe con tendencias, anomalías y recomendaciones:

            {texto}
            """
            respuesta_ia = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt_cierre}],
                temperature=0.4
            )
            cierre = respuesta_ia.choices[0].message.content.strip()
            nombre_pdf = f"cierre_mensual_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            generar_pdf_cierre_ia(cierre, nombre_pdf)
            return {"accion": "cierre_mensual", "informe": cierre, "pdf": nombre_pdf}

        elif accion == "seguimiento_facturas":
            texto = df.to_csv(index=False) if df is not None else texto_archivo
            prompt_seg = f"""
            Eres una IA contable. Analiza el estado de estas facturas: cobros pendientes, duplicadas, vencidas...

            {texto}
            """
            respuesta_ia = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt_seg}],
                temperature=0.4
            )
            seguimiento = respuesta_ia.choices[0].message.content.strip()
            nombre_pdf = f"seguimiento_facturas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            generar_pdf_texto_ia(seguimiento, nombre_pdf)
            return {"accion": "seguimiento_facturas", "seguimiento": seguimiento, "pdf": nombre_pdf}

        elif accion == "enviar_promocion":
            if df is None:
                raise HTTPException(status_code=400, detail="Debe adjuntar un Excel válido con columna 'email'")
            col_correo = next(col for col in df.columns if col.lower() in ["email", "correo", "correos"])
            correos = df[col_correo].dropna().astype(str).str.strip().tolist()
            prompt_correo = f"""
            Redacta un correo promocional profesional y breve para esta empresa: {empresa}.
            Mensaje del usuario: {mensaje}
            """
            respuesta_ia = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt_correo}],
                temperature=0.5
            )
            texto_email = respuesta_ia.choices[0].message.content.replace("[Tu nombre]", nombre).replace("[Tu empresa]", empresa)
            enviados = 0
            for email in correos:
                try:
                    enviar_promocion_email(email, texto_email)
                    enviados += 1
                except Exception as err:
                    print(f"❌ Error al enviar a {email}: {err}")
            return {
                "accion": "consulta_fiscal",
                "tipo": "respuesta_ia",
                "datos": {
                    "productos": []
                },
                "response": respuesta.choices[0].message.content.strip()
            }

        elif accion == "consulta_fiscal":
            prompt_fiscal = f"Eres un asesor fiscal profesional. Responde esta consulta de forma clara:\n\n{mensaje}"
            respuesta = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_fiscal}],
                temperature=0.3
            )
            return {
                "accion": "consulta_fiscal",
                "tipo": "respuesta_ia",
                "datos": {
                    "productos": []
                },
                "response": respuesta.choices[0].message.content.strip()
            }

        return {
            "estado": "ok",
            "accion_detectada": accion,
            "motivo": decision,
            "nota": "Acción ejecutada o analizada."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
