USE rede_trecho;

-- 1. Feed público com dados do autor
SELECT
    p.id AS post_id,
    p.conteudo,
    p.data_publicacao,
    u.nome AS autor,
    u.username
FROM posts p
INNER JOIN usuarios u ON p.usuario_id = u.id
WHERE 
    p.status_post = 'ativo'
    AND u.status_conta = 'ativo'
ORDER BY p.data_publicacao DESC;

-- 2. Ranking de posts por engajamento
SELECT
    p.id AS post_id,
    p.conteudo,
    u.username AS autor,
    COUNT(DISTINCT curt.id) AS total_curtidas,
    COUNT(DISTINCT c.id) AS total_comentarios,
    COUNT(DISTINCT d.id) AS total_denuncias,
    (
        COUNT(DISTINCT curt.id) +
        COUNT(DISTINCT c.id) -
        COUNT(DISTINCT d.id)
    ) AS pontuacao_engajamento
FROM posts p
INNER JOIN usuarios u ON p.usuario_id = u.id
LEFT JOIN curtidas curt ON p.id = curt.post_id
LEFT JOIN comentarios c ON p.id = c.post_id
LEFT JOIN denuncias d ON p.id = d.post_id
GROUP BY
    p.id,
    p.conteudo,
    u.username
ORDER BY pontuacao_engajamento DESC;

-- 3. Usuários com mais posts publicados
SELECT
    u.id AS usuario_id,
    u.nome,
    u.username,
    COUNT(p.id) AS total_posts
FROM usuarios u
LEFT JOIN posts p ON u.id = p.usuario_id
GROUP BY
    u.id,
    u.nome,
    u.username
ORDER BY total_posts DESC;

-- 4. Posts com denúncias pendentes
SELECT
    d.id AS denuncia_id,
    d.motivo,
    d.data_denuncia,
    p.id AS post_id,
    p.conteudo,
    autor.username AS autor_post,
    denunciante.username AS denunciante
FROM denuncias d
INNER JOIN posts p ON d.post_id = p.id
INNER JOIN usuarios autor ON p.usuario_id = autor.id
INNER JOIN usuarios denunciante ON d.denunciante_id = denunciante.id
WHERE d.status_denuncia = 'pendente'
ORDER BY d.data_denuncia ASC;

-- 5. Usuários que nunca publicaram nenhum post
SELECT
    u.id,
    u.nome,
    u.username
FROM usuarios u
WHERE u.id NOT IN (
    SELECT usuario_id
    FROM posts
);

-- 6. Usuários que já tiveram post denunciado
SELECT DISTINCT
    u.id,
    u.nome,
    u.username
FROM usuarios u
WHERE EXISTS (
    SELECT 1
    FROM posts p
    INNER JOIN denuncias d ON p.id = d.post_id
    WHERE p.usuario_id = u.id
);

-- 7. Posts com curtidas acima da média geral
SELECT
    p.id,
    p.conteudo,
    u.username AS autor,
    COUNT(curt.id) AS total_curtidas
FROM posts p
INNER JOIN usuarios u ON p.usuario_id = u.id
LEFT JOIN curtidas curt ON p.id = curt.post_id
GROUP BY
    p.id,
    p.conteudo,
    u.username
HAVING COUNT(curt.id) > (
    SELECT AVG(total_curtidas)
    FROM (
        SELECT COUNT(c2.id) AS total_curtidas
        FROM posts p2
        LEFT JOIN curtidas c2 ON p2.id = c2.post_id
        GROUP BY p2.id
    ) AS media_posts
);

-- 8. Relatório de usuários por perfil
SELECT
    pf.nome AS perfil,
    COUNT(u.id) AS total_usuarios
FROM perfis pf
LEFT JOIN usuarios u ON pf.id = u.perfil_id
GROUP BY pf.nome
ORDER BY total_usuarios DESC;

-- 9. Quantidade de denúncias por status
SELECT
    status_denuncia,
    COUNT(*) AS total
FROM denuncias
GROUP BY status_denuncia;

-- 10. Histórico de ações de moderação
SELECT
    l.id AS log_id,
    moderador.username AS moderador,
    l.acao,
    l.justificativa,
    p.conteudo AS post_afetado,
    usuario_alvo.username AS usuario_afetado,
    l.data_acao
FROM logs_moderacao l
INNER JOIN usuarios moderador ON l.moderador_id = moderador.id
LEFT JOIN posts p ON l.post_id = p.id
LEFT JOIN usuarios usuario_alvo ON l.usuario_alvo_id = usuario_alvo.id
ORDER BY l.data_acao DESC;

-- 11. Feed personalizado: posts de usuários que Pedro segue
SELECT
    p.id AS post_id,
    p.conteudo,
    autor.username AS autor,
    p.data_publicacao
FROM seguidores s
INNER JOIN posts p ON s.seguido_id = p.usuario_id
INNER JOIN usuarios autor ON p.usuario_id = autor.id
WHERE 
    s.seguidor_id = 2
    AND p.status_post = 'ativo'
ORDER BY p.data_publicacao DESC;

-- 12. Usuários ativos com total de interações feitas
SELECT
    u.id,
    u.nome,
    u.username,
    COUNT(DISTINCT p.id) AS posts_criados,
    COUNT(DISTINCT c.id) AS comentarios_feitos,
    COUNT(DISTINCT curt.id) AS curtidas_feitas,
    COUNT(DISTINCT d.id) AS denuncias_feitas
FROM usuarios u
LEFT JOIN posts p ON u.id = p.usuario_id
LEFT JOIN comentarios c ON u.id = c.usuario_id
LEFT JOIN curtidas curt ON u.id = curt.usuario_id
LEFT JOIN denuncias d ON u.id = d.denunciante_id
WHERE u.status_conta = 'ativo'
GROUP BY
    u.id,
    u.nome,
    u.username
ORDER BY posts_criados DESC, comentarios_feitos DESC;