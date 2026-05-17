from django.shortcuts import render, get_object_or_404, redirect
from django.db import connection
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from minio import Minio
from django.conf import settings
import os
import uuid
import random
import json
from .models import BankContract, AccountRequest, RequestedContract
from .serializers import BankContractSerializer, AccountRequestSerializer, RequestedContractSerializer
from .permissions import IsModerator, IsModeratorOrReadOnly, IsOwner
from django.shortcuts import redirect


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_current_user(request):
    """Получить текущего пользователя из сессии"""
    if request.user.is_authenticated:
        return request.user
    return None

def get_or_create_draft_request(user):
    """Получить или создать черновик заявки для пользователя"""
    if not user:
        return None
    draft, created = AccountRequest.objects.get_or_create(
        creator=user,
        status='DRAFT',
        defaults={
            'balance_account_number': '',
            'currency_code': '810'
        }
    )
    return draft

def get_image_url(image_key):
    """Получить публичную ссылку на изображение"""
    if not image_key:
        return None
    return f"http://localhost:9000/banking-images/{image_key}"

# ============================================
# ШАБЛОННЫЕ VIEWS (для 1-2 лабораторных)
# ============================================

def contracts_list(request):
    """Страница 1: список договоров + карточка корзины"""
    search_query = request.GET.get('search', '')
    
    contracts = BankContract.objects.filter(is_active=True)
    if search_query:
        contracts = contracts.filter(counterparty_name__icontains=search_query)
    
    # Добавляем URL изображений
    for contract in contracts:
        contract.image_url = get_image_url(contract.image_key)
    
    # Получаем черновик текущего пользователя
    user = get_current_user(request)
    account_request = get_or_create_draft_request(user) if user else None
    
    cart_items_count = 0
    account_request_id = None
    if account_request:
        account_request_id = account_request.id
        cart_items_count = account_request.requested_contracts.count()
    
    context = {
        'contracts': contracts,
        'search_query': search_query,
        'account_request_id': account_request_id,
        'cart_items_count': cart_items_count,
    }
    return render(request, 'contracts/contracts_list.html', context)


def contract_detail(request, contract_id):
    """Страница 2: детальная информация о договоре"""
    contract = get_object_or_404(BankContract, id=contract_id, is_active=True)
    contract.image_url = get_image_url(contract.image_key)
    return render(request, 'contracts/contract_detail.html', {
        'contract': contract,
    })


def account_request_detail(request, request_id):
    """Страница 3: просмотр заявки (корзины)"""
    try:
        account_request = AccountRequest.objects.get(id=request_id)
    except AccountRequest.DoesNotExist:
        return redirect('contracts_list')
    
    # Если заявка не в статусе DRAFT - редирект на главную
    if account_request.status != 'DRAFT':
        return redirect('contracts_list')
    
    requested_contracts = account_request.requested_contracts.select_related('bank_contract').all()
    
    requested_contracts_with_details = []
    for item in requested_contracts:
        contract = item.bank_contract
        contract.image_url = get_image_url(contract.image_key)
        requested_contracts_with_details.append({
            'contract': contract,
            'comment': item.comment,
            'connection_date': item.connection_date,
        })
    
    context = {
        'account_request': account_request,
        'requested_contracts': requested_contracts_with_details,
    }
    return render(request, 'contracts/account_request_detail.html', context)


def delete_account_request(request, request_id):
    """Логическое удаление заявки через прямой SQL запрос"""
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE contracts_accountrequest SET status = 'DELETED' WHERE id = %s AND status = 'DRAFT'",
            [request_id]
        )
    messages.success(request, 'Заявка удалена')
    return redirect('contracts_list')


def set_primary_contract(request, request_id, contract_id):
    """Установка/снятие основного договора для счета"""
    if request.method == 'POST':
        account_request = get_object_or_404(AccountRequest, id=request_id, status='DRAFT')
        
        # Если contract_id == 0, снимаем основной договор
        if contract_id == 0:
            account_request.primary_contract = None
            account_request.save()
            return JsonResponse({'status': 'success', 'message': 'Основной договор снят'})
        
        # Иначе устанавливаем новый основной договор
        contract = get_object_or_404(BankContract, id=contract_id)
        account_request.primary_contract = contract
        account_request.save()
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


def submit_account_request(request, request_id):
    """Создание заявки (меняем статус с DRAFT на SUBMITTED)"""
    if request.method == 'POST':
        account_request = get_object_or_404(AccountRequest, id=request_id, status='DRAFT')
        
        if not account_request.primary_contract:
            messages.error(request, 'Выберите основной договор')
            return redirect('account_request_detail', request_id=request_id)
        
        account_request.status = 'SUBMITTED'
        account_request.submitted_at = timezone.now()
        account_request.save()
        
        messages.success(request, 'Заявка успешно создана')
        return redirect('contracts_list')
    return redirect('contracts_list')


