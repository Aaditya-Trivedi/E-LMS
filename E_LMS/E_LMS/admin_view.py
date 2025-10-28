from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from app.EmailBackEnd import EmailBackEnd
from app.models import *
from django.db.models import Sum
from E_LMS.views import page_not_found
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db.models import Q

import re

from xhtml2pdf import pisa

NAME_REGEX = re.compile(r'^[A-Za-z0-9\s]+$')          # letters, numbers, spaces
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MOBILE_REGEX = re.compile(r'^[0-9]{10}$')             # exactly 10 digits
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{6,}$')  # ≥6 chars, at least 1 letter & 1 digit
FIRST_NAME_REGEX = re.compile(r'^[A-Za-z\s]+$')
LAST_NAME_REGEX = re.compile(r'^[A-Za-z\s]+$')
CITY_REGEX = re.compile(r'^[A-Za-z\s]+$')
STATE_REGEX = re.compile(r'^[A-Za-z\s]+$')
POSTAL_CODE_REGEX = re.compile(r'^[0-9]{6}$')


@login_required
def admin_dashboard(request):
    user = request.user

    # Only admins allowed
    if user.role != 'admin':
        return page_not_found(request)

    course_count = Course.objects.count()
    student_count = Student.objects.count()
    teacher_count = Teacher.objects.count()
    application_count = TeacherApplication.objects.filter(status='pending').count()

    total_earnings = AdminEarning.objects.aggregate(total=models.Sum('commission_amount'))['total'] or 0

    recent_courses = Course.objects.select_related('teacher', 'course_category').order_by('-id')[:5]

    context = {
        'course_count': course_count,
        'student_count': student_count,
        'teacher_count': teacher_count,
        'application_count': application_count,
        'total_earnings': total_earnings,
        'recent_courses': recent_courses,
    }
    return render(request, 'admin/admin_dashboard.html', context)

@login_required
def edit_profile(request):
    user = request.user

    # Only admins allowed
    if user.role != 'admin':
        return page_not_found(request)

    # Get or create AdminProfile for this user
    admin_profile, created = AdminProfile.objects.get_or_create(user=user)

    if request.method == 'POST':

        # Get submitted data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        contact_no = request.POST.get('contact_no', '').strip()
        bio = request.POST.get('bio', None)

        # --- Validation checks ---
        errors = []
        if first_name and not FIRST_NAME_REGEX.match(first_name):
            errors.append("First name can contain only letters and spaces.")
        if last_name and not LAST_NAME_REGEX.match(last_name):
            errors.append("Last name can contain only letters and spaces.")
        if email and not EMAIL_REGEX.match(email):
            errors.append("Please enter a valid email address.")
        if contact_no and not MOBILE_REGEX.match(contact_no):
            errors.append("Contact number must be exactly 10 digits.")

        # If validation fails, show errors and reload page
        if errors:
            for err in errors:
                messages.error(request, err)
            context = {'user': user, 'admin_profile': admin_profile}
            return render(request, 'admin/admin_profile.html', context)

        # Update user fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()  # Save updated user info

        # Update admin profile contact_no
        contact_no = request.POST.get('contact_no', '')
        if contact_no:
            admin_profile.contact_no = contact_no

        # Optional bio field, if present
        bio = request.POST.get('bio', None)
        if bio is not None:
            admin_profile.bio = bio

        admin_profile.save()  # Save profile updates

        messages.success(request, 'Profile updated successfully.')
        return redirect('edit_profile')  # or wherever you want to redirect

    context = {
        'user': user,
        'admin_profile': admin_profile,
    }
    return render(request, 'admin/admin_profile.html', context)

@login_required
def manage_languages_categories(request):
    user = request.user

    # Only admins allowed
    if user.role != "admin":
        return page_not_found(request)

    # Fetch all
    categories = Categories.objects.all().order_by("id")
    languages = Language.objects.all().order_by("id")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        print("form_type", form_type)
        # --- Add Category ---
        if form_type == "category":
            name = request.POST.get("name", "").strip()
            icon = request.POST.get("icon", "").strip()

            if not name:
                messages.error(request, "Category name is required.")
            elif not icon:
                messages.error(request, "icon is required.")
            elif Categories.objects.filter(name__iexact=name).exists():
                messages.warning(request, "This category already exists.")
            else:
                Categories.objects.create(name=name, icon=icon)
                messages.success(request, f"Category '{name}' added successfully!")
            return redirect("manage_languages_categories")

        # --- Add Language ---
        elif form_type == "language":
            name = request.POST.get("name", "").strip()

            if not name:
                messages.error(request, "Language name is required.")
            elif Language.objects.filter(name__iexact=name).exists():
                messages.warning(request, "This language already exists.")
            else:
                Language.objects.create(name=name)
                messages.success(request, f"Language '{name}' added successfully!")
            return redirect("manage_languages_categories")

    context = {
        "categories": categories,
        "languages": languages,
    }
    return render(request, "admin/manage_language_category.html", context)

