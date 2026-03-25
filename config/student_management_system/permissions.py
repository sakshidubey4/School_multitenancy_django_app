from rest_framework import permissions
from .models import Member


class MemberRBACPermission(permissions.BasePermission):
    """
    Custom RBAC:
    - Admin (is_staff): full access.
    - Teacher: can see/edit self and own students.
    - Student: can only read self.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Admin: full access
        if user.is_staff:
            return True

        # Get Member profile
        try:
            member = user.member_profile
        except Member.DoesNotExist:
            return False

        # Students: read-only
        if member.role == "student":
            return request.method in permissions.SAFE_METHODS

        # Teachers: allow all methods for now, object-level will restrict which objects
        if member.role == "teacher":
            return True

        # Default: deny
        return False

    def has_object_permission(self, request, view, obj):
        """
        Object-level checks for a specific Member instance (obj).
        """
        user = request.user

        # Admin: full access
        if user.is_staff:
            return True

        try:
            me = user.member_profile
        except Member.DoesNotExist:
            return False

        # Student: only their own Member record, read-only (handled in has_permission)
        if me.role == "student":
            return obj.user_id == user.id

        # Teacher:
        if me.role == "teacher":
            # Teacher can see/edit their own Member record
            if obj.user_id == user.id:
                return True
            # Teacher can see/manage only their own students
            return obj.teacher_id == me.id

        return False
