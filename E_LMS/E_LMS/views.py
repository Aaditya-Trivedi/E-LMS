from time import time
from app.models import *
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db.models import Sum
from django.conf import settings
import razorpay
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import re

client = razorpay.Client(auth=(settings.KEY_ID, settings.KEY_SECRET))

NAME_REGEX = re.compile(r'^[A-Za-z0-9\s]+$')          # letters, numbers, spaces
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MOBILE_REGEX = re.compile(r'^[0-9]{10}$')             # exactly 10 digits
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{6,}$')  # ≥6 chars, at least 1 letter & 1 digit
FIRST_NAME_REGEX = re.compile(r'^[A-Za-z\s]+$')
LAST_NAME_REGEX = re.compile(r'^[A-Za-z\s]+$')
CITY_REGEX = re.compile(r'^[A-Za-z\s]+$')
STATE_REGEX = re.compile(r'^[A-Za-z\s]+$')
POSTAL_CODE_REGEX = re.compile(r'^[0-9]{6}$')

# 🔹 Helper function to avoid repeating the same code
def get_common_context():
    category = Categories.objects.all().order_by('id')
    courses = Course.objects.all().order_by('id')
    return {
        'category': category,
        'courses': courses,
    }

def base(request):
    context = get_common_context()
    return render(request, 'base.html', context)

def home(request):
    context = get_common_context()
    context['category'] = Categories.objects.all().order_by('id')[0:5]  # limit 5
    context['courses'] = Course.objects.all().order_by('id')[0:5]      # limit 5

    return render(request, "main/index.html", context)

def courses_all(request):
    context = get_common_context()
    context['levels'] = Level.objects.all().order_by('id')
    return render(request, "main/courses_all.html", context)

def contactUs(request):
    context = get_common_context()
    return render(request, "main/contact_us.html", context)

def aboutUs(request):
    context = get_common_context()
    return render(request, "main/about_us.html", context)

def search(request):
    context = get_common_context()
    search_item = request.GET['search']
    context['courses'] = Course.objects.filter(title__icontains = search_item)
    # print(courses)
    # context = {
    #     'courses': courses,
    # }
    return render(request, "search/search.html", context)

@login_required
def course_details(request, slug):
    context = get_common_context()

    course = Course.objects.prefetch_related("lesson_set__video_set").filter(slug=slug).first()
    if not course:
        return render(request, 'error/404.html', context, status=404)

    time_duration = Video.objects.filter(course__slug=slug).aggregate(sum=Sum('time_duration'))

    # Get student profile
    try:
        student = request.user.student_profile
    except Student.DoesNotExist:
        messages.error(request, 'You must be logged in as a student to enroll.')
        return redirect('doLogin')

    # Enrollment check
    is_enrolled = Enrollment.objects.filter(student=student, course=course).exists()
    if is_enrolled:
        messages.info(request, "You are already enrolled in this course.")

    context.update({
        'course': course,
        'lessons': course.lesson_set.all().order_by("id"),
        'time_duration': time_duration,
        'is_enrolled': is_enrolled,
    })
    return render(request, "course/course_details.html", context)

def page_not_found(request):
    context = get_common_context()
    return render(request, 'error/404.html', context)

