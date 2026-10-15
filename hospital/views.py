import csv
import json
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Sum, Q, Count
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import CustomLoginForm, PatientForm, AppointmentForm, UserProfileForm, ExpenseForm
from .models import Patient, Appointment, CustomUser, Payment, Expense

# --- Authentication Views ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    next_url = request.POST.get('next') or request.GET.get('next')
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if next_url and next_url != 'None':
                return redirect(next_url)
            return redirect('dashboard')
    else:
        form = CustomLoginForm()
        
    return render(request, 'login.html', {'form': form, 'next': next_url})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was successfully updated!')
            return redirect('edit_profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('edit_profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.is_main_doctor or request.user.is_superuser:
        return redirect('admin_dashboard')
    elif request.user.is_working_doctor:
        return redirect('doctor_dashboard')
    elif request.user.is_receptionist:
        return redirect('receptionist_dashboard')
    else:
        return render(request, 'base.html')

@login_required
def patient_profile(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    appointments = patient.appointments.all().order_by('-date_assigned')
    return render(request, 'patient_profile.html', {'patient': patient, 'appointments': appointments})

# --- Main Doctor (Admin) Dashboards ---
@login_required
def admin_dashboard(request):
    if not (request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
    
    valid_patients = Patient.objects.all()
    
    total_patients = valid_patients.count()
    doctors_count = CustomUser.objects.filter(Q(is_working_doctor=True) | Q(is_main_doctor=True)).count()
    
    pending_appointments = Appointment.objects.filter(status='Pending', patient__in=valid_patients).count()
    completed_appointments = Appointment.objects.filter(status__in=['Completed', 'Paid']).count()
    
    recent_patients = valid_patients.order_by('-id')[:5]
    
    # Use timezone-aware datetime to prevent DateTimeField RuntimeWarning
    seven_days_ago = timezone.localtime() - timedelta(days=7)
    doctors_list = CustomUser.objects.filter(
        Q(is_working_doctor=True) | Q(is_main_doctor=True)
    ).annotate(
        patients_treated=Count('appointment', filter=Q(appointment__status__in=['Completed', 'Paid'], appointment__date_assigned__gte=seven_days_ago)),
        revenue_generated=Sum('appointment__bill_amount', filter=Q(appointment__status='Paid', appointment__date_assigned__gte=seven_days_ago))
    ).order_by('-patients_treated')

    today = timezone.localtime().date()
    chart_dates = []
    chart_revenue = []
    
    for i in range(6, -1, -1):
        target_day = today - timedelta(days=i)
        chart_dates.append(target_day.strftime("%b %d"))
        
        day_start = timezone.localtime().replace(year=target_day.year, month=target_day.month, day=target_day.day, hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # Include all paid appointments in daily revenue
        daily_rev = Appointment.objects.filter(
            status='Paid', 
            date_assigned__gte=day_start, 
            date_assigned__lt=day_end
        ).aggregate(Sum('bill_amount'))['bill_amount__sum'] or 0.00
        
        chart_revenue.append(float(daily_rev))

    context = {
        'role': 'Main Doctor',
        'total_patients': total_patients,
        'doctors_count': doctors_count,
        'pending_appointments': pending_appointments,
        'completed_appointments': completed_appointments,
        'recent_patients': recent_patients,
        'doctors_list': doctors_list,
        'chart_dates': chart_dates,
        'chart_revenue': chart_revenue,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_revenue_json': json.dumps(chart_revenue),
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
def export_financials_csv(request):
    if not (request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="hospital_financial_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Appointment ID', 'Date & Time', 'Patient Name', 'Attending Doctor', 'Amount (INR)', 'Status'])
    
    appointments = Appointment.objects.filter(status='Paid').order_by('-date_assigned')
    
    target_date_str = request.GET.get('date')
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            day_start = timezone.localtime().replace(year=target_date.year, month=target_date.month, day=target_date.day, hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            appointments = appointments.filter(
                Q(payment_details__payment_date__gte=day_start, payment_details__payment_date__lt=day_end) |
                Q(payment_details__payment_date__isnull=True, date_assigned__gte=day_start, date_assigned__lt=day_end)
            )
        except ValueError:
            pass

    for appt in appointments:
        pt_name = f"{appt.patient.first_name} {appt.patient.last_name}" if appt.patient else "Deleted Patient"
        doc_name = f"Dr. {appt.assigned_doctor.last_name}" if appt.assigned_doctor else "Deleted Doctor"
        appt_time = timezone.localtime(appt.date_assigned).strftime("%Y-%m-%d %H:%M") if appt.date_assigned else "N/A"
        
        writer.writerow([
            appt.id,
            appt_time,
            pt_name, doc_name, appt.bill_amount, appt.status
        ])
    return response

@login_required
def financial_reports(request):
    if not (request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
    
    valid_patients = Patient.objects.all()
    total_revenue = Appointment.objects.filter(status='Paid').aggregate(Sum('bill_amount'))['bill_amount__sum'] or 0.00
    total_expenses = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0.00
    net_profit = float(total_revenue) - float(total_expenses)
    
    total_patients = valid_patients.count()
    working_doctors = CustomUser.objects.filter(Q(is_working_doctor=True) | Q(is_main_doctor=True))

    context = {
        'role': 'Main Doctor', 'total_revenue': total_revenue,
        'total_expenses': total_expenses, 'net_profit': net_profit,
        'total_patients': total_patients, 'working_doctors': working_doctors,
    }
    return render(request, 'admin/financial_reports.html', context)

@login_required
def manage_expenses(request):
    if not (request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, "Expense recorded successfully.")
            return redirect('manage_expenses')
        else:
            messages.error(request, "Please correct the errors in the expense form.")
    else:
        form = ExpenseForm()
        
    expenses = Expense.objects.all().order_by('-date_incurred', '-id')
    
    context = {
        'role': 'Main Doctor', 'form': form, 'expenses': expenses
    }
    return render(request, 'admin/manage_expenses.html', context)

@login_required
def print_all_records(request):
    if not (request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
        
    today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    today_date = timezone.localtime().date() 
    
    target_date_str = request.GET.get('date')
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            today_start = timezone.localtime().replace(year=target_date.year, month=target_date.month, day=target_date.day, hour=0, minute=0, second=0, microsecond=0)
            today_date = target_date
        except ValueError:
            pass

    today_end = today_start + timedelta(days=1)
    
    appointments = Appointment.objects.filter(
        Q(date_assigned__gte=today_start, date_assigned__lt=today_end) |
        Q(scheduled_date=today_date)
    ).order_by('-date_assigned')
    
    context = {
        'today': today_date,
        'appointments': appointments,
        'main_doctor': request.user
    }
    return render(request, 'admin/print_all_records.html', context)

# --- Doctor Views ---
@login_required
def doctor_dashboard(request):
    if not (request.user.is_working_doctor or request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
        
    today = timezone.localtime().date()
    treated_appts = Appointment.objects.filter(
        assigned_doctor=request.user, 
        patient__in=Patient.objects.all()
    ).exclude(status='Pending').order_by('-id')
    
    patients_treated_count = treated_appts.count()
    pending_queue_count = Appointment.objects.filter(
        assigned_doctor=request.user,
        status='Pending',
        scheduled_date__lte=today,
        patient__in=Patient.objects.all()
    ).count()
    
    search_query = request.GET.get('search', '')
    if search_query:
        treated_appts = treated_appts.filter(
            Q(patient__first_name__icontains=search_query) | 
            Q(patient__last_name__icontains=search_query) | 
            Q(patient__contact_number__icontains=search_query)
        )

    paginator = Paginator(treated_appts, 5)
    page_number = request.GET.get('page')
    treated_appts_page = paginator.get_page(page_number)

    context = {
        'role': 'Doctor', 
        'treated_appts': treated_appts_page,
        'patients_treated_count': patients_treated_count,
        'pending_queue_count': pending_queue_count,
        'search_query': search_query,
    }
    return render(request, 'doctor/dashboard.html', context)

@login_required
def doctor_queue(request):
    if not (request.user.is_working_doctor or request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
        
    today = timezone.localtime().date()
    appointments = Appointment.objects.filter(
        assigned_doctor=request.user, 
        status='Pending',
        scheduled_date__lte=today,
        patient__in=Patient.objects.all()
    ).order_by('scheduled_date', 'scheduled_time', 'id')
    
    if request.method == 'POST':
        appt_id = request.POST.get('appointment_id')
        notes = request.POST.get('doctor_notes')
        prescription = request.POST.get('prescription')
        bill_amount_raw = request.POST.get('bill_amount')
        
        try:
            bill_amount = float(bill_amount_raw)
            if bill_amount < 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Invalid bill amount provided.")
            return redirect('doctor_queue')
            
        appt = get_object_or_404(Appointment, id=appt_id, status='Pending')
        if not (request.user.is_superuser or appt.assigned_doctor == request.user):
            messages.error(request, "You are not authorized to treat this appointment.")
            return redirect('doctor_queue')

        appt.doctor_notes = notes
        appt.prescription = prescription
        appt.bill_amount = bill_amount
        appt.status = 'Completed'
        appt.save()
        
        # Integrate Payment Model
        Payment.objects.update_or_create(
            appointment=appt,
            defaults={'amount_due': bill_amount, 'status': 'Unpaid'}
        )
        
        pt_name = appt.patient.first_name if appt.patient else "Deleted Patient"
        messages.success(request, f"Treatment completed for {pt_name}. Bill sent to Reception.")
        return redirect('doctor_queue')

    context = {'role': 'Doctor', 'appointments': appointments}
    return render(request, 'doctor/queue.html', context)

@login_required
def generate_prescription(request, appt_id):
    if not (request.user.is_working_doctor or request.user.is_main_doctor or request.user.is_receptionist or request.user.is_superuser):
        return redirect('dashboard')
        
    appointment = get_object_or_404(Appointment, id=appt_id)
    return render(request, 'doctor/prescription.html', {'appointment': appointment})

# --- Receptionist Dashboards ---
@login_required
def receptionist_dashboard(request):
    if not (request.user.is_receptionist or request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
                
    today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    today_date = timezone.localtime().date()
    
    valid_patients = Patient.objects.all()
    patients_today = valid_patients.filter(created_at__gte=today_start).count()
    
    appointments_today = Appointment.objects.filter(
        Q(date_assigned__gte=today_start) | Q(scheduled_date=today_date),
        patient__in=valid_patients
    ).count()
    
    doctors_list = CustomUser.objects.filter(Q(is_working_doctor=True) | Q(is_main_doctor=True))
    
    search_query = request.GET.get('search', '')
    if search_query:
        patients = valid_patients.filter(
            Q(first_name__icontains=search_query) | Q(last_name__icontains=search_query) | Q(contact_number__icontains=search_query)
        ).order_by('-id')
    else:
        patients = valid_patients.order_by('-id')
        
    paginator = Paginator(patients, 5)
    page_number = request.GET.get('page')
    patients_page = paginator.get_page(page_number)
    
    appointments = Appointment.objects.filter(patient__in=valid_patients).order_by('-id')[:10]
        
    context = {
        'role': 'Receptionist', 'patients': patients_page, 'appointments': appointments,
        'patients_today': patients_today, 'appointments_today': appointments_today,
        'doctors_list': doctors_list, 'search_query': search_query,
    }
    return render(request, 'receptionist/dashboard.html', context)

@login_required
def reception_desk(request):
    if not (request.user.is_receptionist or request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
        
    patient_id = request.GET.get('patient_id')
    initial_appt = {}
    if patient_id:
        try:
            p = Patient.objects.get(id=patient_id)
            initial_appt['patient'] = p.id
        except Patient.DoesNotExist:
            pass

    patient_form = PatientForm()
    appointment_form = AppointmentForm(initial=initial_appt)
    
    if request.method == 'POST':
        if 'add_patient' in request.POST:
            patient_form = PatientForm(request.POST)
            if patient_form.is_valid():
                new_patient = patient_form.save()
                messages.success(request, f"Patient {new_patient.first_name} {new_patient.last_name} registered successfully!")
                return redirect(f"{request.path}?patient_id={new_patient.id}")
            else:
                messages.error(request, "Please correct the errors in the patient form.")
        elif 'add_appointment' in request.POST:
            appointment_form = AppointmentForm(request.POST)
            if appointment_form.is_valid():
                appointment_form.save()
                messages.success(request, "Appointment booked successfully!")
                return redirect('reception_desk')
            else:
                messages.error(request, "Please correct the errors in the appointment form.")
                
    pending_bills = Appointment.objects.filter(status='Completed', patient__in=Patient.objects.all()).order_by('-id')
    
    recently_paid_bills = Appointment.objects.filter(
        status='Paid'
    ).order_by('-payment_details__payment_date', '-date_assigned')[:5]
        
    context = {
        'role': 'Receptionist', 'patient_form': patient_form,
        'appointment_form': appointment_form, 'pending_bills': pending_bills,
        'recently_paid_bills': recently_paid_bills,
    }
    return render(request, 'receptionist/reception_desk.html', context)

@login_required
def daily_report(request):
    if not (request.user.is_receptionist or request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
        
    today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    today_date = timezone.localtime().date() 
    
    target_date_str = request.GET.get('date')
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            today_start = timezone.localtime().replace(year=target_date.year, month=target_date.month, day=target_date.day, hour=0, minute=0, second=0, microsecond=0)
            today_date = target_date
        except ValueError:
            pass

    today_end = today_start + timedelta(days=1)
    
    paid_appointments = Appointment.objects.filter(
        status='Paid'
    ).filter(
        Q(payment_details__payment_date__gte=today_start, payment_details__payment_date__lt=today_end) |
        Q(payment_details__payment_date__isnull=True, date_assigned__gte=today_start, date_assigned__lt=today_end)
    ).order_by('-payment_details__payment_date', '-date_assigned')
    
    total_revenue = paid_appointments.aggregate(Sum('bill_amount'))['bill_amount__sum'] or 0.00
    
    context = {
        'today': today_date, 'paid_appointments': paid_appointments,
        'total_revenue': total_revenue, 'receptionist': request.user
    }
    return render(request, 'receptionist/daily_report.html', context)

@login_required
@require_POST
def process_payment(request, appt_id):
    if not (request.user.is_receptionist or request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
        
    appointment = get_object_or_404(Appointment, id=appt_id)
    appointment.status = 'Paid'
    appointment.save()
    
    payment, _ = Payment.objects.get_or_create(
        appointment=appointment,
        defaults={'amount_due': appointment.bill_amount}
    )
    payment.status = 'Paid'
    payment.amount_paid = appointment.bill_amount
    payment.payment_date = timezone.now()
    payment.processed_by = request.user
    payment.save()
    
    pt_name = appointment.patient.first_name if appointment.patient else "Deleted Patient"
    messages.success(request, f"Payment of ₹{appointment.bill_amount} collected for {pt_name}.")
    return redirect('reception_desk')

@login_required
def generate_receipt(request, appt_id):
    if not (request.user.is_receptionist or request.user.is_main_doctor or request.user.is_superuser):
        return redirect('dashboard')
        
    appointment = get_object_or_404(Appointment, id=appt_id)
    return render(request, 'receptionist/receipt.html', {'appointment': appointment})