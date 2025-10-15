from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import *
from django.http import JsonResponse
from E_LMS.views import page_not_found
from datetime import date
from django.db.models import Sum
import re,os
from django.conf import settings

FIRST_NAME_REGEX = re.compile(r'^[A-Za-z\s]+$')
LAST_NAME_REGEX = re.compile(r'^[A-Za-z\s]+$')
MOBILE_REGEX = re.compile(r'^[0-9]{10}$')             # exactly 10 digits
QUALIFICATION_REGEX = re.compile(r'^[A-Za-z\s,.\-]+$')  # letters, numbers, spaces, commas, dots
EXPERIENCE_REGEX = re.compile(r'^[0-9]{1,2}$')
TITLE_REGEX = re.compile(r'^[A-Za-z0-9\s,.\-()]+$')       # Letters, numbers, spaces, commas, dots, hyphens, brackets
DESCRIPTION_MIN_LENGTH = 20                               # Minimum description length
PRICE_REGEX = re.compile(r'^(?:\d+)(?:\.\d{1,2})?$')      # Non-negative number, optional decimals (0, 100, 99999.99)
DISCOUNT_REGEX = re.compile(r'^(?:\d+)(?:\.\d{1,2})?$')# 0–99 percent only
LESSON_REGEX = re.compile(r'^[A-Za-z\s]+$')
TIME_REGEX = re.compile(r'^(?:\d+)(?:\.\d{1,2})?$')        # minutes, allows decimal (e.g., 5 or 12.5)
THUMB_EXTS = {'jpg', 'jpeg', 'png', 'webp'}
VIDEO_EXTS = {'mp4', 'mkv', 'webm', 'mov'}
MAX_THUMB_BYTES = 2 * 1024 * 1024      # 2 MB
MAX_VIDEO_BYTES = 500 * 1024 * 1024    # 500 MB (adjust as needed)

@login_required
def teacher_dashboard(request):
    # check if the logged-in user is a teacher
    if not hasattr(request.user, "teacher_profile"):
        messages.error(request, "Access denied! You are not a teacher.")
        return redirect("home")

    teacher = request.user.teacher_profile

    # fetch teacher details
    courses = Course.objects.filter(teacher=teacher)
    total_courses = courses.count()

    # students enrolled in teacher's courses
    total_students = Enrollment.objects.filter(course__in=courses).count()

    # teacher earnings
    pending_earnings = TeacherEarning.objects.filter(
        teacher=teacher, is_paid=False
    ).aggregate(total=models.Sum("amount"))["total"] or 0
    recieved_earnings = TeacherEarning.objects.filter(teacher=teacher, is_paid=True).aggregate(total=models.Sum("amount"))["total"] or 0

    context = {
        "teacher": teacher,
        "courses": courses,
        "total_courses": total_courses,
        "total_students": total_students,
        "pending_earnings": pending_earnings,
        "received_earnings": recieved_earnings


    }
    return render(request, "teacher/teacher_dashboard.html", context)

@login_required
def edit_teacher_profile(request):
    teacher = request.user.teacher_profile  # because of OneToOneField in Teacher

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        contact_no = request.POST.get("contact_no", "").strip()
        qualification = request.POST.get("qualification", "").strip()
        experience = request.POST.get("experience", "").strip()
        bio = request.POST.get("bio", "").strip()

        # -------------------
        # Validation Section
        # -------------------
        errors = []

        if first_name and not FIRST_NAME_REGEX.match(first_name):
            errors.append("First name can contain only letters and spaces.")
        if last_name and not LAST_NAME_REGEX.match(last_name):
            errors.append("Last name can contain only letters and spaces.")
        if contact_no and not MOBILE_REGEX.match(contact_no):
            errors.append("Contact number must be exactly 10 digits.")
        if qualification and not QUALIFICATION_REGEX.match(qualification):
            errors.append("Qualification can contain only letters, spaces, commas, and periods.")
        if experience and not EXPERIENCE_REGEX.match(experience):
            errors.append("Experience must be a valid number (in years).")

        # If validation fails
        if errors:
            for err in errors:
                messages.error(request, err)
            context = {"teacher": teacher}
            return render(request, "teacher/edit_profile.html", context)

        # -------------------
        # Save updates
        # -------------------
        request.user.first_name = first_name or request.user.first_name
        request.user.last_name = last_name or request.user.last_name
        request.user.save()

        teacher.contact_no = contact_no or teacher.contact_no
        teacher.qualification = qualification or teacher.qualification
        teacher.experience = int(experience) if experience else 0
        teacher.bio = bio or teacher.bio
        teacher.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("teacher_dashboard")

    context = {
        "teacher": teacher
    }
    return render(request, "teacher/edit_profile.html", context)