@login_required
def delete_category(request, cat_id):
    user = request.user
    if user.role != "admin":
        return page_not_found(request)

    try:
        category = Categories.objects.get(id=cat_id)
        category.delete()
        messages.success(request, f"Category '{category.name}' deleted successfully.")
    except Categories.DoesNotExist:
        messages.error(request, "Category not found.")
    return redirect("manage_languages_categories")

@login_required
def delete_language(request, lang_id):
    user = request.user
    if user.role != "admin":
        return page_not_found(request)

    try:
        language = Language.objects.get(id=lang_id)
        language.delete()
        messages.success(request, f"Language '{language.name}' deleted successfully.")
    except Language.DoesNotExist:
        messages.error(request, "Language not found.")
    return redirect("manage_languages_categories")

@login_required
def admin_courses(request):
    user = request.user

    # Only admins allowed
    if user.role != 'admin':
        return page_not_found(request)

    courses = Course.objects.select_related('teacher', 'course_category').all().order_by('-id')

    context = {
        'courses': courses
    }
    return render(request, 'admin/admin_courses.html', context)

@login_required
def admin_students(request):
    user = request.user

    # Only admins allowed
    if user.role != 'admin':
        return page_not_found(request)

    students = Student.objects.select_related('user').all()
    return render(request, 'admin/admin_students.html', {'students': students})

@login_required
def admin_teachers(request):
    user = request.user

    # Only admins allowed
    if user.role != 'admin':
        return page_not_found(request)

    teachers = Teacher.objects.select_related('user').all()
    return render(request, 'admin/admin_teacher.html', {'teachers': teachers})

@login_required
def admin_earnings(request):
    user = request.user

    # Only admins allowed
    if user.role != 'admin':
        return page_not_found(request)

    # Get date filters from GET params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Base queryset
    earnings_qs = AdminEarning.objects.all()

    if start_date:
        earnings_qs = earnings_qs.filter(payment__payment_date__date__gte=start_date)
    if end_date:
        earnings_qs = earnings_qs.filter(payment__payment_date__date__lte=end_date)

    # Total admin earnings for filtered range
    total_admin_earnings = earnings_qs.aggregate(total=Sum('commission_amount'))['total'] or 0

    # Optional: earnings grouped by date
    from django.db.models.functions import TruncDate
    earnings_by_date = (
        earnings_qs
        .annotate(date=TruncDate('payment__payment_date'))
        .values('date')
        .annotate(day_total=Sum('commission_amount'))
        .order_by('-date')
    )

    context = {
        'total_admin_earnings': total_admin_earnings,
        'earnings_by_date': earnings_by_date,
        'start_date': start_date,
        'end_date': end_date
    }
    return render(request, 'admin/admin_earnings.html', context)

@login_required
def admin_earnings_view(request):
    user = request.user

    # Only admins allowed
    if user.role != 'admin':
        return page_not_found(request)

    filter_status = request.GET.get('status', 'all')  # all, paid, unpaid

    earnings_qs = TeacherEarning.objects.select_related('course', 'teacher__user')

    if filter_status == 'paid':
        earnings_qs = earnings_qs.filter(is_paid=True)
    elif filter_status == 'unpaid':
        earnings_qs = earnings_qs.filter(is_paid=False)

    # Group by course and teacher and sum amounts
    earnings_summary = earnings_qs.values(
        'course__id',
        'course__title',
        'teacher__user__first_name',
        'teacher__user__last_name',
        'is_paid',
    ).annotate(total_earned=Sum('amount')).order_by('-total_earned')

    context = {
        'teacher_earnings': earnings_summary,
        'filter_status': filter_status,
    }
    return render(request, 'admin/admin_payment.html', context)

