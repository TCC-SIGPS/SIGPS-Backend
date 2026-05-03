import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_swagger_ui import get_swaggerui_blueprint
from app.fila import bp_fila as fila_blueprint
from app.exames import bp_exames as exames_blueprint
from app.models import db
from app.auth import auth as auth_blueprint
from app.pacientes import bp_paciente as paciente_blueprint

app = Flask(__name__)

SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Sistema SIGPS - API Documentation"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

#Configuração de CORS para comunicação com o Angular
CORS(app) 

#Configurações de Pasta de Upload e Segurança
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'exames')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

#Configurações de Banco de Dados e JWT
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456%40@localhost/sigps_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key' 

#Inicializa o Banco e o Gerenciador de Token
db.init_app(app)
jwt = JWTManager(app) 

#Tratamento de Erros de Token
@jwt.expired_token_loader
def my_expired_token_callback(jwt_header, jwt_payload):
    return {"message": "O token expirou. Por favor, faça login novamente."}, 401

#Registro dos Blueprints
app.register_blueprint(auth_blueprint)
app.register_blueprint(paciente_blueprint)
app.register_blueprint(exames_blueprint)
app.register_blueprint(fila_blueprint)

#Cria as tabelas automaticamente
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)