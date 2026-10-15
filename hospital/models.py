import re
import urllib.parse
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# 1. Custom User Model for RBAC (Role-Based Access Control)
class CustomUser(AbstractUser):
    # Boolean fields to identify user roles
    is_main_doctor = models.BooleanField(default=False)
    is_working_doctor = models.BooleanField(default=False)
    is_receptionist = models.BooleanField(default=False)
    
    # Extra profile details
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True, null=True) # For doctors

    def save(self, *args, **kwargs):
        if self.is_main_doctor or self.is_superuser:
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

# 2. Patient Model (Managed by Receptionist)
class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    contact_number = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.contact_number}"

# 3. Appointment & Treatment Model
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending (Waiting for Doctor)'),
        ('In Progress', 'In Progress (With Doctor)'),
        ('Completed', 'Completed (Bill Set)'),
        ('Paid', 'Paid (Settled)'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    assigned_doctor = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to=models.Q(is_working_doctor=True) | models.Q(is_main_doctor=True)
    )
    date_assigned = models.DateTimeField(auto_now_add=True)
    
    # Future Scheduling
    scheduled_date = models.DateField(default=timezone.now)
    scheduled_time = models.TimeField(default=timezone.now)
    
    symptoms_noted = models.TextField(help_text="Noted by Receptionist or Doctor")
    
    # Filled by the Doctor
    doctor_notes = models.TextField(blank=True, null=True)
    prescription = models.TextField(blank=True, null=True)
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        pt_name = self.patient.first_name if self.patient else "Deleted Patient"
        doc_name = self.assigned_doctor.last_name if self.assigned_doctor else "Deleted Doctor"
        return f"Appt #{self.id} - {pt_name} with Dr. {doc_name}"

    @property
    def get_whatsapp_url(self):
        if not self.patient:
            return "#"
        clean_num = re.sub(r'\D', '', str(self.patient.contact_number))
        if len(clean_num) == 10:
            clean_num = "91" + clean_num
        amount = self.bill_amount
        if hasattr(self, 'payment_details') and self.payment_details and self.payment_details.amount_paid:
            amount = self.payment_details.amount_paid
        message = (
            f"Hello {self.patient.first_name},\n\n"
            f"Your payment of ₹{amount} for Appointment #{self.id} has been received successfully.\n\n"
            f"Thank you for choosing our Hospital!"
        )
        encoded_message = urllib.parse.quote(message)
        return f"https://wa.me/{clean_num}?text={encoded_message}"

# 4. Payment/Billing Model (Managed by Receptionist)
class Payment(models.Model):
    PAYMENT_STATUS = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
    ]
    
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='payment_details')
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Unpaid')
    payment_date = models.DateTimeField(blank=True, null=True)
    processed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to=models.Q(is_receptionist=True) | models.Q(is_main_doctor=True) | models.Q(is_superuser=True)
    )

    def __str__(self):
        pt_name = str(self.appointment.patient) if self.appointment and self.appointment.patient else "Deleted Patient"
        return f"Bill #{self.id} - {pt_name} - {self.status}"
        
    @property
    def get_whatsapp_url(self):
        if self.appointment:
            return self.appointment.get_whatsapp_url
        return "#"

# 5. Expense Tracking Model (Managed by Main Doctor)
class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Salary', 'Salary/Payroll'),
        ('Equipment', 'Medical Equipment'),
        ('Utilities', 'Utilities & Rent'),
        ('Supplies', 'Consumable Supplies'),
        ('Other', 'Other/Miscellaneous'),
    ]
    
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    date_incurred = models.DateField(default=timezone.now)
    recorded_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to=models.Q(is_main_doctor=True) | models.Q(is_superuser=True)
    )

    def __str__(self):
        return f"{self.title} - ₹{self.amount} ({self.category})"