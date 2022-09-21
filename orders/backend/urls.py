from django.urls import path

from backend.views import PartnerUpdate, PartnerState, PartnerOrders, RegisterAccount

app_name = 'backend'
urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    path('user/register', RegisterAccount.as_view(), name='user-register')
    # path('user/login', LoginAccount.as_view(), name='user-login')
]