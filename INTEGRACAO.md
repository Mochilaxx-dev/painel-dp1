# 🔗 Integração: Painel DP + Painel Profissional de Tarefas

## Status: ✅ ATIVO E FUNCIONANDO

Seu painel DP está **online** e **integrado** com o painel profissional de gestão de tarefas!

---

## 🌐 URLs de Acesso

### Painel DP (Demandas)
```
https://web-production-6a11a75f.up.railway.app/
```

### Painel Profissional (Tarefas)
```
https://gerenciador-de-tarefas-ef1.netlify.app/
```

---

## ⚙️ Como Funciona a Integração

### Fluxo de Sincronização

```
┌─────────────────────────────────┐
│   PAINEL DP (Demandas)          │
│  - Cria demanda                 │
│  - Define tipo, cliente, prazo  │
└──────────────┬──────────────────┘
               │
               │ [Sincroniza automaticamente]
               ▼
┌─────────────────────────────────┐
│   PAINEL PROFISSIONAL (Tarefas) │
│  - Cria tarefa correspondente   │
│  - Mapeia status e prioridade   │
│  - Atualiza em tempo real       │
└─────────────────────────────────┘
```

### O que é Sincronizado

| Painel DP | → | Painel Profissional |
|-----------|---|-------------------|
| Cliente | → | Descrição da tarefa |
| Descrição | → | Título da tarefa |
| Tipo | → | Categoria/Tags |
| Prioridade | → | Prioridade |
| Prazo | → | Data de término |
| Status | → | Status (A fazer/Fazendo/Concluída) |
| Observações | → | Notas da tarefa |

---

## 🚀 Como Usar

### 1. Criar uma Demanda no Painel DP
1. Acesse: https://web-production-6a11a75f.up.railway.app/
2. Clique em **"+ Nova demanda"**
3. Preencha:
   - **Cliente**: Nome da empresa
   - **O que precisa ser feito**: Descrição
   - **Tipo**: Admissão, Rescisão, Férias, etc.
   - **Prazo**: Data limite (opcional)
   - **Prioridade**: Alta, Média, Baixa
   - **Colaborador**: Nome (opcional)

4. Clique em **"Salvar"**

✅ **Automaticamente** uma tarefa é criada no painel profissional!

### 2. Acompanhar no Painel Profissional
1. Acesse: https://gerenciador-de-tarefas-ef1.netlify.app/
2. Faça login (erick / 1111)
3. Veja a tarefa criada em **"Tarefas"**
4. Atualize o status conforme avança

---

## 🔐 Configuração de Produção

### Variáveis de Ambiente (Railway)

O sistema usa as seguintes variáveis (já configuradas):

```
RAILWAY_ENVIRONMENT_NAME = production
PORT = 3000
```

### Para Conectar com API da Django (Backend)

Se você tiver o backend em outro servidor, configure:

```
PAINEL_API_URL = https://seu-backend.com/api
PAINEL_API_USER = erick
PAINEL_API_PASSWORD = 1111
```

---

## 📊 Tipos de Demandas com Arquivos Necessários

Ao criar uma demanda, o sistema mostra automaticamente os **arquivos necessários**:

- **Admissão**: Contrato, documentos pessoais, ASO
- **Rescisão**: TRCT, dados bancários, comprovante homologação
- **Férias**: Concessão de férias, cálculo, datas aprovadas
- **Folha de Pagamento**: Folha, holerites
- **Afastamento/Atestado**: Atestado médico, comunicação INSS
- **Acidente de Trabalho**: CAT, atestado, BO
- **Benefícios (VT/VR/Plano)**: Solicitação, documentos operadora
- **Alteração Contratual/Salarial**: Aditivo, comprovante ciência
- **Encargos e Guias**: DARF/GPS, FGTS Digital, recibos
- **eSocial**: Comprovante de envio, eventos transmitidos
- **Pró-labore**: Nota fiscal, comprovante pagamento
- **13º Salário**: Folha, cálculo, comprovantes
- **Documentos e Declarações**: Documento solicitado, IR, PPP
- **Notificação de órgão público**: Cópia notificação, documentos relacionados

---

## 🔄 Sincronização Manual

Se precisar sincronizar manualmente (em caso de erro):

### No Painel DP
```
Clique em "Atualizar" (botão ⟳) no topo
```

### No Painel Profissional
```
Clique em "Atualizar" para recarregar tarefas
```

---

## 🐛 Troubleshooting

### Demanda não aparece no Painel Profissional
1. Espere 5 segundos (sincronização é assíncrona)
2. Clique em "Atualizar" no Painel Profissional
3. Verifique se tem conexão com internet

### Erro ao criar demanda
1. Certifique-se de preencher **Cliente** e **Descrição**
2. Escolha um **Tipo** válido
3. Verifique se o **Prazo** (se informado) é uma data válida

### Status não sincroniza
1. Atualize o Painel DP clicando no botão ⟳
2. Aguarde alguns segundos
3. Recarregue o Painel Profissional (F5)

---

## 📞 Suporte

Para problemas com a integração:
1. Verifique os logs em Railway (painel.app)
2. Teste a conexão acessando ambos painéis
3. Verifique se as credenciais estão corretas

---

## ✅ Próximos Passos

1. ✅ Painel DP online no Railway
2. ✅ Integração com Painel Profissional
3. ✅ Sincronização automática de demandas
4. ⏳ Configurar alertas por email
5. ⏳ Adicionar webhooks para notificações

---

**Sistema pronto para produção!** 🚀
