"""
Constancia de no adeudo (reglamento Art. 16): la Tesorería la emite al
vendedor de una vivienda para que el comprador sepa que está al corriente. Un
PDF NO fiscal generado al vuelo, igual que el recibo de pago (receipt_service).
"""

from datetime import date

from fpdf import FPDF

from app.models.property import Property
from app.models.tenant import Tenant


def build_no_debt_certificate_pdf(propiedad: Property, tenant: Tenant, fecha: date) -> bytes:
    pdf = FPDF(format="Letter")
    pdf.add_page()

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Constancia de no adeudo", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, tenant.nombre, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(
        0, 7,
        f"La Tesorería del Comité de Administración hace constar que la vivienda {propiedad.identificador} "
        f"se encuentra al corriente en el pago de sus cuotas de mantenimiento y demás obligaciones "
        f"condominales, al {fecha.strftime('%d/%m/%Y')}.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(6)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        0, 5,
        "Este documento NO es un comprobante fiscal. Solo es válido a la fecha de emisión; cargos generados "
        "después no están amparados por esta constancia.",
        new_x="LMARGIN", new_y="NEXT",
    )
    return bytes(pdf.output())
