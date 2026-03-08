from django.conf import settings
from django.db import models


class Client(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    INVOICE_TYPE_CHOICES = [
        ("hourly", "Hourly invoice"),
        ("weekly", "Weekly invoice"),
        ("fixed", "Fixed amount invoice"),
    ]

    VAT_CHOICES = [
        (0, "0%"),
        (13.5, "13.5%"),
        (25.5, "25.5%"),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    invoice_number = models.CharField(max_length=50)
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        default="hourly",
    )

    # للفواتير الأسبوعية فقط - يكتبها المستخدم بحرية
    weeks_text = models.CharField(max_length=200, blank=True, null=True)

    # لفواتير الساعات فقط
    work_hours = models.FloatField(default=0, blank=True)
    hourly_rate = models.FloatField(default=0, blank=True)

    issue_date = models.DateField()
    due_date = models.DateField()

    # السعر قبل الضريبة
    subtotal = models.FloatField(default=0)
    vat_rate = models.FloatField(default=25.5, choices=VAT_CHOICES)
    vat_amount = models.FloatField(default=0)
    total = models.FloatField(default=0)
    
    

    def save(self, *args, **kwargs):
        self.subtotal = round(float(self.work_hours or 0) * float(self.hourly_rate or 0), 2)
        vat_amount = float(self.subtotal or 0) * float(self.vat_rate or 0) / 100
        self.total = round(float(self.subtotal or 0) + vat_amount, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number