from io import BytesIO

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def booking_qr_png(booking):
    content = (
        f'AU-PCRS\n'
        f'ID: {booking["booking_id"]}\n'
        f'Room: {booking["room"]}\n'
        f'Date: {booking["booking_date"]}\n'
        f'Time: {booking["start_time"]}-{booking["end_time"]}\n'
        f'Name: {booking["applicant_name"]}\n'
        f'Status: {booking["status"]}'
    )
    image = qrcode.make(content)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _pdf_safe(value):
    """Keep PDF generation stable when the default font cannot render CJK."""
    text = str(value)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def booking_pdf(booking):
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    _, height = A4
    pdf.setTitle(f'AU-PCRS {booking["booking_id"]}')
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 60, "AU-PCRS Reservation Confirmation")
    pdf.setFont("Helvetica", 11)
    lines = [
        f'Booking ID: {booking["booking_id"]}',
        f'Applicant: {_pdf_safe(booking["applicant_name"])}',
        f'Identification Code: {booking["identification_code"]}',
        f'Room: {booking["room"]}',
        f'Date: {booking["booking_date"]}',
        f'Time: {booking["start_time"]} - {booking["end_time"]}',
        f'Purpose: {_pdf_safe(booking["reason"])}',
        f'Status: {_pdf_safe(booking["status"])}',
    ]
    y = height - 100
    for line in lines:
        pdf.drawString(50, y, line[:110])
        y -= 24
    pdf.showPage()
    pdf.save()
    return output.getvalue()
