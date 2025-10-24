from django.shortcuts import get_object_or_404
from .models import Order
from .utils import generate_order_pdf


def generate_order_pdf_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return generate_order_pdf(order)
