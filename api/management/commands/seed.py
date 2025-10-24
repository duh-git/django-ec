# management/commands/populate_fake_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from faker import Faker
import random
from decimal import Decimal

from api.models import (
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


class Command(BaseCommand):
    help = "Заполняет базу данных тестовыми данными с использованием Faker"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Количество продуктов для создания (по умолчанию: 50)",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=20,
            help="Количество пользователей для создания (по умолчанию: 20)",
        )

    def handle(self, *args, **options):
        fake = Faker("ru_RU")
        product_count = options["count"]
        user_count = options["users"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Начинаем создание тестовых данных: {user_count} пользователей, {product_count} продуктов"
            )
        )

        try:
            with transaction.atomic():
                categories = self.create_categories(fake)
                brands = self.create_brands(fake)
                users = self.create_users(fake, user_count)
                products = self.create_products(fake, product_count, categories, brands)
                self.create_product_images(fake, products)
                self.create_reviews(fake, users, products)
                self.create_profiles(fake, users)
                self.create_wishlists(users, products)
                self.create_carts(users, products)
                self.create_orders(fake, users, products)

            self.stdout.write(self.style.SUCCESS("Тестовые данные успешно созданы!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при создании тестовых данных: {e}"))

    def create_categories(self, fake):
        """Создание категорий"""
        categories = []

        # Создаем основные категории
        main_categories = ["Электроника", "Одежда", "Книги", "Дом и сад", "Спорт", "Красота", "Игрушки", "Автотовары"]

        for name in main_categories:
            category = Category.objects.create(name=name)
            categories.append(category)

            # Создаем подкатегории для каждой основной категории
            for _ in range(random.randint(2, 5)):
                subcategory_name = fake.word().capitalize() + " " + fake.word().capitalize()
                subcategory = Category.objects.create(name=subcategory_name, parent=category)
                categories.append(subcategory)

        self.stdout.write(self.style.SUCCESS(f"Создано {len(categories)} категорий"))
        return categories

    def create_brands(self, fake):
        """Создание брендов"""
        brands = []
        brand_names = set()

        for _ in range(30):
            while True:
                brand_name = fake.company()
                if brand_name not in brand_names:
                    brand_names.add(brand_name)
                    break

            brand = Brand.objects.create(name=brand_name, description=fake.text(200) if random.random() > 0.3 else None)
            brands.append(brand)

        self.stdout.write(self.style.SUCCESS(f"Создано {len(brands)} брендов"))
        return brands

    def create_users(self, fake, user_count):
        """Создание пользователей"""
        users = []

        for i in range(user_count):
            username = fake.user_name()
            email = fake.email()

            user = User.objects.create_user(
                username=username,
                email=email,
                password="user_password",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
            )
            users.append(user)

        self.stdout.write(self.style.SUCCESS(f"Создано {len(users)} пользователей"))
        return users

    def create_products(self, fake, product_count, categories, brands):
        """Создание продуктов"""
        products = []

        for i in range(product_count):
            product = Product.objects.create(
                name=fake.catch_phrase(),
                description=fake.text(500) if random.random() > 0.2 else None,
                category=random.choice(categories),
                brand=random.choice(brands),
                price=Decimal(random.uniform(100, 50000)).quantize(Decimal("0.01")),
                stock=random.randint(0, 1000),
                warranty_months=random.choice([0, 6, 12, 24, 36]),
                is_available=random.random() > 0.1,  # 90% доступны
                is_featured=random.random() > 0.8,  # 20% рекомендуемые
            )
            products.append(product)

        self.stdout.write(self.style.SUCCESS(f"Создано {len(products)} продуктов"))
        return products

    def create_product_images(self, fake, products):
        """Создание изображений продуктов"""
        image_count = 0

        for product in products:
            # Создаем 1-4 изображения для каждого продукта
            for i in range(random.randint(1, 4)):
                ProductImage.objects.create(
                    product=product,
                    image=f"products/placeholder_{random.randint(1, 10)}.jpg",  # Заглушка
                    is_primary=(i == 0),  # Первое изображение - основное
                    order=i,
                )
                image_count += 1

        self.stdout.write(self.style.SUCCESS(f"Создано {image_count} изображений продуктов"))

    def create_reviews(self, fake, users, products):
        """Создание отзывов"""
        reviews_count = 0

        for product in products:
            # Создаем 0-8 отзывов для каждого продукта
            review_users = random.sample(users, min(random.randint(0, 8), len(users)))

            for user in review_users:
                # Пропускаем некоторые комбинации пользователь-продукт
                if random.random() > 0.7:
                    continue

                try:
                    review = Review.objects.create(
                        user=user,
                        product=product,
                        rating=random.randint(1, 5),
                        comment=fake.text(200) if random.random() > 0.3 else None,
                        admin_response=fake.text(150) if random.random() > 0.8 else None,
                    )
                    reviews_count += 1
                except:
                    # Игнорируем ошибки уникальности
                    pass

        self.stdout.write(self.style.SUCCESS(f"Создано {reviews_count} отзывов"))

    def create_profiles(self, fake, users):
        """Создание профилей"""
        profiles_count = 0

        for user in users:
            Profile.objects.create(
                user=user,
                delivery_address=fake.address() if random.random() > 0.4 else None,
                phone_number=fake.phone_number() if random.random() > 0.3 else None,
                profile_picture=f"profiles/avatar_{random.randint(1, 5)}.jpg" if random.random() > 0.6 else None,
            )
            profiles_count += 1

        self.stdout.write(self.style.SUCCESS(f"Создано {profiles_count} профилей"))

    def create_wishlists(self, users, products):
        """Создание списков желаний"""
        wishlist_items_count = 0

        for user in users:
            wishlist, created = Wishlist.objects.get_or_create(user=user)

            # Добавляем 0-15 товаров в список желаний
            wishlist_products = random.sample(products, min(random.randint(0, 15), len(products)))

            for product in wishlist_products:
                try:
                    WishlistItem.objects.create(wishlist=wishlist, product=product)
                    wishlist_items_count += 1
                except:
                    # Игнорируем ошибки уникальности
                    pass

        self.stdout.write(self.style.SUCCESS(f"Создано {wishlist_items_count} элементов списков желаний"))

    def create_carts(self, users, products):
        """Создание корзин"""
        cart_items_count = 0

        for user in users:
            cart, created = Cart.objects.get_or_create(user=user)

            # Добавляем 0-8 товаров в корзину
            cart_products = random.sample(products, min(random.randint(0, 8), len(products)))

            for product in cart_products:
                try:
                    CartItem.objects.create(cart=cart, product=product, quantity=random.randint(1, 5))
                    cart_items_count += 1
                except:
                    # Игнорируем ошибки уникальности
                    pass

        self.stdout.write(self.style.SUCCESS(f"Создано {cart_items_count} элементов корзин"))

    def create_orders(self, fake, users, products):
        """Создание заказов"""
        orders_count = 0
        order_items_count = 0

        for user in users:
            # Создаем 0-5 заказов для каждого пользователя
            for _ in range(random.randint(0, 5)):
                order = Order.objects.create(
                    user=user,
                    status=random.choice(["pending", "processing", "shipped", "delivered", "cancelled", "refunded"]),
                    shipping_address=fake.address(),
                    phone_number=fake.phone_number(),
                    customer_notes=fake.text(100) if random.random() > 0.7 else None,
                )
                orders_count += 1

                # Добавляем 1-6 товаров в заказ
                order_products = random.sample(products, min(random.randint(1, 6), len(products)))

                for product in order_products:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=random.randint(1, 3),
                        price=product.price,  # Сохраняем цену на момент заказа
                    )
                    order_items_count += 1

                # Обновляем общую сумму заказа
                order.update_total_amount()

        self.stdout.write(self.style.SUCCESS(f"Создано {orders_count} заказов с {order_items_count} элементами"))
