# GUIA DE CONFIGURAÇÃO — GOOGLE DRIVE 5 TB (OAUTH 2.0)

Para conectar o seu Google Drive de 5 TB à Central Inteligente de Shorts, siga os passos oficiais abaixo no Google Cloud Console.

---

### Passo 1: Criar o Projeto no Google Cloud Console
1. Acesse: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Clique no seletor de projetos e crie um novo projeto chamado: **`Central-Shorts-5TB`**.
3. No menu lateral, acesse **APIs e Serviços > Biblioteca**.
4. Pesquise por **Google Drive API** e clique em **Ativar**.

---

### Passo 2: Configurar a Tela de Consentimento OAuth
1. Vá em **APIs e Serviços > Tela de permissão OAuth**.
2. Selecione **Usuário Externo** e clique em **Criar**.
3. Preencha o nome do aplicativo (*Central Shorts 5TB*) e seu e-mail de suporte.
4. Em **Escopos**, adicione o escopo oficial:  
   `https://www.googleapis.com/auth/drive`
5. Em **Usuários de teste**, adicione o seu e-mail do Google (da conta dona dos 5 TB).

---

### Passo 3: Gerar as Credenciais OAuth (Client ID)
1. Vá em **APIs e Serviços > Credenciais**.
2. Clique em **Criar Credenciais > ID do cliente OAuth**.
3. Tipo de aplicativo: selecione **Aplicativo para Computador** (*Desktop App*).
4. Clique em **Criar** e depois em **Baixar JSON**.
5. Salve o arquivo baixado com o nome exato na pasta do projeto:  
   `credentials/gdrive_credentials.json`  
   *(Exemplo: `<diretório_do_vantis>\credentials\gdrive_credentials.json`)*

---

### Passo 4: Conectar e Criar as 13 Pastas
No terminal do projeto, execute o script de sincronização:
```powershell
python -c "from core.gdrive_manager import GDriveManager; g = GDriveManager(); g.setup_drive_structure()"
```
* Uma aba do navegador se abrirá solicitando autorização na sua conta Google.
* Após clicar em **Permitir**, o token permanente é salvo em `credentials/gdrive_token.json`.
* O sistema cria imediatamente as 13 pastas oficiais no seu Drive e exibe o medidor de 5 TB no Dashboard!
