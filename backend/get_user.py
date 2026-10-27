import firebase_admin
from firebase_admin import credentials, auth
from google.auth.credentials import AnonymousCredentials

try:
    firebase_admin.initialize_app(AnonymousCredentials(), options={'projectId': 'ai-enterprise-crm'})
    user = auth.get_user_by_email('admin@system.local')
    print("Email:", user.email)
    print("UID:", user.uid)
    print("Email Verified:", user.email_verified)
except Exception as e:
    print("Error:", repr(e))
