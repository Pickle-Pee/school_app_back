from fastapi import status


def test_login_teacher(client, seed_data):
    response = client.post(
        "/auth/login",
        json={
            "phone": seed_data["teacher"].phone,
            "password": "teacher123",
            "teacher_code": "TCH-001",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["role"] == "teacher"
    assert data["user"]["phone"] == seed_data["teacher"].phone


def test_login_student(client, seed_data):
    response = client.post(
        "/auth/login",
        json={
            "phone": seed_data["student"].phone,
            "password": "student123",
            "teacher_code": None,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["role"] == "student"
    assert data["user"]["phone"] == seed_data["student"].phone
