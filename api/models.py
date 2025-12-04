from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from django.utils import timezone
from uuid import uuid4
from django.urls import reverse
from .managers import *


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name="Категория")
    slug = models.SlugField(max_length=80, unique=True, verbose_name="URL")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, blank=True, null=True, related_name="children", verbose_name="Подкатегория"
    )
    objects = CategoryManager()

    def get_absolute_url(self):
        return reverse("products_by_category", kwargs={"category_slug": self.slug})

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name="Бренд")
    slug = models.SlugField(max_length=80, unique=True, verbose_name="URL")
    official_website = models.URLField(blank=True, null=True, verbose_name="Официальный сайт")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    def get_absolute_url(self):
        return reverse("products_by_brand", kwargs={"brand_slug": self.slug})

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Тег")
    color = models.CharField(max_length=7, default="#000000", verbose_name="Цвет")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Продукт")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="URL")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="Категория")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products", verbose_name="Бренд")
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="products", through="ProductTagRelationship", verbose_name="Теги"
    )

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Цена")
    stock = models.PositiveIntegerField(default=0, verbose_name="Количество")
    warranty_months = models.PositiveIntegerField(default=0, verbose_name="Гаранития, мес")
    is_available = models.BooleanField(default=True, verbose_name="Доступен")
    is_featured = models.BooleanField(default=False, verbose_name="Показан на главной")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    objects = ProductManager()

    @property
    def average_rating(self):
        return self.reviews.aggregate(Avg("rating"))["rating__avg"] or 0

    @property
    def review_count(self):
        return self.reviews.count()

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"product_slug": self.slug})

    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"
        indexes = [
            models.Index(fields=["is_available", "is_featured", "-created_at"]),  # Для главной страницы
            models.Index(fields=["category", "is_available", "price"]),  # Для фильтрации по категориям
            models.Index(fields=["category", "brand", "is_available"]),  # Для поиска и сортировки
            models.Index(fields=["-created_at", "is_available"]),  # Для админки
            models.Index(fields=["is_available"]),  # Для тегов
        ]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name="Продукт")
    image = models.ImageField(upload_to="products/", verbose_name="Изображение")
    is_primary = models.BooleanField(default=False, verbose_name="Основное")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядковый номер")

    class Meta:
        verbose_name = "Изображение продукта"
        verbose_name_plural = "Изображения продуктов"
        ordering = ["order", "id"]

    def __str__(self):
        return f"Изображение {self.product} - {self.order}{f'(основное)' if self.is_primary else ''}"


class ProductFile(models.Model):
    FILE_TYPES = (
        ("manual", "Инструкция"),
        ("certificate", "Сертификат"),
        ("specification", "Технические характеристики"),
        ("software", "ПО/Драйверы"),
        ("other", "Другое"),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="files", verbose_name="Продукт")
    name = models.CharField(max_length=255, verbose_name="Название файла")
    file = models.FileField(upload_to="product_files/%Y/%m/%d/", verbose_name="Файл")
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default="other", verbose_name="Тип файла")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    size = models.PositiveIntegerField(editable=False, verbose_name="Размер файла (байт)")
    downloads_count = models.PositiveIntegerField(default=0, verbose_name="Количество скачиваний")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def save(self, *args, **kwargs):
        if self.file:
            self.size = self.file.size
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Файл продукта"
        verbose_name_plural = "Файлы продуктов"
        ordering = ["file_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.product.name})"


class ProductTagRelationship(models.Model):
    """Промежуточная модель для связи Product и Tag с дополнительными данными"""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, verbose_name="Тег")
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Добавил")
    weight = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="Вес связи",
        help_text="Насколько сильно тег связан с продуктом (1-10)",
    )
    is_auto_generated = models.BooleanField(default=False, verbose_name="Автоматически сгенерирован")

    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Связь продукта и тега"
        verbose_name_plural = "Связи продуктов и тегов"
        unique_together = ("product", "tag")
        ordering = ["-weight", "added_at"]

    def __str__(self):
        return f"{self.product.name} - {self.tag.name} ({self.weight})"


class Review(models.Model):
    RATING_CHOICES = (
        (1, "1 - Ужасно"),
        (2, "2 - Плохо"),
        (3, "3 - Нормально"),
        (4, "4 - Хорошо"),
        (5, "5 - Отлично"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews", verbose_name="Пользователь")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", verbose_name="Продукт")
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Рейтинг"
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    admin_response = models.TextField(blank=True, null=True, verbose_name="Ответ")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    objects = ReviewManager()

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"product_slug": self.product.slug}) + "#reviews"

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        unique_together = ("user", "product")

    def __str__(self):
        return f"Отзыв от {self.user.email} на {self.product.name}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    delivery_address = models.TextField(blank=True, null=True, verbose_name="Адрес доставки")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Контактная информация")
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True, verbose_name="Аватар")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"Профиль {self.user.username}"


class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Список желаний"
        verbose_name_plural = "Списки желаний"

    def __str__(self):
        return f"Список желаний {self.user.username}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, verbose_name="Список желаний")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")

    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Элемент списка желаний"
        verbose_name_plural = "Элементы списков желаний"
        unique_together = ("wishlist", "product")

    def __str__(self):
        return f"{self.product.name} в списке {self.wishlist.user.username}"


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart", verbose_name="Ползователь")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Корзина {self.user.email}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", verbose_name="Корзина")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")

    @property
    def total_price(self):
        if None in [self.quantity, self.product.price]:
            return "Some error"
        return self.quantity * self.product.price

    def clean(self):
        if self.quantity > self.product.stock:
            raise ValidationError("Недостаточно товара на складе")

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзин"
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Ожидает обработки"),
        ("processing", "В обработке"),
        ("shipped", "Отправлен"),
        ("delivered", "Доставлен"),
        ("cancelled", "Отменен"),
        ("refunded", "Возврат"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders", verbose_name="Пользователь")
    order_number = models.CharField(max_length=100, unique=True, verbose_name="Номер заказа")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Статус")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Общая сумма")
    shipping_address = models.TextField(null=False, verbose_name="Адрес доставки")
    phone_number = models.CharField(max_length=20, verbose_name="Контактная информация")
    customer_notes = models.TextField(blank=True, null=True, verbose_name="Комментарий пользователя")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    objects = OrderManager()

    def update_total_amount(self):
        """Пересчитывает общую сумму заказа"""
        self.total_amount = sum(item.total_price for item in self.items.all())
        self.save()

    def save(self, *args, **kwargs):
        """Генерируем номер заказа"""
        if not self.order_number:
            self.order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{str(uuid4())[:8]}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("order_detail", kwargs={"order_number": self.order_number})

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f"Заказ {self.order_number} от {self.user.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items", verbose_name="Продукт")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Цена")

    @property
    def total_price(self):
        if None in [self.quantity, self.price]:
            return f"{self.quantity} * {self.price}"
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        """Созраняем цену на момент заказа"""
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказов"

    def __str__(self):
        return f"{self.order.order_number}: {self.quantity} x {self.product.name[:15]}..."
