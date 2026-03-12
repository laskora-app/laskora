from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from .models import Invoice
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.conf import settings
import base64
import resend

COMPANY_NAME = "Laskora"
COMPANY_BUSINESS_ID = "1234567-8"
COMPANY_VAT_ID = "FI12345678"
COMPANY_EMAIL = "laskora.invoice@gmail.com"
COMPANY_ADDRESS = "Helsinki, Finland"


def draw_invoice_pdf(p, invoice):
    blue = HexColor("#2563EB")
    teal = HexColor("#14B8A6")
    dark = HexColor("#0F172A")
    gray = HexColor("#475569")

    # Header
    p.setFont("Helvetica-Bold", 20)
    p.setFillColor(blue)
    p.drawString(50, 800, COMPANY_NAME)

    p.setFont("Helvetica", 10)
    p.setFillColor(gray)
    p.drawString(50, 785, COMPANY_ADDRESS)
    p.drawString(50, 772, f"Business ID: {COMPANY_BUSINESS_ID}")
    p.drawString(50, 759, f"VAT ID (ALV): {COMPANY_VAT_ID}")
    p.drawString(50, 746, f"Email: {COMPANY_EMAIL}")

    # Invoice title
    p.setFillColor(dark)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(400, 800, "INVOICE")

    p.setFont("Helvetica", 11)
    p.drawString(400, 780, f"Number: {invoice.invoice_number}")
    p.drawString(400, 764, f"Issue Date: {invoice.issue_date}")
    p.drawString(400, 748, f"Due Date: {invoice.due_date}")

    # Client box
    p.setStrokeColor(teal)
    p.rect(50, 655, 500, 65, stroke=1, fill=0)

    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(dark)
    p.drawString(60, 700, "Bill To")

    p.setFont("Helvetica", 11)
    p.drawString(60, 682, f"Client: {invoice.client.name}")
    p.drawString(60, 666, f"Email: {invoice.client.email or '-'}")

    # Work / invoice details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 625, "Invoice Details")

    p.setFont("Helvetica", 11)

    if invoice.invoice_type == "hourly":
        p.drawString(60, 607, "Type: Hourly invoice")
        p.drawString(60, 589, f"Work Hours: {invoice.work_hours:.2f}")
        p.drawString(60, 571, f"Hourly Rate: {invoice.hourly_rate:.2f} EUR")

    elif invoice.invoice_type == "weekly":
        p.drawString(60, 607, "Type: Weekly invoice")
        p.drawString(60, 589, f"Weeks: {invoice.weeks_text or '-'}")

    elif invoice.invoice_type == "fixed":
        p.drawString(60, 607, "Type: Fixed amount invoice")

    # Amount summary
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 535, "Amount Summary")

    p.setStrokeColor(blue)
    p.line(50, 525, 550, 525)

    p.setFont("Helvetica", 11)
    p.setFillColor(dark)

    p.drawString(60, 505, "Subtotal")
    p.drawRightString(530, 505, f"{invoice.subtotal:.2f} EUR")

    p.drawString(60, 485, f"ALV ({invoice.vat_rate}%)")
    p.drawRightString(530, 485, f"{invoice.vat_amount:.2f} EUR")

    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(blue)
    p.drawString(60, 455, "Total")
    p.drawRightString(530, 455, f"{invoice.total:.2f} EUR")

    # Footer
    p.setFillColor(gray)
    p.setFont("Helvetica", 10)
    p.drawString(50, 100, "Thank you for your business.")
    p.drawString(50, 85, "Laskora - Simple invoicing for modern businesses.")

@login_required
def send_invoice_email(request, invoice_id):
    invoice = Invoice.objects.get(id=invoice_id, owner=request.user)

    if not invoice.client.email:
        return HttpResponse("Client has no email address.")

    response = HttpResponse(content_type="application/pdf")
    p = canvas.Canvas(response)
    draw_invoice_pdf(p, invoice)
    p.showPage()
    p.save()

    pdf_file = response.content
    resend.api_key = settings.RESEND_API_KEY

    try:
        resend.Emails.send({
            "from": "Laskora <onboarding@resend.dev>",
            "to": ["laskora.invoice@gmail.com"],
            "subject": f"Invoice {invoice.invoice_number}",
            "html": "<p>Please find your invoice attached.</p>",
            "attachments": [
                {
                    "filename": f"invoice_{invoice.invoice_number}.pdf",
                    "content": base64.b64encode(pdf_file).decode("utf-8"),
                }
            ],
        })
    except Exception as e:
        print(e)

    return redirect("/invoices/")

