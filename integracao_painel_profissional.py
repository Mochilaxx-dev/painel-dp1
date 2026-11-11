"""
Integração entre Painel DP e Painel Profissional de Tarefas
Sincroniza demandas com o sistema Django REST do painel de gestão de tarefas
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional

API_BASE = os.environ.get('PAINEL_API_URL', 'http://localhost:8000/api')
API_USER = os.environ.get('PAINEL_API_USER', 'erick')
API_PASSWORD = os.environ.get('PAINEL_API_PASSWORD', '1111')

class IntegracaoPainelProfissional:
    def __init__(self):
        self.base_url = API_BASE
        self.usuario = API_USER
        self.senha = API_PASSWORD
        self.token = None
        self.session = requests.Session()

    def autenticar(self) -> bool:
        """Autentica com o painel profissional e obter JWT token"""
        try:
            url = f"{self.base_url}/auth/login/"
            dados = {"username": self.usuario, "password": self.senha}
            resp = self.session.post(url, json=dados, timeout=10)

            if resp.status_code == 200:
                self.token = resp.json().get('access')
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                return True
            return False
        except Exception as e:
            print(f"Erro autenticação: {e}")
            return False

    def criar_tarefa(self, demanda: Dict[str, Any]) -> Optional[Dict]:
        """Cria uma tarefa no painel profissional a partir de uma demanda"""
        if not self.token:
            if not self.autenticar():
                return None

        try:
            tarefa = {
                "titulo": demanda.get('descricao', 'Sem descrição'),
                "descricao": f"Demanda: {demanda.get('tipo', '')}\nCliente: {demanda.get('cliente', '')}\nObservações: {demanda.get('obs', '')}",
                "status": self._mapear_status(demanda.get('status', 'Pendente')),
                "prioridade": self._mapear_prioridade(demanda.get('prioridade', 'Média')),
                "data_inicio": demanda.get('data_criacao', datetime.now().isoformat()),
                "data_termino": demanda.get('prazo', None),
                "responsavel": self.usuario,
            }

            resp = self.session.post(f"{self.base_url}/tarefas/", json=tarefa, timeout=10)

            if resp.status_code in [200, 201]:
                return resp.json()
            return None
        except Exception as e:
            print(f"Erro ao criar tarefa: {e}")
            return None

    def atualizar_tarefa(self, tarefa_id: int, demanda: Dict[str, Any]) -> bool:
        """Atualiza uma tarefa no painel profissional"""
        if not self.token:
            if not self.autenticar():
                return False

        try:
            dados_atualizacao = {
                "status": self._mapear_status(demanda.get('status', 'Pendente')),
                "prioridade": self._mapear_prioridade(demanda.get('prioridade', 'Média')),
            }

            if demanda.get('data_conclusao'):
                dados_atualizacao['data_conclusao'] = demanda.get('data_conclusao')

            resp = self.session.patch(f"{self.base_url}/tarefas/{tarefa_id}/", json=dados_atualizacao, timeout=10)
            return resp.status_code in [200, 204]
        except Exception as e:
            print(f"Erro ao atualizar tarefa: {e}")
            return False

    def listar_tarefas(self) -> list:
        """Lista todas as tarefas do painel profissional"""
        if not self.token:
            if not self.autenticar():
                return []

        try:
            resp = self.session.get(f"{self.base_url}/tarefas/", timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception:
            return []

    def sincronizar_demanda(self, demanda: Dict[str, Any]) -> bool:
        """Sincroniza uma demanda do painel DP com o painel profissional"""
        tarefa_id = demanda.get('tarefa_id')

        if tarefa_id:
            return self.atualizar_tarefa(tarefa_id, demanda)
        else:
            resultado = self.criar_tarefa(demanda)
            return resultado is not None

    @staticmethod
    def _mapear_status(status_dp: str) -> str:
        """Mapeia status do painel DP para status do painel profissional"""
        mapeamento = {
            'Pendente': 'A fazer',
            'Em andamento': 'Fazendo',
            'Concluída': 'Concluída',
            'Bloqueada': 'Bloqueada',
        }
        return mapeamento.get(status_dp, 'A fazer')

    @staticmethod
    def _mapear_prioridade(prioridade_dp: str) -> str:
        """Mapeia prioridade do painel DP para painel profissional"""
        mapeamento = {
            'Alta': 'Alta',
            'Média': 'Média',
            'Baixa': 'Baixa',
        }
        return mapeamento.get(prioridade_dp, 'Média')


# Função auxiliar para sincronizar ao criar/atualizar demanda
def sincronizar_ao_criar(demanda: Dict[str, Any]) -> Optional[int]:
    """Sincroniza uma nova demanda e retorna o ID da tarefa criada"""
    integracao = IntegracaoPainelProfissional()
    resultado = integracao.criar_tarefa(demanda)
    return resultado.get('id') if resultado else None


def sincronizar_ao_atualizar(demanda: Dict[str, Any]) -> bool:
    """Sincroniza uma demanda atualizada"""
    integracao = IntegracaoPainelProfissional()
    return integracao.sincronizar_demanda(demanda)
