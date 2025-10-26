from django.core.cache import cache
from .models import Product, Category
from django.conf import settings


def get_featured_products():
    """Получает избранные товары с кешированием"""
    cache_key = "featured_products"
    featured_products = cache.get(cache_key)

    if featured_products is None:
        # Кеш пустой, получаем данные из БД
        featured_products = list(
            Product.objects.filter(is_featured=True, is_available=True)
            .select_related("category", "brand")
            .values("id", "name", "price", "slug", "category__name", "brand__name")
        )
        cache.set(cache_key, featured_products, 5 * 60)

    return featured_products


def get_categories_with_counts():
    """Получает категории с количеством товаров с кешированием"""
    cache_key = "categories_with_counts"
    categories = cache.get(cache_key)

    if categories is None:
        categories = list(
            Category.objects.annotate(products_count=Count("products")).values("id", "name", "slug", "products_count")
        )
        cache.set(cache_key, categories, 10 * 60)

    return categories


def clear_product_cache():
    """Очищает кеш связанный с товарами"""
    cache.delete("featured_products")
    cache.delete("categories_with_counts")
