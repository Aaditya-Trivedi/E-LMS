# app/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Users, Student, Teacher, AdminProfile

@receiver(post_save, sender=Users)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == "student":
            Student.objects.create(user=instance)
        elif instance.role == "teacher":
            Teacher.objects.create(user=instance, email=instance.email)
        elif instance.role == "admin":
            AdminProfile.objects.create(user=instance, contact_no="")

@receiver(post_save, sender=Users)
def save_user_profile(sender, instance, **kwargs):
    if instance.role == "student" and hasattr(instance, "student_profile"):
        instance.student_profile.save()
    elif instance.role == "teacher" and hasattr(instance, "teacher_profile"):
        instance.teacher_profile.save()
    elif instance.role == "admin" and hasattr(instance, "admin_profile"):
        instance.admin_profile.save()
