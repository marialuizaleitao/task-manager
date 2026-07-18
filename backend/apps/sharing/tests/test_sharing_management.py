import pytest
from django.urls import reverse
from rest_framework import status

from apps.sharing.models import TaskShare
from apps.tasks.models import Task


def shares_url(task_id: int) -> str:
    return reverse("tasks:task-shares", args=[task_id])


def remove_share_url(task_id: int, share_id: int) -> str:
    return reverse("tasks:task-remove-share", args=[task_id, share_id])


@pytest.fixture
def task(user) -> Task:
    return Task.objects.create(owner=user, title="Tarefa a compartilhar")


@pytest.mark.django_db
def test_owner_can_share_task(authenticated_client, task, another_user):
    response = authenticated_client.post(
        shares_url(task.id), {"email": another_user.email, "permission": "read"}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert TaskShare.objects.filter(task=task, shared_with=another_user).exists()
    assert response.data["shared_with"]["email"] == another_user.email
    assert response.data["permission"] == "read"


@pytest.mark.django_db
def test_owner_can_list_shares(authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    response = authenticated_client.get(shares_url(task.id))

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["shared_with"]["email"] == another_user.email


@pytest.mark.django_db
def test_owner_can_remove_share(authenticated_client, task, another_user):
    share = TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    response = authenticated_client.delete(remove_share_url(task.id, share.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not TaskShare.objects.filter(id=share.id).exists()


@pytest.mark.django_db
def test_cannot_remove_nonexistent_share(authenticated_client, task):
    response = authenticated_client.delete(remove_share_url(task.id, 9999))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_cannot_share_task_with_self(authenticated_client, task, user):
    response = authenticated_client.post(
        shares_url(task.id), {"email": user.email, "permission": "read"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data
    assert not TaskShare.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_cannot_share_task_with_nonexistent_email(authenticated_client, task):
    response = authenticated_client.post(
        shares_url(task.id), {"email": "ninguem@example.com", "permission": "read"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data


@pytest.mark.django_db
def test_cannot_share_task_twice_with_same_user(authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    response = authenticated_client.post(
        shares_url(task.id), {"email": another_user.email, "permission": "edit"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data
    assert TaskShare.objects.filter(task=task, shared_with=another_user).count() == 1


@pytest.mark.django_db
def test_share_requires_valid_permission_choice(authenticated_client, task, another_user):
    response = authenticated_client.post(
        shares_url(task.id), {"email": another_user.email, "permission": "admin"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "permission" in response.data


@pytest.mark.django_db
def test_sharing_requires_authentication(api_client, task):
    response = api_client.get(shares_url(task.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_shared_user_with_edit_cannot_share_with_third_party(
    authenticated_client, another_authenticated_client, task, another_user, third_user
):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="edit")

    response = another_authenticated_client.post(
        shares_url(task.id), {"email": third_user.email, "permission": "read"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not TaskShare.objects.filter(shared_with=third_user).exists()


@pytest.mark.django_db
def test_shared_user_cannot_list_shares(authenticated_client, another_authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    response = another_authenticated_client.get(shares_url(task.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_shared_user_cannot_remove_share(authenticated_client, another_authenticated_client, task, another_user):
    share = TaskShare.objects.create(task=task, shared_with=another_user, permission="edit")

    response = another_authenticated_client.delete(remove_share_url(task.id, share.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert TaskShare.objects.filter(id=share.id).exists()


@pytest.mark.django_db
def test_unrelated_user_cannot_manage_shares_of_alien_task(third_authenticated_client, task):
    response = third_authenticated_client.get(shares_url(task.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
