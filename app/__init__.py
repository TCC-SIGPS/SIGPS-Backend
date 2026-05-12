import os
from flask import Flask, send_from_directory, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from .config import config_by_name
from .extensions import db, jwt, cors

def create_app(config_name='dev'):
    app = Flask(__name__, static_folder='../static')
    app.config.from_object(config_by_name[config_name])

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)

    @jwt.expired_token_loader
    def my_expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"message": "O token expirou. Por favor, faça login novamente."}), 401

    register_blueprints(app)

    SWAGGER_URL = '/docs'
    API_URL = '/static/swagger.json'
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Sistema SIGPS - API Documentation"
        }
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


    return app

def register_blueprints(app):
    from app.routes.auth import auth as auth_blueprint
    from app.routes.pacientes import bp_paciente as paciente_blueprint
    from app.routes.exames import bp_exames as exames_blueprint
    from app.routes.fila import bp_fila as fila_blueprint
    from app.routes.chat import bp_chat as chat_blueprint
    from app.routes.agendas import bp_agendas as agendas_blueprint
    from app.routes.admin import bp_admin as admin_blueprint
    from app.routes.specialists import bp_specialists as specialists_blueprint
    from app.routes.clinicas import bp_clinicas as clinicas_blueprint
    from app.routes.perfil import bp_perfil as perfil_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(paciente_blueprint)
    app.register_blueprint(exames_blueprint)
    app.register_blueprint(fila_blueprint)
    app.register_blueprint(chat_blueprint)
    app.register_blueprint(agendas_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(specialists_blueprint)
    app.register_blueprint(clinicas_blueprint)
    app.register_blueprint(perfil_blueprint)
