from io import TextIOWrapper
import csv

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from .forms import MemberForm, SchoolAdminSignupForm, SchoolForm
from .models import Member, School


# ---------- Role helpers ----------


def is_admin(user):
    # App-level admin = superuser in this project
    return user.is_authenticated and user.is_superuser


def is_teacher(user):
    return (
        user.is_authenticated
        and user.groups.filter(name="Teacher").exists()
    )


def is_student(user):
    return (
        user.is_authenticated
        and user.groups.filter(name="Student").exists()
    )


def is_global_superuser(user):
    # Same as is_admin now; kept separate in case you change later
    return user.is_authenticated and user.is_superuser


# ---------- Auth views ----------


def login_page(request):
    return render(request, "login.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")  # you are using email as username
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            return render(
                request,
                "login.html",
                {"error": "Invalid email or password"},
            )
    else:
        return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# ---------- Home (RBAC: admin / teacher / student, multi-school) ----------


@login_required
def home(request):
    user = request.user

    is_admin_flag = is_admin(user)
    is_teacher_flag = is_teacher(user)
    is_student_flag = is_student(user)

    # ----- Ensure we have member_profile and school -----
    member_profile = getattr(user, "member_profile", None)
    current_school = getattr(member_profile, "school", None)

    if member_profile is None:
        # Create or get a default school
        default_school, _ = School.objects.get_or_create(
            code="default-school",
            defaults={"name": "Default School"},
        )

        # Decide role for this new profile
        if is_admin_flag:
            role_value = "admin"
        elif is_teacher_flag:
            role_value = "teacher"
        else:
            role_value = "student"

        # Create a basic Member profile for this user
        member_profile = Member.objects.create(
            user=user,
            name=user.get_full_name() or user.username,
            email=user.email or f"{user.username}@example.com",
            phone="0000000000",
            role=role_value,
            school=default_school,
        )

    current_school = member_profile.school

    # ----- Dashboard counts (admin within their school) -----
    total_members = teachers_count = students_count = None
    if is_admin_flag and current_school is not None:
        total_members = Member.objects.filter(
            school=current_school
        ).count()
        teachers_count = Member.objects.filter(
            school=current_school,
            role="teacher",
        ).count()
        students_count = Member.objects.filter(
            school=current_school,
            role="student",
        ).count()

    form = None

    # ================== POST ==================
    if request.method == "POST":
        print("DEBUG MODE:", request.POST.get("mode"))
        print("DEBUG MEMBER_ID:", request.POST.get("member_id"))
        mode = request.POST.get("mode", "add")
        member_id = request.POST.get("member_id")

        # ---------- ADMIN ----------
        if is_admin_flag:
            if mode == "edit" and member_id:
                # update existing member (only within this school)
                member = get_object_or_404(
                    Member,
                    id=member_id,
                    school=current_school,
                )
                form = MemberForm(request.POST, instance=member)
            else:
                # add new member
                form = MemberForm(request.POST)

            if form.is_valid():
                member = form.save(commit=False)
                member.school = current_school  # enforce school
                member.save()
                messages.success(request, "Member saved successfully.")
                return redirect("home")
            else:
                print("DEBUG FORM ERRORS (ADMIN):", form.errors)

        # ---------- TEACHER ----------
        elif is_teacher_flag:
            if not member_profile.can_add_student:
                messages.error(
                    request,
                    "You do not have permission to add or edit students.",
                )
                return redirect("home")

            if mode == "edit" and member_id:
                member = get_object_or_404(
                    Member,
                    id=member_id,
                    school=current_school,
                )
                if (
                    member.role != "student"
                    or member.teacher_id != member_profile.id
                ):
                    messages.error(
                        request,
                        "You do not have permission to edit this member.",
                    )
                    return redirect("home")

                form = MemberForm(request.POST, instance=member)
                if form.is_valid():
                    student = form.save(commit=False)
                    # enforce role, teacher, and school
                    student.role = "student"
                    student.teacher = member_profile
                    student.school = current_school
                    student.save()

                    messages.success(request, "Student updated successfully.")
                    return redirect("home")
                else:
                    print("DEBUG FORM ERRORS (TEACHER EDIT):", form.errors)
            else:
                # add new student
                form = MemberForm(request.POST)
                if form.is_valid():
                    member = form.save(commit=False)
                    member.role = "student"          # force student
                    member.teacher = member_profile  # link to this teacher
                    member.school = current_school   # ensure same school
                    member.save()
                    messages.success(request, "Student added successfully.")
                    return redirect("home")
                else:
                    print("DEBUG FORM ERRORS (TEACHER ADD):", form.errors)

        else:
            form = None

    # ================== GET ==================
    else:
        if is_admin_flag or is_teacher_flag:
            form = MemberForm()
        else:
            form = None

    # ----- Which members to show in table (filter by school) -----
    if is_admin_flag:
        members = Member.objects.filter(school=current_school)
    elif is_teacher_flag:
        me = member_profile
        members = Member.objects.filter(school=current_school).filter(
            Q(id=me.id) | Q(teacher=me)
        )
    elif is_student_flag:
        members = Member.objects.filter(
            school=current_school,
            user=user,
        )
    else:
        members = Member.objects.none()

    return render(
        request,
        "home.html",
        {
            "members": members,
            "form": form,
            "is_admin": is_admin_flag,
            "is_teacher": is_teacher_flag,
            "is_student": is_student_flag,
            "total_members": total_members,
            "teachers_count": teachers_count,
            "students_count": students_count,
        },
    )


