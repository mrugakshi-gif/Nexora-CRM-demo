import os
import base64
import json
import firebase_admin
from firebase_admin import credentials

_initialized = False

def init_firebase():
    global _initialized
    if _initialized:
        return
        
    try:
        # Check if already initialized by another module/test
        firebase_admin.get_app()
        _initialized = True
        return
    except ValueError:
        pass # Not initialized yet

    cred_base64 = os.environ.get("FIREBASE_CREDENTIALS_BASE64")
    
    try:
        if cred_base64:
            # Decode base64 JSON credentials
            cred_json = base64.b64decode(cred_base64).decode('utf-8')
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin initialized via FIREBASE_CREDENTIALS_BASE64.")
        else:
            # Fallback to Anonymous Credentials if ADC is missing (allows token verification to work locally)
            from google.auth.credentials import AnonymousCredentials
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", os.environ.get("FIREBASE_PROJECT_ID", "ai-enterprise-crm"))
            firebase_admin.initialize_app(AnonymousCredentials(), options={'projectId': project_id})
            print(f"Firebase Admin initialized via Anonymous Credentials for project: {project_id}.")

            
        _initialized = True
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Firebase Admin SDK: {e}")
        print("Ensure FIREBASE_CREDENTIALS_BASE64 is set or GOOGLE_APPLICATION_CREDENTIALS is valid.")
        raise
