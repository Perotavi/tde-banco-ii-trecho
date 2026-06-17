# Trecho — Sistema de Microblogging

O **Trecho** é uma rede social de microblogging desenvolvida como projeto acadêmico de Banco de Dados II.

O sistema utiliza **Flask**, **SQLAlchemy**, **PyMySQL** e **MySQL 8**, contando com recursos de usuários, posts, curtidas, comentários, denúncias, moderação, auditoria, views, procedures e controle de acesso.



## Clonar o repositório

Abra o terminal do VS Code e rode:

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


## Instalar as dependências

Com a venv ativada, rode:

python -m pip install -r requirements.txt


## Configurar o arquivo `.env`

Na raiz do projeto, crie um arquivo chamado:
.env


Com o seguinte conteúdo:

SECRET_KEY=chave_secreta_tde_trecho
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_NAME=rede_trecho


Caso o usuário `root` do MySQL tenha senha, preencha o campo `DB_PASSWORD`.

Exemplo:


DB_PASSWORD=sua_senha_aqui


O arquivo `.env` não deve ser enviado ao GitHub, pois pode conter senha do banco de dados.


## Verificar se o MySQL está rodando

No PowerShell, rode:


Get-Service *mysql*


Se o serviço aparecer como parado, inicie com:


Start-Service MySQL80


Caso o nome do serviço seja diferente, use o nome que apareceu no comando `Get-Service`.



## Acessar o MySQL com UTF-8

Para evitar problemas com acentos, sempre abra o MySQL usando `--default-character-set=utf8mb4`.

Se o MySQL estiver sem senha para o usuário `root`, use:


& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --default-character-set=utf8mb4 -u root


Se o MySQL tiver senha, use:


& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --default-character-set=utf8mb4 -u root -p


Digite a senha quando solicitado.


## Importar o banco de dados pelo `run.sql`

Para simplificar a importação, o projeto usa um arquivo `run.sql` na raiz do projeto.

A estrutura esperada é:


tde-banco-ii-trecho/
├── run.sql
├── database/
│   ├── 01_schema.sql
│   ├── 02_dados_iniciais.sql
│   ├── 03_views.sql
│   ├── 04_procedures.sql
│   ├── 05_roles_permissoes.sql
│   ├── 06_consultas.sql
│   └── 07_melhorias_sociais.sql


O arquivo `run.sql` deve conter:


SET NAMES utf8mb4;

SOURCE database/01_schema.sql;

USE rede_trecho;

SOURCE database/02_dados_iniciais.sql;
SOURCE database/03_views.sql;
SOURCE database/04_procedures.sql;
SOURCE database/05_roles_permissoes.sql;
SOURCE database/06_consultas.sql;
SOURCE database/07_melhorias_sociais.sql;


No terminal do vscode, entre na raiz do projeto:

cd C:\Users\SEU_USUARIO\tde-banco-ii-trecho


Depois abra o MySQL com UTF-8:


& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --default-character-set=utf8mb4 -u root -p


Dentro do prompt do MySQL, rode:


SOURCE run.sql;


Para conferir se deu certo:


USE rede_trecho;

SHOW TABLES;

SELECT nome, username, email FROM usuarios;

SELECT conteudo FROM posts;

DESCRIBE usuarios;


Os acentos devem aparecer corretamente, por exemplo:


Pedro Usuário
Alice Usuária
denúncia
moderação
avançadas


A tabela `usuarios` também deve conter as colunas novas usadas pelo sistema:

suspenso_ate
motivo_punicao
bio
foto_perfil_url
capa_perfil_url

Depois saia do MySQL:


exit;




## Observação sobre acentos

O projeto utiliza codificação `utf8mb4` para evitar problemas com acentos no Windows e no MySQL.

Se os acentos aparecerem incorretos, verifique estes pontos:

1. Os arquivos `.sql` devem estar salvos como **UTF-8** no VS Code.
2. O MySQL deve ser aberto com `--default-character-set=utf8mb4`.
3. Antes de importar os scripts, o `run.sql` deve executar:


SET NAMES utf8mb4;


No VS Code, para conferir a codificação de um arquivo, olhe no canto inferior direito. Se não estiver como `UTF-8`, clique na codificação atual e escolha:

Save with Encoding > UTF-8

## Atualizar as senhas dos usuários de teste

Depois de importar o banco, com a venv ativada, rode:

python criar_senhas_teste.py


Esse comando define a senha dos usuários de teste como:


123456

## Rodar o projeto

Com a venv ativada, rode:

python run.py

Depois acesse no navegador:
http://127.0.0.1:5000

## Usuários de teste

Após rodar o script `criar_senhas_teste.py`, todos os usuários abaixo usam a senha:

123456

Usuários disponíveis:

pedro@trecho.com       - usuário comum
alice@trecho.com       - usuária comum
bruno@trecho.com       - moderador
carla@trecho.com       - analista
daniel@trecho.com      - administrador
visitante@trecho.com   - visitante, se estiver presente nos dados iniciais



## Perfis do sistema

O sistema trabalha com os seguintes perfis:

visitante    - acesso mais limitado
usuario      - pode postar, comentar, curtir, denunciar e editar perfil
moderador    - pode moderar denúncias, remover posts e punir usuários comuns
analista     - pode acessar relatórios, mas não pode postar nem moderar
admin        - possui acesso administrativo completo


## Política de suspensão e banimento

Usuário suspenso:

- pode logar;
- pode visualizar o feed;
- pode curtir posts;
- pode denunciar posts;
- pode bloquear usuários;
- pode editar o próprio perfil;
- não pode criar posts;
- não pode comentar.

Usuário banido:

- não consegue entrar no sistema;
- recebe aviso de conta banida na tentativa de login.


## Fluxos principais cobertos pelos testes

Os testes verificam os principais fluxos do sistema, incluindo:

- visitante visualizando o feed;
- tentativa de interação sem login;
- login com senha incorreta;
- login com senha correta;
- criação de post;
- edição de post;
- curtida;
- comentário;
- denúncia;
- bloqueio de usuário;
- notificações;
- edição de bio do perfil;
- acesso do moderador ao painel de moderação;
- remoção de post denunciado;
- suspensão de usuário;
- bloqueio de postagem e comentário para usuário suspenso;
- banimento de usuário;
- bloqueio de login para usuário banido;
- acesso do analista aos relatórios;
- bloqueio do analista em áreas restritas;
- acesso do admin à administração;
- reativação de usuário;
- alteração de hierarquia;
- validação de usuário promovido a moderador.


## Ordem resumida dos comandos

git clone https://github.com/perotavi/tde-banco-ii-trecho
cd tde-banco-ii-trecho

python -m venv venv

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

Depois crie o `.env`.

Em seguida, abra o MySQL com UTF-8:

& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --default-character-set=utf8mb4 -u root -p

Dentro do MySQL:

SOURCE run.sql;
exit;

Depois rode:

python criar_senhas_teste.py
python run.py