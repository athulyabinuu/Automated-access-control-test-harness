import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'securehub-demo-development-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'securehub.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
