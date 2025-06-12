# booking/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template

import mysql.connector
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import razorpay
from xhtml2pdf import pisa

# Razorpay config
razorpay_client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_KEY_SECRET"))

DB_CONFIG = dict(
    host="localhost",
    user="root",
    password="root",
    database="laxmifarmhouse"
)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def booking_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        members = request.POST.get("members")
        farmhouse = request.POST.get("farmhouse")
        check_in = request.POST.get("checkin")
        check_out = request.POST.get("checkout")
        advance = request.POST.get("advance")

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM customer WHERE farmhouse=%s AND check_in=%s", (farmhouse, check_in))
        if cursor.fetchone():
            messages.error(request, "❌ Selected check-in date is NOT available!")
            return redirect('booking')

        cursor.execute("""
            INSERT INTO customer (name, phone, members, farmhouse, check_in, check_out, advance)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, phone, members, farmhouse, check_in, check_out, advance))
        db.commit()
        messages.success(request, "✅ Booking successful! Welcome to Laxmi Farmhouse.")
        return redirect('home')

    return render(request, 'booking.html')

@csrf_exempt
def create_order(request):
    if request.method == "POST":
        amount = int(request.POST["advance"]) * 100
        payment = razorpay_client.order.create({"amount": amount, "currency": "INR", "payment_capture": "1"})
        return JsonResponse(payment)

@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        data = request.body.decode("utf-8")
        try:
            razorpay_client.utility.verify_payment_signature(eval(data))
            return JsonResponse({"status": "success"})
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"status": "failed"})

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

def admin_dashboard(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    db = get_db()
    cursor = db.cursor()

    if start and end:
        cursor.execute("SELECT * FROM customer WHERE farmhouse='AK Farmhouse' AND check_in BETWEEN %s AND %s", (start, end))
        ak_bookings = cursor.fetchall()
        cursor.execute("SELECT * FROM customer WHERE farmhouse='Malusare Farmhouse' AND check_in BETWEEN %s AND %s", (start, end))
        malusare_bookings = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM customer WHERE farmhouse='AK Farmhouse'")
        ak_bookings = cursor.fetchall()
        cursor.execute("SELECT * FROM customer WHERE farmhouse='Malusare Farmhouse'")
        malusare_bookings = cursor.fetchall()

    return render(request, 'admin.html', {
        'ak_bookings': ak_bookings,
        'malusare_bookings': malusare_bookings,
        'month_list': [],
    })

def download_excel(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    db = get_db()
    cursor = db.cursor()

    if start and end:
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM customer WHERE farmhouse = 'AK Farmhouse' AND check_in BETWEEN %s AND %s", (start, end))
        ak_data = cursor.fetchall()
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM customer WHERE farmhouse = 'Malusare Farmhouse' AND check_in BETWEEN %s AND %s", (start, end))
        malusare_data = cursor.fetchall()
    else:
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM customer WHERE farmhouse = 'AK Farmhouse'")
        ak_data = cursor.fetchall()
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM customer WHERE farmhouse = 'Malusare Farmhouse'")
        malusare_data = cursor.fetchall()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame(ak_data, columns=["Name", "Phone", "Members", "Check-in", "Check-out", "Advance"]).to_excel(writer, sheet_name='AK_Farmhouse', index=False)
        pd.DataFrame(malusare_data, columns=["Name", "Phone", "Members", "Check-in", "Check-out", "Advance"]).to_excel(writer, sheet_name='Malusare_Farmhouse', index=False)

    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="farmhouse_bookings.xlsx"'
    return response

def download_pdf(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    db = get_db()
    cursor = db.cursor()

    if start and end:
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM customer WHERE farmhouse = 'AK Farmhouse' AND check_in BETWEEN %s AND %s", (start, end))
        ak_data = cursor.fetchall()
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM customer WHERE farmhouse = 'Malusare Farmhouse' AND check_in BETWEEN %s AND %s", (start, end))
        malusare_data = cursor.fetchall()
    else:
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM customer WHERE farmhouse = 'AK Farmhouse'")
        ak_data = cursor.fetchall()
        cursor.execute("SELECT name, phone, members, check_in, check_out, advance FROM customer WHERE farmhouse = 'Malusare Farmhouse'")
        malusare_data = cursor.fetchall()

    template = get_template("pdf_template.html")
    html = template.render({ 'ak_bookings': ak_data, 'malusare_bookings': malusare_data })
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="farmhouse_bookings.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    return response if not pisa_status.err else HttpResponse("Error generating PDF", status=500)

@csrf_exempt
def clear_all_bookings(request):
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM customer")
        db.commit()
        messages.success(request, "✅ All bookings have been cleared.")
    return redirect("admin_panel")

def booking_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        members = request.POST.get("members")
        farmhouse = request.POST.get("farmhouse")
        check_in = request.POST.get("checkin")
        check_out = request.POST.get("checkout")
        advance = request.POST.get("advance")

        db = get_db()
        cursor = db.cursor()

        # Check if date is already booked
        cursor.execute("SELECT * FROM customer WHERE farmhouse=%s AND check_in=%s", (farmhouse, check_in))
        if cursor.fetchone():
            messages.error(request, "❌ Selected check-in date is NOT available!")
            return redirect('booking')

        # Insert booking
        cursor.execute("""
            INSERT INTO customer (name, phone, members, farmhouse, check_in, check_out, advance)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, phone, members, farmhouse, check_in, check_out, advance))
        db.commit()

        messages.success(request, "✅ Booking successful! Welcome to Laxmi Farmhouse.")
        return redirect('home')

    return render(request, 'booking.html')