@login_required
def add_course(request):
    # Automatically get the teacher from logged-in user
    try:
        teacher = request.user.teacher_profile  # OneToOneField relation
    except Teacher.DoesNotExist:
        messages.error(request, "You must be logged in as a teacher to add a course.")
        return redirect("doLogin")

    if request.method == 'POST':
        # Get form data
        course_image = request.FILES.get('course_image')
        title = request.POST.get('title', '').strip()
        descriptions = request.POST.get('descriptions', '').strip()
        category_id = request.POST.get('course_category', '').strip()
        level_id = request.POST.get('level', '').strip()
        language_id = request.POST.get('language', '').strip()
        price = request.POST.get('price', '').strip()
        discount = request.POST.get('discount', '').strip() or '0'

        # ------------------------
        # Validation
        # ------------------------
        errors = []

        required_fields = {

            "Course Title": title,
            "Description": descriptions,
            "Category": category_id,
            "Level": level_id,
            "Language": language_id,
            "Price": price,
        }
        if not course_image:
            errors.append("Please upload a course image.")
        else:
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp']
            ext = course_image.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                errors.append("Invalid image format. Allowed formats: JPG, JPEG, PNG, WEBP.")

        filled_values = [v for v in required_fields.values() if v.strip()]

        if not filled_values:
            errors.append("All fields are empty. Please fill in the form before submitting.")
        else:
            missing = [name for name, value in required_fields.items() if not value.strip()]
            if missing:
                errors.append(f"The following fields are required: {', '.join(missing)}.")

        if title and not TITLE_REGEX.match(title):
            errors.append("Course title can contain only letters, numbers, spaces, and punctuation (, . - ()).")

        if descriptions and len(descriptions) < DESCRIPTION_MIN_LENGTH:
            errors.append(f"Description must be at least {DESCRIPTION_MIN_LENGTH} characters long.")

        if price and not PRICE_REGEX.match(price):
            errors.append("Enter a valid price (e.g., 0, 99, 1000.50).")
        else:
            try:
                if float(price) < 0:
                    errors.append("Price cannot be negative.")
            except ValueError:
                errors.append("Enter a valid numeric price.")

        if discount and not DISCOUNT_REGEX.match(discount):
            errors.append("Discount must be between 0 and 99.")

        if errors:
            for err in errors:
                messages.error(request, err)

            categories = Categories.objects.all()
            levels = Level.objects.all()
            languages = Language.objects.all()
            context = {
                "categories": categories,
                "levels": levels,
                "languages": languages,
                "title": title,
                "descriptions": descriptions,
                "price": price,
                "discount": discount,
                "teacher": teacher,
            }
            return render(request, "teacher/newcourse.html", context)

        # Fetch related objects
        try:
            category = Categories.objects.get(id=category_id)
            level = Level.objects.get(id=level_id)
            language = Language.objects.get(id=language_id)
        except (Categories.DoesNotExist, Level.DoesNotExist, Language.DoesNotExist):
            messages.error(request, "Invalid category, level, or language selected.")
            return redirect('add_course')

        # Create Course object with logged-in teacher
        Course.objects.create(
            teacher=teacher,
            title=title,
            descriptions=descriptions,
            course_category=category,
            level=level,
            language=language,
            price=price,
            discount=discount,
            course_image=course_image,
        )

        messages.success(request, "Course added successfully.")
        return redirect('teacher_dashboard')

    else:
        categories = Categories.objects.all()
        levels = Level.objects.all()
        languages = Language.objects.all()

        context = {
            "categories": categories,
            "levels": levels,
            "languages": languages,
            "teacher": request.user.teacher_profile,
        }
        return render(request, "teacher/newcourse.html", context)

