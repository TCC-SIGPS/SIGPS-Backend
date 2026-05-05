import sys
from app.models import db, User
from run import app

def mudar_perfil(email, novo_perfil):
    perfis_validos = ['Paciente', 'Admin', 'Gestor', 'Especialista', 'Visualizador']
    
    if novo_perfil not in perfis_validos:
        print(f"Erro: O perfil '{novo_perfil}' é inválido.")
        print(f"Perfis válidos: {', '.join(perfis_validos)}")
        return

    with app.app_context():
        usuario = User.query.filter_by(email=email).first()
        if not usuario:
            print(f"Erro: Usuário com e-mail '{email}' não encontrado.")
            return
            
        perfil_antigo = usuario.perfil
        usuario.perfil = novo_perfil
        db.session.commit()
        print(f"Sucesso! O perfil de {usuario.nome} ({email}) foi alterado de '{perfil_antigo}' para '{novo_perfil}'.")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python mudar_perfil.py <email_do_usuario> <novo_perfil>")
        print("Exemplo: python mudar_perfil.py admin@teste.com Admin")
    else:
        mudar_perfil(sys.argv[1], sys.argv[2])
