from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.http import urlencode
from .utils import generate_order_pdf
from .cache_utils import clear_product_cache

from .models import (
    Product,
    ProductImage,
    ProductFile,
    Category,
    Brand,
    Tag,
    ProductTagRelationship,
    Profile,
    Review,
    Wishlist,
    WishlistItem,
    Cart,
    CartItem,
    Order,
    OrderItem,
)


# Inline модели
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ["image_preview"]

    @admin.display(description="Превью")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "-"


class ProductFileInline(admin.TabularInline):
    model = ProductFile
    extra = 1
    readonly_fields = ["downloads_count"]


class ProductTagRelationshipInline(admin.TabularInline):
    model = ProductTagRelationship
    extra = 1
    raw_id_fields = ["tag", "added_by"]
    readonly_fields = ["added_at"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "added_by":
            kwargs["initial"] = request.user.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Профиль"


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ["created_at"]
    can_delete = False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["price", "total_price"]
    can_delete = False

    @admin.display(description="Общая стоимость")
    def total_price(self, obj):
        return f"{obj.total_price} ₽"


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["total_price"]

    @admin.display(description="Общая стоимость")
    def total_price(self, obj):
        return f"{obj.total_price} ₽"


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    readonly_fields = ["added_at"]


# Фильтры для админки
class RatingFilter(admin.SimpleListFilter):
    title = "Рейтинг"
    parameter_name = "rating"

    def lookups(self, request, model_admin):
        return (
            ("5", "⭐️⭐️⭐️⭐️⭐️ (5)"),
            ("4", "⭐️⭐️⭐️⭐️ (4+)"),
            ("3", "⭐️⭐️⭐️ (3+)"),
            ("2", "⭐️⭐️ (2+)"),
            ("1", "⭐️ (1)"),
        )

    def queryset(self, request, queryset):
        if self.value() == "5":
            return queryset.filter(rating=5)
        elif self.value() == "4":
            return queryset.filter(rating__gte=4)
        elif self.value() == "3":
            return queryset.filter(rating__gte=3)
        elif self.value() == "2":
            return queryset.filter(rating__gte=2)
        elif self.value() == "1":
            return queryset.filter(rating=1)
        return queryset


class StockFilter(admin.SimpleListFilter):
    title = "Наличие"
    parameter_name = "stock_status"

    def lookups(self, request, model_admin):
        return (
            ("in_stock", "В наличии"),
            ("low_stock", "Мало на складе"),
            ("out_of_stock", "Нет в наличии"),
        )

    def queryset(self, request, queryset):
        if self.value() == "in_stock":
            return queryset.filter(stock__gte=10)
        elif self.value() == "low_stock":
            return queryset.filter(stock__range=[1, 9])
        elif self.value() == "out_of_stock":
            return queryset.filter(stock=0)
        return queryset


# ModelAdmin классы
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "category",
        "brand",
        "price",
        "stock",
        "average_rating_display",
        "review_count",
        "is_available",
        "is_featured",
        "warranty_months",
        "created_at",
    ]
    list_display_links = ["name"]
    list_filter = ["is_available", "is_featured", "category", "brand", "tags", "created_at", StockFilter]
    search_fields = ["name", "description", "tags__name"]
    list_editable = ["price", "stock", "is_available", "is_featured"]
    readonly_fields = ["created_at", "updated_at", "average_rating", "review_count"]
    prepopulated_fields = {"name": ()}
    inlines = [ProductImageInline, ProductTagRelationshipInline, ReviewInline, ProductFileInline]
    fieldsets = (
        ("Основная информация", {"fields": ("name", "slug", "description", "category", "brand")}),
        ("Цена и наличие", {"fields": ("price", "stock", "warranty_months")}),
        ("Статусы", {"fields": ("is_available", "is_featured")}),
        ("Отзывы", {"fields": ("average_rating", "review_count")}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    # filter_horizontal = ["tags"]
    date_hierarchy = "created_at"

    @admin.display(description="Рейтинг")
    def average_rating_display(self, obj):
        avg = obj.average_rating
        stars = "⭐️" * int(avg) + "☆" * (5 - int(avg))
        return format_html(f"{stars} ({avg:.1f})")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(avg_rating=Avg("reviews__rating"))

    def save_model(self, request, obj, form, change):
        """Очищаем кеш при сохранении товара в админке"""
        super().save_model(request, obj, form, change)
        clear_product_cache()

    def delete_model(self, request, obj):
        """Очищаем кеш при удалении товара в админке"""
        super().delete_model(request, obj)
        clear_product_cache()


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "image_preview", "is_primary", "order"]
    list_editable = ["is_primary", "order"]
    list_filter = ["is_primary", "product__category"]
    search_fields = ["product__name"]

    @admin.display(description="Изображение")
    def image_preview(self, obj):
        if obj.image:
            return format_html(f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />')
        return "-"


@admin.register(ProductFile)
class ProductFileAdmin(admin.ModelAdmin):
    list_display = ["product", "name", "file_type", "downloads_count", "size", "updated_at"]
    list_editable = ["name", "file_type"]
    list_filter = ["product__category", "file_type"]
    search_fields = ["product__name", "product"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "products_count"]
    list_filter = ["parent"]
    search_fields = ["name"]
    prepopulated_fields = {"name": ()}

    @admin.display(description="Количество товаров")
    def products_count(self, obj):
        count = obj.products.count()
        url = reverse("admin:api_product_changelist") + "?" + urlencode({"category__id": f"{obj.id}"})
        return format_html(f'<a href="{url}">{count} товаров</a>')


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "official_website", "products_count"]
    search_fields = ["name", "description"]

    @admin.display(description="Количество товаров")
    def products_count(self, obj):
        count = obj.products.count()
        url = reverse("admin:api_product_changelist") + "?" + urlencode({"brand__id": f"{obj.id}"})
        return format_html(f'<a href="{url}">{count} товаров</a>')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "color_display", "products_count", "description_preview"]
    list_editable = ["color"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"name": ()}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(relationships_count=Count("producttagrelationship"))

    @admin.display(description="Количество связей")
    def products_count(self, obj):
        count = obj.producttagrelationship_set.count()
        url = reverse("admin:api_producttagrelationship_changelist") + "?" + urlencode({"tag__id": f"{obj.id}"})
        return format_html(f'<a href="{url}">{count} связей</a>')

    @admin.display(description="Цвет")
    def color_display(self, obj):
        return format_html(
            f'<div style="background-color: {obj.color}; width: 20px; height: 20px; border-radius: 3px; border: 1px solid #ccc;"></div>'
        )

    @admin.display(description="Количество товаров")
    def products_count(self, obj):
        count = obj.products.count()
        url = reverse("admin:api_product_changelist") + "?" + urlencode({"tags__id": f"{obj.id}"})
        return format_html(f'<a href="{url}">{count} товаров</a>')

    @admin.display(description="Описание")
    def description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
        return "-"