@login_required
def my_courses(request):
    teacher = request.user.teacher_profile  # Get teacher profile from logged-in user
    courses = Course.objects.filter(teacher=teacher).order_by('-id')  # Fetch courses by this teacher

    context = {
        'courses': courses,
    }
    return render(request, 'teacher/my_courses.html', context)

@login_required
def edit_course(request, course_id):
    teacher = request.user.teacher_profile

    try:
        course = Course.objects.get(id=course_id, teacher=teacher)
    except Course.DoesNotExist:
        return page_not_found(request)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        descriptions = request.POST.get('descriptions', '').strip()
        category_id = request.POST.get('course_category', '').strip()
        level_id = request.POST.get('level', '').strip()
        language_id = request.POST.get('language', '').strip()
        price = request.POST.get('price', '').strip()
        discount = request.POST.get('discount', '').strip() or '0'
        course_image = request.FILES.get('course_image')

        # ------------------------
        # Validation Section
        # ------------------------
        errors = []

        # Required field check
        required_fields = {
            "Course Title": title,
            "Description": descriptions,
            "Category": category_id,
            "Level": level_id,
            "Language": language_id,
            "Price": price,
        }

        filled_values = [v for v in required_fields.values() if v.strip()]
        if not filled_values:
            errors.append("All fields are empty. Please fill in the form before submitting.")
        else:
            missing = [name for name, value in required_fields.items() if not value.strip()]
            if missing:
                errors.append(f"The following fields are required: {', '.join(missing)}.")

        # Title validation
        if title and not TITLE_REGEX.match(title):
            errors.append("Course title can contain only letters, numbers, spaces, and punctuation (, . - ()).")

        # Description validation
        if descriptions and len(descriptions) < DESCRIPTION_MIN_LENGTH:
            errors.append(f"Description must be at least {DESCRIPTION_MIN_LENGTH} characters long.")

        # Price validation (non-negative, decimals allowed)
        if price and not PRICE_REGEX.match(price):
            errors.append("Enter a valid price (e.g., 0, 99, 1000.50).")
        else:
            try:
                if float(price) < 0:
                    errors.append("Price cannot be negative.")
            except ValueError:
                errors.append("Enter a valid numeric price.")

        # Discount validation (0–99)
        if discount and not DISCOUNT_REGEX.match(discount):
            errors.append("Discount must be a number between 0 and 99.")

        # Image validation (if uploaded)
        if course_image:
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp']
            ext = course_image.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                errors.append("Invalid image format. Allowed formats: JPG, JPEG, PNG, WEBP.")

        # Stop if any validation fails
        if errors:
            for err in errors:
                messages.error(request, err)

            categories = Categories.objects.all()
            levels = Level.objects.all()
            languages = Language.objects.all()

            context = {
                'course': course,
                'categories': categories,
                'levels': levels,
                'languages': languages,
            }
            return render(request, 'teacher/edit_course.html', context)

        # ------------------------
        # If validation passes → update
        # ------------------------
        try:
            course.course_category = Categories.objects.get(id=category_id)
            course.level = Level.objects.get(id=level_id)
            course.language = Language.objects.get(id=language_id)
        except (Categories.DoesNotExist, Level.DoesNotExist, Language.DoesNotExist):
            messages.error(request, "Invalid category, level, or language selected.")
            return redirect('edit_course', course_id=course.id)

        course.title = title
        course.descriptions = descriptions
        course.price = price
        course.discount = discount

        #Delete old image if a new one is uploaded
        if course_image:
            if course.course_image and course.course_image.name:  # existing file
                old_path = os.path.join(settings.MEDIA_ROOT, course.course_image.name)
                if os.path.exists(old_path):
                    os.remove(old_path)
            course.course_image = course_image

        course.save()
        messages.success(request, 'Course updated successfully.')
        return redirect('my_coursess')

    # ------------------------
    # Render edit page
    # ------------------------
    categories = Categories.objects.all()
    levels = Level.objects.all()
    languages = Language.objects.all()

    context = {
        'course': course,
        'categories': categories,
        'levels': levels,
        'languages': languages,
    }
    return render(request, 'teacher/edit_course.html', context)

