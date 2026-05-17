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

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=(env == 'dev'))