# ---------- Delete Member ----------


@login_required
def delete_member(request, id):
    user = request.user
    member_profile = getattr(user, "member_profile", None)
    current_school = getattr(member_profile, "school", None)

    # Only delete inside current school
    member = get_object_or_404(
        Member,
        id=id,
        school=current_school,
    )

    if is_admin(user):
        allowed = True
    elif is_teacher(user):
        teacher_profile = member_profile
        allowed = (
            teacher_profile.can_delete_student
            and member.teacher_id == teacher_profile.id
            and member.role == "student"
        )
    else:
        allowed = False

    if not allowed:
        messages.error(
            request,
            "You do not have permission to delete this member.",
        )
        return redirect("home")

    if request.method == "POST":
        if member.user:
            member.user.delete()
        member.delete()
        return redirect("home")

    # form submits directly with confirm(), so just redirect
    return redirect("home")


# ---------- Import / Export (admin only) ----------


@login_required
@user_passes_test(is_admin)
def export_members_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename=\"members.csv\"'

    writer = csv.writer(response)
    writer.writerow(["id", "name", "email", "phone", "role"])

    # export only current admin's school members
    member_profile = getattr(request.user, "member_profile", None)
    current_school = getattr(member_profile, "school", None)
    qs = Member.objects.all()
    if current_school is not None:
        qs = qs.filter(school=current_school)

    for m in qs:
        writer.writerow([m.id, m.name, m.email, m.phone, m.role])

    return response


@login_required
@user_passes_test(is_admin)
def manage_teacher_permissions(request):
    member_profile = getattr(request.user, "member_profile", None)
    current_school = getattr(member_profile, "school", None)

    if current_school is not None:
        teachers = Member.objects.filter(
            school=current_school,
            role="teacher",
        )
    else:
        teachers = Member.objects.filter(role="teacher")

    if request.method == "POST":
        print("DEBUG: manage_teacher_permissions POST", request.POST)
        teacher_id = request.POST.get("teacher_id")
        can_add = request.POST.get("can_add_student") == "on"
        can_del = request.POST.get("can_delete_student") == "on"

        teacher = get_object_or_404(Member, id=teacher_id, role="teacher")
        teacher.can_add_student = can_add
        teacher.can_delete_student = can_del
        teacher.save()
        return redirect("manage_teacher_permissions")

    return render(
        request,
        "manage_teacher_permissions.html",
        {"teachers": teachers},
    )


