from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Q
from django.utils import timezone
from uuid import uuid4
from django.core.exceptions import ValidationError


class ProductManager(models.Manager):
    def available(self):
        """Только доступные продукты"""
        return self.filter(is_available=True)

    def featured(self):
        """Избранные продукты"""
        return self.filter(is_available=True, is_featured=True)

    def by_category(self, category_slug):
        """Продукты по категории"""
        return self.filter(category__slug=category_slug, is_available=True)

    def with_high_rating(self, min_rating=4.0):
        """Продукты с высоким рейтингом"""
        return (
            self.filter(is_available=True)
            .annotate(avg_rating=Avg("reviews__rating"))
            .filter(avg_rating__gte=min_rating)
        )

    def search(self, query):
        """Поиск продуктов"""
        return self.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(brand__name__icontains=query)
            | Q(category__name__icontains=query),
            is_available=True,
        )


class OrderManager(models.Manager):
    def pending(self):
        """Ожидающие обработки заказы"""
        return self.filter(status="pending")

    def for_user(self, user):
        """Заказы пользователя"""
        return self.filter(user=user).order_by("-created_at")

    def recent(self, days=30):
        """Недавние заказы"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)


class ReviewManager(models.Manager):
    def approved(self):
        """Одобренные отзывы (можно добавить поле is_approved)"""
        return self.all()  # В будущем можно добавить модерацию

    def for_product(self, product):
        """Отзывы для продукта"""
        return self.filter(product=product).order_by("-created_at")

    def with_response(self):
        """Отзывы с ответами администратора"""
        return self.exclude(admin_response__isnull=True).exclude(admin_response="")


class CategoryManager(models.Manager):
    def main_categories(self):
        """Основные категории (без родительских)"""
        return self.filter(parent__isnull=True)
