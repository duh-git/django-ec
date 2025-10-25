# utils.py
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from django.conf import settings
from django.http import HttpResponse
from datetime import datetime
from django.shortcuts import get_object_or_404
from .models import Order
from django.core.exceptions import ValidationError


MAIN_FONT = "Arial"
MAIN_FONT_ROOT = settings.BASE_DIR / "api/fonts/arialmt.ttf"
MAIN_FONT_STYLE_1 = "Arial-BI"
MAIN_FONT_STYLE_1_ROOT = settings.BASE_DIR / "api/fonts/arial_bolditalicmt.ttf"


try:
    """Регистрация шрифта, в reportlab нет шрифтов поддерживающих кирилицу"""
    pdfmetrics.registerFont(TTFont(MAIN_FONT, MAIN_FONT_ROOT))
    pdfmetrics.registerFont(TTFont(MAIN_FONT_STYLE_1, MAIN_FONT_STYLE_1_ROOT))
except:
    ValidationError("Не удалось загрузить шрифт, проверьте api.utils.py и api.fonts")


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
    styles["Heading1"].fontName = "Arial"
    styles["Heading2"].fontName = "Arial"
    styles["Heading4"].fontName = "Arial"
    title_style = ParagraphStyle("CustomTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=30, alignment=1)

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
                ("FONT", (0, 0), (-1, -1), MAIN_FONT, 10),
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
        items_data.append(
            [
                Paragraph(item.product.name, styles["Heading4"]),
                Paragraph(f"{item.price:.2f} Р", styles["Heading4"]),
                Paragraph(str(item.quantity), styles["Heading4"]),
                Paragraph(f"{item.total_price:.2f} Р", styles["Heading4"]),
            ]
        )

    # Итоговая сумма
    items_data.append(["", "", "ИТОГО:", f"{order.total_amount:.2f} Р"])

    items_table = Table(items_data, colWidths=[80 * mm, 30 * mm, 25 * mm, 30 * mm])
    items_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), MAIN_FONT_STYLE_1, 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                ("FONT", (0, -1), (-1, -1), MAIN_FONT_STYLE_1, 10),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
            ]
        )
    )

    elements.append(items_table)

    # Генерация PDF
    doc.build(elements)
    return response