def remove_from_request(request, contract_id):
    """Удаление договора из заявки"""
    if request.method == 'POST':
        user = get_current_user(request)
        account_request = get_or_create_draft_request(user) if user else None
        if account_request:
            RequestedContract.objects.filter(
                account_request=account_request,
                bank_contract_id=contract_id
            ).delete()
            messages.success(request, 'Договор удалён из заявки')
            return redirect('account_request_detail', request_id=account_request.id)
    return redirect('contracts_list')


# ============================================
# ЗАГРУЗКА ИЗОБРАЖЕНИЙ
# ============================================

@csrf_exempt
@require_http_methods(["POST"])
def upload_contract_image(request, contract_id):
    """Загрузка изображения для договора"""
    try:
        contract = BankContract.objects.get(id=contract_id, is_active=True)
    except BankContract.DoesNotExist:
        return JsonResponse({'error': 'Договор не найден'}, status=404)
    
    if 'image' not in request.FILES:
        return JsonResponse({'error': 'Файл изображения не передан'}, status=400)
    
    image_file = request.FILES['image']
    
    file_extension = os.path.splitext(image_file.name)[1].lower()
    if file_extension not in ['.jpg', '.jpeg', '.png', '.gif']:
        return JsonResponse({'error': 'Неподдерживаемый формат изображения'}, status=400)
    
    new_filename = f"contract_{contract.id}_{uuid.uuid4().hex[:8]}{file_extension}"
    
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL
    )
    
    if contract.image_key:
        try:
            client.remove_object(settings.MINIO_BUCKET_NAME, contract.image_key)
        except Exception:
            pass
    
    client.put_object(
        settings.MINIO_BUCKET_NAME,
        new_filename,
        image_file,
        length=image_file.size,
        content_type=image_file.content_type
    )
    
    contract.image_key = new_filename
    contract.save()
    
    return JsonResponse({
        'status': 'success',
        'image_key': new_filename,
        'image_url': get_image_url(new_filename)
    })


# ============================================
# API VIEWSETS (для 3-4 лабораторных)
# ============================================

class BankContractViewSet(viewsets.ModelViewSet):
    """API для работы с договорами"""
    queryset = BankContract.objects.filter(is_active=True)
    serializer_class = BankContractSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['counterparty_name', 'contract_number']
    filterset_fields = ['contract_type', 'is_active']
    ordering_fields = ['contract_number', 'created_at']
    
    def perform_destroy(self, instance):
        """Удаление договора вместе с изображением из Minio"""
        if instance.image_key:
            try:
                client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_USE_SSL
                )
                client.remove_object(settings.MINIO_BUCKET_NAME, instance.image_key)
            except Exception:
                pass
        instance.delete()


