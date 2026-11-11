#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sqlite3
import re
from pathlib import Path

# Caminho do banco de dados
db_path = Path(__file__).parent / "painel.db"

def extrair_dominio(email):
    """Extrai o domínio de um email"""
    if not email or '@' not in email:
        return None
    return email.split('@')[1].lower()

def extrair_emails(campo_email):
    """Extrai múltiplos emails de um campo (podem ser separados por /)"""
    if not campo_email:
        return []
    # Separar por / e limpar espaços
    emails = [e.strip() for e in str(campo_email).split('/')]
    return [e for e in emails if e and '@' in e]

def processar_clientes(arquivo_json):
    """Processa o arquivo JSON e importa para o banco"""

    with open(arquivo_json, 'r', encoding='utf-8-sig') as f:
        clientes_dados = json.load(f)

    print(f"Processando {len(clientes_dados)} clientes...")

    # Conectar ao banco
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Criar tabela se não existir
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            nome TEXT PRIMARY KEY,
            apelidos TEXT,
            ativo INTEGER DEFAULT 1,
            obrigacoes TEXT,
            obs TEXT
        )
    ''')

    importados = 0
    atualizados = 0

    for cliente in clientes_dados:
        nome = cliente['Nome'].strip()
        if not nome:
            continue

        # Extrair emails e criar apelidos (domínios + serviço)
        emails = extrair_emails(cliente.get('Email', ''))
        dominios = [extrair_dominio(e) for e in emails if extrair_dominio(e)]

        # Criar apelidos: nome do cliente + domínios + serviço
        apelidos = [
            nome,
            cliente.get('CNPJ', '').replace('.', '').replace('/', ''),  # CNPJ sem formatação
            cliente.get('Servidor', ''),  # Servidor como apelido
            cliente.get('Servico', ''),  # Serviço como apelido
        ]
        apelidos.extend(dominios)

        # Remover vazios e duplicatas
        apelidos = list(set([a for a in apelidos if a]))
        apelidos_str = '; '.join(apelidos)

        # Observação com informações de contato e serviço
        obs = f"CNPJ: {cliente.get('CNPJ', '')}\n"
        obs += f"Serviço: {cliente.get('Servico', '')}\n"
        obs += f"Servidor: {cliente.get('Servidor', '')}\n"
        obs += f"Email(s): {', '.join(emails)}"

        # Verificar se cliente já existe
        cur.execute('SELECT * FROM clientes WHERE nome = ?', (nome,))
        existe = cur.fetchone()

        if existe:
            # Atualizar
            cur.execute('''
                UPDATE clientes
                SET apelidos = ?, ativo = 1, obs = ?
                WHERE nome = ?
            ''', (apelidos_str, obs, nome))
            atualizados += 1
            print(f"  ✓ Atualizado: {nome}")
        else:
            # Inserir
            cur.execute('''
                INSERT INTO clientes (nome, apelidos, ativo, obs)
                VALUES (?, ?, 1, ?)
            ''', (nome, apelidos_str, obs))
            importados += 1
            print(f"  ✓ Importado: {nome}")

    con.commit()
    con.close()

    print(f"\n✅ Importação concluída!")
    print(f"  - Novos clientes: {importados}")
    print(f"  - Atualizados: {atualizados}")
    print(f"  - Total: {importados + atualizados}")

if __name__ == '__main__':
    arquivo = Path(__file__).parent / 'clientes_importacao.json'

    if not arquivo.exists():
        print(f"❌ Arquivo não encontrado: {arquivo}")
        exit(1)

    processar_clientes(arquivo)
