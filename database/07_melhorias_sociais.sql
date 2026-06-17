USE rede_trecho;

SET NAMES utf8mb4;


-- Usuarios


SET @existe_coluna = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'suspenso_ate'
);

SET @sql = IF(
    @existe_coluna = 0,
    'ALTER TABLE usuarios ADD COLUMN suspenso_ate DATETIME NULL',
    'SELECT "Coluna suspenso_ate já existe" AS info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @existe_coluna = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'motivo_punicao'
);

SET @sql = IF(
    @existe_coluna = 0,
    'ALTER TABLE usuarios ADD COLUMN motivo_punicao VARCHAR(255) NULL',
    'SELECT "Coluna motivo_punicao já existe" AS info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @existe_coluna = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'bio'
);

SET @sql = IF(
    @existe_coluna = 0,
    'ALTER TABLE usuarios ADD COLUMN bio VARCHAR(280) NULL',
    'SELECT "Coluna bio já existe" AS info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @existe_coluna = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'foto_perfil_url'
);

SET @sql = IF(
    @existe_coluna = 0,
    'ALTER TABLE usuarios ADD COLUMN foto_perfil_url VARCHAR(500) NULL',
    'SELECT "Coluna foto_perfil_url já existe" AS info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @existe_coluna = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'capa_perfil_url'
);

SET @sql = IF(
    @existe_coluna = 0,
    'ALTER TABLE usuarios ADD COLUMN capa_perfil_url VARCHAR(500) NULL',
    'SELECT "Coluna capa_perfil_url já existe" AS info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;



-- Tabela de bloqueios

CREATE TABLE IF NOT EXISTS bloqueios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bloqueador_id INT NOT NULL,
    bloqueado_id INT NOT NULL,
    data_bloqueio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_bloqueios_bloqueador
        FOREIGN KEY (bloqueador_id)
        REFERENCES usuarios(id),

    CONSTRAINT fk_bloqueios_bloqueado
        FOREIGN KEY (bloqueado_id)
        REFERENCES usuarios(id),

    CONSTRAINT uk_bloqueio_unico
        UNIQUE (bloqueador_id, bloqueado_id)
);



-- Tabela Comentarios


CREATE TABLE IF NOT EXISTS comentarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    usuario_id INT NOT NULL,
    conteudo VARCHAR(280) NOT NULL,
    status_comentario ENUM('ativo', 'removido') NOT NULL DEFAULT 'ativo',
    data_comentario TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_comentarios_post
        FOREIGN KEY (post_id)
        REFERENCES posts(id),

    CONSTRAINT fk_comentarios_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
);

SET @existe_coluna = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'comentarios'
      AND COLUMN_NAME = 'status_comentario'
);

SET @sql = IF(
    @existe_coluna = 0,
    'ALTER TABLE comentarios ADD COLUMN status_comentario ENUM("ativo", "removido") NOT NULL DEFAULT "ativo" AFTER conteudo',
    'SELECT "Coluna status_comentario já existe" AS info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;



-- Tabela notificacoes


CREATE TABLE IF NOT EXISTS notificacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    origem_usuario_id INT NULL,
    post_id INT NULL,
    comentario_id INT NULL,
    tipo VARCHAR(50) NOT NULL,
    mensagem VARCHAR(255) NOT NULL,
    lida BOOLEAN NOT NULL DEFAULT FALSE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notificacoes_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id),

    CONSTRAINT fk_notificacoes_origem_usuario
        FOREIGN KEY (origem_usuario_id)
        REFERENCES usuarios(id),

    CONSTRAINT fk_notificacoes_post
        FOREIGN KEY (post_id)
        REFERENCES posts(id),

    CONSTRAINT fk_notificacoes_comentario
        FOREIGN KEY (comentario_id)
        REFERENCES comentarios(id)
);



-- Procedures

DELIMITER $$

-- PROCEDURE: BLOQUEAR USUÁRIO

DROP PROCEDURE IF EXISTS sp_bloquear_usuario $$

CREATE PROCEDURE sp_bloquear_usuario(
    IN p_bloqueador_id INT,
    IN p_bloqueado_id INT
)
BEGIN
    DECLARE v_status_bloqueador VARCHAR(20);
    DECLARE v_total_bloqueado INT DEFAULT 0;

    SELECT status_conta
    INTO v_status_bloqueador
    FROM usuarios
    WHERE id = p_bloqueador_id;

    SELECT COUNT(*)
    INTO v_total_bloqueado
    FROM usuarios
    WHERE id = p_bloqueado_id;

    IF v_status_bloqueador IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário bloqueador não encontrado.';

    ELSEIF v_total_bloqueado = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário a ser bloqueado não encontrado.';

    ELSEIF p_bloqueador_id = p_bloqueado_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Um usuário não pode bloquear a própria conta.';

    ELSEIF v_status_bloqueador = 'banido' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário banido não pode bloquear outros usuários.';

    ELSE
        INSERT IGNORE INTO bloqueios (
            bloqueador_id,
            bloqueado_id
        )
        VALUES (
            p_bloqueador_id,
            p_bloqueado_id
        );
    END IF;
END $$


-- PROCEDURE: COMENTAR POST

DROP PROCEDURE IF EXISTS sp_comentar_post $$

