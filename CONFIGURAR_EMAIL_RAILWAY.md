# 📧 Configurar Email no Railway

## Passo 1: Preparar Credencial Gmail (Recomendado)

### 1.1 Ativar verificação em 2 etapas no Gmail
1. Acesse: https://myaccount.google.com/security
2. Procure por **"Verificação em 2 etapas"**
3. Clique e siga as instruções

### 1.2 Criar "Senha de App"
1. Acesse: https://myaccount.google.com/apppasswords
2. Escolha: **App: Mail** e **Device: Windows Computer**
3. Clique em **"Gerar"**
4. Copie a senha de 16 caracteres (SEM ESPAÇOS)

**Exemplo:** `abcdefghijklmnop`

---

## Passo 2: Adicionar Variáveis no Railway

1. Acesse seu projeto no Railway:
   ```
   https://railway.app/project/seu-projeto
   ```

2. Clique na aba **"Variables"**

3. Adicione duas variáveis:

### Variável 1: EMAIL_USUARIO
- **Key:** `EMAIL_USUARIO`
- **Value:** `seu.email@gmail.com`
- Clique em **"Add"**

### Variável 2: EMAIL_SENHA
- **Key:** `EMAIL_SENHA`
- **Value:** `abcdefghijklmnop` (a senha de 16 caracteres gerada)
- Clique em **"Add"**

---

## Passo 3: Deploy

1. Volte ao Railway
2. As variáveis já estão aplicadas (geralmente automático)
3. Se necessário, clique em **"Redeploy"** para forçar

---

## ✅ Pronto!

Agora o painel DP vai:
- ✅ Conectar ao Gmail automaticamente
- ✅ Ler emails a cada intervalo configurado
- ✅ Reconhecer demandas automaticamente
- ✅ Enviar resumo diário

---

## 🔒 Segurança

- A senha de app é específica para essa aplicação
- Você pode revogar a qualquer momento em: https://myaccount.google.com/apppasswords
- As variáveis no Railway são criptografadas

---

## Provedores Alternativos

### Yahoo Mail
1. Gerar "Senha de App" em: https://login.yahoo.com/account/security
2. Usar essa senha como `EMAIL_SENHA`

### Outlook/Microsoft 365
1. Gerar "Senha de App" em: https://account.live.com/security/
2. Usar essa senha como `EMAIL_SENHA`

### Hospedagem Própria (Locaweb, UOL, etc)
Usar a senha normal da conta de email como `EMAIL_SENHA`

---

## Verificar se Está Funcionando

1. Acesse: https://web-production-6a11a75f.up.railway.app/
2. Vá em **"Configurações"**
3. Procure por **"Conta de e-mail"**
4. Deve mostrar ✅ **Chave encontrada**

---

## Troubleshooting

### "Chave não encontrada"
- Verifique se as variáveis foram criadas corretamente
- Spelling: `EMAIL_USUARIO` (com underscore)
- Refaça o deploy

### Não recebe emails
- Verifique o email/senha estão corretos
- Procure em spam/lixo do Gmail
- Clique em "Testar Conexão" em Configurações

### Erro: "Senha incorreta"
- A senha de 16 caracteres pode ter espaços
- Copie sem espaços: `abcdefghijklmnop`
- Para Gmail, DEVE ser a "Senha de App", não a senha normal

---

**Sistema pronto para ler emails!** 📧✅