@login_required
@user_passes_test(is_admin)
def import_members_csv(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        wrapped = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapped)

        created = 0
        skipped = 0

        teacher_group, _ = Group.objects.get_or_create(name="Teacher")
        student_group, _ = Group.objects.get_or_create(name="Student")

        # current school for this admin; we will import into this tenant
        member_profile = getattr(request.user, "member_profile", None)
        current_school = getattr(member_profile, "school", None)

        for row in reader:
            name = row.get("name", "").strip()
            email = row.get("email", "").strip()
            phone = row.get("phone", "").strip()
            role = (
                row.get("role", "student").strip().lower() or "student"
            )
            raw_password = (
                row.get("password", "").strip() or "default123"
            )

            if role not in ["teacher", "student"]:
                role = "student"

            if not email:
                skipped += 1
                continue

            # If member already exists, skip
            if Member.objects.filter(email=email).exists():
                skipped += 1
                continue

            # Create auth user
            user = User.objects.create(
                username=email,
                email=email,
                password=make_password(raw_password),
                first_name=name,
            )

            # Create member linked to user
            member = Member.objects.create(
                user=user,
                name=name,
                email=email,
                phone=phone,
                role=role,
                school=current_school,  # assign to this admin's school
            )

            # Add user to proper group (Teacher/Student)
            if role == "teacher":
                user.groups.add(teacher_group)
            else:
                user.groups.add(student_group)

            created += 1

        messages.success(
            request,
            f"Imported {created} members, skipped {skipped} existing/invalid rows.",
        )
        return redirect("home")

    return render(request, "import_members.html")


# ---------- Create School + Admin (global superuser only) ----------


@user_passes_test(is_global_superuser)
def create_school_and_admin(request):
    if request.method == "POST":
        form = SchoolAdminSignupForm(request.POST)
        if form.is_valid():
            school_name = form.cleaned_data["school_name"]
            school_code = form.cleaned_data["school_code"]

            admin_username = form.cleaned_data["admin_username"]
            admin_email = form.cleaned_data["admin_email"]
            admin_password = form.cleaned_data["admin_password"]

            try:
                with transaction.atomic(): #either everything succeeds or everything fails
                    # 1) Create School
                    school = School.objects.create(
                        name=school_name,
                        code=school_code,
                    )

                    # 2) Create User (school admin)
                    user = User.objects.create_user(
                        username=admin_username,
                        email=admin_email,
                        password=admin_password,
                    )
                    # Give them staff + superuser for now so they can access /admin/
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()

                    # 3) Create Member profile for this admin (role="admin")
                    Member.objects.create(
                        user=user,
                        school=school,
                        name=f"{school_name} Admin",
                        email=admin_email,
                        phone="",
                        role="admin",
                    )

                messages.success(
                    request,
                    "School and admin created successfully.",
                )
                return redirect("super_admin_dashboard")
            except Exception as e:
                messages.error(request, f"Error: {e}")
    else:
        form = SchoolAdminSignupForm()

    return render(request, "create_school_admin.html", {"form": form})


# ---------- Super Admin Dashboard ----------


@user_passes_test(is_global_superuser)
def super_admin_dashboard(request):
    schools = list(School.objects.all())
    admins = Member.objects.filter(role="admin").select_related(
        "school",
        "user",
    )

    admin_by_school = {a.school_id: a for a in admins}

    rows = []
    for s in schools:
        rows.append(
            {
                "school": s,
                "admin": admin_by_school.get(s.id),
            }
        )

    return render(
        request,
        "super_admin_dashboard.html",
        {"rows": rows},
    )

@user_passes_test(is_global_superuser)
def edit_school(request, school_id):
    school = get_object_or_404(School, id=school_id)

    if request.method == "POST":
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "School updated successfully.")
            return redirect("super_admin_dashboard")
    else:
        form = SchoolForm(instance=school)

    return render(request, "edit_school.html", {"form": form, "school": school})


@user_passes_test(is_global_superuser)
def delete_school(request, school_id):
    school = get_object_or_404(School, id=school_id)

    if request.method == "POST":
        school.delete()
        messages.success(request, "School deleted (and its members) successfully.")
        return redirect("super_admin_dashboard")

    return render(request, "confirm_delete_school.html", {"school": school})
