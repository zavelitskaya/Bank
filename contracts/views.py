from django.shortcuts import render
from datetime import date
from django.http import JsonResponse
import random
import string

def contracts_list(request):
    contracts = [
        {
            'id': 1,
            'number': 'Д-001', 
            'client': 'ООО "Центр кибернетической интеграции и облачных решений будущего"',
            'image_url': 'http://10.253.114.132:9000/public-bucket/rko.png'
        },
        {
            'id': 2,
            'client': 'ИП Иванов А.С.',
            'number': 'Д-002', 
            'image_url': 'http://10.253.114.132:9000/public-bucket/salary.png'
        },
        {
            'id': 3, 
            'client': 'ОАО "Агентство стратегического планирования и трансформации бизнес-процессов"',
            'number': 'Д-003',
            'image_url': 'http://10.253.114.132:9000/public-bucket/acquiring.png'
        }
    ]
    
    # Обработка поиска
    search_query = request.GET.get('search', '')
    if search_query:
        contracts = [contract for contract in contracts 
                    if search_query.lower() in contract['client'].lower()]
    
    # Получаем корзину из сессии
    cart = request.session.get('cart', [])
    cart_count = len(cart)
    
    return render(request, 'contracts_list.html', {
        'contracts': contracts,
        'search_query': search_query,
        'cart_count': cart_count
    })

def add_to_cart(request, contract_id):
    if request.method == 'POST':
        # Получаем текущую корзину из сессии
        cart = request.session.get('cart', [])
        
        # Добавляем договор в корзину если его там нет
        if contract_id not in cart:
            cart.append(contract_id)
            request.session['cart'] = cart
            request.session.modified = True
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Договор добавлен в корзину',
            'cart_count': len(cart)
        })
    
    return JsonResponse({'status': 'error'}, status=400)

def contract_detail(request, contract_id):
    """Детальная информация о договоре"""
    # Статические данные (позже заменим на БД)
    contracts_data = {
        1: {
            'number': 'Д-001',
            'client': 'ООО "Ромашка"',
            'service_type': 'РКО',
            'start_date': '2024-01-15',
            'end_date': '2025-01-14',
            'status': 'Активен',
            'description': 'Расчетно-кассовое обслуживание для малого бизнеса',
            'image_url': 'http://10.253.114.132:9000/public-bucket/rko.png'
        },
        2: {
            'number': 'Д-002', 
            'client': 'ИП Иванов А.С.',
            'service_type': 'Зарплатный проект',
            'start_date': '2024-02-01',
            'end_date': '2025-01-31', 
            'status': 'Активен',
            'description': 'Зарплатный проект для индивидуального предпринимателя',
            'image_url': 'http://10.253.114.132:9000/public-bucket/salary.png'
        },
        3: {
            'number': 'Д-003',
            'client': 'ОАО "Завод"', 
            'service_type': 'Эквайринг',
            'start_date': '2024-03-10',
            'end_date': '2025-03-09',
            'status': 'Активен',
            'description': 'Торговый эквайринг для розничной сети',
            'image_url': 'http://10.253.114.132:9000/public-bucket/acquiring.png'
        }
    }
    
    contract = contracts_data.get(contract_id)
    
    if not contract:
        # Если договор не найден
        return render(request, '404.html', status=404)
    
    return render(request, 'contract_detail.html', {
        'contract': contract
    })

def add_to_cart(request, contract_id):
    """Добавление договора в корзину"""
    if request.method == 'POST':
        # Получаем текущую корзину из сессии
        cart = request.session.get('cart', [])
        
        # Добавляем договор в корзину если его там нет
        if contract_id not in cart:
            cart.append(contract_id)
            request.session['cart'] = cart
            request.session.modified = True
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Договор добавлен в корзину',
            'cart_count': len(cart)
        })
    
    return JsonResponse({'status': 'error'}, status=400)

def generate_account_number():
    """Генерация номера счета"""
    return '40702810' + ''.join(random.choices(string.digits, k=12))

def cart(request):
    """Страница корзины"""
    cart_contracts = request.session.get('cart', [])
    
    contracts_data = {
        1: {
            'id': 1,
            'number': 'Д-001', 
            'client': 'ООО "Центр кибернетической интеграции и облачных решений будущего"',
            'service_type': 'РКО',
            'image_url': 'http://10.253.114.132:9000/public-bucket/rko.png'
        },
        2: {
            'id': 2,
            'client': 'ИП Иванов А.С.',
            'number': 'Д-002', 
            'service_type': 'Зарплатный проект',
            'image_url': 'http://10.253.114.132:9000/public-bucket/salary.png'
        },
        3: {
            'id': 3, 
            'client': 'ОАО "Агентство стратегического планирования и трансформации бизнес-процессов"',
            'number': 'Д-003',
            'service_type': 'Эквайринг',
            'image_url': 'http://10.253.114.132:9000/public-bucket/acquiring.png'
        }
    }
    
    cart_items = []
    for contract_id in cart_contracts:
        if contract_id in contracts_data:
            cart_items.append(contracts_data[contract_id])
    
    # Генерируем номер счета
    account_number = generate_account_number()
    
    # Получаем основной договор из сессии
    main_contract_id = request.session.get('main_contract_id')
    
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'cart_count': len(cart_contracts),
        'account_number': account_number,
        'main_contract_id': main_contract_id
    })

def set_main_contract(request, contract_id):
    """Установка основного договора для счета"""
    if request.method == 'POST':
        request.session['main_contract_id'] = contract_id
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Основной договор установлен'
        })
    
    return JsonResponse({'status': 'error'}, status=400)

def remove_from_cart(request, contract_id):
    """Удаление договора из корзины"""
    if request.method == 'POST':
        cart = request.session.get('cart', [])
        
        if contract_id in cart:
            cart.remove(contract_id)
            request.session['cart'] = cart
            request.session.modified = True
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Договор удален из корзины',
            'cart_count': len(cart)
        })
    
    return JsonResponse({'status': 'error'}, status=400)