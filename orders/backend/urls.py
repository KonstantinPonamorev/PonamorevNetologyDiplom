from django.urls import path, include
from rest_framework.routers import DefaultRouter

from backend.views import PartnerUpdateView, PartnerStateView, PartnerOrdersView, RegisterAccountView, \
    AccountDetailsView, LoginAccountView, \
    CategoryViewSet, ShopViewSet, BasketView, ContactView, OrderView, ConfirmAccountView, ProductInfoViewSet


app_name = 'backend'


product_info = ProductInfoViewSet.as_view({
    'get': 'product_info'
})

shop_list = ShopViewSet.as_view({
    'get': 'list'
})

shop_detail = ShopViewSet.as_view({
    'get': 'retrieve'
})

category_list = CategoryViewSet.as_view({
    'get': 'list'
})

category_detail = CategoryViewSet.as_view({
    'get': 'retrieve'
})



router = DefaultRouter()
router.register(r'products', ProductInfoViewSet, basename='product_info')
router.register(r'shops', ShopViewSet, basename='shop')
router.register(r'categories', CategoryViewSet, basename='category')


urlpatterns = [
    path('partner/update', PartnerUpdateView.as_view(), name='partner-update'),
    path('partner/state', PartnerStateView.as_view(), name='partner-state'),
    path('partner/orders', PartnerOrdersView.as_view(), name='partner-orders'),
    path('user/register', RegisterAccountView.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccountView.as_view(), name='user-register-confirm'),
    path('user/details', AccountDetailsView.as_view(), name='user-details'),
    path('user/login', LoginAccountView.as_view(), name='user-login'),
    path('user/contact', ContactView.as_view(), name='user-contact'),
    # path('categories', CategoryView.as_view(), name='categories'),
    # path('shops', ShopView.as_view(), name='shops'),
    # path('products', ProductInfoView.as_view(), name='products'),
    path('basket', BasketView.as_view(), name='basket'),
    path('orders', OrderView.as_view(), name='orders'),
    path('', include(router.urls))
]

