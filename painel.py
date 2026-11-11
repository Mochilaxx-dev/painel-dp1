"""
PAINEL DE DEMANDAS DP (versão local e gratuita)

- Lê sua caixa de e-mail por IMAP usando uma "senha de app" (Gmail, Yahoo, provedores de hospedagem...)
- Identifica demandas por regras de palavras-chave e datas (sem IA, sem custo)
- Calcula prazos legais (rescisão, férias, admissão...) e gera o calendário de obrigações de cada cliente
- Mostra tudo num painel no navegador: http://localhost:8765
- Envia um resumo diário por e-mail (opcional), usando a mesma conta

Usa somente a biblioteca padrão do Python 3.10+. Os dados ficam na pasta "dados", ao lado deste arquivo.
"""

import base64
import csv
import email
import email.policy
import hashlib
import html
import imaplib
import io
import json
import logging
import os
import re
import smtplib
import socket
import sqlite3
import ssl
import sys
import threading
import time
import unicodedata
import uuid
import webbrowser
import zipfile
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote
import mimetypes

PORTA = int(os.environ.get('PORT', 8765))
PRODUCAO = os.environ.get('RAILWAY_ENVIRONMENT_NAME') == 'production' or os.environ.get('ENVIRONMENT') == 'production'
BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS = os.path.join(BASE, 'dados')
DB_PATH = os.path.join(PASTA_DADOS, 'painel.db')
CONFIG_PATH = os.path.join(PASTA_DADOS, 'config.json')
os.makedirs(PASTA_DADOS, exist_ok=True)

log = logging.getLogger('painel')
log.setLevel(logging.INFO)
_fh = logging.FileHandler(os.path.join(PASTA_DADOS, 'painel.log'), encoding='utf-8')
_fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
log.addHandler(_fh)
if sys.stdout:  # rodando com python.exe (com janela), mostra o log também na tela
    log.addHandler(logging.StreamHandler(sys.stdout))

TIPOS = [
    'Admissão', 'Rescisão', 'Férias', 'Folha de pagamento', 'Afastamento/Atestado', 'Acidente de trabalho',
    'Benefícios (VT/VR/plano)', 'Alteração contratual/salarial', 'Encargos e guias', 'eSocial', 'Pró-labore',
    '13º salário', 'Documentos e declarações', 'Notificação de órgão público', 'Dúvida/Consultoria', 'Outros',
]
STATUS = ['Pendente', 'Em andamento', 'Concluída']
PRIORIDADES = ['Alta', 'Média', 'Baixa']

ARQUIVOS_NECESSARIOS = {
    'Admissão': [
        ('Contrato de Trabalho', 'Cópia assinada', 'obrigatorio'),
        ('Documentos Pessoais', 'CPF, RG, CTPS, Cartão Bancário', 'obrigatorio'),
        ('Exame Admissional', 'ASO do médico do trabalho', 'obrigatorio'),
        ('Comprovante de Residência', 'Endereço atualizado', 'recomendado'),
    ],
    'Rescisão': [
        ('TRCT', 'Termo com todas as parcelas', 'obrigatorio'),
        ('Dados Bancários', 'Conta para depósito', 'obrigatorio'),
        ('Comprovante de Homologação', 'Se aplicável', 'recomendado'),
        ('Cálculo da Rescisão', 'Folha com todas as verbas', 'recomendado'),
    ],
    'Férias': [
        ('Concessão de Férias', 'Datas aprovadas', 'obrigatorio'),
        ('Cálculo de Férias', 'Parcelas (1/3 e saldo)', 'obrigatorio'),
        ('Período Aprovado', 'Datas início e término', 'obrigatorio'),
    ],
    'Folha de pagamento': [
        ('Folha de Pagamento', 'Comprovante de processamento', 'obrigatorio'),
        ('Holerites', 'Cópia para colaborador', 'recomendado'),
    ],
    'Afastamento/Atestado': [
        ('Atestado Médico', 'Com CRM e assinatura', 'obrigatorio'),
        ('Comunicação ao INSS', 'Se > 15 dias', 'recomendado'),
        ('Recibos de Pagamento', 'Durante afastamento', 'recomendado'),
    ],
    'Acidente de trabalho': [
        ('CAT', 'Formulário completo', 'obrigatorio'),
        ('Atestado Médico', 'Com diagnóstico', 'obrigatorio'),
        ('Boletim de Ocorrência', 'Se houver terceiros', 'recomendado'),
        ('Fotos/Evidências', 'Documentar lesão e local', 'opcional'),
    ],
    'Benefícios (VT/VR/plano)': [
        ('Solicitação', 'E-mail ou formulário', 'obrigatorio'),
        ('Documentos da Operadora', 'Formulários de inscrição', 'recomendado'),
        ('Dados Pessoais', 'Para processamento', 'obrigatorio'),
    ],
    'Alteração contratual/salarial': [
        ('Aditivo Contratual', 'Assinado', 'obrigatorio'),
        ('Comprovante de Ciência', 'Assinatura do colaborador', 'obrigatorio'),
        ('Novo Contrato', 'Se total, assinado', 'recomendado'),
    ],
    'Encargos e guias': [
        ('DARF/GPS', 'Boleto ou comprovante', 'obrigatorio'),
        ('FGTS Digital', 'Comprovante de envio', 'obrigatorio'),
        ('Recibos de Pagamento', 'Comprovantes', 'obrigatorio'),
    ],
    'eSocial': [
        ('Comprovante de Envio', 'Recibo do governo', 'obrigatorio'),
        ('Eventos Transmitidos', 'Lista dos eventos', 'recomendado'),
        ('Retornos do Sistema', 'Aceite ou rejeição', 'recomendado'),
    ],
    'Pró-labore': [
        ('Nota Fiscal/Recibo', 'Comprovante de serviço', 'obrigatorio'),
        ('Comprovante de Pagamento', 'Transferência bancária', 'obrigatorio'),
    ],
    '13º salário': [
        ('Folha de Pagamento', 'Comprovante de processamento', 'obrigatorio'),
        ('Cálculo do 13º', 'Demonstrativo das parcelas', 'obrigatorio'),
        ('Comprovantes de Pagamento', 'Extratos bancários', 'recomendado'),
    ],
    'Documentos e declarações': [
        ('Documento Solicitado', 'Especificar qual', 'obrigatorio'),
        ('Informe de Rendimentos', 'IR anual', 'opcional'),
        ('PPP', 'Perfil Profissiográfico', 'opcional'),
    ],
    'Notificação de órgão público': [
        ('Cópia da Notificação', 'Documento oficial', 'obrigatorio'),
        ('Documentos Relacionados', 'Processos e prazos', 'obrigatorio'),
        ('Histórico do Caso', 'Comunicações anteriores', 'recomendado'),
    ],
}

PROVEDORES = {
    'gmail': {'imap_host': 'imap.gmail.com', 'imap_port': 993, 'smtp_host': 'smtp.gmail.com', 'smtp_port': 465},
    'yahoo': {'imap_host': 'imap.mail.yahoo.com', 'imap_port': 993, 'smtp_host': 'smtp.mail.yahoo.com', 'smtp_port': 465},
    'outlook': {'imap_host': 'outlook.office365.com', 'imap_port': 993, 'smtp_host': 'smtp.office365.com', 'smtp_port': 587},
    'outro': {'imap_host': '', 'imap_port': 993, 'smtp_host': '', 'smtp_port': 465},
}

OBRIGACOES_PADRAO = [
    ('Pagamento da folha (salários)', 'Folha de pagamento', 'DIA_UTIL', 5, '', 1, 'Até o 5º dia útil; sábado conta como dia útil (CLT art. 459 §1º)'),
    ('eSocial – eventos periódicos (S-1200/S-1299)', 'eSocial', 'ANTECIPA', 15, '', 1, 'Até o dia 15; antecipa se não for dia útil'),
    ('DCTFWeb – transmissão', 'Encargos e guias', 'ANTECIPA', 15, '', 1, 'Até o dia 15 (regra conservadora: antecipa)'),
    ('INSS – DARF previdenciário', 'Encargos e guias', 'ANTECIPA', 20, '', 1, 'Até o dia 20; antecipa se não houver expediente bancário'),
    ('FGTS Digital – guia mensal', 'Encargos e guias', 'ANTECIPA', 20, '', 1, 'Até o dia 20; antecipa'),
    ('IRRF sobre salários', 'Encargos e guias', 'ANTECIPA', 20, '', 1, 'Até o dia 20; antecipa'),
    ('13º salário – 1ª parcela', '13º salário', 'ANTECIPA', 30, '11', 1, 'Até 30/11'),
    ('13º salário – 2ª parcela', '13º salário', 'ANTECIPA', 20, '12', 1, 'Até 20/12'),
]

# ============================================================================
# CONFIGURAÇÃO E SENHA PROTEGIDA (Windows DPAPI)
# ============================================================================

def _config_padrao():
    return {
        'provedor': 'gmail', 'chave_windows': 'gmail', 'email': '',
        'imap_host': 'imap.gmail.com', 'imap_port': 993, 'smtp_host': 'smtp.gmail.com', 'smtp_port': 465,
        'pasta': 'INBOX',
        'ler_a_partir': (date.today() - timedelta(days=3)).isoformat(),
        'intervalo_min': 10, 'prazo_padrao': 3, 'antecedencia': 45,
        'resumo_ativo': True, 'resumo_para': '',
        'ignorar_remetentes': 'noreply, no-reply, naoresponda, nao-responda, donotreply, newsletter, marketing, mailer-daemon, postmaster',
    }


def carregar_config():
    cfg = _config_padrao()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding='utf-8') as f:
            cfg.update(json.load(f))
    return cfg


