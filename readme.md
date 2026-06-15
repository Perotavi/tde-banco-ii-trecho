# Trecho — Sistema de Microblogging

O **Trecho** é uma rede social de microblogging desenvolvida como projeto acadêmico de Banco de Dados II.

O sistema utiliza **Flask**, **SQLAlchemy**, **PyMySQL** e **MySQL 8**, contando com recursos de usuários, posts, curtidas, comentários, denúncias, moderação, auditoria, views, procedures e controle de acesso.

## Clonar o repositório

Abra o terminal do vscode e rode
git clone https://github.com/perotavi/tde-banco-ii-trecho
cd tde-banco-ii-trecho

## Criar o ambiente virtual

Dentro da pasta do projeto, rode:


python -m venv venv

Depois tente ativar a venv:
.\venv\Scripts\Activate.ps1

Caso o PowerShell bloqueie a execução de scripts, rode:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Depois tente ativar novamente:
.\venv\Scripts\Activate.ps1

Quando funcionar, o terminal deve ficar parecido com:
(venv) PS C:\Users\SEU_USUARIO\tde-banco-ii-trecho>

## 4. Instalar as dependências
Com a venv ativada, rode:
python -m pip install -r requirements.txt

## 5. Configurar o arquivo `.env`

Na raiz do projeto, crie um arquivo chamado:
.env

Com o seguinte conteúdo:
SECRET_KEY=chave_secreta_tde_trecho
DB_USER=root
DB_PASSWORD=(deixe vazio se o root do seu sql nao tiver senha)
DB_HOST=127.0.0.1
DB_NAME=rede_trecho

Caso o usuário `root` do MySQL tenha senha, preencha o campo `DB_PASSWORD`.

## 6. Verificar se o MySQL está rodando
Get-Service *mysql*
Se o serviço aparecer como parado, inicie com:
Start-Service MySQL80
Caso o nome do serviço seja diferente, use o nome que aparecer no comando anterior.

## 7. Acessar o MySQL

Se o MySQL estiver sem senha para o usuário `root`, use:
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --default-character-set=utf8mb4 -u root

Se o MySQL tiver senha, use:
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --default-character-set=utf8mb4 -u root -p
Digite a senha quando solicitado.

## Importar o banco de dados

Dentro do prompt do MySQL, rode os comandos abaixo.

Troque `SEU_USUARIO` pelo nome do usuário do Windows.

Exemplo de caminho:

C:/Users/SEU_USUARIO/tde-banco-ii-trecho
Comandos:
SET NAMES utf8mb4;

SOURCE C:/Users/SEU_USUARIO/tde-banco-ii-trecho/database/01_schema.sql;

USE rede_trecho;

SOURCE C:/Users/SEU_USUARIO/tde-banco-ii-trecho/database/02_dados_iniciais.sql;
SOURCE C:/Users/SEU_USUARIO/tde-banco-ii-trecho/database/03_views.sql;
SOURCE C:/Users/SEU_USUARIO/tde-banco-ii-trecho/database/04_procedures.sql;
SOURCE C:/Users/SEU_USUARIO/tde-banco-ii-trecho/database/05_roles_permissoes.sql;
SOURCE C:/Users/SEU_USUARIO/tde-banco-ii-trecho/database/06_consultas.sql;

Para conferir se deu certo:

SHOW TABLES;
SELECT nome, username, email FROM usuarios;
SELECT conteudo FROM posts;

Os acentos devem aparecer corretamente, por exemplo:
Pedro Usuário
Alice Usuária
denúncia
moderação
avançadas

Depois saia do MySQL:
exit;

## Atualizar as senhas dos usuários de teste

Com a venv ativada, rode:

python criar_senhas_teste.py
Esse comando define a senha de todos os usuários de teste como:
123456

## Rodar o projeto

python run.py

Depois acesse no navegador:
http://127.0.0.1:5000

## Usuários de teste

Após rodar o script `criar_senhas_teste.py`, todos os usuários abaixo usam a senha:
123456

Usuários disponíveis:
pedro@trecho.com    - usuário comum
bruno@trecho.com    - moderador
carla@trecho.com    - analista
daniel@trecho.com   - administrador

## Observações importantes

O arquivo `.env` não pode ser enviado ao GitHub, pois pode conter senha do banco de dados.

O projeto utiliza codificação `utf8mb4` para evitar problemas com acentos no Windows.

Caso os acentos apareçam incorretos, reimporte o banco usando:

& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --default-character-set=utf8mb4 -u root

E dentro do MySQL:
SET NAMES utf8mb4;
Depois importe novamente os arquivos SQL.

## 13. Ordem resumida dos comandos


git clone https://github.com/perotavi/tde-banco-ii-trecho
cd tde-banco-ii-trecho

python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass (caso de erro de permissão)
.\venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

Depois configurar o `.env`, importar o banco no MySQL e rodar:


python criar_senhas_teste.py
python run.py

