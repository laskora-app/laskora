from django.contrib import admin
from django.utils.html import format_html
from .models import Client, Invoice


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "owner")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "invoice_type",
        "client",
        "weeks_text",
        "work_hours",
        "hourly_rate",
        "subtotal",
        "vat_rate",
        "vat_amount",
        "total",
        "send_invoice_link",
    )

    def send_invoice_link(self, obj):
        return format_html(
            '<a href="/invoice/{}/send/" style="color:white;background:#2563EB;padding:6px 10px;border-radius:6px;text-decoration:none;">Send Invoice</a>',
            obj.id
        )

    send_invoice_link.short_description = "Send Invoice"