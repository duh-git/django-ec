from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api.views import generate_order_pdf


urlpatterns = [
    path("admin/orders/order/<int:order_id>/pdf/", generate_order_pdf, name="generate_order_pdf"),
    path("api/", include("api.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
