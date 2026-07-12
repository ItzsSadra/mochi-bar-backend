import os
from app import create_app
from app.models import db
from app.init_db import initialize_database

app = create_app()

with app.app_context():
    db.create_all()
    initialize_database()

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
    )