@admin.register(ProductTagRelationship)
class ProductTagRelationshipAdmin(admin.ModelAdmin):
    list_display = ["product", "tag", "weight", "added_by", "added_at", "is_auto_generated", "color_display"]
    list_filter = ["weight", "is_auto_generated", "added_at", "tag"]
    search_fields = ["product__name", "tag__name", "added_by__username"]
    raw_id_fields = ["product", "tag", "added_by"]
    list_editable = ["weight", "is_auto_generated"]
    readonly_fields = ["added_at"]
    date_hierarchy = "added_at"

    @admin.display(description="Цвет тега")
    def color_display(self, obj):
        return format_html(
            f'<div style="background-color: {obj.tag.color}; width: 20px; height: 20px; border-radius: 3px; border: 1px solid #ccc;"></div>'
        )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone_number", "profile_picture_preview"]
    search_fields = ["user__username", "user__email", "phone_number"]

    @admin.display(description="Аватар")
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                f'<img src="{obj.profile_picture.url}" width="50" height="50" style="object-fit: cover; border-radius: 50%;" />'
            )
        return "-"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "user",
        "rating_stars",
        "comment_preview",
        "admin_response",
        "created_at",
        "has_admin_response",
    ]
    raw_id_fields = ["user", "product"]
    list_filter = [RatingFilter, "created_at", "product__tags", "product__category"]
    search_fields = ["product__name", "user__email", "comment"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["admin_response"]
    date_hierarchy = "created_at"

    @admin.display(description="Рейтинг")
    def rating_stars(self, obj):
        return "⭐️" * obj.rating

    @admin.display(description="Комментарий")
    def comment_preview(self, obj):
        if obj.comment:
            return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return "-"

    @admin.display(description="Ответ", boolean=True)
    def has_admin_response(self, obj):
        return bool(obj.admin_response)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ["user", "items_count", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [WishlistItemInline]
    search_fields = ["user__username", "user__email"]

    @admin.display(description="Количество товаров")
    def items_count(self, obj):
        return obj.wishlistitem_set.count()


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["wishlist", "product", "added_at"]
    list_filter = ["added_at", "product__tags", "product__category"]
    raw_id_fields = ["wishlist", "product"]
    search_fields = ["wishlist__user__username", "product__name"]
    readonly_fields = ["added_at"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "items_count", "total_price_display", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at", "total_price_display"]
    inlines = [CartItemInline]
    search_fields = ["user__username", "user__email"]

    @admin.display(description="Товаров в корзине")
    def items_count(self, obj):
        return obj.items.count()

    @admin.display(description="Общая стоимость")
    def total_price_display(self, obj):
        return f"{obj.total_price} ₽"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["cart", "product", "quantity", "total_price_display"]
    list_editable = ["quantity"]
    raw_id_fields = ["cart", "product"]
    search_fields = ["cart__user__username", "product__name", "product__tags__name"]

    @admin.display(description="Общая стоимость")
    def total_price_display(self, obj):
        return f"{obj.total_price} ₽"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    actions = ["mark_as_processing", "mark_as_shipped", "mark_as_delivered", "generate_pdf"]
    list_display = ["order_number", "user", "status", "total_amount_display", "items_count", "created_at"]
    list_filter = ["status", "created_at"]
    list_editable = ["status"]
    list_display_links = ["order_number"]
    raw_id_fields = ["user"]
    search_fields = ["order_number", "user__email", "user__username"]
    readonly_fields = ["order_number", "created_at", "updated_at", "total_amount_display", "user_info"]
    inlines = [OrderItemInline]
    fieldsets = (
        ("Основная информация", {"fields": ("order_number", "user_info", "status", "total_amount_display")}),
        ("Детали доставки", {"fields": ("shipping_address", "phone_number", "customer_notes")}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    date_hierarchy = "created_at"

    @admin.display(description="Общая сумма")
    def total_amount_display(self, obj):
        return f"{obj.total_amount} ₽"

    @admin.display(description="Количество товаров")
    def items_count(self, obj):
        return obj.items.count()

    @admin.display(description="Пользователь")
    def user_info(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html(f'<a href="{url}">{obj.user.username}</a> - {obj.user.email}')

    @admin.action(description="Перевести в статус 'В обработке'")
    def mark_as_processing(self, request, queryset):
        queryset.update(status="processing")

    @admin.action(description="Перевести в статус 'Отправлен'")
    def mark_as_shipped(self, request, queryset):
        queryset.update(status="shipped")

    @admin.action(description="Перевести в статус 'Доставлен'")
    def mark_as_delivered(self, request, queryset):
        queryset.update(status="delivered")

    # PDF Task
    change_form_template = "admin/order_change_form.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_pdf_button"] = True
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    @admin.action(description="Сгенерировать PDF для выбранных заказов")
    def generate_pdf(self, request, queryset):
        """Генерация PDF для выбранных заказов"""
        if queryset.count() != 1:
            self.message_user(request, "Выберите ОДИН заказ для генерации PDF", level="ERROR")
            return

        # TO-DO
        # for order in queryset:
        #     return generate_order_pdf(request, order.id)

        order = queryset.first()
        return generate_order_pdf(request, order.id)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product", "quantity", "price", "total_price_display"]
    list_filter = ["order__status", "product__category"]
    raw_id_fields = ["order", "product"]
    search_fields = ["order__order_number", "product__name"]
    readonly_fields = ["price", "total_price_display"]

    def total_price_display(self, obj):
        return f"{obj.total_price} ₽"

    total_price_display.short_description = "Общая стоимость"


# Модификация базового представления
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ["username", "email", "first_name", "last_name", "is_staff", "profile_info"]

    def profile_info(self, obj):
        try:
            profile = obj.profile
            return f"📞 {profile.phone_number}" if profile.phone_number else "📞 Не указан"
        except Profile.DoesNotExist:
            return "❌ Профиль не создан"

    profile_info.short_description = "Контактная информация"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


admin.site.site_header = "Панель управления интернет-магазином"
admin.site.site_title = "Админ-панель магазина"
admin.site.index_title = "Управление магазином"
