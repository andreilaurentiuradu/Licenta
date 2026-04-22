import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY       = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    KEYCLOAK_URL     = os.environ.get("KEYCLOAK_URL", "http://localhost:8180")
    KEYCLOAK_REALM   = "sport-analytics"
    KEYCLOAK_CLIENT_ID  = "sport-analytics-client"
    KEYCLOAK_ADMIN_USER = "admin"
    KEYCLOAK_ADMIN_PASS = "admin123"
    SQLALCHEMY_DATABASE_URI     = os.environ.get("DATABASE_URL", "postgresql://sa_user:sa_pass@localhost:5432/sportanalytics")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