CREATE PROCEDURE sp_comentar_post(
    IN p_usuario_id INT,
    IN p_post_id INT,
    IN p_conteudo VARCHAR(280)
)
BEGIN
    DECLARE v_status_usuario VARCHAR(20);
    DECLARE v_status_post VARCHAR(20);
    DECLARE v_autor_post_id INT;
    DECLARE v_total_bloqueios INT DEFAULT 0;
    DECLARE v_comentario_id INT;

    SELECT status_conta
    INTO v_status_usuario
    FROM usuarios
    WHERE id = p_usuario_id;

    SELECT usuario_id, status_post
    INTO v_autor_post_id, v_status_post
    FROM posts
    WHERE id = p_post_id;

    SELECT COUNT(*)
    INTO v_total_bloqueios
    FROM bloqueios
    WHERE
        (bloqueador_id = p_usuario_id AND bloqueado_id = v_autor_post_id)
        OR
        (bloqueador_id = v_autor_post_id AND bloqueado_id = p_usuario_id);

    IF v_status_usuario IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário não encontrado.';

    ELSEIF v_status_usuario <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário suspenso ou banido não pode comentar.';

    ELSEIF v_status_post IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Post não encontrado.';

    ELSEIF v_status_post <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Não é possível comentar em post que não está ativo.';

    ELSEIF v_total_bloqueios > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Comentário bloqueado por relação de bloqueio entre usuários.';

    ELSEIF p_conteudo IS NULL OR TRIM(p_conteudo) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'O comentário não pode estar vazio.';

    ELSE
        INSERT INTO comentarios (
            post_id,
            usuario_id,
            conteudo
        )
        VALUES (
            p_post_id,
            p_usuario_id,
            p_conteudo
        );

        SET v_comentario_id = LAST_INSERT_ID();

        IF v_autor_post_id <> p_usuario_id THEN
            INSERT INTO notificacoes (
                usuario_id,
                origem_usuario_id,
                post_id,
                comentario_id,
                tipo,
                mensagem
            )
            VALUES (
                v_autor_post_id,
                p_usuario_id,
                p_post_id,
                v_comentario_id,
                'comentario',
                'Seu post recebeu um novo comentário.'
            );
        END IF;
    END IF;
END $$


-- PROCEDURE: ATUALIZAR PERFIL

DROP PROCEDURE IF EXISTS sp_atualizar_perfil_usuario $$

CREATE PROCEDURE sp_atualizar_perfil_usuario(
    IN p_usuario_id INT,
    IN p_bio VARCHAR(280),
    IN p_foto_perfil_url VARCHAR(500),
    IN p_capa_perfil_url VARCHAR(500)
)
BEGIN
    DECLARE v_status_usuario VARCHAR(20);

    SELECT status_conta
    INTO v_status_usuario
    FROM usuarios
    WHERE id = p_usuario_id;

    IF v_status_usuario IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário não encontrado.';

    ELSEIF v_status_usuario = 'banido' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário banido não pode editar o perfil.';

    ELSE
        UPDATE usuarios
        SET
            bio = p_bio,
            foto_perfil_url = p_foto_perfil_url,
            capa_perfil_url = p_capa_perfil_url
        WHERE id = p_usuario_id;
    END IF;
END $$


-- PROCEDURE: ALTERAR PERFIL DE USUÁRIO

DROP PROCEDURE IF EXISTS sp_alterar_perfil_usuario $$

CREATE PROCEDURE sp_alterar_perfil_usuario(
    IN p_admin_id INT,
    IN p_usuario_alvo_id INT,
    IN p_novo_perfil VARCHAR(50),
    IN p_justificativa VARCHAR(255)
)
BEGIN
    DECLARE v_perfil_executor VARCHAR(50);
    DECLARE v_status_executor VARCHAR(20);
    DECLARE v_novo_perfil_id INT;
    DECLARE v_total_alvo INT DEFAULT 0;

    SELECT p.nome, u.status_conta
    INTO v_perfil_executor, v_status_executor
    FROM usuarios u
    INNER JOIN perfis p ON u.perfil_id = p.id
    WHERE u.id = p_admin_id;

    SELECT id
    INTO v_novo_perfil_id
    FROM perfis
    WHERE nome = p_novo_perfil;

    SELECT COUNT(*)
    INTO v_total_alvo
    FROM usuarios
    WHERE id = p_usuario_alvo_id;

    IF v_perfil_executor <> 'admin' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Apenas administradores podem alterar perfis de usuários.';

    ELSEIF v_status_executor <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Administrador executor não está ativo.';

    ELSEIF v_total_alvo = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário alvo não encontrado.';

    ELSEIF p_admin_id = p_usuario_alvo_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Administrador não pode alterar o próprio perfil por esta ação.';

    ELSEIF v_novo_perfil_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Perfil informado não existe.';

    ELSEIF p_novo_perfil NOT IN ('usuario', 'moderador', 'analista', 'admin') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Perfil informado não pode ser atribuído.';

    ELSEIF p_justificativa IS NULL OR TRIM(p_justificativa) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A justificativa é obrigatória.';

    ELSE
        UPDATE usuarios
        SET perfil_id = v_novo_perfil_id
        WHERE id = p_usuario_alvo_id;

        INSERT INTO logs_moderacao (
            moderador_id,
            usuario_alvo_id,
            acao,
            justificativa
        )
        VALUES (
            p_admin_id,
            p_usuario_alvo_id,
            CONCAT('alterar_perfil_para_', p_novo_perfil),
            p_justificativa
        );
    END IF;
END $$

DELIMITER ;