def salvar_config(novos):
    cfg = carregar_config()
    for k in _config_padrao():
        if k in ('email',) or k not in novos:
            continue  # e-mail e senha vêm sempre da chave do Windows
        cfg[k] = novos[k]
    cfg.pop('senha', None)  # versões antigas guardavam a senha aqui
    cfg['chave_windows'] = str(cfg.get('chave_windows') or 'gmail').strip()
    for k in ('imap_port', 'smtp_port', 'intervalo_min', 'prazo_padrao', 'antecedencia'):
        cfg[k] = max(1, int(cfg[k] or 1))
    cfg['email'] = str(cfg['email']).strip()
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


def mascarar(email_):
    nome, _, dominio = email_.partition('@')
    if not dominio:
        return ''
    return (nome[0] + '•••' + nome[-1] if len(nome) > 2 else nome[0] + '•••') + '@' + dominio


def config_publica():
    """Configuração enviada para a tela: sem a senha e com o e-mail mascarado."""
    cfg = carregar_config()
    cfg.pop('senha', None)
    cfg.pop('email', None)
    cfg['chave'] = status_chave(cfg)
    return cfg


if os.name == 'nt':
    import ctypes
    import ctypes.wintypes as wt

    class _BLOB(ctypes.Structure):
        _fields_ = [('cbData', wt.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

    def _dpapi(dados, proteger_):
        buf = ctypes.create_string_buffer(dados, len(dados))
        entrada = _BLOB(len(dados), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        saida = _BLOB()
        fn = ctypes.windll.crypt32.CryptProtectData if proteger_ else ctypes.windll.crypt32.CryptUnprotectData
        if not fn(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(saida)):
            raise OSError('Falha ao proteger/ler a senha (DPAPI).')
        try:
            return ctypes.string_at(saida.pbData, saida.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(ctypes.cast(saida.pbData, ctypes.c_void_p))


    class _CREDENTIAL(ctypes.Structure):
        _fields_ = [('Flags', wt.DWORD), ('Type', wt.DWORD), ('TargetName', wt.LPWSTR), ('Comment', wt.LPWSTR),
                    ('LastWritten', wt.FILETIME), ('CredentialBlobSize', wt.DWORD),
                    ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wt.DWORD),
                    ('AttributeCount', wt.DWORD), ('Attributes', ctypes.c_void_p),
                    ('TargetAlias', wt.LPWSTR), ('UserName', wt.LPWSTR)]


def ler_chave_windows(nome):
    """Lê uma credencial genérica do Gerenciador de Credenciais do Windows. Retorna (usuário, senha) ou None."""
    if os.name != 'nt' or not nome:
        return None
    p = ctypes.POINTER(_CREDENTIAL)()
    if not ctypes.windll.advapi32.CredReadW(ctypes.c_wchar_p(nome), 1, 0, ctypes.byref(p)):  # 1 = genérica
        return None
    try:
        c = p.contents
        blob = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize) if c.CredentialBlobSize else b''
        try:
            senha = blob.decode('utf-16-le') if len(blob) % 2 == 0 else blob.decode('utf-8')
        except UnicodeDecodeError:
            senha = blob.decode('utf-8', 'replace')
        return (c.UserName or '').strip(), senha.replace(' ', '').strip()
    finally:
        ctypes.windll.advapi32.CredFree(p)


def credenciais(cfg):
    """E-mail e senha da conta: do Windows (local) ou variáveis de ambiente (produção)."""
    # Em produção (Railway), ler das variáveis de ambiente
    if PRODUCAO:
        email = os.environ.get('EMAIL_USUARIO', '')
        senha = os.environ.get('EMAIL_SENHA', '')
        if email and senha:
            if '@' not in email:
                raise ErroConfig('EMAIL_USUARIO deve ser um e-mail completo (ex: seu@gmail.com).')
            return email.lower(), senha
        # Se não tiver variáveis, retornar vazio para painel funcionar sem email
        raise ErroConfig('Configure EMAIL_USUARIO e EMAIL_SENHA no Railway para ler emails.')

    # Local: ler do Windows Credential Manager
    nome = cfg.get('chave_windows') or 'gmail'
    achou = ler_chave_windows(nome)
    if not achou:
        raise ErroConfig('Chave "' + nome + '" não encontrada no Gerenciador de Credenciais do Windows. '
                         'Veja o passo a passo em Configurações.')
    usuario, senha = achou
    if '@' not in usuario:
        raise ErroConfig('Na chave "' + nome + '", o campo "Nome de usuário" deve ser o seu e-mail completo.')
    if not senha:
        raise ErroConfig('A chave "' + nome + '" está sem senha. Coloque nela a senha de app do Google.')
    return usuario.lower(), senha


def status_chave(cfg):
    if PRODUCAO:
        return {'ok': True, 'email_mascarado': 'producao@railway.app', 'erro': ''}
    try:
        usuario, _ = credenciais(cfg)
        return {'ok': True, 'email_mascarado': mascarar(usuario), 'erro': ''}
    except ErroConfig as e:
        return {'ok': False, 'email_mascarado': '', 'erro': str(e)}


def proteger(texto):
    """A senha é criptografada com a sua conta do Windows: só você, neste computador, consegue lê-la."""
    if os.name == 'nt':
        return 'dpapi:' + base64.b64encode(_dpapi(texto.encode('utf-8'), True)).decode()
    return 'b64:' + base64.b64encode(texto.encode('utf-8')).decode()


def revelar(valor):
    if not valor:
        return ''
    tipo, _, dado = valor.partition(':')
    raw = base64.b64decode(dado)
    return (_dpapi(raw, False) if tipo == 'dpapi' else raw).decode('utf-8')

# ============================================================================
# BANCO DE DADOS (SQLite)
# ============================================================================

_lock_db = threading.RLock()


def db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def iniciar_db():
    with _lock_db, db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS demandas(
            id TEXT PRIMARY KEY, criado TEXT, cliente TEXT, tipo TEXT, descricao TEXT, colaborador TEXT,
            prazo TEXT, origem TEXT, prioridade TEXT, status TEXT, fonte TEXT, remetente TEXT, assunto TEXT,
            email_chave TEXT, conversa TEXT, trecho TEXT, obs TEXT, concluido TEXT);
        CREATE TABLE IF NOT EXISTS emails(
            chave TEXT PRIMARY KEY, recebido TEXT, remetente TEXT, assunto TEXT, trecho TEXT,
            resultado TEXT, sugestao TEXT, demanda_id TEXT, lido_em TEXT);
        CREATE TABLE IF NOT EXISTS clientes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, apelidos TEXT, ativo INTEGER, obrigacoes TEXT, obs TEXT);
        CREATE TABLE IF NOT EXISTS obrigacoes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, tipo TEXT, regra TEXT, dia INTEGER, meses TEXT, ativa INTEGER, obs TEXT);
        CREATE TABLE IF NOT EXISTS feriados(data TEXT PRIMARY KEY, descricao TEXT);
        CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
        CREATE INDEX IF NOT EXISTS ix_dem_conversa ON demandas(conversa);
        CREATE INDEX IF NOT EXISTS ix_emails_lido ON emails(lido_em);
        ''')
        for tabela in ('demandas', 'emails'):  # atualização de versões anteriores
            if 'anexos' not in [r[1] for r in con.execute('PRAGMA table_info(%s)' % tabela)]:
                con.execute("ALTER TABLE %s ADD COLUMN anexos TEXT DEFAULT ''" % tabela)
        if con.execute('SELECT COUNT(*) FROM obrigacoes').fetchone()[0] == 0:
            con.executemany('INSERT INTO obrigacoes(nome,tipo,regra,dia,meses,ativa,obs) VALUES (?,?,?,?,?,?,?)', OBRIGACOES_PADRAO)


def meta_get(k, padrao=''):
    with db() as con:
        r = con.execute('SELECT v FROM meta WHERE k=?', (k,)).fetchone()
    return r[0] if r else padrao


def meta_set(k, v):
    with _lock_db, db() as con:
        con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES (?,?)', (k, str(v)))


def agora():
    return datetime.now().strftime('%Y-%m-%d %H:%M')


def nova_demanda(con, **d):
    did = d.get('id') or (d.get('prefixo', 'DM') + '-' + uuid.uuid4().hex[:8])
    con.execute('''INSERT OR IGNORE INTO demandas
        (id,criado,cliente,tipo,descricao,colaborador,prazo,origem,prioridade,status,fonte,remetente,assunto,email_chave,conversa,trecho,obs,concluido,anexos)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        did, agora(), d.get('cliente') or 'Não identificado', d.get('tipo') or 'Outros', d.get('descricao') or '',
        d.get('colaborador') or '', d.get('prazo') or '', d.get('origem') or '', d.get('prioridade') or 'Média',
        'Pendente', d.get('fonte') or 'Manual', d.get('remetente') or '', d.get('assunto') or '',
        d.get('email_chave') or '', d.get('conversa') or '', d.get('trecho') or '', d.get('obs') or '', '',
        d.get('anexos') or ''))
    return did

# ============================================================================
# DATAS, DIAS ÚTEIS E FERIADOS
# ============================================================================

def pascoa(ano):
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e, f = b // 4, b % 4, (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


_cache_feriados = {}


def feriados(ano):
    if ano not in _cache_feriados:
        s = {date(ano, m, d) for m, d in [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (11, 20), (12, 25)]}
        p = pascoa(ano)
        s |= {p + timedelta(days=n) for n in (-48, -47, -2, 60)}  # Carnaval, Sexta-feira Santa, Corpus Christi
        with db() as con:
            for (k,) in con.execute('SELECT data FROM feriados'):
                try:
                    s.add(date.fromisoformat(k))
                except ValueError:
                    pass
        _cache_feriados[ano] = s
    return _cache_feriados[ano]


def util_bancario(d):
    return d.weekday() < 5 and d not in feriados(d.year)


def util_trabalhista(d):
    return d.weekday() < 6 and d not in feriados(d.year)


