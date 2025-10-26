from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"categories", views.CategoryViewSet)
router.register(r"brands", views.BrandViewSet)
router.register(r"tags", views.TagViewSet)
router.register(r"products", views.ProductViewSet)
router.register(r"product-images", views.ProductImageViewSet)
router.register(r"product-files", views.ProductFileViewSet)
router.register(r"reviews", views.ReviewViewSet)
router.register(r"profiles", views.ProfileViewSet, basename="profile")
router.register(r"wishlists", views.WishlistViewSet, basename="wishlist")
router.register(r"wishlist-items", views.WishlistItemViewSet, basename="wishlistitem")
router.register(r"carts", views.CartViewSet, basename="cart")
router.register(r"cart-items", views.CartItemViewSet, basename="cartitem")
router.register(r"orders", views.OrderViewSet, basename="order")
router.register(r"order-items", views.OrderItemViewSet, basename="orderitem")
router.register(r"users", views.UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("auth/login/", views.login, name="login"),
    path("auth/register/", views.register, name="register"),
    # path("auth/logout/", views.logout, name="logout"),
]
