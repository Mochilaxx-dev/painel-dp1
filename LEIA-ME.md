# Painel DP (versão local e gratuita)

Roda no seu computador, sem mensalidade e sem IA paga. Lê seus e-mails, identifica as demandas por palavras-chave e datas, calcula os prazos legais e mostra tudo num painel.

## Como abrir

Dê dois cliques no ícone **Painel DP** na área de trabalho. O painel abre no navegador (endereço `http://localhost:8765`).

> O sistema só lê e-mails **enquanto estiver ligado**. Para ele ligar sozinho com o Windows, dê dois cliques em **abrir_com_o_windows.bat** (uma vez só). Para desligar, use **parar.bat**.

## Primeira configuração (5 minutos)

O sistema não pede senha em lugar nenhum. Ele busca o e-mail e a senha numa **chave genérica do Windows** chamada `gmail`.

1. **Crie a senha de app no Gmail.** O Gmail não aceita a senha normal da conta em programas.
   - Ative a verificação em duas etapas da conta Google.
   - Acesse https://myaccount.google.com/apppasswords, dê o nome "Painel DP" e clique em Criar.
   - Copie a senha de 16 letras.
2. **Crie a chave genérica no Windows:** Painel de Controle › Gerenciador de Credenciais › Credenciais do Windows › **Adicionar uma credencial genérica**.
   - Endereço: `gmail`
   - Nome de usuário: `erick.formalize@gmail.com`
   - Senha: a senha de app de 16 letras
3. No painel, abra **Configurações** e clique em **Verificar chave** e depois em **Testar conexão**.

Para trocar de conta ou de senha, edite essa chave no Gerenciador de Credenciais. O sistema passa a usar a nova automaticamente.
3. Em **Cadastros > Clientes**, cadastre seus clientes. Em "Apelidos e domínios", coloque o domínio do e-mail deles (ex.: `padariasol.com.br`) e os nomes pelos quais costumam ser chamados.
4. Clique em **Gerar calendário legal agora**.

Outros provedores: Yahoo e provedores de hospedagem (Locaweb, UOL, HostGator...) também funcionam por IMAP. O Outlook/Microsoft 365 costuma bloquear senhas de app.

## Como ele lê os e-mails

| Situação | O que acontece |
|---|---|
| Tem palavras de DP (rescisão, férias, admissão, atestado, FGTS, folha...) | Vira **demanda** com cliente, tipo, colaborador e prazo |
| Não tem palavras de DP | Vai para **Triagem**: você decide se vira demanda ou se descarta |
| Propaganda, resposta automática, "ok, obrigada", remetentes "noreply" | **Ignorado** (aparece em "E-mails lidos", caso precise recuperar) |
| Nova mensagem na mesma conversa | Atualiza a demanda existente, sem duplicar |

**Anexos:**
- O sistema guarda os anexos em `dados\anexos` e mostra cada um na demanda (Detalhes › 📎 Abrir).
- Ele lê o texto de PDF, Word (.docx), Excel (.xlsx), .txt e .csv.
- Quando o e-mail diz só "segue em anexo", o tipo, o colaborador e as datas são tirados dos documentos.
- Fotos (como as do WhatsApp) e PDFs escaneados não têm texto: ficam guardados, mas não são lidos.

**Prazos calculados:**
- Prazo escrito no e-mail ("até sexta", "até 20/11"): esse prazo é usado.
- Rescisão: 10 dias após o término. Com aviso trabalhado, conta a partir do fim do aviso.
- Férias: pagamento 2 dias antes do início, com alerta se o aviso tiver menos de 30 dias.
- Admissão: véspera do início (eSocial).
- Acidente: CAT até o 1º dia útil seguinte.
- Nenhum dos casos acima: prazo padrão de 3 dias úteis (ajustável).
- Prazo de pagamento que cai em fim de semana ou feriado é antecipado.

As regras não entendem o texto como uma pessoa. Na primeira semana, confira a **Triagem** e os **E-mails lidos**.

## Seus dados

- Tudo fica na pasta `dados` (banco `painel.db`). **Faça cópia dessa pasta de vez em quando.**
- O sistema não guarda senha nenhuma: ele lê a chave `gmail` do Gerenciador de Credenciais do Windows a cada uso.
- O painel só é acessível neste computador.
- Para levar as demandas ao Excel, use o link **Exportar** no fim da tela de Demandas.
