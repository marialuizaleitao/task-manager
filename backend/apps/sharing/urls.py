from django.urls import path

from .views import SharedTaskListView

app_name = "sharing"

urlpatterns = [
    path("shared-tasks/", SharedTaskListView.as_view(), name="shared-task-list"),
]
