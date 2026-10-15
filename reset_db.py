import os
import django

# 1. Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms_project.settings')
django.setup()

# 2. Import your models
from hospital.models import Patient, Appointment, Payment, Expense

def clear_hms_data():
    print("========================================")
    print("      HMS DATABASE CLEANUP UTILITY      ")
    print("========================================")
    print("WARNING: This will permanently delete ALL:")
    print(" - Patients")
    print(" - Appointments & Treatment Histories")
    print(" - Bills & Payments")
    print(" - Expenses")
    print("----------------------------------------")
    
    # Require strict confirmation
    confirm = input("Type 'YES' to confirm deletion: ")
    
    if confirm == 'YES':
        print("\n⏳ Clearing database...")
        
        # Step 1: Clean up any orphaned Appointments, Payments, and Expenses
        Payment.objects.all().delete()
        Appointment.objects.all().delete()
        Expense.objects.all().delete()
        
        # Step 2: Delete all Patients (this would normally cascade, but Step 1 ensures 100% cleanliness)
        patients_deleted, _ = Patient.objects.all().delete()
        
        print("\n✅ SUCCESS: Database has been cleared!")
        print(f"🗑️  Cleared {patients_deleted} Patient records and all associated treatments.")
        print("ℹ️  NOTE: Your Staff (Doctors, Receptionists, Admins) were NOT deleted.")
    else:
        print("\n❌ Operation cancelled. Nothing was deleted.")

if __name__ == '__main__':
    clear_hms_data()