from django.shortcuts import render, redirect
from .models import Client, Invoice
@login_required
def create_invoice_page(request):
    clients = Client.objects.all()

    if request.method == "POST":
        action = request.POST.get("action")
        company_name = request.POST.get("company_name", "").strip()
        person_name = request.POST.get("person_name", "").strip()
        customer_email = request.POST.get("customer_email", "").strip()

        invoice_number = request.POST.get("invoice_number")
        issue_date = request.POST.get("invoice_date")
        due_date = request.POST.get("due_date")

        quantity_list = request.POST.getlist("quantity[]")
        unit_price_list = request.POST.getlist("unit_price[]")
        vat_rate_list = request.POST.getlist("vat_rate[]")
        discount_list = request.POST.getlist("discount[]")

        client_name = company_name if company_name else person_name

        if not client_name:
            return HttpResponse("Client name is required")

        client, created = Client.objects.get_or_create(
            owner=request.user,
            name=client_name,
            defaults={"email": customer_email if customer_email else None}
)

        if customer_email and not client.email:
            client.email = customer_email
            client.save()

        work_hours = float(quantity_list[0]) if quantity_list and quantity_list[0] else 0
        hourly_rate = float(unit_price_list[0]) if unit_price_list and unit_price_list[0] else 0
        vat_rate = float(vat_rate_list[0]) if vat_rate_list and vat_rate_list[0] else 0
        discount = float(discount_list[0]) if discount_list and discount_list[0] else 0

        subtotal = work_hours * hourly_rate
        subtotal = subtotal - (subtotal * discount / 100)

        total = float(subtotal) if subtotal else 0
        if total == 0:
            total = float(work_hours) * float(hourly_rate)

        vat_amount = total * (float(vat_rate) / 100)
        total_with_vat = total + vat_amount

        invoice = Invoice.objects.create(
            owner=request.user,
            client=client,
            invoice_number=invoice_number,
            issue_date=issue_date,
            due_date=due_date,
            work_hours=work_hours,
            hourly_rate=hourly_rate,
            subtotal=total,
            vat_rate=vat_rate,
            total=total_with_vat,
        )

        if action == "send":
             return redirect(f"/invoice/{invoice.id}/send/")

        return redirect("/invoices/") 
    
    return render(request, "billing/create_invoice.html", {"clients": clients})
@login_required
def dashboard(request):
    invoices = Invoice.objects.all().order_by('-id')[:5]
    clients_count = Client.objects.count()
    invoices_count = Invoice.objects.count()
    total_revenue = sum(invoice.total for invoice in Invoice.objects.all())

    context = {
        "invoices": invoices,
        "clients_count": clients_count,
        "invoices_count": invoices_count,
        "total_revenue": total_revenue,
    }

    return render(request, "billing/dashboard.html", context)
def invoices_list(request):
    invoices = Invoice.objects.all().order_by('-id')
    return render(request, "billing/invoices_list.html", {"invoices": invoices})

from django.shortcuts import redirect
@login_required
def delete_invoice(request, invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    invoice.delete()
    return redirect("/invoices/")
@login_required
def edit_invoice(request, invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    clients = Client.objects.all()

    if request.method == "POST":
        invoice.client_id = request.POST.get("client")
        invoice.invoice_number = request.POST.get("invoice_number")
        invoice.issue_date = request.POST.get("issue_date")
        invoice.due_date = request.POST.get("due_date")
        invoice.work_hours = request.POST.get("work_hours") or 0
        invoice.hourly_rate = request.POST.get("hourly_rate") or 0
        invoice.subtotal = request.POST.get("subtotal") or 0
        invoice.vat_rate = request.POST.get("vat_rate") or 0
        invoice.save()
        return redirect("/invoices/")

    return render(request, "billing/edit_invoice.html", {
        "invoice": invoice,
        "clients": clients,
    })
def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("/dashboard/")
    else:
        form = UserCreationForm()

    return render(request, "billing/signup.html", {"form": form})


from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

def login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/dashboard/')
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'billing/login.html')

def logout_view(request):
    logout(request)
    return redirect('/login/')
def home_page(request):
    return render(request, 'billing/home.html')

@login_required
def invoice_pdf(request, invoice_id):
    invoice = Invoice.objects.get(id=invoice_id, owner=request.user)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="invoice_{invoice.invoice_number}.pdf"'

    p = canvas.Canvas(response)
    draw_invoice_pdf(p, invoice)
    p.showPage()
    p.save()

    return response