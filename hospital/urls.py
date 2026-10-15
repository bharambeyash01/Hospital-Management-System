from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login_alias'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/finance/', views.financial_reports, name='financial_reports'),
    path('dashboard/admin/print-all-records/', views.print_all_records, name='print_all_records'),
    path('dashboard/admin/expenses/', views.manage_expenses, name='manage_expenses'),
    
    # NEW FEATURE: Profile & Password Management
    path('profile/', views.edit_profile, name='edit_profile'),
    path('profile/password/', views.change_password, name='change_password'),
    
    # NEW FEATURE: Export to CSV
    path('dashboard/admin/export-csv/', views.export_financials_csv, name='export_financials_csv'), 
    
    # Doctor URLs
    path('dashboard/doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/doctor/queue/', views.doctor_queue, name='doctor_queue'),
    
    # NEW FEATURE: Print Prescription
    path('dashboard/doctor/prescription/<int:appt_id>/', views.generate_prescription, name='generate_prescription'), 
    
    # Receptionist URLs
    path('dashboard/receptionist/', views.receptionist_dashboard, name='receptionist_dashboard'),
    path('dashboard/receptionist/desk/', views.reception_desk, name='reception_desk'),
    path('dashboard/receptionist/daily-report/', views.daily_report, name='daily_report'),
    
    # NEW FEATURE: Detailed Patient Profile
    path('patient/<int:patient_id>/', views.patient_profile, name='patient_profile'), 
    
    # Billing Actions
    path('payment/process/<int:appt_id>/', views.process_payment, name='process_payment'),
    path('payment/receipt/<int:appt_id>/', views.generate_receipt, name='generate_receipt'),
]