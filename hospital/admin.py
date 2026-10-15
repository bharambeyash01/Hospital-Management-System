from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Patient, Appointment, Payment, Expense

# Registering the Custom User model with custom roles
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'first_name', 'last_name', 'is_main_doctor', 'is_working_doctor', 'is_receptionist', 'is_staff', 'is_active']
    list_filter = ['is_main_doctor', 'is_working_doctor', 'is_receptionist', 'is_staff', 'is_active']
    
    # Adding our custom fields to the admin editing screen
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Roles & Details', {'fields': ('is_main_doctor', 'is_working_doctor', 'is_receptionist', 'phone_number', 'specialization')}),
    )

class PatientAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'age', 'gender', 'contact_number', 'created_at']
    search_fields = ['first_name', 'last_name', 'contact_number']
    list_filter = ['gender', 'created_at']

class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'assigned_doctor', 'scheduled_date', 'scheduled_time', 'status', 'bill_amount']
    list_filter = ['status', 'scheduled_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'assigned_doctor__last_name', 'symptoms_noted']

class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'appointment', 'amount_due', 'amount_paid', 'status', 'payment_date', 'processed_by']
    list_filter = ['status', 'payment_date']
    search_fields = ['appointment__patient__first_name', 'appointment__patient__last_name']

class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'amount', 'category', 'date_incurred', 'recorded_by']
    list_filter = ['category', 'date_incurred']
    search_fields = ['title']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(Appointment, AppointmentAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Expense, ExpenseAdmin)