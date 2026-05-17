from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'api/contracts', views.BankContractViewSet)
router.register(r'api/account-requests', views.AccountRequestViewSet, basename='account-request')
router.register(r'api/requested-contracts', views.RequestedContractViewSet, basename='requested-contract')

urlpatterns = [
    # Шаблонные URL (для 1-2 лабораторных)
    path('', views.contracts_list, name='contracts_list'),
    path('contracts/<int:contract_id>/', views.contract_detail, name='contract_detail'),
    path('account-request/<int:request_id>/', views.account_request_detail, name='account_request_detail'),
    path('account-request/<int:request_id>/delete/', views.delete_account_request, name='delete_account_request'),
    path('account-request/<int:request_id>/set-primary/<int:contract_id>/', views.set_primary_contract, name='set_primary_contract'),
    path('account-request/<int:request_id>/submit/', views.submit_account_request, name='submit_account_request'),
    path('request/remove/<int:contract_id>/', views.remove_from_request, name='remove_from_request'),
    
    # Загрузка изображений
    path('api/contracts/<int:contract_id>/upload-image/', views.upload_contract_image, name='upload_contract_image'),
    
    # Аутентификация
    path('api/register/', views.register_user, name='register'),
    path('api/login/', views.auth_login, name='login'),
    path('api/logout/', views.auth_logout, name='logout'),
    path('api/profile/', views.user_profile, name='profile'),
    path('api/profile/update/', views.update_user, name='update_profile'),
    
    # API URL (для 3 лабораторной)
    path('', include(router.urls)),
]