@login_required
def checkout(request, slug):
    course = Course.objects.filter(slug=slug).first()
    if not course:
        context = get_common_context()
        return render(request, 'error/404.html', context, status=404)

    action = request.GET.get('action')
    context = {'course': course, 'order': None}

    # Student check
    try:
        student = request.user.student_profile
    except:
        messages.error(request, 'You must be logged in as a student to enroll.')
        return redirect('doLogin')

    # Already enrolled check
    if Enrollment.objects.filter(student=student, course=course).exists():
        messages.warning(request, "You are already enrolled in this course.")
        return redirect('course_details', slug=course.slug)

    # Free course
    if course.price == 0:
        free_payment, _ = Payment.objects.get_or_create(
            student=student,
            course=course,
            amount_paid=0,
            status='successful',
            transaction_id='free_course_payment',
            defaults={'payment_date': timezone.now()}
        )
        Enrollment.objects.get_or_create(student=student, course=course, payment=free_payment)
        messages.success(request, "You have been successfully enrolled.")
        return redirect('my_courses')

    # Paid course
    if action == 'create_payment' and request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        country_code = request.POST.get('country')
        address_1 = request.POST.get('address_1')
        address_2 = request.POST.get('address_2')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('postcode')
        phone = request.POST.get('phone')
        email = request.POST.get('email')

        amount = course.price
        discount = (amount * course.discount) / 100
        order_amount = amount - discount
        raz_order_amount = int(order_amount * 100)


        if not first_name or not last_name or not country_code or not address_1 or not city or not state or not zip_code or not phone:
            messages.error(request, 'Please fill all fields.')
            return redirect('checkout',slug=course.slug)

        if not FIRST_NAME_REGEX.match(first_name):
            messages.error(request, 'First name must contain only letters.')
            return redirect('checkout',slug=course.slug)

        if not LAST_NAME_REGEX.match(last_name):
            messages.error(request, 'Last name must contain only letters.')
            return redirect('checkout',slug=course.slug)

        if not CITY_REGEX.match(city):
            messages.error(request, 'Please enter a valid city name.')
            return redirect('checkout',slug=course.slug)

        if not STATE_REGEX.match(state):
            messages.error(request, 'Please enter a valid state.')
            return redirect('checkout',slug=course.slug)

        if not POSTAL_CODE_REGEX.match(zip_code):
            messages.error(request, 'Please enter a valid zip code.')
            return redirect('checkout',slug=course.slug)

        if not MOBILE_REGEX.match(phone):
            messages.error(request, 'Please enter a valid mobile number.')
            return redirect('checkout',slug=course.slug)

        receipt = f"ELMS-{int(time())}"
        order = client.order.create({
            'receipt': receipt,
            'notes': {"name": f"{first_name} {last_name}"},
            'amount': raz_order_amount,
            'currency': 'INR',
        })

        Payment.objects.create(
            student=student,
            course=course,
            order_id=order.get('id'),
            amount_paid=order_amount,
            status='failed',  # default until verified
        )

        context['order'] = order
        context['KEY_ID'] = settings.KEY_ID

    return render(request, 'checkout/checkout.html', context)

@login_required
def my_courses(request):
    try:
        student = request.user.student_profile
    except Student.DoesNotExist:
        messages.error(request, "You must be logged in as a student to view your courses.")
        return redirect('doLogin')

    enrollments = Enrollment.objects.filter(student=student).select_related('course')
    courses = [enrollment.course for enrollment in enrollments]

    context = get_common_context()
    context['courses'] = courses

    return render(request, 'course/my_course.html', context)

@csrf_exempt
def verify_payment(request):
    if request.method == 'POST':
        data = request.POST
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': data.get('razorpay_order_id'),
                'razorpay_payment_id': data.get('razorpay_payment_id'),
                'razorpay_signature': data.get('razorpay_signature'),
            })

            payment = Payment.objects.filter(order_id=data.get('razorpay_order_id')).first()
            if not payment:
                context = get_common_context()
                return render(request, 'error/404.html', context, status=404)

            payment.transaction_id = data.get('razorpay_payment_id')
            payment.status = 'successful'
            payment.save()

            Enrollment.objects.get_or_create(
                student=payment.student,
                course=payment.course,
                payment=payment
            )
            teacher_amount = (Decimal('0.8') * payment.amount_paid).quantize(Decimal('0.01'))
            admin_amount = (Decimal('0.2') * payment.amount_paid).quantize(Decimal('0.01'))
            # Save teacher earning
            TeacherEarning.objects.create(
                teacher=payment.course.teacher,
                course=payment.course,
                payment=payment,
                amount=teacher_amount,
                is_paid=False  # initially False
            )

            # Save admin earning
            AdminEarning.objects.create(
                course=payment.course,
                payment=payment,
                commission_amount=admin_amount
            )

            return render(request, 'verify_payment/success.html', {'payment': payment})

        except Exception as e:
            print("Payment verification failed:", e)
            return render(request, 'verify_payment/fail.html')

    return render(request, 'verify_payment/fail.html')