def somar_dias_uteis(d, n):
    while n > 0:
        d += timedelta(days=1)
        if util_bancario(d):
            n -= 1
    return d


def proximo_dia_util(d):
    return somar_dias_uteis(d, 1)


def ultimo_dia_mes(ano, mes):
    return (date(ano + mes // 12, mes % 12 + 1, 1) - timedelta(days=1)).day

# ============================================================================
# REGRAS DE LEITURA DOS E-MAILS (sem IA)
# ============================================================================

def norm(s):
    """minúsculas e sem acentos: 'Férias' -> 'ferias', '13º' -> '13o'"""
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()


# Cada tipo tem uma lista de expressões (sobre o texto sem acentos). Ordem = desempate.
REGRAS_TIPO = [
    ('Acidente de trabalho', [r'acidente', r'\bcat\b', r'machucou', r'se feriu']),
    ('Notificação de órgão público', [r'notificac', r'intimac', r'fiscaliza', r'auto de infracao', r'reclamatoria',
                                      r'processo trabalhista', r'\bmte\b', r'ministerio do trabalho', r'audiencia', r'sindicato']),
    ('Rescisão', [r'rescis', r'deslig', r'demiss', r'demitir', r'demitid', r'dispensa', r'aviso previo', r'justa causa',
                  r'\btrct\b', r'homolog', r'pediu (as )?contas']),
    ('Admissão', [r'admiss', r'admitir', r'admitid', r'contratac', r'contratar', r'novo funcionario', r'nova funcionaria',
                  r'novo colaborador', r'nova colaboradora', r'comeca a trabalhar', r'inicio das atividades', r'exame admissional']),
    ('Férias', [r'ferias']),
    ('Afastamento/Atestado', [r'atestado', r'afastament', r'licenca', r'auxilio[- ]doenca', r'beneficio por incapacidade', r'maternidade']),
    ('13º salário', [r'\b13o\b', r'13o salario', r'decimo terceiro', r'\b13 salario']),
    ('Pró-labore', [r'pro[- ]?labore']),
    ('Benefícios (VT/VR/plano)', [r'vale[- ]transporte', r'vale[- ]refeicao', r'vale[- ]alimentacao', r'plano de saude',
                                  r'plano odonto', r'\bvt\b', r'\bvr\b', r'\bva\b']),
    ('Alteração contratual/salarial', [r'aumento', r'reajuste', r'promoc', r'alteracao salarial', r'alteracao de cargo',
                                       r'mudanca de cargo', r'alteracao contratual', r'troca de horario', r'mudanca de horario']),
    ('eSocial', [r'esocial']),
    ('Encargos e guias', [r'\bguias?\b', r'\bfgts\b', r'\bdarf\b', r'dctfweb', r'\bgps\b', r'\birrf\b', r'\binss\b']),
    ('Folha de pagamento', [r'\bfolha\b', r'holerite', r'contracheque', r'hora extra', r'horas extras', r'\bfaltas?\b',
                            r'comiss', r'adiantamento', r'cartao de ponto', r'folha de ponto', r'banco de horas', r'adicional noturno']),
    ('Documentos e declarações', [r'declaracao', r'informe de rendimentos', r'carta de referencia', r'\bppp\b',
                                  r'segunda via', r'2a via', r'\bctps\b']),
    ('Dúvida/Consultoria', [r'\bduvida', r'gostaria de saber', r'como (devo|faco|fica|funciona|proceder)',
                            r'pode(ria)? me (explicar|orientar)', r'qual (o|a) (procedimento|valor|prazo)']),
]
REGRAS_TIPO_RE = [(t, [re.compile(p) for p in ps]) for t, ps in REGRAS_TIPO]

R_IGNORAR_CORPO = re.compile(r'descadastr|unsubscribe|cancelar (a )?inscricao|nao deseja mais receber|view in browser|visualizar no navegador')
R_AUTO_RESPOSTA = re.compile(r'^(resposta automatica|automatic reply|auto[- ]?reply|out of office|ausente|fora do escritorio)')
R_AGRADECIMENTO = re.compile(r'^\W*(ok|okay|obrigad[oa]|muito obrigad[oa]|recebid[oa]|grat[oa]|perfeito|certo|beleza|blz|show|combinado|de nada)\b')
R_URGENTE = re.compile(r'urgen|imediat|o quanto antes|com urgencia|\basap\b|prioridade')
R_PREFIXO_ASSUNTO = re.compile(r'^\s*((re|res|fw|fwd|enc|tr|rv|resp)\s*:\s*)+', re.I)

MESES = {'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7,
         'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12}
DIAS_SEM = {'segunda': 0, 'terca': 1, 'quarta': 2, 'quinta': 3, 'sexta': 4, 'sabado': 5, 'domingo': 6}
_MESES_RE = '|'.join(MESES)
R_DATA_NUM = re.compile(r'(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?![\d/])')
R_DATA_EXT = re.compile(r'\b(\d{1,2})o? de (' + _MESES_RE + r')(?: de (\d{4}))?')
R_DIA = re.compile(r'\bdia (\d{1,2})\b(?!\s*/)(?! de (?:' + _MESES_RE + r'))')
R_RELATIVA = re.compile(r'\b(depois de amanha|amanha|hoje)\b')
R_SEMANA = re.compile(r'\b(?:ate|na|nesta|nessa|esta|essa|proxima|para|pra)\s+(?:a\s+|o\s+)?(segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:[- ]feira)?\b(?!\s+(?:via|parcela|quinzena))')
R_ANTES_PRAZO = re.compile(r'(\bate\b|prazo|limite|antes d|no maximo|vence|vencimento|impreterivelmente)[^.\n]{0,30}$')

_MAI = 'A-ZÁÉÍÓÚÂÊÔÃÕÇ'
_MIN = 'a-záéíóúâêôãõçü'
NOME = r'([' + _MAI + r'][' + _MIN + r']+(?:[ \t]+(?:d[aeo]s?[ \t]+)?[' + _MAI + r'][' + _MIN + r']+){0,4})'
NOME_MAI = r'([' + _MAI + r']{2,}(?:[ \t]+(?:D[AEO]S?[ \t]+|E[ \t]+)?[' + _MAI + r']{2,}){1,5})'
R_COLAB = [
    # "SOLICITAÇÃO DE FÉRIAS - ANA PAULA DA SILVA" / "Documentos admissionais Luiz Renato de Jesus"
    re.compile(r'(?i:f[ée]rias|admissiona(?:l|is)|admiss[ãa]o|rescis[ãa]o|desligamento|demiss[ãa]o|atestado|afastamento|registro)'
               r'[ \t]*[-–:]?[ \t]*(?:' + NOME + '|' + NOME_MAI + ')'),
    re.compile(r'(?i:colaborador[a]?|funcion[aá]ri[oa]|empregad[oa]|trabalhador[a]?)(?:\(a\))?[ \t]*[:\-]?[ \t]*' + NOME),
    re.compile(r'(?i:f[ée]rias|admiss[ãa]o|desligamento|demiss[ãa]o|rescis[ãa]o|atestado|afastamento|registro|contrata[çc][ãa]o)'
               r'[ \t]+(?i:d[oa]s?|para[ \t]+[oa]?)[ \t]+' + NOME),
    # Em documentos: "Nome do empregado: FULANO", "Nome completo: Fulano de Tal"
    re.compile(r'(?i:nome(?:[ \t]+completo)?(?:[ \t]+d[oa][ \t]+(?:empregad[oa]|colaborador[a]?|funcion[aá]ri[oa]|trabalhador[a]?|segurad[oa]))?)'
               r'(?:\(a\))?[ \t]*:[ \t]*(?:' + NOME + '|' + NOME_MAI + ')'),
    re.compile(r'(?:^|[.!?\n]\s*|,\s*)(?:O|A|o|a)[ \t]+' + NOME +
               r'[ \t]+(?:pediu|foi|vai|ser[áa]|est[áa]|entra|come[çc]a|sai|faltou|apresentou|teve|precisa|se)\b'),
]
NAO_NOMES = {'bom', 'boa', 'dia', 'tarde', 'noite', 'empresa', 'senhor', 'senhora', 'obrigado', 'obrigada', 'att',
             'atenciosamente', 'prezado', 'prezada', 'olá', 'oi', 'segue', 'favor', 'gente', 'equipe', 'pessoal', 'loja',
             'vamos', 'preciso', 'precisamos', 'por', 'pode', 'poderia', 'quero', 'gostaria', 'mês', 'semana'}
DOMINIOS_GENERICOS = {'gmail.com', 'hotmail.com', 'outlook.com', 'live.com', 'yahoo.com', 'yahoo.com.br', 'uol.com.br',
                      'bol.com.br', 'icloud.com', 'terra.com.br', 'ig.com.br', 'msn.com', 'globo.com', 'outlook.com.br'}


def limpar_corpo(texto, encaminhado):
    """Remove o histórico citado das respostas (fica só a mensagem nova)."""
    linhas = []
    tl = (texto or '').replace('\r\n', '\n').split('\n')
    for i, l in enumerate(tl):
        n = norm(l).strip()
        if not encaminhado:
            if re.match(r'^(em|on) .{5,160} (escreveu|wrote):?$', n) or re.match(r'^-{2,}\s*(mensagem original|original message)', n):
                break
            if re.match(r'^(de|from):\s', n) and any(re.match(r'^(enviad[oa]|sent|data|date):', norm(x).strip()) for x in tl[i + 1:i + 4]):
                break
        if l.lstrip().startswith('>'):
            continue
        linhas.append(l)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(linhas)).strip()


def _montar_data(d, m, a, base):
    try:
        if a is None:
            cand = date(base.year, m, d)
            if cand < base - timedelta(days=120):
                cand = date(base.year + 1, m, d)
            return cand
        a = int(a)
        if a < 100:
            a += 2000
        return date(a, m, d)
    except ValueError:
        return None


def extrair_datas(tn, base):
    """Encontra datas no texto (sem acentos). Retorna [(posição, data, é_prazo)]."""
    achadas = []

    def add(pos, dt, prazo=False):
        if dt and base - timedelta(days=60) <= dt <= base + timedelta(days=400):
            eh_prazo = prazo or bool(R_ANTES_PRAZO.search(tn[max(0, pos - 45):pos]))
            achadas.append((pos, dt, eh_prazo))

    for m in R_DATA_NUM.finditer(tn):
        add(m.start(), _montar_data(int(m.group(1)), int(m.group(2)), m.group(3), base))
    for m in R_DATA_EXT.finditer(tn):
        add(m.start(), _montar_data(int(m.group(1)), MESES[m.group(2)], m.group(3), base))
    for m in R_DIA.finditer(tn):
        dia = int(m.group(1))
        ano, mes = base.year, base.month
        if dia < base.day:
            mes += 1
            if mes > 12:
                mes, ano = 1, ano + 1
        add(m.start(), _montar_data(dia, mes, ano, base))
    for m in R_RELATIVA.finditer(tn):
        add(m.start(), base + timedelta(days={'hoje': 0, 'amanha': 1, 'depois de amanha': 2}[m.group(1)]))
    for m in R_SEMANA.finditer(tn):
        alvo = DIAS_SEM[m.group(1)]
        add(m.start(), base + timedelta(days=(alvo - base.weekday()) % 7), m.group(0).startswith('ate'))
    achadas.sort(key=lambda x: x[0])
    return achadas


def detectar_tipo(assunto_n, corpo_n):
    pontos = {}
    for tipo, regs in REGRAS_TIPO_RE:
        p = 0
        for r in regs:
            if r.search(assunto_n):
                p += 3
            p += min(len(r.findall(corpo_n)), 3)
        if p:
            pontos[tipo] = p
    if not pontos:
        return None, []
    ordem = [t for t, _ in REGRAS_TIPO]
    ranking = sorted(pontos, key=lambda t: (-pontos[t], ordem.index(t)))
    return ranking[0], ranking[1:3]


def detectar_colaborador(texto):
    for r in R_COLAB:
        for m in r.finditer(texto):
            nome = next(g for g in m.groups() if g).strip()
            if nome.isupper():  # "ANA PAULA DA SILVA" -> "Ana Paula da Silva"
                nome = ' '.join(p.lower() if p in ('DA', 'DE', 'DO', 'DAS', 'DOS', 'E') else p.capitalize() for p in nome.split())
            if nome.split()[0].lower() not in NAO_NOMES:
                return nome
    return ''


def identificar_cliente(rem_email, rem_nome, assunto, corpo, clientes):
    dominio = rem_email.split('@')[-1].lower()
    for c in clientes:
        for ap in [c['nome']] + [a for a in (c['apelidos'] or '').split(';')]:
            ap = ap.strip().lower()
            if ap and ('@' in ap or ('.' in ap and ' ' not in ap)) and (ap.lstrip('@') == dominio or ap == rem_email):
                return c['nome'], True
    alvo = norm(' '.join([rem_nome, assunto, corpo[:3000]]))
    for c in clientes:
        for ap in [c['nome']] + [a for a in (c['apelidos'] or '').split(';')]:
            apn = norm(ap).strip()
            if len(apn) >= 3 and '@' not in apn and not ('.' in apn and ' ' not in apn):
                if re.search(r'\b' + re.escape(apn) + r'\b', alvo):
                    return c['nome'], True
    if dominio and dominio not in DOMINIOS_GENERICOS:
        return dominio.split('.')[0].replace('-', ' ').title(), False
    return (rem_nome or rem_email), False


def analisar(rem_nome, rem_email, assunto, corpo, recebido, clientes, cfg, anexos_texto=''):
    """Aplica as regras e devolve a sugestão de demanda. resultado: demanda | triagem | ignorado

    O assunto e o corpo têm prioridade. O texto dos anexos só é usado para completar o que faltar
    (tipo, colaborador, datas), porque documentos como holerites citam INSS, FGTS etc. e confundiriam o tipo."""
    base = recebido
    assunto_limpo = R_PREFIXO_ASSUNTO.sub('', assunto or '').strip() or '(sem assunto)'
    encaminhado = bool(re.match(r'^\s*(fw|fwd|enc|tr)\s*:', assunto or '', re.I))
    corpo_limpo = limpar_corpo(corpo, encaminhado)[:8000]
    an, cn = norm(assunto_limpo), norm(corpo_limpo)
    trecho = corpo_limpo[:700]

    ignorar = [x.strip().lower() for x in (cfg.get('ignorar_remetentes') or '').split(',') if x.strip()]
    if any(x in rem_email.lower() for x in ignorar):
        return {'resultado': 'ignorado', 'motivo': 'Remetente na lista de ignorados', 'trecho': trecho}
    if R_AUTO_RESPOSTA.match(an):
        return {'resultado': 'ignorado', 'motivo': 'Resposta automática', 'trecho': trecho}
    if R_IGNORAR_CORPO.search(cn):
        return {'resultado': 'ignorado', 'motivo': 'Parece newsletter ou propaganda', 'trecho': trecho}

    tipo, outros = detectar_tipo(an, cn)
    if len(cn) < 160 and R_AGRADECIMENTO.match(cn) and not detectar_tipo('', cn)[0] and not anexos_texto:
        return {'resultado': 'ignorado', 'motivo': 'Agradecimento ou confirmação', 'trecho': trecho}

    obs = []
    xn = norm(anexos_texto)
    if not tipo and xn:
        tipo, outros = detectar_tipo('', xn)
        if tipo:
            obs.append('Tipo identificado pelo conteúdo dos anexos.')

    cliente, cadastrado = identificar_cliente(rem_email, rem_nome, assunto_limpo, corpo_limpo, clientes)
    colaborador = detectar_colaborador(assunto_limpo + '\n' + corpo_limpo)
    if not colaborador and anexos_texto:
        colaborador = detectar_colaborador(anexos_texto)
        if colaborador:
            obs.append('Colaborador encontrado nos anexos.')

    # ---------- prazo ----------
    datas = extrair_datas(an + '\n' + cn, base)
    datas_do_anexo = False
    if not datas and xn:
        datas = extrair_datas(xn, base)
        datas_do_anexo = bool(datas)
    explicitos = [d for _, d, p in datas if p]
    eventos = [d for _, d, p in datas if not p]
    futuros = [d for d in eventos if d >= base]
    prazo_legal, origem_legal = None, ''
    if tipo == 'Rescisão':
        janela = [d for _, d, _ in datas if base - timedelta(days=30) <= d <= base + timedelta(days=60)]
        if re.search(r'aviso', cn) and janela:
            # "cumprir o aviso até 30/11": a data é o fim do contrato, não o prazo do DP
            termino, explicitos = max(janela), []
        else:
            termino = next((d for d in eventos if base - timedelta(days=30) <= d <= base + timedelta(days=60)), base)
        prazo_legal = termino + timedelta(days=10)
        origem_legal = 'Regra legal: 10 dias após o término (' + termino.strftime('%d/%m') + ')'
    elif tipo == 'Admissão' and futuros:
        prazo_legal = futuros[0] - timedelta(days=1)
        origem_legal = 'Regra legal: eSocial até a véspera do início (' + futuros[0].strftime('%d/%m') + ')'
    elif tipo == 'Férias' and futuros:
        inicio = futuros[0]
        prazo_legal = inicio - timedelta(days=2)
        origem_legal = 'Regra legal: pagamento 2 dias antes do início (' + inicio.strftime('%d/%m') + ')'
        if (inicio - base).days < 30:
            obs.append('Atenção: o aviso de férias exige 30 dias de antecedência (CLT art. 135).')
    elif tipo == 'Acidente de trabalho':
        prazo_legal = proximo_dia_util(base)
        origem_legal = 'Regra legal: CAT até o 1º dia útil seguinte'

    if prazo_legal and tipo in ('Rescisão', 'Férias'):
        while not util_bancario(prazo_legal):  # pagamento: antecipa para o dia útil anterior
            prazo_legal -= timedelta(days=1)
    candidatos = []
    if explicitos:
        candidatos.append((min(explicitos), 'Informado no e-mail'))
    if prazo_legal:
        candidatos.append((prazo_legal, origem_legal))
    if candidatos:
        prazo, origem = min(candidatos, key=lambda x: x[0])
    else:
        prazo = somar_dias_uteis(base, int(cfg.get('prazo_padrao') or 3))
        origem = 'Prazo padrão (' + str(cfg.get('prazo_padrao')) + ' dias úteis)'
    if datas_do_anexo and not origem.startswith('Prazo padrão') and tipo != 'Acidente de trabalho':
        obs.append('Prazo calculado com data lida dos anexos: confira.')

    # ---------- prioridade ----------
    if R_URGENTE.search(an + ' ' + cn) or tipo in ('Rescisão', 'Acidente de trabalho', 'Notificação de órgão público') \
            or prazo <= somar_dias_uteis(base, 2):
        prioridade = 'Alta'
    elif tipo in ('Dúvida/Consultoria', None):
        prioridade = 'Baixa'
    else:
        prioridade = 'Média'

    if outros:
        obs.append('Também menciona: ' + ', '.join(outros) + '.')
    if not cadastrado:
        obs.append('Cliente não cadastrado: confira o nome.')

    return {
        'resultado': 'demanda' if tipo else 'triagem',
        'motivo': '' if tipo else 'Nenhuma palavra-chave de DP encontrada',
        'cliente': cliente, 'tipo': tipo or 'Outros', 'descricao': assunto_limpo, 'colaborador': colaborador,
        'prazo': prazo.isoformat(), 'origem': origem, 'prioridade': prioridade, 'obs': ' '.join(obs),
        'trecho': trecho, 'conversa': norm(assunto_limpo) + '|' + cliente,
    }

# ============================================================================
# ANEXOS: salvar e extrair texto (PDF, Word, Excel, TXT/CSV)
# ============================================================================

PASTA_ANEXOS = os.path.join(PASTA_DADOS, 'anexos')
MAX_TEXTO_ANEXO = 20000


def _xml_texto(xml, quebra):
    xml = re.sub(quebra, '\n', xml)
    return html.unescape(re.sub(r'<[^>]+>', '', xml))


def texto_docx(dados):
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        partes = [n for n in z.namelist() if re.match(r'word/(document|header\d*|footer\d*)\.xml$', n)]
        xml = ' '.join(z.read(n).decode('utf-8', 'replace') for n in sorted(partes))
    xml = re.sub(r'<w:tab/>', '\t', xml)
    return _xml_texto(xml, r'</w:p>|<w:br/>')


def texto_xlsx(dados):
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        compart = []
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in re.findall(r'<si>(.*?)</si>', z.read('xl/sharedStrings.xml').decode('utf-8', 'replace'), re.S):
                compart.append(html.unescape(''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))))
        linhas = []
        for n in sorted(x for x in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', x)):
            for row in re.findall(r'<row[^>]*>(.*?)</row>', z.read(n).decode('utf-8', 'replace'), re.S):
                cels = []
                for atrs, corpo in re.findall(r'<c([^>]*)>(.*?)</c>', row, re.S):
                    v = re.search(r'<v>(.*?)</v>', corpo, re.S)
                    t = re.search(r'<t[^>]*>(.*?)</t>', corpo, re.S)
                    if 't="s"' in atrs and v:
                        i = int(v.group(1))
                        cels.append(compart[i] if i < len(compart) else '')
                    elif t:
                        cels.append(html.unescape(t.group(1)))
                    elif v:
                        cels.append(v.group(1))
                if any(c.strip() for c in cels):
                    linhas.append(' | '.join(cels))
                if len(linhas) > 500:
                    break
    return '\n'.join(linhas)


def texto_pdf(dados):
    try:
        from pypdf import PdfReader
    except ImportError:
        return ''
    leitor = PdfReader(io.BytesIO(dados))
    textos = []
    for pagina in leitor.pages[:30]:
        textos.append(pagina.extract_text() or '')
        if sum(map(len, textos)) > MAX_TEXTO_ANEXO:
            break
    return '\n'.join(textos)


def extrair_texto_anexo(nome, dados):
    """Retorna (texto, aviso). aviso explica quando não foi possível ler."""
    ext = os.path.splitext(nome.lower())[1]
    try:
        if ext == '.pdf':
            t = texto_pdf(dados)
            aviso = '' if t.strip() else 'PDF sem texto (provavelmente escaneado/foto)'
        elif ext == '.docx':
            t, aviso = texto_docx(dados), ''
        elif ext in ('.xlsx', '.xlsm'):
            t, aviso = texto_xlsx(dados), ''
        elif ext in ('.txt', '.csv', '.xml', '.html', '.htm'):
            try:
                t = dados.decode('utf-8')
            except UnicodeDecodeError:
                t = dados.decode('cp1252', 'replace')
            if ext in ('.html', '.htm', '.xml'):
                t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
            aviso = ''
        elif ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.heic', '.webp'):
            t, aviso = '', 'Imagem: texto não pode ser lido automaticamente'
        else:
            t, aviso = '', 'Formato não lido automaticamente'
    except Exception as e:
        log.warning('Falha ao ler anexo %s: %s', nome, e)
        t, aviso = '', 'Não foi possível ler este arquivo'
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t).strip()
    return t[:MAX_TEXTO_ANEXO], aviso


