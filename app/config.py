import os

class Config:
    DB_HOST = os.environ.get('DB_HOST', 'postgres')
    DB_NAME = os.environ.get('DB_NAME', 'ueba_db')
    DB_USER = os.environ.get('DB_USER', 'ueba_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'ueba_pass')
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'votre-cle-secrete-tres-longue-et-securisee-pour-jwt')
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    
    UPLOAD_BASE_DIR = "/app/uploads"
    TRASH_DIR = "/app/uploads/trash"
    
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx',
        'xls', 'xlsx', 'ppt', 'pptx', 'py', 'js', 'html', 'css', 'json', 'xml', 'md'
    }