@login_required
def watch_course(request, slug):
    lecture_id = request.GET.get("lecture")
    course = Course.objects.filter(slug=slug).first()

    if not course:
        return render(request, "error/404.html")

    # Check enrollment
    try:
        enrollment = Enrollment.objects.get(student=request.user.student_profile, course=course)
    except Enrollment.DoesNotExist:
        messages.error(request, "You are not enrolled in this course.")
        return redirect("course_details", slug=slug)

    # Get selected video or first available
    if lecture_id:
        video = Video.objects.filter(id=lecture_id, lesson__course=course).first()
    else:
        video = Video.objects.filter(course=course).order_by("serial_number").first()

    if not video:
        video = None

    context = get_common_context()
    context.update({
        "course": course,
        "video": video,
    })
    return render(request, "course/watch_course.html", context)

def apply_as_teacher(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        contact_no = request.POST.get('contact_no', '').strip()
        qualification = request.POST.get('qualification', '').strip()
        experience = request.POST.get('experience', '').strip()
        resume = request.FILES.get('resume')

        # === Validation ===
        if not username or not first_name or not last_name or not email or not contact_no or not experience or not qualification:
            messages.error(request, "All fields are required.")
            return redirect('apply_as_teacher')

        if not NAME_REGEX.match(username):
            messages.error(request, "Username may contain only letters, numbers, and spaces.")
            return redirect('apply_as_teacher')

        if not FIRST_NAME_REGEX.match(first_name):
            messages.error(request, "First name may contain only letters.")
            return redirect('apply_as_teacher')

        if not LAST_NAME_REGEX.match(last_name):
            messages.error(request, "Last name may contain only letters.")
            return redirect('apply_as_teacher')

        if not EMAIL_REGEX.match(email):
            messages.error(request, "Please enter a valid email address.")
            return redirect('apply_as_teacher')

        if not MOBILE_REGEX.match(contact_no):
            messages.error(request, "Please enter a valid mobile number.")
            return redirect('apply_as_teacher')

        if Users.objects.filter(email=email,role='teacher').exists():
            messages.error(request, 'Email already registered!')
            return redirect('apply_as_teacher')

        if Users.objects.filter(username=username).exists():
            messages.error(request, 'Username already registered!')
            return redirect('apply_as_teacher')

        # User must not already be a Teacher
        if Teacher.objects.filter(user__username=username).exists():
            messages.error(request, "This user is already registered as a teacher.")
            return redirect('apply_as_teacher')

        # User must not have already applied
        if TeacherApplication.objects.filter(username=username).exists():
            messages.error(request, "This username is already exist username.")
            return redirect('apply_as_teacher')

        # Email must not already be used in another application
        if Teacher.objects.filter(email=email).exists():
            messages.error(request, "This email has already been used to apply as a teacher.")
            return redirect('apply_as_teacher')

        # Resume must be PDF
        if not resume:
            messages.error(request, "Please upload your resume.")
            return redirect('apply_as_teacher')

        if not resume.name.lower().endswith('.pdf'):
            messages.error(request, "Resume must be a PDF file.")
            return redirect('apply_as_teacher')

        # Save application
        TeacherApplication.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            contact_no=contact_no,
            qualification=qualification,
            experience=experience,
            resume=resume
        )

        messages.success(request, "Your application has been submitted successfully.")
        return redirect('home')

    return render(request, 'career/join_teacher_application.html')

