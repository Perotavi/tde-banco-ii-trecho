DROP DATABASE IF EXISTS rede_trecho;
CREATE DATABASE rede_trecho CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE rede_trecho;

CREATE TABLE perfis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(50) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL
);

CREATE TABLE usuarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    perfil_id INT NOT NULL,
    status_conta ENUM('ativo', 'suspenso', 'banido') NOT NULL DEFAULT 'ativo',
    data_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (perfil_id) REFERENCES perfis(id)
);

CREATE TABLE posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT NOT NULL,
    conteudo VARCHAR(280) NOT NULL,
    status_post ENUM('ativo', 'oculto', 'removido') NOT NULL DEFAULT 'ativo',
    data_publicacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao DATETIME NULL,

    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE comentarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    usuario_id INT NOT NULL,
    conteudo VARCHAR(280) NOT NULL,
    status_comentario ENUM('ativo', 'removido') NOT NULL DEFAULT 'ativo',
    data_comentario DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE curtidas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    usuario_id INT NOT NULL,
    data_curtida DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),

    UNIQUE (post_id, usuario_id)
);

CREATE TABLE seguidores (
    id INT PRIMARY KEY AUTO_INCREMENT,
    seguidor_id INT NOT NULL,
    seguido_id INT NOT NULL,
    data_seguindo DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (seguidor_id) REFERENCES usuarios(id),
    FOREIGN KEY (seguido_id) REFERENCES usuarios(id),

    UNIQUE (seguidor_id, seguido_id),
    CHECK (seguidor_id <> seguido_id)
);

CREATE TABLE denuncias (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    denunciante_id INT NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    status_denuncia ENUM('pendente', 'analisada', 'rejeitada') NOT NULL DEFAULT 'pendente',
    data_denuncia DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (denunciante_id) REFERENCES usuarios(id)
);

CREATE TABLE logs_moderacao (
    id INT PRIMARY KEY AUTO_INCREMENT,
    moderador_id INT NOT NULL,
    post_id INT NULL,
    usuario_alvo_id INT NULL,
    acao VARCHAR(100) NOT NULL,
    justificativa VARCHAR(255) NOT NULL,
    data_acao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (moderador_id) REFERENCES usuarios(id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (usuario_alvo_id) REFERENCES usuarios(id)
);

CREATE TABLE logs_login (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT NOT NULL,
    data_login DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_acesso VARCHAR(45) NULL,

    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);