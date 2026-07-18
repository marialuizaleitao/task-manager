import django_filters

from .models import Task

# Reutilizados por TaskViewSet e SharedTaskListView, para que "minhas tarefas"
# e "compartilhadas comigo" ofereçam exatamente a mesma busca e ordenação.
TASK_SEARCH_FIELDS = ["title", "description"]
TASK_ORDERING_FIELDS = ["title", "due_date", "created_at", "updated_at"]


class TaskFilterSet(django_filters.FilterSet):
    """Filtros combináveis de tarefas.

    category aceita o sentinel "none" (tarefas sem categoria) além de um id —
    por isso é declarado manualmente em vez de deixar o django-filter gerar
    um ModelChoiceFilter a partir do campo do model, que rejeitaria "none".
    """

    category = django_filters.CharFilter(method="filter_category")
    due_date_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    due_date_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")

    class Meta:
        model = Task
        fields = ["completed"]

    def filter_category(self, queryset, name, value):
        if value == "none":
            return queryset.filter(category__isnull=True)
        if not value.isdigit():
            # Um id inválido não deve virar 500 (o comportamento manual da
            # Sprint 3 fazia exatamente isso): tratamos como "nenhuma tarefa
            # corresponde", que é semanticamente correto e sempre retorna 200.
            return queryset.none()
        return queryset.filter(category_id=value)
