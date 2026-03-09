from django.contrib import admin
from django.urls import path
from billing import views
from django.conf import settings
from django.conf.urls.static import static
from billing.views import invoice_pdf, send_invoice_email, create_invoice_page, dashboard, invoices_list, delete_invoice, edit_invoice, signup_view, login_view
from billing.views import logout_view, signup_view, login_view
urlpatterns = [
    path('', views.home_page, name='home'),
    path('admin/', admin.site.urls),
    path('invoice/<int:invoice_id>/pdf/', invoice_pdf),
    path('invoice/<int:invoice_id>/send/', send_invoice_email),
    path('invoice/<int:invoice_id>/delete/', delete_invoice),
    path('create-invoice/', create_invoice_page),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('invoices/', invoices_list),
    path('invoice/<int:invoice_id>/edit/', edit_invoice),
    path('signup/', signup_view),
    path('login/', login_view),
    path('logout/', logout_view),
]

urlpatterns += static(
    settings.STATIC_URL,
    document_root=settings.BASE_DIR / "billing" / "static"
)