@login_required
def add_lesson(request):
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        # Handle gracefully (could redirect or show a message)
        return redirect('teacher_dashboard')  # or wherever appropriate

    if request.method == 'POST':
        course_id = request.POST.get('course')
        name = request.POST.get('name')

        if not name:
            messages.error(request, 'Please enter a Lesson name.')
            return redirect('add_lesson')
        if not LESSON_REGEX.match(name):
            messages.error(request, 'Invalid lesson name.')
            return redirect('add_lesson')

        # Ensure course belongs to this teacher
        course = Course.objects.filter(id=course_id, teacher=teacher).first()

        if course and name:
            Lesson.objects.create(course=course, name=name, teacher=teacher)
            return redirect('add_lesson')  # or redirect elsewhere
        else:
            # Optional: add error handling (e.g. invalid course or missing name)
            return render(request, 'teacher/add_lesson.html', {
                'courses': Course.objects.filter(teacher=teacher),
                'error': 'Invalid course or missing lesson name.'
            })

    # GET request
    courses = Course.objects.filter(teacher=teacher)
    return render(request, 'teacher/add_lesson.html', {'courses': courses})

@login_required
def add_video(request):
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, "You must be logged in as a teacher to add videos.")
        return redirect('doLogin')

    courses = Course.objects.filter(teacher=teacher)
    selected_course_id = request.GET.get('course')

    if selected_course_id:
        lessons = Lesson.objects.filter(course_id=selected_course_id, course__teacher=teacher)
    else:
        lessons = Lesson.objects.none()

    if request.method == 'POST':
        # Get form data
        lesson_id = request.POST.get('lesson', '').strip()
        serial_number = request.POST.get('serial_number', '').strip()
        title = request.POST.get('title', '').strip()
        time_duration = request.POST.get('time_duration', '').strip() or None
        thumbnail = request.FILES.get('thumbnail')
        video_file = request.FILES.get('video_file')

        errors = []

        # ------------------------------
        # Required field validation
        # ------------------------------
        if not lesson_id:
            errors.append("Please select a lesson.")
        if not title:
            errors.append("Please enter a video title.")
        if not time_duration:
            errors.append("Please enter the time duration in minutes.")
        if not video_file:
            errors.append("Please upload a video file.")
        if not thumbnail:
            errors.append("Please upload a Thumbnail Image.")

        # ------------------------------
        # Format and type validation
        # ------------------------------

        if title and not TITLE_REGEX.match(title):
            errors.append("Title contains invalid characters.")
        if time_duration:
            if not TIME_REGEX.match(time_duration):
                errors.append("Time duration must be a valid number (e.g., 5, 10.5).")
            else:
                try:
                    minutes = float(time_duration)
                    if minutes <= 0:
                        errors.append("Time duration must be greater than 0 minutes.")
                except ValueError:
                    errors.append("Enter a valid numeric time duration.")

        # ------------------------------
        # Thumbnail validation (optional)
        # ------------------------------
        if thumbnail:
            thumb_ext = thumbnail.name.split('.')[-1].lower()
            if thumb_ext not in THUMB_EXTS:
                errors.append("Thumbnail must be an image (JPG, JPEG, PNG, WEBP).")
            elif thumbnail.size > MAX_THUMB_BYTES:
                errors.append("Thumbnail file is too large (max 2 MB).")

        # ------------------------------
        # Video file validation
        # ------------------------------
        if video_file:
            vid_ext = video_file.name.split('.')[-1].lower()
            if vid_ext not in VIDEO_EXTS:
                errors.append("Video file must be in MP4, MKV, WEBM, or MOV format.")
            elif video_file.size > MAX_VIDEO_BYTES:
                errors.append("Video file is too large (max 500 MB).")

        # ------------------------------
        # If validation fails → show errors
        # ------------------------------
        if errors:
            for err in errors:
                messages.error(request, err)

            # Reload context
            lessons = Lesson.objects.filter(course_id=selected_course_id, course__teacher=teacher) if selected_course_id else Lesson.objects.none()
            context = {
                'courses': courses,
                'lessons': lessons,
                'selected_course_id': selected_course_id,
                'prev': {
                    'lesson_id': lesson_id,
                    'serial_number': serial_number,
                    'title': title,
                    'time_duration': time_duration,
                }
            }
            return render(request, 'teacher/add_video.html', context)

        # ------------------------------
        # Lesson ownership check
        # ------------------------------
        try:
            lesson = Lesson.objects.get(id=lesson_id, course__teacher=teacher)
            course = lesson.course
        except Lesson.DoesNotExist:
            messages.error(request, "Invalid lesson selected.")
            return redirect('add_video')

        # Ensure serial number is unique within the same lesson
        if Video.objects.filter(lesson=lesson, serial_number=serial_number).exists():
            messages.error(request, "A video with this serial number already exists in the selected lesson.")
            lessons = Lesson.objects.filter(course_id=selected_course_id, course__teacher=teacher)
            context = {
                'courses': courses,
                'lessons': lessons,
                'selected_course_id': selected_course_id,
                'prev': {
                    'lesson_id': lesson_id,
                    'serial_number': serial_number,
                    'title': title,
                    'time_duration': time_duration,
                }
            }
            return render(request, 'teacher/add_video.html', context)

        # ------------------------------
        # Create video record
        # ------------------------------
        Video.objects.create(
            course=course,
            lesson=lesson,
            serial_number=int(serial_number),
            title=title,
            time_duration=time_duration,  # stored as minutes
            thumbnail=thumbnail,
            video_file=video_file,
        )

        messages.success(request, "Video added successfully.")
        return redirect('teacher_dashboard')

    # ------------------------------
    # GET request → render form
    # ------------------------------
    context = {
        'courses': courses,
        'lessons': lessons,
        'selected_course_id': selected_course_id,
    }
    return render(request, 'teacher/add_video.html', context)

