import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="../frontend/.env")
api_key = os.environ.get("VITE_FIREBASE_API_KEY")
url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

passwords = ["admin", "admin123", "password", "password123", "admin@system.local", "123456", "12345678"]
for p in passwords:
    res = requests.post(url, json={"email": "admin@system.local", "password": p, "returnSecureToken": True})
    if res.status_code == 200:
        token = res.json()["idToken"]
        print(f"Success with {p}!")
        with open("token.txt", "w") as f:
            f.write(token)
        break
else:
    print("Failed to find password.")
