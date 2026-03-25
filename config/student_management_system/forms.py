from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password
from .models import Member, School


class MemberForm(forms.ModelForm):
    # Form-only password field (not in Member model)
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(render_value=False),
        required=False,  # we'll enforce required-on-create in clean()
        max_length=128,
    )

    class Meta:
        model = Member
        fields = ['name', 'email', 'phone', 'role']  # no password here
        widgets = {
            'phone': forms.TextInput(attrs={
                'pattern': r'\d{10}',
                'title': 'Please enter a 10-digit phone number',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make role optional so teacher POST without role is valid
        if 'role' in self.fields:
            self.fields['role'].required = False

        # Default: password not required; we'll enforce it in clean() only for create
        self.fields['password'].required = False

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()

        if not phone.isdigit():
            raise forms.ValidationError(
                "Please enter a valid phone number using digits only."
            )

        if len(phone) != 10:
            raise forms.ValidationError("Please enter a 10-digit phone number.")

        return phone

    def clean(self):
        cleaned_data = super().clean()
        raw_password = cleaned_data.get('password')

        # If this is a CREATE (no pk yet) → password required
        if not self.instance.pk and not raw_password:
            raise forms.ValidationError("Password is required for new members.")

        return cleaned_data

    def save(self, commit=True):
        # This member is either new (no pk) or existing (has pk)
        member = super().save(commit=False)
        raw_password = self.cleaned_data.get('password')

        # ---------------- CREATE ----------------
        if not member.pk:
            # create auth user
            user = User.objects.create(
                username=member.email,
                email=member.email,
                password=make_password(raw_password),
                first_name=member.name,
            )
            member.user = user

            if not member.role:
                member.role = "student"

            if commit:
                member.save()

            # add user to group based on role
            teacher_group = Group.objects.get(name="Teacher")
            student_group = Group.objects.get(name="Student")

            if member.role == 'teacher':
                user.groups.add(teacher_group)
            else:
                user.groups.add(student_group)

        # ---------------- UPDATE ----------------
        else:
            user = member.user

            if user:
                # keep username == email in sync
                user.username = member.email
                user.email = member.email
                user.first_name = member.name

                # if password provided, change it; else keep old
                if raw_password:
                    user.password = make_password(raw_password)

                user.save()

                # update groups based on role
                teacher_group = Group.objects.get(name="Teacher")
                student_group = Group.objects.get(name="Student")
                user.groups.remove(teacher_group, student_group)

                if member.role == 'teacher':
                    user.groups.add(teacher_group)
                else:
                    user.groups.add(student_group)

            if commit:
                member.save()

        return member


class SchoolAdminSignupForm(forms.Form):
    school_name = forms.CharField(max_length=255, label="School name")
    school_code = forms.SlugField(max_length=50, label="School code")  # e.g. my-school

    admin_username = forms.CharField(max_length=150, label="Admin username")
    admin_email = forms.EmailField(label="Admin email")
    admin_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Admin password",
    )
    
class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "code", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "code": forms.TextInput(attrs={"class": "input"}),
            "address": forms.Textarea(attrs={"rows": 3, "class": "input"}),
        }