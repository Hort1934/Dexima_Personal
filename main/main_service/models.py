import os
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
from django.core.validators import EmailValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.core.exceptions import ValidationError
from phonenumber_field.phonenumber import PhoneNumber
from django.db.models import JSONField


def validate_phone_number(value):
    try:
        phone_number = PhoneNumber.from_string(value)
        if not phone_number.is_valid():
            raise ValidationError("Invalid phone number format.")
    except Exception:
        raise ValidationError("Invalid phone number format.")


MALE = "M"
FEMALE = "F"
GENDER_CHOICES = [(MALE, "Male"), (FEMALE, "Female")]

# ICON_CHOICES = (
#     ('static/images/profile_icons/man_1.png', 'man_1'),
#     ('static/images/profile_icons/man_2.png', 'man_2'),
# )
ICON_CHOICES = [
    ("man_1.png", "man_1"),
    ("woman_1.png", "woman_1"),
    ("man_2.png", "man_2"),
    ("woman_2.png", "woman_2"),
    ("man_3.png", "man_3"),
    ("man_4.png", "man_4"),
    ("woman_3.png", "woman_3"),
    ("man_5.png", "man_5"),
    ("woman_4.png", "woman_4"),
    ("man_6.png", "man_6"),
    ("woman_5.png", "woman_5"),
    ("man_7.png", "man_7"),
]


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    icon = models.CharField(
        max_length=40, choices=ICON_CHOICES, blank=False, null=False
    )

    first_name = models.CharField(max_length=40, null=True, blank=True)
    last_name = models.CharField(max_length=40, null=True, blank=True)
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=False, null=False
    )
    verification_code = models.CharField(max_length=32, blank=True, null=True)
    email = models.EmailField(unique=True, validators=[EmailValidator], blank=False)
    email_verified = models.BooleanField(default=False)
    phone_number = PhoneNumberField(
        blank=True, default="", validators=[validate_phone_number]
    )
    phone_number_verified = models.BooleanField(default=False)
    num_of_backtesting = models.IntegerField(default=5)
    num_of_optimization = models.IntegerField(default=1)
    num_of_ats = models.IntegerField(default=1)
    backtesting_in_basket = models.IntegerField(default=0)
    optimization_in_basket = models.IntegerField(default=0)
    selected_pair = models.CharField(max_length=30, default="BTCUSDT")
    selected_exchange = models.CharField(max_length=30, blank=True, null=True)
    selected_strategy = models.CharField(max_length=30, blank=True, null=True)
    total_amount_to_pay = models.IntegerField(default=0)
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, null=True, blank=True
    )
    minimal_investment = models.FloatField(default=0)
    is_active = models.BooleanField(default=False)


class BinanceApiCredentials(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    hashed_api_key = models.CharField(max_length=255)
    hashed_secret_key = models.CharField(max_length=255)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, unique=True)
    permissions = models.JSONField()


class BybitApiCredentials(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    hashed_api_key = models.CharField(max_length=255)
    hashed_secret_key = models.CharField(max_length=255)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, unique=True)
    permissions = models.JSONField()


def image_file_path(instance, filename):
    _, extension = os.path.splitext(filename)

    filename = f"{slugify(instance.user)}-{uuid.uuid4()}.{extension}"

    return os.path.join("uploads/", filename)


class SupportRequest(models.Model):
    TOPIC_CHOICES = [
        ("connection", "Connection of trading bot"),
        ("payment", "Payment issues"),
        ("other", "Other"),
    ]
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255, choices=TOPIC_CHOICES)
    message = models.TextField()
    photo = models.ImageField(null=True, upload_to=image_file_path)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Support Request ({self.subject}) - {self.created_at}"


class Strategy(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField()
    high_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    low_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    grid_step = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    grids = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    days_of_backtest = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    interval = models.FloatField(null=True, blank=True)
    start_balance = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    setting1 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    setting2 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    setting3 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    setting4 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    setting5 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )


class BacktestAndOptimizationHistory(models.Model):
    user_id = models.UUIDField(default=uuid.uuid4)
    date = models.DateTimeField(auto_now_add=True)
    asset = models.CharField(max_length=255)
    strategy = models.CharField(max_length=255)
    # 184-AddExchangeToDb
    exchange = models.CharField(max_length=255, default="bybit")
    # 184-AddExchangeToDb
    activity = models.CharField(max_length=15)
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    pnl = models.CharField(max_length=255)
    data = JSONField()

    # 57-iterationsAndStatusesForBacktestAndOptimizationHistory
    STATUS_CHOICES = (
        ("created", "Created"),
        ("success", "Success"),
        ("processing", "Processing"),
        ("failed", "Failed"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    progress = models.IntegerField(default=0)
    final_progress_number = models.IntegerField(default=100)


class Payment(models.Model):
    STATUS_CHOICES = (
        ("success", "Success"),
        ("processing", "Processing"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="payments"
    )
    start_date = models.DateTimeField(auto_now_add=True)  # Дата начала транзакции
    end_date = models.DateTimeField()  # Дата окончания транзакции
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES
    )  # Статус транзакции
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Сумма оплаты

    def __str__(self):
        return f"Payment for {self.user.username} - {self.amount} ({self.status})"


class Statuses(models.Model):
    STATUS_CHOICES = (
        ("VIP", "VIP"),
        ("BASIC", "BASIC"),
        ("PRO", "PRO"),
        ("TRIAL", "TRIAL"),  # Добавленный статус "Trial"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    max_ats_count = models.IntegerField()
    max_backtests = models.IntegerField()
    max_optimizations = models.IntegerField()
    backtest_and_optimization_duration_days = models.IntegerField()
    cost = models.CharField(max_length=255, choices=STATUS_CHOICES)
    max_investment = models.IntegerField(default=100)


class UserStatus(models.Model):
    STATUS_CHOICES = (
        ("VIP", "VIP"),
        ("BASIC", "BASIC"),
        ("PRO", "PRO"),
        ("TRIAL", "TRIAL"),  # Добавленный статус "Trial"
    )

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="user_statuses"
    )
    status = models.ForeignKey(
        Statuses, on_delete=models.CASCADE, related_name="statuses"
    )
    max_investment = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # Максимальная инвестиция
    max_ats_count = models.IntegerField()  # Количество доступных АТС одновременно
    max_backtests = models.IntegerField()  # Количество доступных бектестов
    max_optimizations = models.IntegerField()  # Количество доступных оптимизаций
    backtest_and_optimization_duration_days = (
        models.IntegerField()
    )  # Длительность доступа к бектестам в днях
    assigned_at = models.DateTimeField(auto_now_add=True)  # Время присвоения статуса
    expiration_date = models.DateTimeField()  # Время окончания действия статуса
    payment = models.ForeignKey(
        Payment, on_delete=models.SET_NULL, null=True, related_name="user_statuses"
    )

    def __str__(self):
        return f"{self.user.username} - {self.status}"
