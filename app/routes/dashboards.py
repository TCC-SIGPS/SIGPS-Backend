from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Paciente, Consulta, FilaAtendimento, Agenda
from datetime import datetime, date, timedelta

bp_dashboards = Blueprint('dashboards', __name__, url_prefix='/api/v1/dashboards')

@bp_dashboards.route('/', methods=['GET'])
@jwt_required()
def get_dashboard_data():
    user_id = int(get_jwt_identity())
    usuario = User.query.get(user_id)
    
    if not usuario:
        return jsonify({"message": "Usuário não encontrado"}), 404

    # Período do Filtro: diario, mensal, anual (padrão: mensal)
    periodo = request.args.get('periodo', 'mensal')
    hoje = date.today()

    # 1. Total de Pacientes no Banco (Permanecendo como total geral para métrica de demografia da clínica)
    total_pacientes = Paciente.query.count()
    
    # 2. Consultas Realizadas com base no período selecionado
    if periodo == 'diario':
        total_consultas = Consulta.query.join(Agenda).filter(Agenda.data == hoje).count()
    elif periodo == 'mensal':
        start_date = hoje.replace(day=1)
        total_consultas = Consulta.query.join(Agenda).filter(Agenda.data >= start_date).count()
    else: # anual
        start_date = hoje.replace(month=1, day=1)
        total_consultas = Consulta.query.join(Agenda).filter(Agenda.data >= start_date).count()
    
    # 3. Pacientes na Sala de Espera (Aguardando na Fila)
    fila_aguardando = FilaAtendimento.query.filter_by(status='Aguardando').all()
    total_fila = len(fila_aguardando)
    
    # Rótulo de Consultas dinâmico com base no filtro
    label_consultas = "Consultas Hoje" if periodo == 'diario' else ("Consultas no Mês" if periodo == 'mensal' else "Consultas no Ano")
    
    # KPIs principais adaptados ao período
    stats_data = [
        { "label": "Total de Pacientes", "value": f"{total_pacientes}", "change": "Geral SUS", "icon": "users", "trend": "up" },
        { "label": label_consultas, "value": f"{total_consultas}", "change": "+100%", "icon": "calendar", "trend": "up" if total_consultas > 0 else "down" },
        { "label": "Sala de Espera", "value": f"{total_fila}", "change": "Fila Ativa", "icon": "list", "trend": "up" if total_fila > 0 else "down" }
    ]

    # 4. Pacientes Recentes (Últimos 5 cadastrados)
    pacientes_recentes = Paciente.query.order_by(Paciente.id.desc()).limit(5).all()
    recent_patients_data = []
    for p in pacientes_recentes:
        nome = p.usuario.nome
        recent_patients_data.append({
            "id": p.id,
            "nome": nome,
            "especialidade": f"Gênero: {p.genero or 'N/I'}",
            "status": "online" if p.id % 2 == 0 else "offline",
            "data": p.data_nascimento.strftime('%d/%m/%Y') if p.data_nascimento else "Cadastrado",
            "foto": f"https://ui-avatars.com/api/?name={nome.replace(' ', '+')}&background=419640&color=fff&size=80"
        })

    # 5. Sala de Espera Real (Pacientes na fila vindos do banco de dados)
    waiting_list = []
    for item in fila_aguardando:
        nome_paciente = item.paciente.usuario.nome
        iniciais_p = "".join([n[0] for n in nome_paciente.split()[:2]]).upper() if nome_paciente else "P"
        waiting_list.append({
            "nome": nome_paciente,
            "prioridade": "Vermelho" if item.prioridade >= 3 else ("Amarelo" if item.prioridade == 2 else "Verde"),
            "tempo": f"Score IA: {item.score}",
            "iniciais": iniciais_p
        })
    
    tempo_medio = f"{total_fila * 5} min" if total_fila > 0 else "0 min"
    waiting_queue_data = {
        "total": total_fila,
        "tempoMedio": tempo_medio,
        "lista": waiting_list[:5]
    }

    # 6. Gráfico de Agendamentos Dinâmico com base no Período do Filtro
    appointments_chart_data = []
    
    if periodo == 'diario':
        # Filtro DIÁRIO: Agrupamento por Hora no dia de hoje
        hours = ['08h', '10h', '12h', '14h', '16h', '18h']
        today_consultas = Consulta.query.join(Agenda).filter(Agenda.data == hoje).all()
        totals = [0] * len(hours)
        
        for c in today_consultas:
            h_str = c.horario[:2]
            try:
                h_int = int(h_str)
                if h_int <= 9: totals[0] += 1
                elif h_int <= 11: totals[1] += 1
                elif h_int <= 13: totals[2] += 1
                elif h_int <= 15: totals[3] += 1
                elif h_int <= 17: totals[4] += 1
                else: totals[5] += 1
            except:
                totals[0] += 1
        
        max_val = max(totals) if max(totals) > 0 else 1
        pcts = [int((t / max_val) * 100) for t in totals]
        
        for idx, hour in enumerate(hours):
            appointments_chart_data.append({
                "mes": hour,
                "total": totals[idx],
                "pct": pcts[idx]
            })
            
    elif periodo == 'mensal':
        # Filtro MENSAL: Agrupamento por Semana no mês atual
        weeks = ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5']
        start_date = hoje.replace(day=1)
        month_consultas = Consulta.query.join(Agenda).filter(Agenda.data >= start_date).all()
        totals = [0] * len(weeks)
        
        for c in month_consultas:
            day = c.agenda.data.day
            idx = (day - 1) // 7
            if idx >= len(weeks): idx = len(weeks) - 1
            totals[idx] += 1
            
        max_val = max(totals) if max(totals) > 0 else 1
        pcts = [int((t / max_val) * 100) for t in totals]
        
        for idx, week in enumerate(weeks):
            appointments_chart_data.append({
                "mes": week,
                "total": totals[idx],
                "pct": pcts[idx]
            })
            
    else: # anual
        # Filtro ANUAL: Agrupamento por Mês nos últimos 6 meses
        meses = ['Dez', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai']
        totals = [0] * len(meses)
        month_map = {12: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
        
        all_consultas = Consulta.query.all()
        for c in all_consultas:
            m = c.created_at.month if c.created_at else hoje.month
            if m in month_map:
                totals[month_map[m]] += 1
                
        max_val = max(totals) if max(totals) > 0 else 1
        pcts = [int((t / max_val) * 100) for t in totals]
        
        for idx, mes in enumerate(meses):
            appointments_chart_data.append({
                "mes": mes,
                "total": totals[idx],
                "pct": pcts[idx]
            })

    # 7. Distribuição de Gênero real do SIGPS (Masculino vs. Feminino)
    total_feminino = Paciente.query.filter_by(genero='F').count()
    total_masculino = Paciente.query.filter_by(genero='M').count()
    
    if total_pacientes > 0:
        pct_feminino = int((total_feminino / total_pacientes) * 100)
        pct_masculino = 100 - pct_feminino
    else:
        pct_feminino = 0
        pct_masculino = 0

    gender_chart_data = [
        { "nome": "Feminino", "pct": pct_feminino, "valor": total_feminino, "cor": "#ec4899" },
        { "nome": "Masculino", "pct": pct_masculino, "valor": total_masculino, "cor": "#3b82f6" }
    ]

    return jsonify({
        "stats": stats_data,
        "recent_activities": [],
        "specialist_performance": [],
        "recent_patients": recent_patients_data,
        "waiting_queue": waiting_queue_data,
        "appointments_chart": appointments_chart_data,
        "gender_chart": gender_chart_data
    }), 200
