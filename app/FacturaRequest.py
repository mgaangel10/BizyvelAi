from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DetalleVenta(BaseModel):
    id: str
    nombreProducto: str
    precioProducto: float
    cantida: int  # ⚠️ si en Angular es "cantida", debe coincidir o cambiar uno de los dos

class VentaDto(BaseModel):
    id: str
    detalleVentas: List[DetalleVenta]
    fecha: datetime
    total: float
    metodoPago: Optional[str] = None
    activo: bool
    terminado:bool
    factura: bool

class VerFactura(BaseModel):
    id: str
    numeroFactura: str
    cliente: str
    impuestos: float
    total: float
    subtotal: float
    nombreEmpresa: str
    cid: Optional[str] = None
    numeroAlbaran: int
    ventaDto: VentaDto