def nome_seguro(nome):
    nome = re.sub(r'[\\/:*?"<>|\r\n]+', '_', nome or 'anexo').strip(' .') or 'anexo'
    return nome[:150]


def salvar_anexos(chave, msg):
    """Salva os anexos em dados/anexos/<pasta> e devolve [{nome, pasta, texto, aviso}]."""
    pasta = hashlib.sha1(chave.encode('utf-8')).hexdigest()[:16]
    destino = os.path.join(PASTA_ANEXOS, pasta)
    lista = []
    for parte in msg.iter_attachments():
        nome = parte.get_filename()
        if not nome:
            continue
        try:
            dados = parte.get_payload(decode=True) or b''
        except Exception:
            continue
        if not dados:
            continue
        nome = nome_seguro(nome)
        os.makedirs(destino, exist_ok=True)
        with open(os.path.join(destino, nome), 'wb') as f:
            f.write(dados)
        texto, aviso = extrair_texto_anexo(nome, dados)
        lista.append({'nome': nome, 'pasta': pasta, 'texto': texto, 'aviso': aviso, 'tamanho': len(dados)})
    return lista


def anexos_para_tela(lista):
    """Versão resumida (sem o texto inteiro) guardada no banco para mostrar no painel."""
    return json.dumps([{'nome': a['nome'], 'pasta': a['pasta'], 'aviso': a['aviso'], 'tamanho': a['tamanho'],
                        'trecho': a['texto'][:1500]} for a in lista], ensure_ascii=False)

