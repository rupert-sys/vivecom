"""
Recibo simple de pago (F1-11, HU-A08): un PDF NO fiscal, solo para que el
residente tenga respaldo documental. Se genera al vuelo a partir de los
datos ya guardados (no hay nada que timbrar ni persistir), así que no
requiere almacenamiento ni un job en background — basta con pedirlo cuando
se necesita.
"""

from fpdf import FPDF

from app.models.payment import Payment
from app.models.property import Property
from app.models.tenant import Tenant


def build_receipt_pdf(payment: Payment, propiedad: Property, tenant: Tenant) -> bytes:
    pdf = FPDF(format="Letter")
    pdf.add_page()

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Recibo de pago", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Este documento NO es un comprobante fiscal.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, tenant.nombre, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    filas = [
        ("Folio", str(payment.id)),
        ("Vivienda", propiedad.identificador),
        ("Monto", f"${float(payment.monto):,.2f} MXN"),
        ("Fecha del depósito", payment.fecha_deteccion.strftime("%d/%m/%Y %H:%M")),
        ("Clave de rastreo", payment.clave_rastreo),
        ("Estado", payment.estado.value.capitalize()),
    ]
    pdf.set_font("helvetica", "", 11)
    for etiqueta, valor in filas:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(50, 8, etiqueta)
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 8, valor, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
