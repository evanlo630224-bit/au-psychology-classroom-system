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


def booking_pdf(booking):
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 60, "AU-PCRS Reservation Confirmation")
    pdf.setFont("Helvetica", 11)
    lines = [
        f'Booking ID: {booking["booking_id"]}',
        f'Applicant: {booking["applicant_name"]}',
        f'Identification Code: {booking["identification_code"]}',
        f'Room: {booking["room"]}',
        f'Date: {booking["booking_date"]}',
        f'Time: {booking["start_time"]} - {booking["end_time"]}',
        f'Purpose: {booking["reason"]}',
        f'Status: {booking["status"]}',
    ]
    y = height - 100
    for line in lines:
        pdf.drawString(50, y, line)
        y -= 24
    pdf.showPage()
    pdf.save()
    return output.getvalue()
