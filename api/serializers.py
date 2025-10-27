from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_staff"]
        read_only_fields = ["id", "is_staff"]


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "parent_name", "children_count"]
        read_only_fields = ["id"]

    def get_children_count(self, obj):
        return obj.children.count()


class BrandSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()

    def get_products_count(self, obj):
        return obj.products.count()

    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "official_website", "description", "products_count"]
        read_only_fields = ["id"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color", "description"]
        read_only_fields = ["id"]


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "image_url", "is_primary", "order", "product"]
        read_only_fields = ["id"]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class ProductFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = ProductFile
        fields = [
            "id",
            "file",
            "file_url",
            "file_type",
            "name",
            "description",
            "size",
            "file_size_mb",
            "downloads_count",
            "product",
            "created_at",
        ]
        read_only_fields = ["id", "size", "downloads_count", "created_at"]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_file_size_mb(self, obj):
        if obj.size:
            return round(obj.size / (1024 * 1024), 2)
        return 0


class ProductTagRelationshipSerializer(serializers.ModelSerializer):
    tag_name = serializers.CharField(source="tag.name", read_only=True)
    tag_color = serializers.CharField(source="tag.color", read_only=True)

    class Meta:
        model = ProductTagRelationship
        fields = [
            "id",
            "product",
            "tag",
            "tag_name",
            "tag_color",
            "added_by",
            "weight",
            "is_auto_generated",
            "added_at",
        ]
        read_only_fields = ["id", "added_at"]


class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    brand_slug = serializers.CharField(source="brand.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "brand",
            "brand_name",
            "brand_slug",
            "category",
            "category_name",
            "category_slug",
            "price",
            "stock",
            "primary_image",
            "average_rating",
            "review_count",
            "is_available",
            "is_featured",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return ProductImageSerializer(primary_image).data
        return None


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    files = ProductFileSerializer(many=True, read_only=True)
    tags = ProductTagRelationshipSerializer(many=True, read_only=True, source="producttagrelationship_set")

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ["description", "warranty_months", "images", "files", "tags"]


class ReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "product",
            "product_name",
            "rating",
            "comment",
            "admin_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    def validate(self, data):
        if self.instance:
            # При обновлении проверяем, что пользователь не меняется
            if "user" in data and data["user"] != self.instance.user:
                raise serializers.ValidationError("Нельзя изменить пользователя отзыва")
            if "product" in data and data["product"] != self.instance.product:
                raise serializers.ValidationError("Нельзя изменить продукт отзыва")
        return data


class ProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ["id", "user", "user_email", "user_name", "delivery_address", "phone_number", "profile_picture"]
        read_only_fields = ["id", "user"]

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


class WishlistSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ["id", "user", "user_email", "items_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_items_count(self, obj):
        return obj.wishlistitem_set.count()


class WishlistItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(source="product.price", read_only=True, max_digits=10, decimal_places=2)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem
        fields = ["id", "wishlist", "product", "product_name", "product_price", "product_image", "added_at"]
        read_only_fields = ["id", "added_at"]

    def get_product_image(self, obj):
        primary_image = obj.product.images.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image.url
        return None


class CartItemSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(source="product.price", read_only=True, max_digits=10, decimal_places=2)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ["id", "cart", "product", "product_name", "product_price", "product_image", "quantity", "total_price"]
        read_only_fields = ["id", "total_price"]

    def get_product_image(self, obj):
        primary_image = obj.product.images.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image.url
        return None

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Количество должно быть не менее 1")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()
    items_count = serializers.SerializerMethodField()
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "user_email", "items", "total_price", "items_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_items_count(self, obj):
        return obj.items.count()


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ["id", "order", "product", "product_name", "product_slug", "quantity", "price", "total_price"]
        read_only_fields = ["id", "price", "total_price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "order_number",
            "status",
            "total_amount",
            "shipping_address",
            "phone_number",
            "customer_notes",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "order_number", "total_amount", "created_at", "updated_at"]

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    def create(self, validated_data):
        # Создание заказа с автоматическим расчетом общей суммы
        order = Order.objects.create(**validated_data)
        return order


class OrderCreateSerializer(serializers.ModelSerializer):
    cart_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Order
        fields = ["shipping_address", "phone_number", "customer_notes", "cart_id"]

    def create(self, validated_data):
        cart_id = validated_data.pop("cart_id")
        user = self.context["request"].user

        try:
            cart = Cart.objects.get(id=cart_id, user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Корзина не найдена")

        # Создаем заказ
        order = Order.objects.create(
            user=user,
            shipping_address=validated_data["shipping_address"],
            phone_number=validated_data["phone_number"],
            customer_notes=validated_data.get("customer_notes", ""),
        )

        # Переносим товары из корзины в заказ
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order, product=cart_item.product, quantity=cart_item.quantity, price=cart_item.product.price
            )

        # Очищаем корзину
        cart.items.all().delete()

        # Пересчитываем общую сумму
        order.update_total_amount()

        return order


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    attrs["user"] = user
                    return attrs
                else:
                    raise serializers.ValidationError("Аккаунт отключен")
            else:
                raise serializers.ValidationError("Неверные учетные данные")
        else:
            raise serializers.ValidationError("Необходимо указать имя пользователя и пароль")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2", "first_name", "last_name"]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "email": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})

        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Пользователь с таким email уже существует"})

        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(**validated_data)
        return user
