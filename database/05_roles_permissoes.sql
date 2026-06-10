USE rede_trecho;

DROP USER IF EXISTS 'visitante_trecho'@'localhost';
DROP USER IF EXISTS 'usuario_trecho'@'localhost';
DROP USER IF EXISTS 'moderador_trecho'@'localhost';
DROP USER IF EXISTS 'analista_trecho'@'localhost';
DROP USER IF EXISTS 'admin_trecho'@'localhost';

DROP ROLE IF EXISTS role_visitante;
DROP ROLE IF EXISTS role_usuario;
DROP ROLE IF EXISTS role_moderador;
DROP ROLE IF EXISTS role_analista;
DROP ROLE IF EXISTS role_admin;

CREATE ROLE role_visitante;
CREATE ROLE role_usuario;
CREATE ROLE role_moderador;
CREATE ROLE role_analista;
CREATE ROLE role_admin;

CREATE USER 'visitante_trecho'@'localhost' IDENTIFIED BY 'visitante123';
CREATE USER 'usuario_trecho'@'localhost' IDENTIFIED BY 'usuario123';
CREATE USER 'moderador_trecho'@'localhost' IDENTIFIED BY 'moderador123';
CREATE USER 'analista_trecho'@'localhost' IDENTIFIED BY 'analista123';
CREATE USER 'admin_trecho'@'localhost' IDENTIFIED BY 'admin123';

GRANT SELECT ON rede_trecho.view_feed_publico TO role_visitante;
GRANT SELECT ON rede_trecho.view_usuarios_publicos TO role_visitante;

GRANT SELECT ON rede_trecho.view_feed_publico TO role_usuario;
GRANT SELECT ON rede_trecho.view_usuarios_publicos TO role_usuario;
GRANT SELECT, INSERT ON rede_trecho.posts TO role_usuario;
GRANT SELECT, INSERT ON rede_trecho.comentarios TO role_usuario;
GRANT SELECT, INSERT ON rede_trecho.curtidas TO role_usuario;
GRANT SELECT, INSERT ON rede_trecho.denuncias TO role_usuario;
GRANT EXECUTE ON PROCEDURE rede_trecho.sp_criar_post TO role_usuario;
GRANT EXECUTE ON PROCEDURE rede_trecho.sp_editar_post TO role_usuario;
GRANT EXECUTE ON PROCEDURE rede_trecho.sp_denunciar_post TO role_usuario;

GRANT SELECT ON rede_trecho.* TO role_moderador;
GRANT UPDATE (status_conta) ON rede_trecho.usuarios TO role_moderador;
GRANT UPDATE (status_post) ON rede_trecho.posts TO role_moderador;
GRANT UPDATE (status_denuncia) ON rede_trecho.denuncias TO role_moderador;
GRANT INSERT ON rede_trecho.logs_moderacao TO role_moderador;
GRANT EXECUTE ON PROCEDURE rede_trecho.sp_moderar_post TO role_moderador;
GRANT EXECUTE ON PROCEDURE rede_trecho.sp_alterar_status_usuario TO role_moderador;

GRANT SELECT ON rede_trecho.view_feed_publico TO role_analista;
GRANT SELECT ON rede_trecho.view_usuarios_publicos TO role_analista;
GRANT SELECT ON rede_trecho.view_relatorio_engajamento TO role_analista;
GRANT EXECUTE ON PROCEDURE rede_trecho.sp_relatorio_usuario TO role_analista;

GRANT ALL PRIVILEGES ON rede_trecho.* TO role_admin;

GRANT role_visitante TO 'visitante_trecho'@'localhost';
GRANT role_usuario TO 'usuario_trecho'@'localhost';
GRANT role_moderador TO 'moderador_trecho'@'localhost';
GRANT role_analista TO 'analista_trecho'@'localhost';
GRANT role_admin TO 'admin_trecho'@'localhost';

SET DEFAULT ROLE role_visitante FOR 'visitante_trecho'@'localhost';
SET DEFAULT ROLE role_usuario FOR 'usuario_trecho'@'localhost';
SET DEFAULT ROLE role_moderador FOR 'moderador_trecho'@'localhost';
SET DEFAULT ROLE role_analista FOR 'analista_trecho'@'localhost';
SET DEFAULT ROLE role_admin FOR 'admin_trecho'@'localhost';

FLUSH PRIVILEGES;