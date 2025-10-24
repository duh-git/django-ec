# utils.py
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from django.http import HttpResponse
from datetime import datetime
from django.shortcuts import get_object_or_404
from .models import Order


def generate_order_pdf(request, order_id):
    """Генерация PDF для заказа"""
    order = get_object_or_404(Order, id=order_id)
    response = HttpResponse(content_type="application/pdf")
    filename = f"{order.order_number}_{datetime.now().strftime('%Y%m%d')}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=30, alignment=1  # center
    )

    # Заголовок
    elements.append(Paragraph(f"ЗАКАЗ № {order.order_number}", title_style))
    elements.append(Spacer(1, 10))

    # Информация о заказе
    order_info = [
        ["Дата заказа:", order.created_at.strftime("%d.%m.%Y %H:%M")],
        ["Статус:", order.get_status_display()],
        ["Покупатель:", f"{order.user.get_full_name()} ({order.user.email})"],
        ["Телефон:", order.phone_number],
        ["Адрес доставки:", order.shipping_address],
    ]

    if order.customer_notes:
        order_info.append(["Комментарий:", order.customer_notes])

    order_table = Table(order_info, colWidths=[60 * mm, 120 * mm])
    order_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    elements.append(order_table)
    elements.append(Spacer(1, 20))

    # Товары в заказе
    elements.append(Paragraph("Состав заказа:", styles["Heading2"]))

    items_data = [["Товар", "Цена", "Кол-во", "Сумма"]]
    for item in order.items.all():
        items_data.append([item.product.name, f"{item.price:.2f} ₽", str(item.quantity), f"{item.total_price:.2f} ₽"])

    # Итоговая сумма
    items_data.append(["", "", "ИТОГО:", f"{order.total_amount:.2f} ₽"])

    items_table = Table(items_data, colWidths=[80 * mm, 30 * mm, 25 * mm, 30 * mm])
    items_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 10),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
            ]
        )
    )

    elements.append(items_table)

    # Генерация PDF
    doc.build(elements)
    return response
