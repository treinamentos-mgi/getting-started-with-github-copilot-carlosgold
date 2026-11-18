from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


@pytest.fixture
def client():
    return TestClient(app)


def test_root_redirects_to_static_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_data(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert "Chess Club" in response.json()
    assert "participants" in response.json()["Chess Club"]


def test_signup_adds_student_to_activity(client):
    response = client.post(
        "/activities/Soccer%20Club/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Signed up student@example.com for Soccer Club"
    }
    assert "student@example.com" in activities["Soccer Club"]["participants"]


def test_signup_returns_404_for_unknown_activity(client):
    response = client.post(
        "/activities/Unknown%20Club/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_returns_400_for_duplicate_student(client):
    response = client.post(
        "/activities/Chess%20Club/signup",
        params={"email": "michael@mergington.edu"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }


def test_signup_returns_409_when_activity_is_full(client):
    activity = activities["Soccer Club"]
    activity["participants"] = [
        f"student{index}@example.com"
        for index in range(activity["max_participants"])
    ]

    response = client.post(
        "/activities/Soccer%20Club/signup",
        params={"email": "new-student@example.com"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Activity is full"}


def test_signup_duplicate_takes_precedence_when_activity_is_full(client):
    activity = activities["Chess Club"]
    activity["participants"] = [
        "michael@mergington.edu",
        *(
            f"student{index}@example.com"
            for index in range(activity["max_participants"] - 1)
        ),
    ]

    response = client.post(
        "/activities/Chess%20Club/signup",
        params={"email": "michael@mergington.edu"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }


def test_cancel_signup_removes_student_from_activity(client):
    activities["Soccer Club"]["participants"].append("student@example.com")

    response = client.delete(
        "/activities/Soccer%20Club/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Cancelled student@example.com's signup for Soccer Club"
    }
    assert "student@example.com" not in activities["Soccer Club"]["participants"]


def test_cancel_signup_returns_404_for_unknown_activity(client):
    response = client.delete(
        "/activities/Unknown%20Club/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_cancel_signup_returns_404_for_unregistered_student(client):
    response = client.delete(
        "/activities/Soccer%20Club/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Student is not signed up for this activity"
    }