# ============================================================================
# LEITURA DA CAIXA DE E-MAIL (IMAP)
# ============================================================================

_lock_leitura = threading.Lock()
_MESES_IMAP = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


class ErroConfig(Exception):
    pass


def conectar_imap(cfg):
    cfg['email'], senha = credenciais(cfg)
    if not cfg['imap_host']:
        raise ErroConfig('Informe o servidor IMAP em Configurações.')
    try:
        M = imaplib.IMAP4_SSL(cfg['imap_host'], int(cfg['imap_port']), timeout=60)
    except (socket.gaierror, OSError) as e:
        raise ErroConfig('Não consegui conectar em ' + cfg['imap_host'] + ': ' + str(e))
    try:
        M.login(cfg['email'], senha)
    except imaplib.IMAP4.error as e:
        raise ErroConfig('O provedor recusou o login. Confira o e-mail e a senha de app. (' + str(e)[:150] + ')')
    return M


def texto_do_email(msg):
    parte = msg.get_body(preferencelist=('plain', 'html'))
    if parte is None:
        return ''
    try:
        conteudo = parte.get_content()
    except Exception:
        conteudo = (parte.get_payload(decode=True) or b'').decode('utf-8', 'replace')
    if parte.get_content_type() == 'text/html':
        conteudo = re.sub(r'(?is)<(script|style).*?</\1>', ' ', conteudo)
        conteudo = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</tr>|</li>', '\n', conteudo)
        conteudo = html.unescape(re.sub(r'<[^>]+>', ' ', conteudo))
        conteudo = re.sub(r'[ \t\xa0]+', ' ', conteudo)
    return conteudo


def ler_emails():
    if not _lock_leitura.acquire(blocking=False):
        return 'Já existe uma leitura em andamento.'
    try:
        return _ler_emails()
    finally:
        _lock_leitura.release()


