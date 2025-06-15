from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from django.conf import settings

import mysql.connector
import pandas as pd
from io import BytesIO
from datetime import datetime
import razorpay
from xhtml2pdf import pisa
import json

# Razorpay client setup
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "laxmifarmhouse"
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# Page Views
def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

# Booking View
def booking_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        members = request.POST.get("members")
        farmhouse_key = request.POST.get("farmhouse")  # e.g., "ak", "malusare"
        check_in = request.POST.get("checkin")
        check_out = request.POST.get("checkout")
        advance = request.POST.get("advance")

        # FARMHOUSE MAP
        farmhouse_map = {
            "ak": {"name": "AK Farmhouse", "table": "ak_bookings"},
            "malusare": {"name": "Malusare Farmhouse", "table": "malusare_bookings"},
        }

        # ✅ Basic Validations
        if not (phone and len(phone) == 10 and phone.isdigit()):
            messages.error(request, "Invalid phone number")
            return redirect('booking')

        if not advance or int(advance) < 1000:
            messages.error(request, "Advance must be at least ₹1000")
            return redirect('booking')

        farmhouse_key = request.POST.get("farmhouse")
        print("🔍 Selected farmhouse key from form:", farmhouse_key)
        # Set correct values
        farmhouse_name = farmhouse_map[farmhouse_key]["name"]
        table = farmhouse_map[farmhouse_key]["table"]

        # DB Insert
        db = get_db()
        cursor = db.cursor()
        try:
            # Check availability
            cursor.execute(f"SELECT * FROM {table} WHERE check_in = %s", (check_in,))
            if cursor.fetchone():
                messages.error(request, "❌ Selected check-in date is NOT available!")
                return redirect('booking')

            # Insert booking
            cursor.execute(f"""
                INSERT INTO {table} (name, phone, members, farmhouse, check_in, check_out, advance)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, phone, members, farmhouse_name, check_in, check_out, advance))
            db.commit()
            messages.success(request, "✅ Booking successful! Welcome to Laxmi Farmhouse.")
            return redirect('home')
        finally:
            cursor.close()
            db.close()

    return render(request, 'booking.html')

# Razorpay Payment APIs
@csrf_exempt
def create_order(request):
    if request.method == "POST":
        amount = int(request.POST["advance"]) * 100
        payment = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": "1"
        })
        return JsonResponse(payment)

@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        try:
            razorpay_client.utility.verify_payment_signature(data)
            return JsonResponse({"status": "success"})
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"status": "failed"})

# Admin Authentication
def admin_login(request):
    if request.method == 'POST':
        if request.POST.get('username') == 'mahesh' and request.POST.get('password') == 'mahesh123':
            request.session['admin_logged_in'] = True
            messages.success(request, 'Login successful!')
            return redirect('admin_panel')
        messages.error(request, 'Invalid credentials')
    return render(request, 'admin_login.html')

def admin_logout(request):
    request.session.pop('admin_logged_in', None)
    messages.success(request, 'Logged out successfully.')
    return redirect('home')

# Admin Dashboard
def admin_dashboard(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    db = get_db()
    cursor = db.cursor()
    ak_bookings, malusare_bookings = [], []

    try:
        if start and end:
            cursor.execute("SELECT * FROM ak_bookings WHERE check_in BETWEEN %s AND %s", (start, end))
            ak_bookings = cursor.fetchall()
            cursor.execute("SELECT * FROM malusare_bookings WHERE check_in BETWEEN %s AND %s", (start, end))
            malusare_bookings = cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM ak_bookings")
            ak_bookings = cursor.fetchall()
            cursor.execute("SELECT * FROM malusare_bookings")
            malusare_bookings = cursor.fetchall()
    finally:
        cursor.close()
        db.close()

    return render(request, 'admin.html', {
        'ak_bookings': ak_bookings,
        'malusare_bookings': malusare_bookings,
        'start_date': start,
        'end_date': end,
    })

# Excel Report
def download_excel(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    db = get_db()
    cursor = db.cursor()

    if start and end:
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM ak_bookings WHERE check_in BETWEEN %s AND %s", (start, end))
        ak_data = cursor.fetchall()
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM malusare_bookings WHERE check_in BETWEEN %s AND %s", (start, end))
        malusare_data = cursor.fetchall()
    else:
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM ak_bookings")
        ak_data = cursor.fetchall()
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM malusare_bookings")
        malusare_data = cursor.fetchall()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame(ak_data, columns=["Name", "Phone", "Members", "Check-in", "Check-out", "Advance"]).to_excel(writer, sheet_name='AK_Farmhouse', index=False)
        pd.DataFrame(malusare_data, columns=["Name", "Phone", "Members", "Check-in", "Check-out", "Advance"]).to_excel(writer, sheet_name='Malusare_Farmhouse', index=False)

    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="farmhouse_bookings.xlsx"'
    return response

# PDF Report
def download_pdf(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    db = get_db()
    cursor = db.cursor()

    if start and end:
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM ak_bookings WHERE check_in BETWEEN %s AND %s", (start, end))
        ak_data = cursor.fetchall()
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM malusare_bookings WHERE check_in BETWEEN %s AND %s", (start, end))
        malusare_data = cursor.fetchall()
    else:
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM ak_bookings")
        ak_data = cursor.fetchall()
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM malusare_bookings")
        malusare_data = cursor.fetchall()

    template = get_template("pdf_template.html")
    html = template.render({'ak_bookings': ak_data, 'malusare_bookings': malusare_data})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="farmhouse_bookings.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    return response if not pisa_status.err else HttpResponse("Error generating PDF", status=500)

# Clear All Bookings
@csrf_exempt
def clear_all_bookings(request):
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM ak_bookings")
        cursor.execute("DELETE FROM malusare_bookings")
        db.commit()
        cursor.close()
        db.close()
        messages.success(request, "✅ All bookings have been cleared.")
    return redirect("admin")
