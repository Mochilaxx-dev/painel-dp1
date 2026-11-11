# Painel DP - Sistema de Gestão de Demandas

Sistema profissional para gestão de demandas de Departamento Pessoal com sincronização automática com o painel de tarefas.

## Funcionalidades

- ✅ Gestão de demandas por tipo (Admissão, Rescisão, Férias, etc)
- ✅ Importação de clientes via Excel
- ✅ Sincronização automática com painel profissional
- ✅ Arquivos necessários por tipo de demanda
- ✅ Impressão de demandas com checklist
- ✅ Integração com email (IMAP/SMTP)
- ✅ Cálculo automático de prazos e dias úteis

## Instalação Local

```bash
# Clonar repositório
git clone https://github.com/seu-usuario/painel-dp.git
cd painel-dp

# Instalar dependências
pip install -r requirements.txt

# Executar
python painel.py
```

Acesso: http://localhost:8765

## Deploy no Railway

1. Conectar repositório GitHub no Railway
2. Definir `PORT` como variável de ambiente
3. Deploy automático ao fazer push

Acesso: https://painel-dp.railway.app

## Estrutura

- `painel.py` - Servidor Python principal
- `painel.html` - Interface web
- `painel.db` - Banco de dados SQLite (criado automaticamente)
- `dados/` - Arquivos de configuração e anexos
- `requirements.txt` - Dependências Python

## Configuração

1. Abrir painel em http://localhost:8765
2. Ir para Configurações
3. Adicionar credenciais de email (Gmail, Outlook, etc)
4. Configurar clientes em Cadastros

## API

### Endpoints Principais

- `GET /api/dados` - Listar demandas
- `POST /api/nova` - Criar nova demanda
- `POST /api/status` - Atualizar status
- `GET /api/arquivos/<tipo>` - Arquivos necessários por tipo
- `GET /api/config` - Configurações

## Integração com Painel Profissional

Sincroniza automaticamente demandas com o painel de tarefas em https://gerenciador-de-tarefas-ef1.netlify.app/

Credenciais configuradas em `dados/config.json`

## Suporte

Para mais informações, contate: erickpontes7@gmail.com
