from app.extension import db
from app import create_app
try:
 if db is None:
        raise RuntimeError("Database not initialized. Ensure that the database is set up correctly and the app context is active.❌")
 else:
        print("Database initialized successfully.✅")
        app = create_app()
except Exception as e:
    print(f"Error occurred: {e}")