class AccountRequestViewSet(viewsets.ModelViewSet):
    """API для работы с заявками"""
    serializer_class = AccountRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'currency_code']
    ordering_fields = ['created_at', 'submitted_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return AccountRequest.objects.exclude(status='DELETED').exclude(status='DRAFT')
        return AccountRequest.objects.filter(creator=user).exclude(status='DELETED').exclude(status='DRAFT')
    
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
    
    @action(detail=False, methods=['get'])
    def cart_icon(self, request):
        """GET иконки корзины"""
        if not request.user.is_authenticated:
            return Response({'account_request_id': None, 'items_count': 0})
        
        draft, created = AccountRequest.objects.get_or_create(
            creator=request.user,
            status='DRAFT',
            defaults={'balance_account_number': '', 'currency_code': '810'}
        )
        
        items_count = draft.requested_contracts.count()
        return Response({
            'account_request_id': draft.id,
            'items_count': items_count
        })
    
    @action(detail=False, methods=['post'])
    def add_contract(self, request):
        """Добавление договора в заявку-черновик"""
        draft, created = AccountRequest.objects.get_or_create(
            creator=request.user,
            status='DRAFT',
            defaults={'currency_code': '810'}
        )
    
        contract_id = request.data.get('contract_id')
        
        try:
            contract = BankContract.objects.get(id=contract_id, is_active=True)
        except BankContract.DoesNotExist:
            return Response({'error': 'Договор не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем, есть ли уже такой договор в заявке
        requested_contract, created = RequestedContract.objects.get_or_create(
            account_request=draft,
            bank_contract=contract,
            defaults={
                'comment': '',
                'connection_date': timezone.now().date()
            }
        )
        
        if not created:
            return Response({'error': 'Договор уже добавлен в заявку'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(RequestedContractSerializer(requested_contract).data)
    
    @action(detail=True, methods=['put'])
    def update_request(self, request, pk=None):
        """PUT изменения полей заявки"""
        account_request = self.get_object()
        if account_request.creator != request.user:
            return Response({'error': 'Только создатель может изменять заявку'}, status=403)
        
        if account_request.status != 'DRAFT':
            return Response({'error': 'Можно изменять только черновик'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        balance_account_number = request.data.get('balance_account_number')
        currency_code = request.data.get('currency_code')
        
        if balance_account_number is not None:
            account_request.balance_account_number = balance_account_number
        if currency_code is not None:
            account_request.currency_code = currency_code
        
        account_request.save()
        return Response(AccountRequestSerializer(account_request).data)
    
    @action(detail=True, methods=['put'])
    def submit(self, request, pk=None):
        """Сформировать заявку"""
        account_request = self.get_object()
        if account_request.creator != request.user:
            return Response({'error': 'Только создатель может сформировать заявку'}, status=403)
        
        if account_request.status != 'DRAFT':
            return Response({'error': 'Можно сформировать только черновик'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if not account_request.primary_contract:
            return Response({'error': 'Выберите основной договор'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        account_request.status = 'SUBMITTED'
        account_request.submitted_at = timezone.now()
        account_request.save()
        
        return Response(AccountRequestSerializer(account_request).data)
    
    @action(detail=True, methods=['put'], permission_classes=[IsModerator])
    def complete(self, request, pk=None):
        """Завершить заявку (только модератор)"""
        account_request = self.get_object()
        if account_request.status != 'SUBMITTED':
            return Response({'error': 'Можно завершить только сформированную заявку'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        account_number = f"{account_request.balance_account_number}{account_request.currency_code}{random.randint(1000000, 9999999)}"
        account_request.assigned_account_number = account_number
        account_request.status = 'COMPLETED'
        account_request.completed_at = timezone.now()
        account_request.moderator = request.user
        account_request.save()
        
        return Response(AccountRequestSerializer(account_request).data)
    
    @action(detail=True, methods=['put'], permission_classes=[IsModerator])
    def reject(self, request, pk=None):
        """Отклонить заявку (только модератор)"""
        account_request = self.get_object()
        if account_request.status != 'SUBMITTED':
            return Response({'error': 'Можно отклонить только сформированную заявку'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        account_request.status = 'REJECTED'
        account_request.completed_at = timezone.now()
        account_request.moderator = request.user
        account_request.save()
        
        return Response(AccountRequestSerializer(account_request).data)
    
    @action(detail=True, methods=['delete'])
    def delete_request(self, request, pk=None):
        """Удаление заявки"""
        account_request = self.get_object()
        if account_request.creator != request.user:
            return Response({'error': 'Только создатель может удалить заявку'}, status=403)
        
        if account_request.status != 'DRAFT':
            return Response({'error': 'Можно удалить только черновик'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        account_request.submitted_at = timezone.now()
        account_request.status = 'DELETED'
        account_request.save()
        
        return Response({'status': 'deleted'})
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Установка основного договора"""
        account_request = self.get_object()
        contract_id = request.data.get('contract_id')
        
        if account_request.status != 'DRAFT':
            return Response({'error': 'Можно изменять только черновик'}, status=400)
        
        try:
            contract = BankContract.objects.get(id=contract_id, is_active=True)
        except BankContract.DoesNotExist:
            return Response({'error': 'Договор не найден'}, status=404)
        
        account_request.primary_contract = contract
        account_request.save()
        
        return Response({'status': 'success', 'contract_id': contract_id})
    
    @action(detail=True, methods=['delete'])
    def remove_contract(self, request, pk=None):
        """Удаление договора из заявки"""
        account_request = self.get_object()
        contract_id = request.data.get('contract_id')
        
        if account_request.status != 'DRAFT':
            return Response({'error': 'Можно изменять только черновик'}, status=400)
        
        deleted = RequestedContract.objects.filter(
            account_request=account_request,
            bank_contract_id=contract_id
        ).delete()
        
        if deleted[0]:
            return Response({'status': 'success'})
        return Response({'error': 'Договор не найден в заявке'}, status=404)

class RequestedContractViewSet(viewsets.ModelViewSet):
    """API для работы с м-м связями"""
    serializer_class = RequestedContractSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return RequestedContract.objects.filter(
            account_request__creator=user,
            account_request__status='DRAFT'
        )
    
    @action(detail=True, methods=['delete'])
    def remove_from_request(self, request, pk=None):
        """DELETE удаление из заявки (без PK м-м, по contract_id)"""
        contract_id = request.data.get('contract_id')
        account_request_id = request.data.get('account_request_id')
        
        if not contract_id or not account_request_id:
            return Response({'error': 'contract_id и account_request_id обязательны'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        deleted = RequestedContract.objects.filter(
            account_request_id=account_request_id,
            bank_contract_id=contract_id,
            account_request__creator=request.user
        ).delete()
        
        if deleted[0]:
            return Response({'status': 'deleted'})
        return Response({'error': 'Связь не найдена'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['put'])
    def update_quantity(self, request, pk=None):
        """PUT изменение количества"""
        requested_contract = self.get_object()
        
        if requested_contract.account_request.creator != request.user:
            return Response({'error': 'Только создатель может изменять'}, status=403)
        
        quantity = request.data.get('quantity')
        
        if quantity is not None:
            requested_contract.quantity = quantity
            requested_contract.save()
        
        return Response(RequestedContractSerializer(requested_contract).data)
    @action(detail=False, methods=['post'])
    def update_comment(self, request):
        """Обновление комментария в м-м связи"""
        account_request_id = request.data.get('account_request_id')
        contract_id = request.data.get('contract_id')
        comment = request.data.get('comment', '')
        
        try:
            requested_contract = RequestedContract.objects.get(
                account_request_id=account_request_id,
                bank_contract_id=contract_id
            )
            requested_contract.comment = comment
            requested_contract.save()
            return Response({'status': 'success', 'comment': comment})
        except RequestedContract.DoesNotExist:
            return Response({'error': 'Связь не найдена'}, status=404)

# ============================================
# АУТЕНТИФИКАЦИЯ (Домен пользователь)
# ============================================

@csrf_exempt
@require_http_methods(["POST"])
def register_user(request):
    """POST регистрация нового пользователя"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '')
    
    if not username or not password:
        return JsonResponse({'error': 'Username и password обязательны'}, status=400)
    
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Пользователь уже существует'}, status=400)
    
    user = User.objects.create_user(username=username, password=password, email=email)
    return JsonResponse({'status': 'success', 'user_id': user.id, 'username': user.username})


@csrf_exempt
@require_http_methods(["POST"])
def auth_login(request):
    """POST аутентификация"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    username = data.get('username')
    password = data.get('password')
    
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({
            'status': 'success', 
            'user_id': user.id, 
            'username': user.username,
            'is_staff': user.is_staff
        })
    return JsonResponse({'error': 'Неверные учетные данные'}, status=401)


@csrf_exempt
@require_http_methods(["POST"])
def auth_logout(request):
    """POST деавторизация"""
    logout(request)
    return JsonResponse({'status': 'success'})


@require_http_methods(["GET"])
def user_profile(request):
    """GET полей пользователя (личный кабинет)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Не авторизован'}, status=401)
    
    return JsonResponse({
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'is_staff': request.user.is_staff
    })


@csrf_exempt
@require_http_methods(["PUT"])
def update_user(request):
    """PUT пользователя (личный кабинет)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Не авторизован'}, status=401)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    if 'email' in data:
        request.user.email = data['email']
    if 'first_name' in data:
        request.user.first_name = data['first_name']
    if 'last_name' in data:
        request.user.last_name = data['last_name']
    if 'password' in data and data['password']:
        request.user.set_password(data['password'])
    
    request.user.save()
    return JsonResponse({'status': 'success', 'username': request.user.username})

@action(detail=True, methods=['put'])
def update_currency(self, request, pk=None):
    """Обновление валюты в заявке"""
    account_request = self.get_object()
    if account_request.creator != request.user:
        return Response({'error': 'Только создатель может изменять заявку'}, status=403)
    
    if account_request.status != 'DRAFT':
        return Response({'error': 'Можно изменять только черновик'}, status=400)
    
    currency_code = request.data.get('currency_code', '')
    
    # Валидация: только 3 цифры
    if len(currency_code) != 3 or not currency_code.isdigit():
        return Response({'error': 'Код валюты должен содержать 3 цифры'}, status=400)
    
    account_request.currency_code = currency_code
    account_request.save()
    
    # Генерируем новый номер счета
    import random
    random_digits = str(random.randint(10000000, 99999999))
    account_request.assigned_account_number = f"40802{currency_code}{random_digits}"
    account_request.save()
    
    return Response({
        'status': 'success',
        'currency_code': currency_code,
        'assigned_account_number': account_request.assigned_account_number
    })