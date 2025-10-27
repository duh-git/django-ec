from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.authtoken.models import Token  # Если используете TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.db.models import Q, F, Count, Avg
from django.shortcuts import get_object_or_404
from django.http import Http404
from .models import *
from .serializers import *
from .utils import generate_order_pdf
from .cache_utils import get_featured_products, get_categories_with_counts, clear_product_cache


def generate_order_pdf_view(request, order_id):
    """Представление для вызова функции генерации pdf"""
    try:
        order = Order.objects.get(id=order_id)
        return generate_order_pdf(order)
    except Order.DoesNotExist:
        raise Http404("Заказ с указанным ID не существует")


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "id"]
    lookup_field = "slug"

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [AllowAny()]

    @action(detail=False, methods=["get"])
    def main(self, request):
        """Получение основных категорий (без родительских)"""
        main_categories = Category.objects.main_categories()
        page = self.paginate_queryset(main_categories)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(main_categories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def products(self, request, slug=None):
        category = self.get_object()
        products = Product.objects.filter(category=category, is_available=True)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "id"]
    lookup_field = "slug"

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [AllowAny()]

    @action(detail=True, methods=["get"])
    def products(self, request, slug=None):
        brand = self.get_object()
        products = Product.objects.filter(brand=brand, is_available=True)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [AllowAny()]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "brand__name", "brand__slug", "category__name", "category__slug"]
    ordering_fields = ["name", "price", "created_at", "average_rating"]
    filterset_fields = ["category", "brand", "is_available", "is_featured"]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        return ProductDetailSerializer

    # def get_permissions(self):
    #     if self.action in ["create", "update", "partial_update", "destroy"]:
    #         return [IsAdminUser()]
    #     return [AllowAny()]

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_staff:
            queryset = queryset.filter(is_available=True)

        price_min = self.request.query_params.get("price_min")
        price_max = self.request.query_params.get("price_max")

        if price_min:
            queryset = queryset.filter(price__gte=price_min)
        if price_max:
            queryset = queryset.filter(price__lte=price_max)

        tags = self.request.query_params.get("tags")
        if tags:
            tag_ids = [int(tag_id) for tag_id in tags.split(",")]
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()

        queryset = queryset.select_related("category", "brand").prefetch_related("images", "tags")
        return queryset

    @action(detail=False, methods=["get"])
    def main_categories(self, request):
        """Основные категории (без родительских)"""
        categories = Category.objects.filter(parent__isnull=True)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def price_list(self, request):
        """Возвращает список цен продуктов"""
        products = Product.objects.filter(is_available=True).values("id", "name", "price", "category__name")
        return Response(list(products))

    @action(detail=False, methods=["get"])
    def product_names(self, request):
        """Возвращает список названий продуктов"""
        names = Product.objects.filter(is_available=True).values_list("name", flat=True)
        return Response(list(names))

    @action(detail=True, methods=["get"])
    def reviews(self, request, slug=None):
        product = self.get_object()
        reviews = product.reviews.all()
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Используем кешированные избранные товары"""
        featured_products = get_featured_products()
        return Response(featured_products)

    @action(detail=False, methods=["get"])
    def search(self, request):
        query = request.query_params.get("q", "")
        if query:
            products = Product.objects.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(brand__slug__icontains=query)
                | Q(category__name__icontains=query)
                | Q(category__slug__icontains=query),
                is_available=True,
            )
        else:
            products = Product.objects.filter(is_available=True)

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """При создании товара очищаем кеш"""
        product = serializer.save()
        clear_product_cache()

    def perform_update(self, serializer):
        """При обновлении товара очищаем кеш"""
        product = serializer.save()
        clear_product_cache()

    def perform_destroy(self, instance):
        """При удалении товара очищаем кеш"""
        instance.delete()
        clear_product_cache()


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "is_primary"]
    ordering_fields = ["order", "id"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [AllowAny()]


class ProductFileViewSet(viewsets.ModelViewSet):
    queryset = ProductFile.objects.all()
    serializer_class = ProductFileSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "file_type"]
    ordering_fields = ["file_type", "name"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [AllowAny()]

    @action(detail=True, methods=["post"])
    def download(self, request, pk=None):
        product_file = self.get_object()
        product_file.downloads_count = F("downloads_count") + 1
        product_file.save()
        product_file.refresh_from_db()
        return Response({"message": "Download counted", "downloads_count": product_file.downloads_count})


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "user", "rating"]
    ordering_fields = ["created_at", "rating", "updated_at"]

    def get_permissions(self):
        if self.action in ["create"]:
            return [IsAuthenticated()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        # Пользователи видят только свои отзывы или все, если они админы
        if not self.request.user.is_staff:
            if self.request.user.is_authenticated:
                queryset = queryset.filter(Q(user=self.request.user) | Q(admin_response__isnull=False))
            else:
                queryset = queryset.filter(admin_response__isnull=False)
        return queryset


class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get", "put", "patch"])
    def me(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)

        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data)

        elif request.method in ["PUT", "PATCH"]:
            serializer = self.get_serializer(profile, data=request.data, partial=request.method == "PATCH")
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def my_wishlist(self, request):
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(wishlist)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add_item(self, request):
        product_id = request.data.get("product_id")
        try:
            product = Product.objects.get(id=product_id, is_available=True)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        wishlist_item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)

        if created:
            return Response({"message": "Product added to wishlist"}, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "Product already in wishlist"})

    @action(detail=False, methods=["post"])
    def remove_item(self, request):
        product_id = request.data.get("product_id")
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_item = WishlistItem.objects.get(wishlist=wishlist, product_id=product_id)
            wishlist_item.delete()
            return Response({"message": "Product removed from wishlist"})
        except (Wishlist.DoesNotExist, WishlistItem.DoesNotExist):
            return Response({"error": "Item not found in wishlist"}, status=status.HTTP_404_NOT_FOUND)


class WishlistItemViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WishlistItem.objects.filter(wishlist__user=self.request.user)

    def perform_create(self, serializer):
        wishlist, created = Wishlist.objects.get_or_create(user=self.request.user)
        serializer.save(wishlist=wishlist)


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]  # Добавляем проверку авторизации

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def my_cart(self, request):
        # Проверяем, что пользователь аутентифицирован
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_create(self, serializer):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)

    @action(detail=True, methods=["post"])
    def update_quantity(self, request, pk=None):
        cart_item = self.get_object()
        quantity = request.data.get("quantity")

        if quantity is None or int(quantity) < 1:
            return Response({"error": "Quantity must be at least 1"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity > cart_item.product.stock:
                return Response({"error": "Not enough stock"}, status=status.HTTP_400_BAD_REQUEST)

            cart_item.quantity = quantity
            cart_item.save()

            serializer = self.get_serializer(cart_item)
            return Response(serializer.data)

        except ValueError:
            return Response({"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "total_amount", "updated_at"]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all().select_related("user").prefetch_related("items")
        return Order.objects.filter(user=self.request.user).select_related("user").prefetch_related("items")

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        if self.request.user.is_staff and "user" in serializer.validated_data:
            # Админы могут создавать заказы для других пользователей
            serializer.save()
        else:
            # Обычные пользователи создают заказы для себя
            serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.user != request.user and not request.user.is_staff:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if order.status not in ["pending", "processing"]:
            return Response({"error": "Order cannot be cancelled"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = "cancelled"
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        order = self.get_object()
        new_status = request.data.get("status")

        if new_status not in dict(Order.STATUS_CHOICES).keys():
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return OrderItem.objects.all()
        return OrderItem.objects.filter(order__user=self.request.user)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "email", "date_joined"]

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)

        return Response(
            {
                "message": "Успешный вход в систему",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "token": token.key,  # Если используете TokenAuthentication
            },
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        Profile.objects.get_or_create(user=user)
        Cart.objects.get_or_create(user=user)
        Wishlist.objects.get_or_create(user=user)

        return Response(
            {
                "message": "Пользователь успешно зарегистрирован",
                "user": {"id": user.id, "username": user.username, "email": user.email},
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
