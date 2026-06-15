USE rede_trecho;

DROP VIEW IF EXISTS view_feed_publico;
DROP VIEW IF EXISTS view_usuarios_publicos;
DROP VIEW IF EXISTS view_denuncias_moderacao;
DROP VIEW IF EXISTS view_relatorio_engajamento;
DROP VIEW IF EXISTS view_logs_admin;

CREATE VIEW view_feed_publico AS
SELECT 
    p.id AS post_id,
    p.conteudo,
    p.data_publicacao,
    u.id AS usuario_id,
    u.nome,
    u.username
FROM posts p
INNER JOIN usuarios u ON p.usuario_id = u.id
WHERE 
    p.status_post = 'ativo'
    AND u.status_conta = 'ativo';

CREATE VIEW view_usuarios_publicos AS
SELECT 
    u.id AS usuario_id,
    u.nome,
    u.username,
    u.status_conta,
    u.data_criacao
FROM usuarios u
WHERE u.status_conta = 'ativo';

DROP VIEW IF EXISTS view_denuncias_moderacao;
CREATE VIEW view_denuncias_moderacao AS
SELECT
    d.id AS denuncia_id,
    d.motivo,
    d.status_denuncia,
    d.data_denuncia,

    p.id AS post_id,
    p.conteudo AS conteudo_denunciado,
    p.status_post,

    autor.id AS autor_id,
    autor.nome AS autor_nome,
    autor.username AS autor_username,
    perfil_autor.nome AS autor_perfil,

    denunciante.id AS denunciante_id,
    denunciante.nome AS denunciante_nome,
    denunciante.username AS denunciante_username
FROM denuncias d
INNER JOIN posts p ON d.post_id = p.id
INNER JOIN usuarios autor ON p.usuario_id = autor.id
INNER JOIN perfis perfil_autor ON autor.perfil_id = perfil_autor.id
INNER JOIN usuarios denunciante ON d.denunciante_id = denunciante.id;

CREATE VIEW view_relatorio_engajamento AS
SELECT
    p.id AS post_id,
    p.conteudo,
    u.nome AS autor_nome,
    u.username AS autor_username,
    p.data_publicacao,
    COUNT(DISTINCT c.id) AS total_comentarios,
    COUNT(DISTINCT curt.id) AS total_curtidas,
    COUNT(DISTINCT d.id) AS total_denuncias
FROM posts p
INNER JOIN usuarios u ON p.usuario_id = u.id
LEFT JOIN comentarios c ON p.id = c.post_id
LEFT JOIN curtidas curt ON p.id = curt.post_id
LEFT JOIN denuncias d ON p.id = d.post_id
GROUP BY
    p.id,
    p.conteudo,
    u.nome,
    u.username,
    p.data_publicacao;

CREATE VIEW view_logs_admin AS
SELECT
    l.id AS log_id,
    l.acao,
    l.justificativa,
    l.data_acao,
    moderador.nome AS moderador_nome,
    moderador.username AS moderador_username,
    p.id AS post_id,
    p.conteudo AS conteudo_post,
    usuario_alvo.nome AS usuario_alvo_nome,
    usuario_alvo.username AS usuario_alvo_username
FROM logs_moderacao l
INNER JOIN usuarios moderador ON l.moderador_id = moderador.id
LEFT JOIN posts p ON l.post_id = p.id
LEFT JOIN usuarios usuario_alvo ON l.usuario_alvo_id = usuario_alvo.id;