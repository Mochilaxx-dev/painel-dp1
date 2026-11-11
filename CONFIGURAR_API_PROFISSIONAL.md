# 🔗 Configurar API do Painel Profissional

## Passo 1: Obter URL do Backend

Você precisará da **URL base** do seu backend Django (onde o painel profissional roda):

**Exemplos de URLs:**
- Local: `http://localhost:8000`
- Railway: `https://seu-app.railway.app`
- Seu domínio: `https://api.seudominio.com.br`

> ⚠️ **IMPORTANTE:** Use a URL **SEM `/api` no final**. O sistema adiciona isso automaticamente.

---

## Passo 2: Configurar no Railway

### Se o Painel DP está no Railway (produção):

1. Acesse seu projeto: https://railway.app/project/seu-projeto
2. Clique em **"web"** (o serviço do Painel DP)
3. Vá na aba **"Variables"**
4. Clique em **"Shared Variables"** ou **"Variables"** (dependendo da interface)
5. Adicione uma nova variável:
   - **Key:** `PAINEL_API_URL`
   - **Value:** `https://seu-backend-url.com/api`
   
   **Exemplo (se backend está em Railway também):**
   ```
   https://painel-backend.railway.app/api
   ```

6. Clique em **"Save"** ou **"Deploy"** para aplicar

---

## Passo 3: Verificar Configuração

### Para conferir se está funcionando:

1. Acesse o Painel DP: https://web-production-6a11a75f.up.railway.app/
2. Crie uma **nova demanda**
3. Aguarde 3-5 segundos
4. Acesse o Painel Profissional: https://gerenciador-de-tarefas-ef1.netlify.app/
5. Faça login (erick / 1111)
6. Veja se a demanda apareceu em **"Tarefas"**

✅ Se a demanda apareceu = **Sincronização ativa!**
❌ Se não apareceu = Verificar logs em Railway

---

## Passo 4: Troubleshooting

### "Demanda não aparece no painel profissional"

**Verifique:**

1. **URL está correta?**
   - Teste a URL no navegador: `https://seu-backend-url.com/api/tarefas/`
   - Deve retornar um JSON ou pedir autenticação (não 404)

2. **Credenciais estão corretas?**
   - Usuário: `erick`
   - Senha: `1111`
   - (Altere em `integracao_painel_profissional.py` se diferente)

3. **Backend está respondendo?**
   - Teste com curl/Postman:
   ```bash
   curl -X POST https://seu-backend-url.com/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username":"erick","password":"1111"}'
   ```

4. **Verifique logs no Railway:**
   - Acesse seu projeto
   - Clique em **"Deployments"**
   - Procure por erros relacionados a `integracao_painel_profissional`

---

## Opção Local (Desenvolvimento)

Se você quer testar localmente antes de colocar em produção:

1. Inicie o Painel DP local:
   ```bash
   python painel.py
   ```

2. Configure a variável de ambiente:
   ```bash
   # Windows (PowerShell)
   $env:PAINEL_API_URL = "http://localhost:8000/api"
   python painel.py
   
   # Linux/Mac
   export PAINEL_API_URL="http://localhost:8000/api"
   python painel.py
   ```

3. Inicie seu backend Django:
   ```bash
   cd seu-backend-painel-profissional
   python manage.py runserver 0.0.0.0:8000
   ```

4. Crie uma demanda e veja se sincroniza

---

## ✅ Resumo das Variáveis

| Variável | Valor | Exemplo |
|----------|-------|---------|
| `PAINEL_API_URL` | URL do backend | `https://painel-backend.railway.app/api` |
| `PAINEL_API_USER` | Usuário (opcional) | `erick` |
| `PAINEL_API_PASSWORD` | Senha (opcional) | `1111` |

---

## 📞 Precisa de Ajuda?

Se a sincronização ainda não funcionar:

1. Verifique se a URL do backend está **correta e acessível**
2. Confirme que o backend **suporta CORS** (Cross-Origin)
3. Teste a autenticação manualmente com a URL

---

**Sistema pronto para sincronizar!** 🚀
