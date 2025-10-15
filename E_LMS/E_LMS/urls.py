"""
URL configuration for E_LMS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views, user_login, teacher_view, admin_view
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('base', views.base, name='base'),
    path('404', views.page_not_found, name='page_not_found'),
    path('', views.home, name='home'),
    path('courses/all', views.courses_all, name='all_courses'),
    # path('filter-data/', views.courses_filter_data, name='courses_filter_data'),
    path('search', views.search, name='search'),
    path('courses/<slug:slug>', views.course_details, name='course_details'),
    path('contact', views.contactUs, name='contact'),
    path('about', views.aboutUs, name='about'),

    path('accounts/',include('django.contrib.auth.urls')),
    path('accounts/register/', user_login.register, name='register'),
    path('doLogin/', user_login.doLogin, name='doLogin'),

    path('teacher/teacher_dashboard', teacher_view.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/edit-profile/', teacher_view.edit_teacher_profile, name="edit_teacher_profile"),
    path('add-course/', teacher_view.add_course, name='add_course'),
    path('my-courses/', teacher_view.my_courses, name='my_coursess'),
    path('edit-course/<int:course_id>/', teacher_view.edit_course, name='edit_course'),
    path('add-lesson/', teacher_view.add_lesson, name='add_lesson'),
    path('add-video/', teacher_view.add_video, name='add_video'),
    path('ajax/get-lessons/<int:course_id>/', teacher_view.get_lessons_ajax, name='get_lessons_ajax'),
    path('ajax/get-next-serial/', teacher_view.get_next_serial_number, name='get_next_serial_number'),
    path('teacher/enrolled-students/', teacher_view.enrolled_students, name='enrolled_students'),
    path('teacher/earnings/', teacher_view.teacher_earnings, name='teacher_earnings'),

    path('ad-min/admin_dashboard/', admin_view.admin_dashboard, name='admin_dashboard'),
    path('ad-min/edit_profile/', admin_view.edit_profile, name='edit_profile'),
    path('ad-min/admin_courses/', admin_view.admin_courses, name='admin_courses'),
    path('ad-min/students/', admin_view.admin_students, name='admin_students'),
    path('ad-min/teachers/', admin_view.admin_teachers, name='admin_teachers'),
    path('ad-min/earnings/', admin_view.admin_earnings, name='admin_earnings'),
    path('ad-min/payment/', admin_view.admin_earnings_view, name='admin_payments'),
    path('ad-min/earnings/pay/<int:course_id>/', admin_view.pay_teacher_earning, name='pay_teacher_earning'),

    path('apply/teacher/', views.apply_as_teacher, name='apply_as_teacher'),
    path('ad-min/joining-applications/', admin_view.admin_joining_applications, name='admin_joining_applications'),
    path('ad-min/application/<int:app_id>/<str:status>/', admin_view.update_application_status,name='update_application_status'),

    path('logout/', user_login.LogoutView, name='logout'),
    path('accounts/profile/', user_login.profile, name='profile'),
    path('accounts/profile/update', user_login.profile_update, name='profile_update'),
    path('checkout/<slug:slug>', views.checkout, name='checkout'),
    path('my-courses', views.my_courses, name='my_courses'),
    path('verify_payment', views.verify_payment, name='verify_payment'),
    path('courses/watch-course/<slug:slug>', views.watch_course, name='watch_course'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
