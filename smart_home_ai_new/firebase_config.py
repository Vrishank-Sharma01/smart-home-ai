from dotenv import load_dotenv
import os
import firebase_admin
from firebase_admin import credentials, db

load_dotenv(dotenv_path=".env")

def get_database():
    db_url = os.getenv("FIREBASE_DB_URL")

    if not db_url:
        raise ValueError("FIREBASE_DB_URL is not set. Check your .env file.")

    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")

        firebase_admin.initialize_app(cred, {
            "databaseURL": db_url
        })

    return db.reference("/")