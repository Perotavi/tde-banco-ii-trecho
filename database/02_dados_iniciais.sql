USE rede_trecho;

INSERT INTO perfis (nome, descricao) VALUES
('visitante', 'Pode visualizar apenas conteúdos públicos.'),
('usuario', 'Pode publicar, comentar, curtir e denunciar posts.'),
('moderador', 'Pode analisar denúncias, ocultar posts e suspender usuários.'),
('analista', 'Pode visualizar relatórios e consultas avançadas sem alterar dados.'),
('admin', 'Possui acesso administrativo completo ao sistema.');

INSERT INTO usuarios (nome, username, email, senha_hash, perfil_id, status_conta) VALUES
('Visitante Teste', 'visitante', 'visitante@trecho.com', 'senha_temporaria', 1, 'ativo'),
('Pedro Usuário', 'pedro', 'pedro@trecho.com', 'senha_temporaria', 2, 'ativo'),
('Alice Usuária', 'alice', 'alice@trecho.com', 'senha_temporaria', 2, 'ativo'),
('Bruno Moderador', 'bruno_mod', 'bruno@trecho.com', 'senha_temporaria', 3, 'ativo'),
('Carla Analista', 'carla_analista', 'carla@trecho.com', 'senha_temporaria', 4, 'ativo'),
('Daniel Admin', 'daniel_admin', 'daniel@trecho.com', 'senha_temporaria', 5, 'ativo');

INSERT INTO posts (usuario_id, conteudo) VALUES
(2, 'Primeiro trecho publicado na plataforma.'),
(3, 'Estudando banco de dados, Flask e SQLAlchemy.'),
(2, 'Esse projeto vai virar portfolio no GitHub.'),
(3, 'Post criado para testar denúncia e moderação.'),
(2, 'Consultas avançadas deixam o banco muito mais interessante.');

INSERT INTO comentarios (post_id, usuario_id, conteudo) VALUES
(1, 3, 'Boa! Gostei da ideia.'),
(2, 2, 'Também estou estudando isso.'),
(3, 5, 'Esse projeto tem potencial para portfolio.'),
(5, 4, 'Esse post pode render um bom relatório.');

INSERT INTO curtidas (post_id, usuario_id) VALUES
(1, 3),
(1, 4),
(1, 5),
(2, 2),
(2, 5),
(3, 3),
(5, 4),
(5, 5);

INSERT INTO seguidores (seguidor_id, seguido_id) VALUES
(2, 3),
(3, 2),
(4, 2),
(5, 2),
(5, 3);

INSERT INTO denuncias (post_id, denunciante_id, motivo) VALUES
(4, 2, 'Conteúdo suspeito para teste de moderação.');