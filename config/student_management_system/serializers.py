from rest_framework import serializers
from .models import Member


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        # Expose fields but not the linked auth user or password
        fields = ["id", "name", "email", "phone", "role"]
