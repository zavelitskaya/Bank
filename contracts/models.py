from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class BankContract(models.Model):
    """Услуга = банковский договор"""
    CONTRACT_TYPES = [
        ('RKO', 'Расчетно-кассовое обслуживание'),
        ('SALARY', 'Зарплатный проект'),
        ('ACQUIRING', 'Эквайринг'),
    ]
    
    contract_number = models.CharField(max_length=50, unique=True)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPES)
    counterparty_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image_key = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.contract_number} - {self.counterparty_name}"


class AccountRequest(models.Model):
    """Заявка на открытие счета"""
    STATUS_CHOICES = [
        ('DRAFT', 'Черновик'),
        ('DELETED', 'Удалён'),
        ('SUBMITTED', 'Сформирован'),
        ('COMPLETED', 'Завершён'),
        ('REJECTED', 'Отклонён'),
    ]
    
    CURRENCY_CODES = [
        ('810', 'RUB'),
        ('840', 'USD'),
    ]
    
    status = models.CharField(max_length=20, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Пользователи
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_requests')
    moderator = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='moderated_requests')
    
    # Поля по вашей теме
    currency_code = models.CharField(max_length=3, choices=CURRENCY_CODES, default='810')
    
    # Основной договор для счета
    primary_contract = models.ForeignKey(
        BankContract, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='primary_for_requests'
    )
    
    # Поле результата (заполняется модератором)
    assigned_account_number = models.CharField(max_length=34, blank=True, null=True)
    
    def __str__(self):
        return f"Заявка #{self.id}"


class RequestedContract(models.Model):
    """Связь м-м: заявка ←→ договор (дополнительные договоры к счету)"""
    account_request = models.ForeignKey(AccountRequest, on_delete=models.CASCADE, related_name='requested_contracts')
    bank_contract = models.ForeignKey(BankContract, on_delete=models.PROTECT)
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    connection_date = models.DateField(default=timezone.now, verbose_name="Дата подключения")
    
    class Meta:
        unique_together = ['account_request', 'bank_contract']
    
    def __str__(self):
        return f"{self.bank_contract.contract_number} - {self.connection_date}"