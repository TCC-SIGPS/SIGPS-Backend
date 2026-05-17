from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User, Paciente, Especialista, FilaAtendimento, Agenda, Consulta, Notification
from datetime import date, datetime, timedelta
import random

app = create_app('dev')

def seed_database():
    with app.app_context():
        print("--- Iniciando Seeder do Banco de Dados SIGPS ---")
        
        # 1. Limpeza de dados antigos de teste (@sigps.com)
        test_users = User.query.filter(User.email.like('%@sigps.com')).all()
        test_user_ids = [u.id for u in test_users]
        
        if test_user_ids:
            print(f"Limpando registros de {len(test_user_ids)} usuários de teste antigos...")
            
            test_pacientes = Paciente.query.filter(Paciente.user_id.in_(test_user_ids)).all()
            test_paciente_ids = [p.id for p in test_pacientes]
            
            if test_paciente_ids:
                FilaAtendimento.query.filter(FilaAtendimento.paciente_id.in_(test_paciente_ids)).delete(synchronize_session=False)
                Paciente.query.filter(Paciente.id.in_(test_paciente_ids)).delete(synchronize_session=False)
                
            Consulta.query.filter(Consulta.paciente_id.in_(test_user_ids)).delete(synchronize_session=False)
            
            agendas = Agenda.query.filter(Agenda.especialista_id.in_(test_user_ids)).all()
            agenda_ids = [a.id for a in agendas]
            if agenda_ids:
                Consulta.query.filter(Consulta.agenda_id.in_(agenda_ids)).delete(synchronize_session=False)
                Agenda.query.filter(Agenda.id.in_(agenda_ids)).delete(synchronize_session=False)
                
            Especialista.query.filter(Especialista.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            User.query.filter(User.id.in_(test_user_ids)).delete(synchronize_session=False)
            
            db.session.commit()
            print("Limpeza concluída com sucesso.")

        # 2. Criando 5 Especialistas (Médicos)
        print("Criando 5 especialistas...")
        especialistas_data = [
            {"nome": "Dr. Ricardo Santos", "email": "ricardo.santos@sigps.com", "especialidade": "Cardiologia", "genero": "Masculino", "crm": "123456", "uf": "SP", "tipo": "Médico", "conselho": "CRM"},
            {"nome": "Dra. Amanda Silva", "email": "amanda.silva@sigps.com", "especialidade": "Dermatologia", "genero": "Feminino", "crm": "234567", "uf": "SP", "tipo": "Médico", "conselho": "CRM"},
            {"nome": "Dr. Carlos Mendes", "email": "carlos.mendes@sigps.com", "especialidade": "Clínico Geral", "genero": "Masculino", "crm": "345678", "uf": "RJ", "tipo": "Médico", "conselho": "CRM"},
            {"nome": "Dra. Juliana Costa", "email": "juliana.costa@sigps.com", "especialidade": "Pediatria", "genero": "Feminino", "crm": "456789", "uf": "MG", "tipo": "Médico", "conselho": "CRM"},
            {"nome": "Dr. Roberto Lins", "email": "roberto.lins@sigps.com", "especialidade": "Ortopedia", "genero": "Masculino", "crm": "567890", "uf": "SP", "tipo": "Médico", "conselho": "CRM"}
        ]
        
        especialistas_db = []
        for esp in especialistas_data:
            user = User(
                nome=esp["nome"],
                email=esp["email"],
                perfil="Especialista",
                genero=esp["genero"]
            )
            user.set_password("Sigps@2026") # Senha padrão forte
            db.session.add(user)
            db.session.flush() # Recupera o user.id
            
            info = Especialista(
                user_id=user.id,
                especialidade=esp["especialidade"],
                tipo_profissional=esp["tipo"],
                conselho_tipo=esp["conselho"],
                numero_registro=esp["crm"],
                crm=esp["crm"],
                uf=esp["uf"],
                status_verificacao="verificado",
                sobre=f"Especialista em {esp['especialidade']} com ampla atuação clínica."
            )
            db.session.add(info)
            especialistas_db.append(user)

        # 3. Criando 15 Pacientes (8 Femininos, 7 Masculinos - aprox 53% F / 47% M)
        print("Criando 15 pacientes...")
        pacientes_data = [
            {"nome": "Maria Oliveira Ramos", "email": "maria.oliveira@sigps.com", "genero": "Feminino", "genero_sigla": "F", "cpf": "111.222.333-44", "nascimento": date(1985, 4, 12), "sangue": "O+", "telefone": "(11) 98765-4321"},
            {"nome": "João Pedro Silva", "email": "joao.pedro@sigps.com", "genero": "Masculino", "genero_sigla": "M", "cpf": "111.222.333-55", "nascimento": date(1992, 8, 24), "sangue": "A+", "telefone": "(11) 97654-3210"},
            {"nome": "Diana Prestes Medeiros", "email": "diana.prestes@sigps.com", "genero": "Feminino", "genero_sigla": "F", "cpf": "111.222.333-66", "nascimento": date(1978, 11, 5), "sangue": "B-", "telefone": "(21) 96543-2109"},
            {"nome": "Nilda Francisca de Souza", "email": "nilda.francisca@sigps.com", "genero": "Feminino", "genero_sigla": "F", "cpf": "111.222.333-77", "nascimento": date(1963, 2, 18), "sangue": "AB+", "telefone": "(31) 95432-1098"},
            {"nome": "Leandro Oliveira Baptista", "email": "leandro.oliveira@sigps.com", "genero": "Masculino", "genero_sigla": "M", "cpf": "111.222.333-88", "nascimento": date(1990, 5, 30), "sangue": "O-", "telefone": "(11) 94321-0987"},
            {"nome": "Lucas Souza Lima", "email": "lucas.souza@sigps.com", "genero": "Masculino", "genero_sigla": "M", "cpf": "111.222.333-99", "nascimento": date(1995, 12, 1), "sangue": "A-", "telefone": "(19) 93210-9876"},
            {"nome": "Camila Ferreira Santos", "email": "camila.ferreira@sigps.com", "genero": "Feminino", "genero_sigla": "F", "cpf": "222.333.444-11", "nascimento": date(1988, 7, 14), "sangue": "O+", "telefone": "(11) 92109-8765"},
            {"nome": "Arthur Ramos Costa", "email": "arthur.ramos@sigps.com", "genero": "Masculino", "genero_sigla": "M", "cpf": "222.333.444-22", "nascimento": date(2001, 3, 22), "sangue": "B+", "telefone": "(21) 91098-7654"},
            {"nome": "Beatriz Costa Pinto", "email": "beatriz.costa@sigps.com", "genero": "Feminino", "genero_sigla": "F", "cpf": "222.333.444-33", "nascimento": date(1999, 10, 8), "sangue": "A+", "telefone": "(31) 90987-6543"},
            {"nome": "Gabriel Santos Silva", "email": "gabriel.santos@sigps.com", "genero": "Masculino", "genero_sigla": "M", "cpf": "222.333.444-44", "nascimento": date(1982, 1, 15), "sangue": "O+", "telefone": "(11) 89876-5432"},
            {"nome": "Letícia Abreu Mendes", "email": "leticia.abreu@sigps.com", "genero": "Feminino", "genero_sigla": "F", "cpf": "222.333.444-55", "nascimento": date(1994, 9, 3), "sangue": "AB-", "telefone": "(21) 88765-4321"},
            {"nome": "Pedro Alves Rocha", "email": "pedro.alves@sigps.com", "genero": "Masculino", "genero_sigla": "M", "cpf": "222.333.444-66", "nascimento": date(1975, 6, 29), "sangue": "B+", "telefone": "(31) 87654-3210"},
            {"nome": "Mariana Lima Duarte", "email": "mariana.lima@sigps.com", "genero": "Feminino", "genero_sigla": "F", "cpf": "222.333.444-77", "nascimento": date(1993, 2, 11), "sangue": "O-", "telefone": "(11) 86543-2109"},
            {"nome": "Thiago Rocha Nascimento", "email": "thiago.rocha@sigps.com", "genero": "Masculino", "genero_sigla": "M", "cpf": "222.333.444-88", "nascimento": date(1987, 8, 19), "sangue": "A+", "telefone": "(19) 85432-1098"},
            {"nome": "Sofia Azevedo Dias", "email": "sofia.azevedo@sigps.com", "genero": "Feminino", "genero_sigla": "F", "cpf": "222.333.444-99", "nascimento": date(2003, 5, 25), "sangue": "B-", "telefone": "(11) 84321-0987"}
        ]
        
        pacientes_db = []
        for pac in pacientes_data:
            user = User(
                nome=pac["nome"],
                email=pac["email"],
                perfil="Paciente",
                genero=pac["genero"]
            )
            user.set_password("Sigps@2026")
            db.session.add(user)
            db.session.flush()
            
            info = Paciente(
                user_id=user.id,
                cpf=pac["cpf"],
                data_nascimento=pac["nascimento"],
                genero=pac["genero_sigla"],
                telefone=pac["telefone"],
                tipo_sanguineo=pac["sangue"],
                alergias="Nenhuma alergia relatada pelo paciente."
            )
            db.session.add(info)
            pacientes_db.append(info)

        db.session.commit()
        print("Usuários e perfis secundários criados com sucesso.")

        # 4. Triagem Inteligente (Fila de Espera com 3 pacientes)
        print("Criando fila de espera ativa...")
        # Adiciona 3 pacientes à fila
        fila_data = [
            {"paciente": pacientes_db[1], "prioridade": 2, "score": 75},  # João Pedro Silva (Amarelo)
            {"paciente": pacientes_db[0], "prioridade": 1, "score": 40},  # Maria Oliveira Ramos (Verde)
            {"paciente": pacientes_db[2], "prioridade": 3, "score": 95}   # Diana Prestes Medeiros (Vermelho)
        ]
        
        for item in fila_data:
            registro = FilaAtendimento(
                paciente_id=item["paciente"].id,
                prioridade=item["prioridade"],
                score=item["score"],
                status='Aguardando',
                data_chegada=datetime.now() - timedelta(minutes=random.randint(5, 30))
            )
            db.session.add(registro)

        # 5. Agendas e Consultas Históricas (Preenchendo os últimos 6 meses)
        print("Criando agendas e consultas históricas...")
        # Cria agendas para os especialistas
        agendas_db = []
        base_date = datetime.now()
        
        for esp in especialistas_db:
            # Cria 5 agendas em datas diferentes no passado
            for d_offset in [10, 30, 60, 90, 120, 150]:
                data_agenda = (base_date - timedelta(days=d_offset)).date()
                agenda = Agenda(
                    especialista_id=esp.id,
                    data=data_agenda,
                    horarios_disponiveis="09:00,10:00,11:00,14:00,15:00"
                )
                db.session.add(agenda)
                db.session.flush()
                agendas_db.append(agenda)

        # Cria 15 consultas históricas distribuídas nos meses de Dez, Jan, Fev, Mar, Abr, Mai
        # Mapeamento aproximado de meses passados:
        # 5 meses atrás = Dez, 4 = Jan, 3 = Fev, 2 = Mar, 1 = Abr, 0 = Mai
        consultas_distribucion = [
            {"offset_months": 5, "count": 1, "label": "Dez"},
            {"offset_months": 4, "count": 2, "label": "Jan"},
            {"offset_months": 3, "count": 2, "label": "Fev"},
            {"offset_months": 2, "count": 3, "label": "Mar"},
            {"offset_months": 1, "count": 3, "label": "Abr"},
            {"offset_months": 0, "count": 4, "label": "Mai"}
        ]
        
        consulta_idx = 0
        for dist in consultas_distribucion:
            days_ago = dist["offset_months"] * 30
            for _ in range(dist["count"]):
                # Seleciona uma agenda correspondente a essa janela de tempo
                target_date = base_date - timedelta(days=days_ago + random.randint(1, 15))
                agenda = Agenda(
                    especialista_id=especialistas_db[random.randint(0, 4)].id,
                    data=target_date.date(),
                    horarios_disponiveis="09:00"
                )
                db.session.add(agenda)
                db.session.flush()
                
                # Associa a um paciente e cria a consulta com a data correspondente
                paciente_user = pacientes_db[consulta_idx % len(pacientes_db)].usuario
                consulta = Consulta(
                    agenda_id=agenda.id,
                    paciente_id=paciente_user.id,
                    horario="09:00",
                    status="Finalizada",
                    created_at=target_date
                )
                db.session.add(consulta)
                consulta_idx += 1

        # 5. Semeando Notificações de teste para Pacientes e Especialistas
        print("Semeando Notificações de teste...")
        Notification.query.delete()

        for p in pacientes_db:
            notif_exame = Notification(
                user_id=p.user_id,
                message="Seu Exame 'Raio-X Tórax' está Disponível",
                route="/painel/exames"
            )
            notif_agenda = Notification(
                user_id=p.user_id,
                message="Consulta com Dr. Ricardo Santos confirmada",
                route="/painel/agendas"
            )
            db.session.add(notif_exame)
            db.session.add(notif_agenda)

        for esp in especialistas_db:
            notif_esp = Notification(
                user_id=esp.id,
                message="Novo agendamento: Paciente Carlos da Silva (Dia 20/05/2026 às 14:00h)",
                route="/painel/agendas"
            )
            db.session.add(notif_esp)

        db.session.commit()
        print("==================================================")
        print("BANCO DE DADOS POPULADO COM SUCESSO!")
        print("==================================================")
        print("- 5 Médicos Especialistas ativos cadastrados.")
        print("- 15 Pacientes SUS reais cadastrados (53% Fem / 47% Masc).")
        print("- 3 Pacientes críticos na Sala de Espera ativa.")
        print("- 15 Consultas históricas mapeadas nos últimos 6 meses.")
        print("==================================================")

if __name__ == "__main__":
    seed_database()
