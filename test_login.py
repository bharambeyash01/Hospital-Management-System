"""
Quick automated test for login routes, authentication, and dashboard redirects.
Run: python test_login.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms_project.settings')
django.setup()

from django.test import Client
from hospital.models import CustomUser, Patient, Appointment, Payment

c = Client()
errors = []

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        errors.append(label)

print("\n=== AUTH & ROUTING TESTS ===")

# Test 1: Unauthenticated /dashboard/ redirects to login with ?next=
r = c.get('/dashboard/')
check("Unauth /dashboard/ → 302", r.status_code == 302)
loc = r.get('Location', '')
check("Redirect includes /login or login url", 'login' in loc.lower() or loc == '/login/', detail=f"Got: {loc}")

# Test 2: Login page accessible at root
r = c.get('/')
check("GET / → 200", r.status_code == 200)

# Test 3: /login/ alias works
r = c.get('/login/')
check("GET /login/ → 200", r.status_code == 200)

# Test 4: Bad credentials don't crash
r = c.post('/', {'username': 'nonexistent', 'password': 'badpass'})
check("POST / bad creds → 200 (shows form again)", r.status_code == 200)

print("\n=== ROLE-BASED DASHBOARD TESTS ===")

# Test 5: Receptionist → receptionist_dashboard
recept = CustomUser.objects.filter(is_receptionist=True).first()
if recept:
    c2 = Client()
    c2.force_login(recept)
    r = c2.get('/dashboard/')
    check(f"Receptionist ({recept.username}) /dashboard/ → 302", r.status_code == 302)
    check("Redirects to receptionist_dashboard", 'receptionist' in r.get('Location', ''), detail=r.get('Location', ''))
else:
    print("  [SKIP] No receptionist user in DB")

# Test 6: Main doctor → admin_dashboard
main_doc = CustomUser.objects.filter(is_main_doctor=True).first()
if main_doc:
    c3 = Client()
    c3.force_login(main_doc)
    r = c3.get('/dashboard/')
    check(f"Main Doctor ({main_doc.username}) /dashboard/ → 302", r.status_code == 302)
    check("Redirects to admin_dashboard", 'admin' in r.get('Location', ''), detail=r.get('Location', ''))
else:
    print("  [SKIP] No main doctor in DB")

# Test 7: Working doctor → doctor_dashboard
work_doc = CustomUser.objects.filter(is_working_doctor=True).first()
if work_doc:
    c4 = Client()
    c4.force_login(work_doc)
    r = c4.get('/dashboard/')
    check(f"Working Doctor ({work_doc.username}) /dashboard/ → 302", r.status_code == 302)
    check("Redirects to doctor_dashboard", 'doctor' in r.get('Location', ''), detail=r.get('Location', ''))
else:
    print("  [SKIP] No working doctor in DB")

print("\n=== RECEPTIONIST PERMISSION TESTS ===")

if recept:
    c2 = Client()
    c2.force_login(recept)
    
    # reception_desk accessible
    r = c2.get('/dashboard/receptionist/desk/')
    check("Receptionist can access reception_desk", r.status_code == 200)

    # daily_report accessible
    r = c2.get('/dashboard/receptionist/daily-report/')
    check("Receptionist can access daily_report", r.status_code == 200)

print("\n=== MAIN DOCTOR PERMISSION TESTS ===")

if main_doc:
    c3 = Client()
    c3.force_login(main_doc)
    
    # reception_desk accessible to main doctor
    r = c3.get('/dashboard/receptionist/desk/')
    check("Main doctor can access reception_desk", r.status_code == 200)

    # admin dashboard
    r = c3.get('/dashboard/admin/')
    check("Main doctor can access admin_dashboard", r.status_code == 200)

    # financial reports
    r = c3.get('/dashboard/admin/finance/')
    check("Main doctor can access financial_reports", r.status_code == 200)

print("\n=== APPOINTMENT FORM VALIDATION ===")

from hospital.forms import AppointmentForm
from hospital.models import Patient

# Check that main doctor appears in AppointmentForm doctor queryset
if main_doc:
    form = AppointmentForm()
    doctors_qs = list(form.fields['assigned_doctor'].queryset)
    check("Main doctor in AppointmentForm queryset", main_doc in doctors_qs,
          detail=f"Doctors: {[str(d) for d in doctors_qs]}")

print("\n=== SUMMARY ===")
if errors:
    print(f"  FAILED: {len(errors)} test(s)")
    for e in errors:
        print(f"    - {e}")
else:
    print("  All tests passed!")
