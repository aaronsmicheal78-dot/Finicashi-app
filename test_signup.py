import requests

BASE_URL = "http://127.0.0.1:5000"

def test_signup():
    url = f"{BASE_URL}/api/signup"
    data = {
        "fullName": "Test User",
        "email": "testuser@example.com",
        "phone": "+256700000001",
        "password": "TestPass123"
    }
    response = requests.post(url, json=data)
    print("Signup:", response.status_code, response.text)

def test_login():
    url = f"{BASE_URL}/api/login"
    data = {
        "email_or_phone": "testuser@example.com",
        "password": "TestPass123"
    }
    session = requests.Session()
    response = session.post(url, json=data)
    print("Login:", response.status_code, response.text)
    return session

def test_profile(session):
    url = f"{BASE_URL}/api/user/profile"
    response = session.get(url)
    print("Profile:", response.status_code, response.text)

def main():
    test_signup()
    session = test_login()
    test_profile(session)

if __name__ == "__main__":
    main()