def _ler_emails():
    cfg = carregar_config()
    try:
        M = conectar_imap(cfg)
    except ErroConfig as e:
        meta_set('ultimo_erro', str(e))
        return str(e)
    novas = atualizadas = triagem = ignorados = 0
    try:
        typ, _ = M.select('"' + cfg['pasta'] + '"', readonly=True)
        if typ != 'OK':
            raise ErroConfig('Pasta "' + cfg['pasta'] + '" não encontrada.')
        uidv = (M.response('UIDVALIDITY')[1] or [b'0'])[0]
        uidv = uidv.decode() if isinstance(uidv, bytes) else str(uidv)
        try:
            corte = date.fromisoformat(cfg['ler_a_partir'])
        except (TypeError, ValueError):
            corte = date.today() - timedelta(days=3)
        desde = max(corte, date.today() - timedelta(days=20))
        criterio = '%02d-%s-%d' % (desde.day, _MESES_IMAP[desde.month - 1], desde.year)
        typ, data = M.uid('search', None, 'SINCE', criterio)
        uids = data[0].split() if data and data[0] else []
        prefixo = cfg['email'].lower() + '|' + cfg['pasta'] + '|' + uidv + '|'
        with db() as con:
            vistos = {r[0] for r in con.execute('SELECT chave FROM emails WHERE chave LIKE ?', (prefixo + '%',))}
            clientes = [dict(r) for r in con.execute("SELECT * FROM clientes WHERE nome <> ''")]
        pendentes = [u for u in uids if prefixo + u.decode() not in vistos][:300]

        for u in pendentes:
            chave = prefixo + u.decode()
            typ, partes = M.uid('fetch', u, '(BODY.PEEK[])')
            raw = next((p[1] for p in partes if isinstance(p, tuple)), None)
            if not raw:
                continue
            msg = email.message_from_bytes(raw, policy=email.policy.default)
            rem_nome, rem_email = parseaddr(str(msg.get('From', '')))
            rem_email = rem_email.lower()
            assunto = str(msg.get('Subject', '') or '')
            try:
                recebido_dt = parsedate_to_datetime(str(msg.get('Date'))).astimezone()
            except Exception:
                recebido_dt = datetime.now()
            recebido = recebido_dt.date()
            remetente = (rem_nome + ' <' + rem_email + '>') if rem_nome else rem_email

            if recebido < corte or rem_email == cfg['email'].lower():
                with _lock_db, db() as con:
                    con.execute('INSERT OR IGNORE INTO emails(chave,recebido,remetente,assunto,resultado,lido_em) VALUES (?,?,?,?,?,?)',
                                (chave, recebido_dt.strftime('%Y-%m-%d %H:%M'), remetente, assunto, 'pulado', agora()))
                continue

            corpo = texto_do_email(msg)
            try:
                anexos = salvar_anexos(chave, msg)
            except Exception:
                log.exception('Erro ao salvar anexos')
                anexos = []
            anexos_json = anexos_para_tela(anexos) if anexos else ''
            anexos_texto = '\n\n'.join(a['texto'] for a in anexos if a['texto'])
            if anexos:
                corpo += '\n\nAnexos: ' + ', '.join(a['nome'] for a in anexos)
            try:
                r = analisar(rem_nome, rem_email, assunto, corpo, recebido, clientes, cfg, anexos_texto)
            except Exception as e:  # nunca perde o e-mail: manda para triagem
                log.exception('Erro nas regras')
                r = {'resultado': 'triagem', 'motivo': 'Erro ao analisar: ' + str(e), 'trecho': corpo[:700]}

            with _lock_db, db() as con:
                demanda_id, resultado = '', r['resultado']
                if resultado == 'demanda':
                    existente = con.execute(
                        "SELECT id, prazo, obs FROM demandas WHERE conversa=? AND status<>'Concluída' ORDER BY criado DESC LIMIT 1",
                        (r['conversa'],)).fetchone()
                    if existente:
                        nota = 'Nova mensagem de ' + (rem_nome or rem_email) + ' em ' + recebido.strftime('%d/%m') + '.'
                        prazo = existente['prazo']
                        if r['origem'].startswith('Informado') and (not prazo or r['prazo'] < prazo):
                            prazo = r['prazo']
                            nota += ' Prazo alterado para ' + date.fromisoformat(prazo).strftime('%d/%m') + '.'
                        if anexos:
                            nota += ' Novos anexos: ' + ', '.join(a['nome'] for a in anexos) + '.'
                            antigos = json.loads(con.execute('SELECT anexos FROM demandas WHERE id=?', (existente['id'],)).fetchone()[0] or '[]')
                            con.execute('UPDATE demandas SET anexos=? WHERE id=?',
                                        (json.dumps(antigos + json.loads(anexos_json), ensure_ascii=False), existente['id']))
                        con.execute('UPDATE demandas SET prazo=?, obs=? WHERE id=?',
                                    (prazo, ((existente['obs'] or '') + '\n' + nota).strip(), existente['id']))
                        demanda_id, resultado = existente['id'], 'atualizou'
                        atualizadas += 1
                    else:
                        demanda_id = nova_demanda(con, prefixo='EM', fonte='E-mail', remetente=remetente, assunto=assunto,
                                                  email_chave=chave, anexos=anexos_json, **{k: r[k] for k in (
                                                      'cliente', 'tipo', 'descricao', 'colaborador', 'prazo', 'origem',
                                                      'prioridade', 'obs', 'trecho', 'conversa')})
                        novas += 1
                elif resultado == 'triagem':
                    triagem += 1
                else:
                    ignorados += 1
                sugestao = {k: r.get(k, '') for k in ('cliente', 'tipo', 'descricao', 'colaborador', 'prazo', 'prioridade', 'motivo')}
                con.execute('INSERT OR REPLACE INTO emails(chave,recebido,remetente,assunto,trecho,resultado,sugestao,demanda_id,lido_em,anexos) '
                            'VALUES (?,?,?,?,?,?,?,?,?,?)', (
                    chave, recebido_dt.strftime('%Y-%m-%d %H:%M'), remetente, assunto, r.get('trecho', ''),
                    resultado, json.dumps(sugestao, ensure_ascii=False), demanda_id, agora(), anexos_json))
        restantes = max(0, len([u for u in uids if prefixo + u.decode() not in vistos]) - len(pendentes))
    except ErroConfig as e:
        meta_set('ultimo_erro', str(e))
        return str(e)
    except (imaplib.IMAP4.error, OSError) as e:
        log.exception('Erro de IMAP')
        meta_set('ultimo_erro', 'Erro de conexão: ' + str(e)[:200])
        return 'Erro de conexão com o e-mail: ' + str(e)[:200]
    finally:
        try:
            M.logout()
        except Exception:
            pass

    txt = '%d demanda(s) nova(s), %d atualizada(s), %d para triagem, %d ignorado(s).' % (novas, atualizadas, triagem, ignorados)
    if restantes:
        txt += ' Ainda há %d e-mail(s) na fila.' % restantes
    meta_set('ultima_leitura', agora())
    meta_set('ultimo_resultado', txt)
    meta_set('ultimo_erro', '')
    log.info('Leitura: ' + txt)
    return txt


def testar_conexao():
    cfg = carregar_config()
    M = conectar_imap(cfg)
    typ, dados = M.select('"' + cfg['pasta'] + '"', readonly=True)
    M.logout()
    if typ != 'OK':
        raise ErroConfig('Login OK, mas a pasta "' + cfg['pasta'] + '" não existe.')
    return 'Conexão OK! A pasta "' + cfg['pasta'] + '" tem ' + dados[0].decode() + ' e-mail(s).'

# ============================================================================
# CALENDÁRIO DE OBRIGAÇÕES LEGAIS
# ============================================================================

def vencimento(o, ano, mes):
    ultimo = ultimo_dia_mes(ano, mes)
    if o['regra'] == 'DIA_UTIL':
        cont = 0
        for dia in range(1, ultimo + 1):
            d = date(ano, mes, dia)
            if util_trabalhista(d):
                cont += 1
                if cont == o['dia']:
                    return d
        return None
    d = date(ano, mes, min(int(o['dia']), ultimo))
    passo = timedelta(days=1 if o['regra'] == 'POSTERGA' else -1)
    while not util_bancario(d):
        d += passo
    return d


def gerar_obrigacoes():
    cfg = carregar_config()
    hoje = date.today()
    limite = hoje + timedelta(days=int(cfg['antecedencia']))
    with db() as con:
        clientes = [dict(r) for r in con.execute('SELECT * FROM clientes WHERE ativo=1 AND nome<>""')]
        obrigs = [dict(r) for r in con.execute('SELECT * FROM obrigacoes WHERE ativa=1 AND dia>0')]
    criadas = 0
    with _lock_db, db() as con:
        ano, mes = hoje.year, hoje.month
        while date(ano, mes, 1) <= limite:
            for o in obrigs:
                meses = [int(x) for x in re.split(r'[;,\s]+', str(o['meses'] or '')) if x.isdigit()]
                if meses and mes not in meses:
                    continue
                venc = vencimento(o, ano, mes)
                if not venc or venc < hoje or venc > limite:
                    continue
                comp = str(ano) if meses else (date(ano, mes, 1) - timedelta(days=1)).strftime('%m/%Y')
                for c in clientes:
                    filtro = [x.strip().lower() for x in (c['obrigacoes'] or '').split(';') if x.strip()]
                    if filtro and not any(x in o['nome'].lower() for x in filtro):
                        continue
                    did = 'CAL-' + uuid.uuid5(uuid.NAMESPACE_URL, c['nome'] + '|' + o['nome'] + '|%d-%d' % (ano, mes)).hex[:10]
                    cur = con.execute('SELECT 1 FROM demandas WHERE id=?', (did,)).fetchone()
                    if cur:
                        continue
                    nova_demanda(con, id=did, cliente=c['nome'], tipo=o['tipo'] or 'Encargos e guias',
                                 descricao=o['nome'] + ' (competência ' + comp + ')', prazo=venc.isoformat(),
                                 origem='Calendário legal', prioridade='Média', fonte='Calendário legal', obs=o['obs'])
                    criadas += 1
            mes += 1
            if mes > 12:
                mes, ano = 1, ano + 1
    return '%d obrigação(ões) criada(s) para os próximos %s dias.' % (criadas, cfg['antecedencia'])

# ============================================================================
# RESUMO DIÁRIO POR E-MAIL (SMTP)
# ============================================================================

