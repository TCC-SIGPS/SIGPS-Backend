from app.models import db, User
from run import app

def seed_admin():
    '''
    Só criará admin no sqlite, por questão de segurança
    '''
    with app.app_context():
        # Verifica se já existe
        admin = User.query.filter_by(email="admin@sigps.com").first()
        if not admin:
            admin = User(
                nome="Administrador do Sistema",
                email="admin@sigps.com",
                perfil="Admin"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Conta Admin criada com sucesso: admin@sigps.com / Senha: admin123")
        else:
            print("Conta Admin já existe: admin@sigps.com")


if __name__ == '__main__':
    seed_admin()


# Para criar usuário admin no MySQL, use:

# $env:DATABASE_URL='mysql+pymysql://user:senha@host:3306/dbname'
# python seed_admin.py