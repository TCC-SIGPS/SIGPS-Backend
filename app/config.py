import os

def get_database_url():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url
        
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '3306')
    db_name = os.environ.get('DB_NAME')
    
    if all([db_user, db_password, db_host, db_name]):
        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return None

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-key'
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'exames')

class DevelopmentConfig(Config):
    DEBUG = True
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__name__)))
    SQLALCHEMY_DATABASE_URI = get_database_url() or 'sqlite:///' + os.path.join(basedir, 'sigps_db.sqlite')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret'

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = get_database_url()

config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig
)