def enviar_resumo(forcar=False):
    cfg = carregar_config()
    if not cfg['resumo_ativo'] and not forcar:
        return 'Resumo diário desativado.'
    try:
        cfg['email'], senha = credenciais(cfg)
    except ErroConfig as e:
        return str(e)
    if not cfg['smtp_host']:
        return 'Informe o servidor SMTP em Configurações.'
    hoje = date.today()
    limite = somar_dias_uteis(hoje, 2).isoformat()
    with db() as con:
        abertas = [dict(r) for r in con.execute(
            "SELECT * FROM demandas WHERE status<>'Concluída' AND prazo<>'' AND prazo<=? ORDER BY prazo, cliente", (limite,))]
    h = hoje.isoformat()
    grupos = [('Atrasadas', '#b42318', [d for d in abertas if d['prazo'] < h]),
              ('Vencem hoje', '#a15c07', [d for d in abertas if d['prazo'] == h]),
              ('Próximos 2 dias úteis', '#2457d6', [d for d in abertas if d['prazo'] > h])]
    if not abertas:
        return 'Nada atrasado ou vencendo nos próximos 2 dias úteis. Resumo não enviado.'
    e = html.escape
    corpo = '<div style="font-family:Arial,sans-serif;max-width:680px"><h2>Resumo do DP · ' + hoje.strftime('%d/%m/%Y') + '</h2>'
    for titulo, cor, itens in grupos:
        if not itens:
            continue
        corpo += '<h3 style="color:%s;margin:18px 0 6px">%s (%d)</h3><table style="border-collapse:collapse;width:100%%;font-size:14px">' % (cor, titulo, len(itens))
        for d in itens:
            corpo += ('<tr><td style="padding:6px 8px;border-bottom:1px solid #eee;white-space:nowrap">%s</td>'
                      '<td style="padding:6px 8px;border-bottom:1px solid #eee"><b>%s</b> · %s<br>%s%s</td></tr>') % (
                date.fromisoformat(d['prazo']).strftime('%d/%m'), e(d['cliente']), e(d['tipo']), e(d['descricao']),
                (' <span style="color:#666">(' + e(d['colaborador']) + ')</span>') if d['colaborador'] else '')
        corpo += '</table>'
    corpo += '<p style="margin-top:20px;color:#666">Painel: http://localhost:%d</p></div>' % PORTA
    partes = ['%d %s' % (len(i), t.lower()) for t, _, i in grupos if i]

    m = EmailMessage()
    m['Subject'] = 'DP: ' + ', '.join(partes)
    m['From'] = cfg['email']
    m['To'] = cfg['resumo_para'] or cfg['email']
    m.set_content('Abra este e-mail num leitor com suporte a HTML.')
    m.add_alternative(corpo, subtype='html')
    porta = int(cfg['smtp_port'])
    if porta == 465:
        with smtplib.SMTP_SSL(cfg['smtp_host'], porta, timeout=30, context=ssl.create_default_context()) as s:
            s.login(cfg['email'], senha)
            s.send_message(m)
    else:
        with smtplib.SMTP(cfg['smtp_host'], porta, timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(cfg['email'], senha)
            s.send_message(m)
    return 'Resumo enviado para ' + m['To'] + '.'

# ============================================================================
# ROTINA AUTOMÁTICA
# ============================================================================

def agendador():
    time.sleep(3)
    try:
        gerar_obrigacoes()
    except Exception:
        log.exception('Erro ao gerar obrigações')
    while True:
        try:
            ler_emails()
        except Exception:
            log.exception('Erro na leitura de e-mails')
        try:
            hoje = date.today().isoformat()
            if meta_get('ultima_rotina') != hoje and datetime.now().hour >= 6:
                meta_set('ultima_rotina', hoje)
                log.info(gerar_obrigacoes())
                log.info(enviar_resumo())
        except Exception:
            log.exception('Erro na rotina diária')
        time.sleep(max(1, int(carregar_config()['intervalo_min'])) * 60)

# ============================================================================
# SERVIDOR WEB LOCAL (API + painel)
# ============================================================================

TABELAS = {
    'clientes': ['nome', 'apelidos', 'ativo', 'obrigacoes', 'obs'],
    'obrigacoes': ['nome', 'tipo', 'regra', 'dia', 'meses', 'ativa', 'obs'],
    'feriados': ['data', 'descricao'],
}


def api_dados():
    corte = (date.today() - timedelta(days=30)).isoformat()
    with db() as con:
        demandas = [dict(r) for r in con.execute(
            "SELECT * FROM demandas WHERE status<>'Concluída' OR concluido>=? OR concluido=''", (corte,))]
        triagem = con.execute("SELECT COUNT(*) FROM emails WHERE resultado='triagem'").fetchone()[0]
        clientes = [r[0] for r in con.execute("SELECT nome FROM clientes WHERE nome<>'' ORDER BY nome")]
    for d in demandas:
        d['anexos'] = json.loads(d.get('anexos') or '[]')
    return {
        'hoje': date.today().isoformat(), 'demandas': demandas, 'clientes': clientes, 'tipos': TIPOS,
        'triagem': triagem, 'configurado': status_chave(carregar_config())['ok'],
        'ultima_leitura': meta_get('ultima_leitura'), 'ultimo_resultado': meta_get('ultimo_resultado'),
        'ultimo_erro': meta_get('ultimo_erro'),
    }


def api_emails(filtro):
    sql = "SELECT * FROM emails WHERE resultado<>'pulado'"
    if filtro == 'triagem':
        sql += " AND resultado='triagem'"
    sql += ' ORDER BY recebido DESC LIMIT 300'
    with db() as con:
        linhas = [dict(r) for r in con.execute(sql)]
    for l in linhas:
        l['sugestao'] = json.loads(l['sugestao'] or '{}')
        l['anexos'] = json.loads(l.get('anexos') or '[]')
    return linhas


def api_post(rota, d):
    if rota == '/api/status':
        if d['status'] not in STATUS:
            raise ValueError('Status inválido.')
        concl = agora() if d['status'] == 'Concluída' else ''
        with _lock_db, db() as con:
            con.executemany('UPDATE demandas SET status=?, concluido=? WHERE id=?', [(d['status'], concl, i) for i in d['ids']])
        return {'ok': True}
    if rota == '/api/prazo':
        date.fromisoformat(d['prazo'])
        with _lock_db, db() as con:
            con.execute("UPDATE demandas SET prazo=?, origem='Alterado manualmente' WHERE id=?", (d['prazo'], d['id']))
        return {'ok': True}
    if rota == '/api/nova':
        if not d.get('cliente') or not d.get('descricao'):
            raise ValueError('Informe pelo menos o cliente e a descrição.')
        prazo = d.get('prazo') or somar_dias_uteis(date.today(), int(carregar_config()['prazo_padrao'])).isoformat()
        date.fromisoformat(prazo)
        with _lock_db, db() as con:
            fonte = 'E-mail' if d.get('email_chave') else 'Manual'
            em = con.execute('SELECT * FROM emails WHERE chave=?', (d.get('email_chave', ''),)).fetchone()
            did = nova_demanda(
                con, prefixo='EM' if em else 'MAN', cliente=d['cliente'], tipo=d.get('tipo') if d.get('tipo') in TIPOS else 'Outros',
                descricao=d['descricao'], colaborador=d.get('colaborador', ''), prazo=prazo,
                origem='Informado manualmente' if d.get('prazo') else 'Prazo padrão',
                prioridade=d.get('prioridade') if d.get('prioridade') in PRIORIDADES else 'Média', fonte=fonte, obs=d.get('obs', ''),
                remetente=em['remetente'] if em else '', assunto=em['assunto'] if em else '', trecho=em['trecho'] if em else '',
                email_chave=em['chave'] if em else '', anexos=em['anexos'] if em else '',
                conversa=(norm(R_PREFIXO_ASSUNTO.sub('', em['assunto'] or '').strip()) + '|' + d['cliente']) if em else '')
            if em:
                con.execute("UPDATE emails SET resultado='demanda (manual)', demanda_id=? WHERE chave=?", (did, em['chave']))
        # Sincronizar com painel profissional em background
        try:
            from integracao_painel_profissional import sincronizar_ao_criar
            threading.Thread(target=lambda: sincronizar_ao_criar({
                'cliente': d['cliente'], 'descricao': d['descricao'], 'tipo': d.get('tipo', 'Outros'),
                'prioridade': d.get('prioridade', 'Média'), 'prazo': prazo, 'obs': d.get('obs', '')
            }), daemon=True).start()
        except Exception:
            pass
        return {'ok': True}
    if rota == '/api/emails/ignorar':
        with _lock_db, db() as con:
            con.executemany("UPDATE emails SET resultado='ignorado (manual)' WHERE chave=?", [(c,) for c in d['chaves']])
        return {'ok': True}
    if rota == '/api/buscar':
        return {'msg': ler_emails()}
    if rota == '/api/calendario':
        return {'msg': gerar_obrigacoes()}
    if rota == '/api/resumo':
        return {'msg': enviar_resumo(forcar=True)}
    if rota == '/api/config':
        salvar_config(d)
        return {'ok': True, 'config': config_publica()}
    if rota == '/api/testar':
        return {'msg': testar_conexao()}
    if rota.startswith('/api/tabela/'):
        nome = rota.rsplit('/', 1)[1]
        cols = TABELAS[nome]
        linhas = [[(l.get(c) if l.get(c) is not None else '') for c in cols] for l in d['linhas']]
        if nome == 'feriados':
            linhas = [l for l in linhas if l[0]]
            for l in linhas:
                date.fromisoformat(l[0])
        else:
            linhas = [l for l in linhas if str(l[0]).strip()]
        with _lock_db, db() as con:
            con.execute('DELETE FROM ' + nome)
            con.executemany('INSERT INTO %s(%s) VALUES (%s)' % (nome, ','.join(cols), ','.join('?' * len(cols))), linhas)
        _cache_feriados.clear()
        return {'ok': True}
    raise KeyError(rota)


def exportar_csv():
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    cols = ['id', 'criado', 'cliente', 'tipo', 'descricao', 'colaborador', 'prazo', 'origem', 'prioridade', 'status',
            'fonte', 'remetente', 'assunto', 'obs', 'concluido']
    w.writerow(cols)
    with db() as con:
        for r in con.execute('SELECT %s FROM demandas ORDER BY prazo' % ','.join(cols)):
            w.writerow(list(r))
    return ('﻿' + buf.getvalue()).encode('utf-8')


def gerar_pagina_impressao():
    css = '<style>* { margin:0; padding:0; } body { font-family:Arial,sans-serif; padding:20px; background:white; } .cab { border-bottom:3px solid #2457d6; padding-bottom:15px; margin-bottom:20px; } .cab h1 { color:#2457d6; font-size:24px; } .item { border:1px solid #ddd; padding:12px; margin-bottom:15px; page-break-inside:avoid; } .linha1 { display:flex; align-items:center; margin-bottom:8px; font-weight:bold; } .check { width:18px; height:18px; border:2px solid #333; margin-right:10px; display:inline-block; } .cliente { color:#2457d6; font-size:15px; } .tipo { background:#e0e0e0; padding:1px 6px; font-size:11px; margin-left:8px; border-radius:3px; } .desc { font-weight:bold; margin:8px 0; } .info { font-size:12px; color:#666; margin:5px 0; } .label { font-weight:bold; width:70px; display:inline-block; } .trecho { background:#f5f5f5; padding:6px; margin:5px 0; font-size:11px; max-height:80px; overflow:hidden; white-space:pre-wrap; border-left:2px solid #ccc; } @media print { body{padding:10px;} }</style>'

    pagina_html = f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>Impressão</title>{css}</head><body>'

    try:
        hoje = date.today()
        with db() as con:
            demandas = [dict(r) for r in con.execute("SELECT * FROM demandas WHERE status<>'Concluída' ORDER BY prazo, cliente")]

        pagina_html += f'<div class="cab"><h1>DEMANDAS DP - CHECKLIST</h1><p>Imprima e marque conforme completar | {hoje.strftime("%d/%m/%Y")}</p></div>'

        for d in demandas:
            prazo_txt = ''
            if d['prazo']:
                dias = (date.fromisoformat(d['prazo']) - hoje).days
                if dias < 0:
                    prazo_txt = f'<b style="color:red">[ATRASADA]</b>'
                elif dias == 0:
                    prazo_txt = f'<b style="color:orange">[HOJE]</b>'
                elif dias <= 2:
                    prazo_txt = f'<b style="color:blue">[{dias}d]</b>'
                else:
                    prazo_txt = date.fromisoformat(d['prazo']).strftime('[%d/%m]')

            pagina_html += '<div class="item"><div class="linha1"><div class="check"></div><span class="cliente">' + html.escape(d['cliente']) + '</span>'
            pagina_html += '<span class="tipo">' + html.escape(d['tipo']) + '</span> ' + prazo_txt + '</div>'
            pagina_html += '<div class="desc">' + html.escape(d['descricao']) + '</div>'

            pagina_html += '<div class="info">'
            if d.get('remetente'):
                pagina_html += '<div><span class="label">De:</span> ' + html.escape(d['remetente']) + '</div>'
            if d.get('assunto'):
                pagina_html += '<div><span class="label">Assunto:</span> ' + html.escape(d['assunto']) + '</div>'
            if d.get('colaborador'):
                pagina_html += '<div><span class="label">Pessoa:</span> ' + html.escape(d['colaborador']) + '</div>'
            if d.get('trecho'):
                pagina_html += '<div class="trecho">' + html.escape(d['trecho'][:500]) + '</div>'
            if d.get('obs'):
                pagina_html += '<div><span class="label">Notas:</span> ' + html.escape(d['obs']) + '</div>'
            pagina_html += '</div></div>'

    except Exception as e:
        pagina_html += '<p style="color:red">Erro: ' + str(e) + '</p>'

    pagina_html += '<script>window.print();</script></body></html>'
    return pagina_html.encode('utf-8')


def gerar_pagina_impressao_old():
    hoje = date.today()
    with db() as con:
        demandas = [dict(r) for r in con.execute(
            "SELECT * FROM demandas WHERE status<>'Concluída' ORDER BY prazo, cliente")]

    pagina = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>Demandas DP - Impressão</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: white; color: #333; line-height: 1.4; }
        .pagina { page-break-after: always; padding: 20px; max-width: 100%; }
        .cabecalho { margin-bottom: 20px; border-bottom: 2px solid #333; padding-bottom: 10px; }
        .cabecalho h1 { font-size: 24px; margin-bottom: 5px; }
        .cabecalho p { font-size: 12px; color: #666; }
        .lista { margin-top: 20px; }
        .item { margin-bottom: 15px; page-break-inside: avoid; }
        .check {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #333;
            margin-right: 10px;
            vertical-align: middle;
        }
        .prazo {
            display: inline-block;
            background: #f0f0f0;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
            margin-left: 10px;
            font-weight: bold;
        }
        .prazo.urgente { background: #ffcccc; }
        .prazo.hoje { background: #ffffcc; }
        .prazo.breve { background: #ccccff; }
        .desc { margin: 5px 0 0 30px; font-size: 13px; }
        .meta { margin: 3px 0 0 30px; font-size: 11px; color: #666; }
        .tipo {
            display: inline-block;
            background: #e0e0e0;
            padding: 1px 6px;
            border-radius: 3px;
            font-size: 11px;
            margin-right: 5px;
        }
        .obs { margin: 3px 0 0 30px; font-size: 11px; color: #666; font-style: italic; }
        @media print {
            body { margin: 0; }
            .pagina { padding: 10px; }
        }
    </style>
</head>
<body>
<div class="cabecalho">
    <h1>DEMANDAS DP - CHECKLIST</h1>
    <p>Imprima e marque conforme completar as tarefas | ''' + hoje.strftime('%d/%m/%Y') + '''</p>
</div>

<div class="lista">
'''

    for d in demandas:
        if d['prazo']:
            dias = (date.fromisoformat(d['prazo']) - hoje).days
            if dias < 0:
                classe_prazo = 'urgente'
                texto_prazo = 'ATRASADA'
            elif dias == 0:
                classe_prazo = 'hoje'
                texto_prazo = 'HOJE'
            elif dias <= 2:
                classe_prazo = 'breve'
                texto_prazo = f'{dias}d'
            else:
                classe_prazo = ''
                texto_prazo = date.fromisoformat(d['prazo']).strftime('%d/%m')
            prazo_html = f'<span class="prazo {classe_prazo}">{texto_prazo}</span>'
        else:
            prazo_html = ''

        obs_html = f'<div class="obs">{html.escape(d["obs"])}</div>' if d['obs'] else ''

        pagina += f'''<div class="item">
    <div>
        <span class="check"></span>
        <strong>{html.escape(d["cliente"])}</strong>
        <span class="tipo">{html.escape(d["tipo"])}</span>
        {prazo_html}
    </div>
    <div class="desc">{html.escape(d["descricao"])}</div>'''

        if d['colaborador']:
            pagina += f'<div class="meta">👤 {html.escape(d["colaborador"])}</div>'

        pagina += obs_html + '</div>'

    pagina += '''
</div>

<script>
    window.print();
</script>
</body>
</html>'''

    return pagina.encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _host_ok(self):
        # Aceita conexões de qualquer host (necessário para Railway/produção)
        return True

    def _enviar(self, codigo, corpo, tipo='application/json; charset=utf-8', extra=None):
        if not isinstance(corpo, bytes):
            corpo = json.dumps(corpo, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(codigo)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(corpo)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if not self._host_ok():
            return self._enviar(403, {'erro': 'Acesso negado'})
        u = urlparse(self.path)
        try:
            if u.path in ('/', '/index.html'):
                with open(os.path.join(BASE, 'painel.html'), 'rb') as f:
                    return self._enviar(200, f.read(), 'text/html; charset=utf-8')
            if u.path == '/api/dados':
                return self._enviar(200, api_dados())
            if u.path == '/api/emails':
                return self._enviar(200, api_emails(parse_qs(u.query).get('filtro', [''])[0]))
            if u.path == '/api/config':
                return self._enviar(200, {'config': config_publica(), 'provedores': PROVEDORES})
            if u.path.startswith('/api/arquivos/'):
                tipo = u.path.split('/api/arquivos/', 1)[1]
                arquivos = ARQUIVOS_NECESSARIOS.get(tipo, [])
                return self._enviar(200, {'tipo': tipo, 'arquivos': arquivos})
            if u.path.startswith('/api/tabela/'):
                nome = u.path.rsplit('/', 1)[1]
                with db() as con:
                    linhas = [dict(r) for r in con.execute('SELECT %s FROM %s' % (','.join(TABELAS[nome]), nome))]
                return self._enviar(200, linhas)
            if u.path == '/anexo':
                q = parse_qs(u.query)
                pasta = q.get('p', [''])[0]
                nome = q.get('n', [''])[0]
                if not re.fullmatch(r'[0-9a-f]{16}', pasta) or nome != nome_seguro(nome):
                    return self._enviar(400, {'erro': 'Arquivo inválido'})
                caminho = os.path.join(PASTA_ANEXOS, pasta, nome)
                if not os.path.isfile(caminho):
                    return self._enviar(404, {'erro': 'Arquivo não encontrado'})
                tipo = mimetypes.guess_type(nome)[0] or 'application/octet-stream'
                inline = tipo in ('application/pdf', 'text/plain') or tipo.startswith('image/')
                with open(caminho, 'rb') as f:
                    disp = ('inline' if inline else 'attachment') + "; filename*=UTF-8''" + quote(nome)
                    return self._enviar(200, f.read(), tipo, {'Content-Disposition': disp})
            if u.path == '/exportar.csv':
                return self._enviar(200, exportar_csv(), 'text/csv; charset=utf-8',
                                    {'Content-Disposition': 'attachment; filename="demandas-dp.csv"'})
            if u.path == '/imprimir':
                return self._enviar(200, gerar_pagina_impressao(), 'text/html; charset=utf-8')
            return self._enviar(404, {'erro': 'Não encontrado'})
        except Exception as e:
            log.exception('GET ' + u.path)
            return self._enviar(500, {'erro': str(e)})

    def do_POST(self):
        # Só aceita pedidos vindos do próprio painel (protege contra sites maliciosos chamando o localhost)
        if not self._host_ok() or self.headers.get('X-Painel') != '1':
            return self._enviar(403, {'erro': 'Acesso negado'})
        try:
            n = int(self.headers.get('Content-Length') or 0)
            dados = json.loads(self.rfile.read(n) or b'{}')
            return self._enviar(200, api_post(urlparse(self.path).path, dados))
        except KeyError as e:
            return self._enviar(404, {'erro': 'Rota ou campo desconhecido: ' + str(e)})
        except (ValueError, ErroConfig) as e:
            return self._enviar(400, {'erro': str(e)})
        except Exception as e:
            log.exception('POST ' + self.path)
            return self._enviar(500, {'erro': str(e)})


def main():
    iniciar_db()
    try:
        servidor = ThreadingHTTPServer(('0.0.0.0', PORTA), Handler)
    except OSError:
        # Já está rodando: só abre o navegador
        webbrowser.open('http://localhost:%d' % PORTA)
        return
    with open(os.path.join(PASTA_DADOS, 'painel.pid'), 'w') as f:
        f.write(str(os.getpid()))
    threading.Thread(target=agendador, daemon=True).start()
    log.info('Painel DP rodando em http://localhost:%d' % PORTA)
    if '--sem-navegador' not in sys.argv:
        webbrowser.open('http://localhost:%d' % PORTA)
    servidor.serve_forever()


if __name__ == '__main__':
    main()