@login_required
def pay_teacher_earning(request, course_id):
    user = request.user

    # Only admins allowed
    if user.role != 'admin':
        return page_not_found(request)

    # Pay all unpaid earnings for this course
    earnings_to_pay = TeacherEarning.objects.filter(course_id=course_id, is_paid=False)

    if not earnings_to_pay.exists():
        messages.warning(request, "No unpaid earnings found for this course.")
        return redirect('admin_payments')

    earnings_to_pay.update(is_paid=True)
    messages.success(request, "Marked teacher earnings as paid for the selected course.")
    return redirect('admin_payments')

@login_required
def admin_joining_applications(request):
    pending_apps = TeacherApplication.objects.filter(status='pending').order_by('-applied_on')
    accepted_apps = TeacherApplication.objects.filter(status='accepted').order_by('-applied_on')
    rejected_apps = TeacherApplication.objects.filter(status='rejected').order_by('-applied_on')

    return render(request, 'admin/admin_joining_applications.html', {
        'pending_apps': pending_apps,
        'accepted_apps': accepted_apps,
        'rejected_apps': rejected_apps
    })

@login_required
def update_application_status(request, app_id, status):
    try:
        application = TeacherApplication.objects.get(id=app_id)
    except TeacherApplication.DoesNotExist:
        return page_not_found(request)

    if status == 'accept':
        if application.status != 'accepted':
            # Generate username and password
            username = application.email
            raw_password = get_random_string(8)

            print("Sending email to:", application.email)
            # Check if user already exists
            user, created = Users.objects.get_or_create(
                username=application.username,
                defaults={
                    'email': application.email,
                    'first_name': application.first_name,
                    'last_name': application.last_name,
                    'role': 'teacher',
                    'password': make_password(raw_password),
                }
            )

            # Send acceptance email with credentials
            if created:
                send_mail(
                    subject='Application Accepted - Teacher Account Created',
                    message=(
                        f"Dear {application.first_name},\n\n"
                        f"Congratulations! Your application to join as a teacher has been accepted.\n\n"
                        f"You can now login with the following credentials:\n"
                        f"Username: {username}\n"
                        f"Password: {raw_password}\n\n"
                        f"Please change your password after logging in and Complete your profile first."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[application.email],
                    fail_silently=False,
                )

            if not Teacher.objects.filter(user=user).exists():
                Teacher.objects.create(
                    user=user,
                    email=application.email,
                    contact_no=application.contact_no,
                    qualification=application.qualification,
                    experience=application.experience,
                    bio="",
                )

            # Update application status
            application.status = 'accepted'
            application.save()

            messages.success(request, "Application accepted and teacher account created.")

    elif status == 'reject':
        if application.status != 'rejected':
            application.status = 'rejected'
            application.save()

            send_mail(
                subject='Application Rejected',
                message=(
                    f"Dear {application.first_name},\n\n"
                    f"We regret to inform you that your application to join as a teacher at ELMS has been rejected."

                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[application.email],
                fail_silently=True,
            )

            messages.success(request, "Application rejected.")

    return redirect('admin_joining_applications')

@login_required
def download_earning_report(request):
    # only admin can access
    user = request.user
    if not user.is_authenticated or getattr(user, "role", None) != "admin":
        return HttpResponse("Unauthorized", status=403)

    filter_status = request.GET.get("status", "all")

    # ----- Admin earnings -----
    admin_earnings = AdminEarning.objects.select_related("course", "payment")


    total_admin = admin_earnings.aggregate(total=Sum("commission_amount"))["total"] or 0

    # ----- Teacher earnings -----
    teacher_earnings = TeacherEarning.objects.select_related("course", "teacher__user")
    if filter_status == "paid":
        teacher_earnings = teacher_earnings.filter(is_paid=True)
    elif filter_status == "unpaid":
        teacher_earnings = teacher_earnings.filter(is_paid=False)

    total_teacher = teacher_earnings.aggregate(total=Sum("amount"))["total"] or 0
    overall_total = total_admin + total_teacher

    # render HTML
    html = render_to_string(
        "admin/earning_report.html",
        {
            "admin_earnings": admin_earnings,
            "teacher_earnings": teacher_earnings,
            "total_admin": total_admin,
            "total_teacher": total_teacher,
            "overall_total": overall_total,
            "filter_status": filter_status,
            "generated_on": timezone.now(),
        },
    )

    # create PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Earning Reports.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response