from datetime import date

def obtener_venta_por_id(venta_id: str) -> dict:
    if venta_id != "1234":
        raise ValueError("Venta no encontrada")

    return {
        "cliente": "Juan Pérez",
        "email": "mg.aangel10@gmail.com",
        "metodo_pago": "Efectivo",
        "fecha": str(date.today()),
        "total": 52.00,
        "productos": [
            {"nombre": "Cerveza", "cantidad": 3, "precio": 5.0},
            {"nombre": "Hamburguesa", "cantidad": 2, "precio": 10.0},
            {"nombre": "Papas fritas", "cantidad": 1, "precio": 7.0}
        ]
    }
