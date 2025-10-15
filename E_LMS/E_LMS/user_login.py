from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from app.EmailBackEnd import EmailBackEnd
from app.models import Users
import re,logging
from django.conf import settings

from datetime import datetime
logger = logging.getLogger(__name__)

NAME_REGEX = re.compile(r'^[A-Za-z0-9\s]+$')          # letters, numbers, spaces
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MOBILE_REGEX = re.compile(r'^[0-9]{10}$')             # exactly 10 digits
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{6,}$')  # ≥6 chars, at least 1 letter & 1 digit
DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}$')
# Student Registration
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()

        # === Validation ===
        # Empty check
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
            return redirect('register')

        # Username check
        if not NAME_REGEX.match(username):
            messages.error(request, "Username may contain only letters, numbers, and spaces.")
            return redirect('register')

        # Email check
        if not EMAIL_REGEX.match(email):
            messages.error(request, "Please enter a valid email address.")
            return redirect('register')

        # Password check
        if not PASSWORD_REGEX.match(password):
            messages.error(
                request,
                "Password must be at least 6 characters long and include both letters and numbers."
            )
            return redirect('register')

        # Email uniqueness check
        if Users.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return redirect('register')

        # Username uniqueness check
        if Users.objects.filter(username=username).exists():
            messages.error(request, 'Username already registered!')
            return redirect('register')

        # === Create the user ===
        user = Users(
            username=username,
            email=email,
            role="student"  # default role
        )
        user.set_password(password)
        user.save()

        messages.success(request, 'Student account created successfully! Please log in.')
        return redirect('login')

    return render(request, 'registration/register.html')

# Login
def doLogin(request):
    if request.method == 'POST':
        email_or_username = request.POST.get('email')
        password = request.POST.get('password')

        # Empty check
        if not email_or_username or not password:
            messages.error(request, "All fields are required.")
            return redirect('login')

        # Email check
        if not EMAIL_REGEX.match(email_or_username):
            messages.error(request, "Please enter a valid email address.")
            return redirect('login')

        user = EmailBackEnd().authenticate(request, username=email_or_username, password=password)
        if user is not None:
            # Login success
            login(request, user)
            messages.success(request, f"Welcome back, {user.username} ({user.role})")

            # Redirect based on role
            if user.role == "student":
                return redirect('home')
            elif user.role == "teacher":
                return redirect('teacher_dashboard')
            elif user.role == "admin":
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Invalid role assigned. Contact support.")
                return redirect('login')
        else:
            messages.error(request, 'Invalid credentials!')
            return redirect('login')

    return redirect('login')

# Logout
def LogoutView(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")


# Profile
@login_required
def profile(request):
    return render(request, 'registration/profile.html')

@login_required
def profile_update(request):
    user = request.user

    # Only allow student users
    if getattr(user, "role", "").lower() != "student":
        messages.error(request, "Access denied.")
        return redirect("profile")

    # Get student profile
    student = getattr(user, "student_profile", None)
    if student is None:
        messages.error(request, "Student profile not found.")
        return redirect("profile")

    if request.method == 'POST':
        # Collect inputs
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        password = request.POST.get('password') or ''
        contact_no = (request.POST.get('contact_no') or '').strip()
        address = (request.POST.get('address') or '').strip()
        date_of_birth = (request.POST.get('date_of_birth') or '').strip()
        gender = (request.POST.get('gender') or '').strip()
        education = (request.POST.get('education') or '').strip()
        status = (request.POST.get('status') or '').strip()

        errors = []

        # --- Validation ---
        if not first_name:
            errors.append("First name is required.")
        elif not NAME_REGEX.match(first_name):
            errors.append("First name can contain only letters and spaces.")

        if not last_name:
            errors.append("Last name is required.")
        elif not NAME_REGEX.match(last_name):
            errors.append("Last name can contain only letters and spaces.")

        if password and not PASSWORD_REGEX.match(password):
            errors.append("Password must be at least 6 characters and include at least one letter and one digit.")

        if contact_no and not MOBILE_REGEX.match(contact_no):
            errors.append("Contact number must be exactly 10 digits.")

        if not address:
            errors.append("Address is required.")

        if date_of_birth:
            if not DATE_REGEX.match(date_of_birth):
                errors.append("Date of birth must be in YYYY-MM-DD format.")
            else:
                try:
                    # ensure valid date
                    datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    errors.append("Enter a valid date of birth.")

        # If any validation error → re-render form with messages
        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'registration/profile.html', {"user": user, "student": student})

        # --- Save data (no transaction) ---
        try:
            # Update user
            user.first_name = first_name
            user.last_name = last_name

            if password:
                user.set_password(password)
                user.save()
                update_session_auth_hash(request, user)
            else:
                user.save()

            # Update student profile
            student.contact_no = contact_no or student.contact_no
            student.address = address or student.address
            student.date_of_birth = (
                datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                if date_of_birth else student.date_of_birth
            )
            student.gender = gender or student.gender
            student.education = education or student.education
            student.status = status or student.status
            student.save()

            messages.success(request, "Profile updated successfully!")
            return redirect("profile")

        except Exception as exc:
            # Show actual error for debugging
            messages.error(request, f"Error updating profile: {exc}")
            return render(request, 'registration/profile.html', {"user": user, "student": student})

    # GET → render profile page
    return render(request, 'registration/profile.html', {"user": user, "student": student})