@login_required
def get_lessons_ajax(request, course_id):
    teacher = request.user
    # Check that the course belongs to the teacher before returning lessons
    lessons = Lesson.objects.filter(course_id=course_id, course__teacher=teacher).values('id', 'name')
    lessons_list = list(lessons)
    return JsonResponse({'lessons': lessons_list})

@login_required
def get_next_serial_number(request):
    lesson_id = request.GET.get('lesson_id')
    if lesson_id:
        try:
            last_video = Video.objects.filter(lesson_id=lesson_id).order_by('-serial_number').first()
            next_serial = last_video.serial_number + 1 if last_video and last_video.serial_number else 1
            return JsonResponse({'next_serial': next_serial})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'No lesson_id provided'}, status=400)

@login_required
def enrolled_students(request):
    if not hasattr(request.user, "teacher_profile"):
        return page_not_found(request)

    teacher = request.user.teacher_profile
    selected_course_id = request.GET.get("course")

    # Get all teacher's courses
    courses = Course.objects.filter(teacher=teacher)

    # Filter enrollments by teacher’s courses
    enrollments = Enrollment.objects.filter(course__in=courses)

    if selected_course_id:
        enrollments = enrollments.filter(course__id=selected_course_id)

    # Calculate student ages
    student_data = []
    for enrollment in enrollments.select_related("student", "student__user", "course"):
        student = enrollment.student
        dob = student.date_of_birth
        age = None
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        student_data.append({
            "username": student.user.username,
            "email": student.user.email,
            "course_title": enrollment.course.title,
            "age": age,
            "enrolled_on": enrollment.enrolled_on,
        })

    context = {
        "courses": courses,
        "selected_course_id": int(selected_course_id) if selected_course_id else None,
        "student_data": student_data,
    }
    return render(request, "teacher/enrolled_students.html", context)

@login_required
def teacher_earnings(request):
    if not hasattr(request.user, "teacher_profile"):
        return page_not_found(request)

    teacher = request.user.teacher_profile
    filter_type = request.GET.get("filter", "all")  # default to "all"

    earnings = TeacherEarning.objects.filter(teacher=teacher).select_related('course', 'payment')

    if filter_type == "received":
        earnings = earnings.filter(is_paid=True)
    elif filter_type == "pending":
        earnings = earnings.filter(is_paid=False)

    # Aggregate total received and pending
    received_total = TeacherEarning.objects.filter(teacher=teacher, is_paid=True).aggregate(total=Sum("amount"))["total"] or 0
    pending_total = TeacherEarning.objects.filter(teacher=teacher, is_paid=False).aggregate(total=Sum("amount"))["total"] or 0
    total_earnings = received_total + pending_total

    context = {
        "earnings": earnings.order_by('-id'),
        "filter_type": filter_type,
        "received_total": received_total,
        "pending_total": pending_total,
        "total_earnings": total_earnings,
    }

    return render(request, "teacher/teacher_earnings.html", context)