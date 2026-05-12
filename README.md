# SIGPS — Sistema Inteligente de Gestão e Priorização na Saúde (Backend)

Este repositório contém o backend do projeto **SIGPS**, desenvolvido utilizando **Python** com o micro-framework **Flask**. 
O sistema tem como objetivo principal gerenciar pacientes, agendamentos, chat entre usuários, envio de exames e uma fila de priorização com simulação de IA.

---

## 🚀 Como Rodar o Projeto

### 1. Pré-requisitos
* **Python 3.8+** instalado.

### 2. Configuração do Ambiente
1. **Clone o repositório** e acesse a pasta do projeto.
2. **Crie um ambiente virtual:**
   ```bash
   python -m venv .venv
   ```
3. **Ative o ambiente virtual:**
   * No Windows: `.venv\Scripts\activate`
   * No Linux/Mac: `source .venv/bin/activate`
4. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

### 3. Executando o Servidor
Com o ambiente configurado, basta iniciar o aplicativo. O banco de dados SQLite (`sigps_db.sqlite`) será criado automaticamente na raiz do projeto:
```bash
python run.py
```
A API estará disponível em: `http://localhost:5000`

---

## 📖 Documentação da API
Após iniciar o servidor, acesse a documentação interativa da API gerada pelo Swagger:
* **Swagger UI:** [http://localhost:5000/api/docs](http://localhost:5000/api/docs)

---

## ✅ O Que Já Está Pronto (Implementado)

O backend possui as seguintes funcionalidades implementadas separadas em arquivos (Blueprints) na pasta `app/routes/`:

*   **Autenticação e Gestão de Usuários (`auth.py` e `admin.py`)**:
    *   Cadastro de usuários com senhas criptografadas (hash).
    *   Login com geração de Access Token e Refresh Token (usando `flask-jwt-extended`).
    *   Renovação de tokens.
    *   Recuperação dos dados do usuário logado (`/me`).
    *   Admin pode listar os usuários do sistema e alterar seus perfis de acesso.
*   **Pacientes (`pacientes.py`)**:
    *   Completar o cadastro clínico (vinculado à conta do usuário logado).
    *   Listagem de pacientes com parâmetros para filtros de busca (nome, CPF).
    *   Exibição de detalhes do paciente e deleção de registros.
*   **Fila e Triagem com IA (`fila.py`)**:
    *   Check-in na fila de espera com cálculo de *Score* simulado por IA baseado nas comorbidades cadastradas.
    *   Listagem da fila ordenada automaticamente por nível de prioridade, score e horário de chegada.
    *   Atualização de status do atendimento (ex: 'Aguardando', 'Em Atendimento', 'Finalizado').
    *   Análise preditiva: um endpoint retornando um resumo estatístico da fila e alertas de pacientes críticos.
*   **Exames (`exames.py`)**:
    *   Upload de arquivos anexos (salvos localmente na pasta `uploads/exames`).
    *   Listagem de histórico de exames de um paciente e exclusão do banco de dados/disco.
*   **Chat Interno (`chat.py`)**:
    *   Envio e recebimento de mensagens.
    *   Marcação de mensagens como lidas.
    *   Opção de limpar o histórico pessoal do chat.
*   **Agendamentos e Consultas (`agendas.py`)**:
    *   Criação de agendas com slots de horários disponíveis pelos especialistas.
    *   Agendamento de consultas pelos pacientes (ocupando as vagas criadas na agenda do médico).
    *   Listagem, edição e exclusão de horários na agenda, bem como atualização do status da consulta.

---

## 🚧 O Que Não Está Pronto (Ausente ou Incompleto)

*   **Integração Real com IA na Triagem**: Atualmente o "score de IA" é gerado por uma validação condicional simples no código (verifica se as strings contêm palavras como diabetes, hipertensão ou câncer nas comorbidades). Nenhuma IA de Machine Learning ou LLM está acoplada de fato.
*   **Paginação nos Endpoints**: Requisições de listagem (pacientes, fila, usuários, mensagens de chat) não possuem suporte à paginação (`limit`, `offset`). Isso pode resultar em problemas de memória e lentidão quando houver muitos dados cadastrados no banco.
*   **Armazenamento em Nuvem**: O upload de exames é salvo no próprio disco local do servidor. Em ambientes de produção reais o ideal é enviar arquivos para o *AWS S3*, *Azure Blob Storage* ou serviços equivalentes.
*   **Comunicação em Tempo Real (WebSockets)**: As funcionalidades de Chat e da Fila dependem que o Frontend fique fazendo repetidas requisições (polling) para buscar por atualizações, uma vez que requisições HTTP tradicionais são unidirecionais.

---

## 💡 Boas Práticas que Podem ser Aplicadas

Para tornar a base de código do backend mais profissional, escalável e segura, as seguintes práticas arquiteturais e técnicas são recomendadas:

1.  **Uso de Variáveis de Ambiente (`.env`)**:
    Remova imediatamente chaves *hardcoded* do código (como a chave `JWT_SECRET_KEY = 'super-secret-key'` e a String de Conexão no `run.py`). Utilize o pacote `python-dotenv` para injetar variáveis sensíveis a partir de um arquivo de configuração na raiz (`.env`).
2.  **Validações de Input Estritas com Schemas**:
    Integre o **Marshmallow** ou **Pydantic** para validar rigorosamente a tipagem e os campos do JSON que são recebidos do cliente, antes de os salvar no banco. Atualmente o sistema confia muito nos dados vindos do `request.get_json()`.
3.  **Habilitar Migrações do Banco de Dados (`Flask-Migrate`)**:
    O sistema hoje utiliza `db.create_all()` cada vez que o app inicializa, o que impede modificações (ALTER TABLE) sem exclusões totais do DB de forma segura. Acople o `Flask-Migrate` para gerar scripts de banco confiáveis e sequenciais.
4.  **Implementar WebSockets (`Flask-SocketIO`)**:
    Para as áreas ao vivo, como Fila de Atendimento e Chat, o uso de WebSockets reduzirá excessos de tráfego na rede, permitindo que alterações disparadas num cliente sejam informadas instantaneamente para a tela do médico, e vice-versa, de forma performática.
5.  **Refatoração do Arquivo Principal (`run.py` para `config.py`)**: *(Implementado)*
    O projeto agora segue a padronização Application Factory (`app/__init__.py`), separando as configurações em um arquivo `config.py` limpo e extraindo dependências para `extensions.py`.
6.  **Gerenciadores Globais de Erros**:
    Inclua *Error Handlers* globais do Flask (`@app.errorhandler`) para reescrever as respostas nativas em HTML que o Flask gera (para falhas como 404, 500) e garanta que sempre retornarão em formato padrão `JSON`.
7.  **Isolamento da Regra de Negócio (Camada Service/Repository)**:
    No momento, o banco de dados (`db.session`) está acoplado de forma crua nas controladoras (blueprints). Centralize o raciocínio complexo dentro de uma pasta `services/` ou `repositories/` para que o código fique mais reaproveitável, limpo e testável.
