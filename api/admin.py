from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.http import urlencode

from .models import (
    Category,
    Brand,
    Product,
    ProductImage,
    Review,
    Profile,
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

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "-"

    image_preview.short_description = "Превью"


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ["user", "rating", "created_at"]
    can_delete = False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["price", "total_price"]
    can_delete = False

    def total_price(self, obj):
        return f"{obj.total_price} ₽"

    total_price.short_description = "Общая стоимость"


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["total_price"]

    def total_price(self, obj):
        return f"{obj.total_price} ₽"

    total_price.short_description = "Общая стоимость"


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
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "products_count"]
    list_filter = ["parent"]
    search_fields = ["name"]
    prepopulated_fields = {"name": ()}

    @admin.display(description="Количество товаров")
    def products_count(self, obj):
        count = obj.products.count()
        # url = reverse("admin:app_product_changelist") + "?" + urlencode({"category__id": f"{obj.id}"})
        return format_html(f'<a href="">{count} товаров</a>')  # TO-DO: reverse


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "products_count"]
    search_fields = ["name", "description"]

    def products_count(self, obj):
        count = obj.products.count()
        # url = reverse("admin:app_product_changelist") + "?" + urlencode({"brand__id": f"{obj.id}"})
        return format_html(f'<a href="">{count} товаров</a>')  # TO-DO: reverse

    products_count.short_description = "Количество товаров"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
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
    list_filter = ["is_available", "is_featured", "category", "brand", "created_at", StockFilter]
    search_fields = ["name", "description"]
    list_editable = ["price", "stock", "is_available", "is_featured"]
    readonly_fields = ["created_at", "updated_at", "average_rating", "review_count"]
    prepopulated_fields = {"name": ()}
    inlines = [ProductImageInline, ReviewInline]
    fieldsets = (
        ("Основная информация", {"fields": ("name", "description", "category", "brand")}),
        ("Цена и наличие", {"fields": ("price", "stock", "warranty_months")}),
        ("Статусы", {"fields": ("is_available", "is_featured")}),
        ("Отзывы", {"fields": ("average_rating", "review_count")}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    date_hierarchy = "created_at"

    @admin.display(description="Рейтинг")
    def average_rating_display(self, obj):
        avg = obj.average_rating
        stars = "⭐️" * int(avg) + "☆" * (5 - int(avg))
        return format_html(f"{stars} ({avg:.1f})")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(avg_rating=Avg("reviews__rating"))


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "image_preview", "is_primary", "order"]
    list_editable = ["is_primary", "order"]
    list_filter = ["is_primary", "product__category"]
    search_fields = ["product__name"]

    def image_preview(self, obj):
        if obj.image:
            return format_html(f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />')
        return "-"

    image_preview.short_description = "Изображение"


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
    list_filter = [RatingFilter, "created_at", "product__category"]
    search_fields = ["product__name", "user__email", "comment"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["admin_response"]
    date_hierarchy = "created_at"

    def rating_stars(self, obj):
        return "⭐️" * obj.rating

    rating_stars.short_description = "Рейтинг"

    def comment_preview(self, obj):
        if obj.comment:
            return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return "-"

    comment_preview.short_description = "Комментарий"

    def has_admin_response(self, obj):
        return bool(obj.admin_response)

    has_admin_response.boolean = True
    has_admin_response.short_description = "Ответ"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone_number", "profile_picture_preview"]
    search_fields = ["user__username", "user__email", "phone_number"]

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                f'<img src="{obj.profile_picture.url}" width="50" height="50" style="object-fit: cover; border-radius: 50%;" />'
            )
        return "-"

    profile_picture_preview.short_description = "Аватар"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ["user", "items_count", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [WishlistItemInline]
    search_fields = ["user__username", "user__email"]

    def items_count(self, obj):
        return obj.wishlistitem_set.count()

    items_count.short_description = "Количество товаров"


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["wishlist", "product", "added_at"]
    list_filter = ["added_at", "product__category"]
    raw_id_fields = ["wishlist", "product"]
    search_fields = ["wishlist__user__username", "product__name"]
    readonly_fields = ["added_at"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "items_count", "total_price_display", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at", "total_price_display"]
    inlines = [CartItemInline]
    search_fields = ["user__username", "user__email"]

    def items_count(self, obj):
        return obj.items.count()

    items_count.short_description = "Товаров в корзине"

    def total_price_display(self, obj):
        return f"{obj.total_price} ₽"

    total_price_display.short_description = "Общая стоимость"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["cart", "product", "quantity", "total_price_display"]
    list_editable = ["quantity"]
    raw_id_fields = ["cart", "product"]
    search_fields = ["cart__user__username", "product__name"]

    def total_price_display(self, obj):
        return f"{obj.total_price} ₽"

    total_price_display.short_description = "Общая стоимость"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "status", "total_amount_display", "items_count", "created_at"]
    list_filter = ["status", "created_at"]
    list_editable = ["status"]
    list_display_links = ["order_number"]
    raw_id_fields = ["user"]  # TO-DO: Проблема связана с user_info
    search_fields = ["order_number", "user__email", "user__username"]
    readonly_fields = ["order_number", "created_at", "updated_at", "total_amount_display", "user_info"]
    inlines = [OrderItemInline]
    fieldsets = (
        ("Основная информация", {"fields": ("order_number", "user_info", "status", "total_amount_display")}),
        ("Детали доставки", {"fields": ("shipping_address", "phone_number", "customer_notes")}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    date_hierarchy = "created_at"

    def total_amount_display(self, obj):
        return f"{obj.total_amount} ₽"

    total_amount_display.short_description = "Общая сумма"

    def items_count(self, obj):
        return obj.items.count()

    items_count.short_description = "Товаров"

    def user_info(self, obj):
        # url = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html(f'<a href="">{obj.user.username}</a> - {obj.user.email}')  # TO-DO: reverse

    user_info.short_description = "Пользователь"

    actions = ["mark_as_processing", "mark_as_shipped", "mark_as_delivered"]

    def mark_as_processing(self, request, queryset):
        queryset.update(status="processing")

    mark_as_processing.short_description = "Перевести в статус 'В обработке'"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status="shipped")

    mark_as_shipped.short_description = "Перевести в статус 'Отправлен'"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status="delivered")

    mark_as_delivered.short_description = "Перевести в статус 'Доставлен'"


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


# Интеграция Profile с User в админке
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Профиль"


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


# Перерегистрируем User с кастомным админом
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


admin.site.site_header = "Панель управления интернет-магазином"
admin.site.site_title = "Админ-панель магазина"
admin.site.index_title = "Управление магазином"
