import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env antes de inicializar a aplicação
load_dotenv()
from app import create_app
from app.extensions import db

env = os.environ.get('FLASK_ENV', 'dev')
# Fallback to dev if 'development' is provided
if env == 'development':
    env = 'dev'
elif env == 'production':
    env = 'prod'

app = create_app(env)

def garantir_banco_de_dados():
    db_name = os.environ.get('DB_NAME')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '3306')
    
    if all([db_name, db_user, db_password, db_host]):
        try:
            import pymysql
            # Conecta sem especificar o banco de dados
            conn = pymysql.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_password.replace('%40', '@')
            )
            c = conn.cursor()
            c.execute(f"CREATE DATABASE IF NOT EXISTS {db_name};")
            conn.close()
        except Exception as e:
            print(f"Erro ao tentar garantir a existência do banco: {e}")

with app.app_context():
    garantir_banco_de_dados()
    db.create_all()

if __name__ == "__main__":
    app.run(debug=(env == 'dev'))