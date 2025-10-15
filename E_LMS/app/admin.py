from django.contrib import admin
from .models import *

# ----------------- USERS -----------------
@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'contact_no', 'education', 'status')
    search_fields = ('user__username', 'contact_no')


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'qualification', 'experience', 'rating')
    search_fields = ('user__username', 'email')


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'contact_no')

# ----------------- INLINE VIDEOS -----------------
class VideoInline(admin.TabularInline):
    model = Video
    extra = 1   # how many empty rows for new entries
    fields = ('serial_number','lesson', 'thumbnail' , 'title', 'video_file', 'time_duration', 'preview')

# ----------------- COURSE -----------------
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'price', 'course_category', 'level')
    search_fields = ('title', 'teacher__user__username')
    list_filter = ('course_category', 'level')
    prepopulated_fields = {"slug": ("title",)}
    inlines = [VideoInline]   # ✅ Videos inline inside Course

# ----------------- LESSON -----------------
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('name', 'course','teacher')
    search_fields = ('name', 'course__title','teacher')

# ----------------- OTHER MODELS -----------------
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'amount_paid', 'status', 'payment_date', 'transaction_id')
    list_filter = ('status', 'payment_date')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'payment', 'enrolled_on')


@admin.register(TeacherEarning)
class TeacherEarningAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'course', 'amount', 'is_paid')


@admin.register(AdminEarning)
class AdminEarningAdmin(admin.ModelAdmin):
    list_display = ('course', 'commission_amount')


@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(TeacherApplication)
class TeacherApplicationAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'status', 'applied_on')
    search_fields = ('first_name', 'last_name', 'email', 'username')
    list_filter = ('status', 'applied_on')
