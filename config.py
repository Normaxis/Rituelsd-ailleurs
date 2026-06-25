from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)

class Config:
    SECRET_KEY = 'change-me-in-production'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{INSTANCE_DIR / 'ritual_manager.sqlite'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / 'app' / 'static' / 'uploads'
