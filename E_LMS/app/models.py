# app/models.py
from django.contrib.auth.models import AbstractUser
# Create your models here.
from django.db import models
from django.utils.text import slugify
from django.db.models.signals import pre_save
import os

class Categories(models.Model):
    name = models.CharField(max_length=200)
    icon = models.CharField(max_length=200, null=True)

    def __str__(self):
        return self.name

    def get_all_categories(self):
        return Categories.objects.all().order_by('id')

# in models.py
class Users(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    def __str__(self):
        return f"{self.username} ({self.role})"

class Student(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name="student_profile")
    contact_no = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=(("Male","Male"), ("Female","Female"), ("Other","Other")), null=True, blank=True)
    education = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=20, choices=(("active","Active"), ("inactive","Inactive")), default="active")

    def __str__(self):
        return f"Student: {self.user.username}"

class Teacher(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name="teacher_profile")
    email = models.EmailField()
    contact_no = models.CharField(max_length=10, null=True, blank=True)
    qualification = models.TextField()
    experience = models.IntegerField(default=0)  # in years
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    bio = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Teacher: {self.user.username}"

class AdminProfile(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name="admin_profile")
    contact_no = models.CharField(max_length=20)

    def __str__(self):
        return f"Admin: {self.user.username}"

class Level(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class Language(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name
# app/models.py

class Course(models.Model):
    course_image = models.ImageField(upload_to="Media/course_image", null=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=255)
    descriptions = models.TextField()
    course_category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name="courses")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, null=True,)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, null=True,)
    slug = models.SlugField(default='',max_length=500, null=True,blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0)


    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("course_details", kwargs={"slug": self.slug})

def create_slug(instance, new_slug=None):
    slug = slugify(instance.title)
    if new_slug is not None:
        slug = new_slug
    qs = Course.objects.filter(slug=slug).order_by("-id")
    exists = qs.exists()
    if exists:
        new_slug = "%s-%s" % (slug, qs.first().id)
        return create_slug(instance, new_slug=new_slug)
    return slug

def pre_save_post_receiver(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = create_slug(instance)

pre_save.connect(pre_save_post_receiver, Course)

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name + " - " + self.course.title

def video_upload_path(instance, filename):
    teacher_username = slugify(instance.course.teacher.user.username)
    course_name = slugify(instance.course.title)
    lesson_name = slugify(instance.lesson.name)

    try:
        serial_number = int(instance.serial_number)
    except (ValueError, TypeError):
        serial_number = 0  # fallback in case of bad input

    extension = filename.split('.')[-1]
    new_filename = f"{serial_number:02d}_{slugify(instance.title)}.{extension}"

    return os.path.join('videos', teacher_username, course_name, lesson_name, new_filename)

class Video(models.Model):
    serial_number = models.IntegerField(null=True)
    thumbnail = models.ImageField(upload_to="media/thumbnail", null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to=video_upload_path, null=True, blank=True)
    time_duration = models.IntegerField(null=True)

    def __str__(self):
        return f"{self.serial_number}. {self.title}"

class Payment(models.Model):
    STATUS_CHOICES = (("successful", "Successful"), ("failed", "Failed"))

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="payments")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='failed')
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    order_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.course.title} - {self.status}"

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.username} enrolled in {self.course.title}"

class TeacherEarning(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="earnings")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.teacher.user.username} - {self.amount}"

class AdminEarning(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Admin Commission {self.commission_amount} from {self.course.title}"

def resume_upload_path(instance, filename):
    # Clean name
    name_slug = slugify(f"{instance.first_name}_{instance.last_name}")
    # Instance may not have an ID yet (if not saved), so fallback to temp folder
    applicant_id = instance.id if instance.id else "temp"

    return os.path.join("joiningapplications", f"{applicant_id}_{name_slug}", filename)

class TeacherApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    username = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    contact_no = models.CharField(max_length=20, blank=True)
    qualification = models.TextField()
    experience = models.PositiveIntegerField()
    resume = models.FileField(upload_to=resume_upload_path)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.status}"