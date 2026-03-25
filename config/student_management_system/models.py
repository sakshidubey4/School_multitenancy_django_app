from django.db import models
from django.contrib.auth.models import User


class School(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.SlugField(max_length=50, unique=True)  # e.g. "abc-school"
    address = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    ROLE_CHOICES = [
        ("admin","Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    ]

    # NEW: every member belongs to one school (tenant)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="members",
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="member_profile",
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="student",
    )

    teacher_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )
    division = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    student_id = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    teacher = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="students",
    )

    can_add_student = models.BooleanField(default=True)
    can_delete_student = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.role})"
