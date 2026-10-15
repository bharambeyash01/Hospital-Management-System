import re
from decimal import Decimal
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.utils import timezone
from .models import Patient, Appointment, CustomUser, Expense

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter your username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter your password'
    }))

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'age', 'gender', 'contact_number', 'address']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'age': forms.NumberInput(attrs={'placeholder': 'Age in years', 'min': 0, 'max': 130}),
            'contact_number': forms.TextInput(attrs={'placeholder': 'e.g. 9876543210'}),
            'address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Full residential address...'}),
        }

    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age is not None and (age < 0 or age > 130):
            raise forms.ValidationError("Please enter a valid age between 0 and 130.")
        return age

    def clean_contact_number(self):
        contact = self.cleaned_data.get('contact_number', '').strip()
        digits = re.sub(r'\D', '', contact)
        if len(digits) < 7 or len(digits) > 15:
            raise forms.ValidationError("Please enter a valid phone number (7 to 15 digits).")
        return contact

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient', 'assigned_doctor', 'scheduled_date', 'scheduled_time', 'symptoms_noted']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time'}),
            'symptoms_noted': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe current symptoms or reason for visit...'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter the dropdown to show BOTH Working Doctors and Main Doctors
        self.fields['assigned_doctor'].queryset = CustomUser.objects.filter(
            Q(is_working_doctor=True) | Q(is_main_doctor=True)
        )
        self.fields['patient'].queryset = Patient.objects.all().order_by('-id')
        if not self.initial.get('scheduled_date'):
            self.fields['scheduled_date'].initial = timezone.localtime().date()
        if not self.initial.get('scheduled_time'):
            self.fields['scheduled_time'].initial = timezone.localtime().strftime('%H:%M')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'specialization']

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'amount', 'category', 'date_incurred']
        widgets = {
            'date_incurred': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('date_incurred'):
            self.fields['date_incurred'].initial = timezone.localtime().date()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0.00'):
            raise forms.ValidationError("Expense amount must be greater than zero.")
        return amount