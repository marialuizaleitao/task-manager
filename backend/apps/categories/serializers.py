from rest_framework import serializers

from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "color", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("O nome da categoria não pode ser vazio.")
        return value

    def validate(self, attrs: dict) -> dict:
        request = self.context["request"]
        name = attrs.get("name", getattr(self.instance, "name", None))

        duplicate_exists = (
            Category.objects.filter(owner=request.user, name__iexact=name)
            .exclude(pk=getattr(self.instance, "pk", None))
            .exists()
        )
        if duplicate_exists:
            raise serializers.ValidationError(
                {"name": "Você já possui uma categoria com este nome."}
            )
        return attrs
