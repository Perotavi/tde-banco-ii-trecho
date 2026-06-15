USE rede_trecho;

ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS suspenso_ate DATETIME NULL,
ADD COLUMN IF NOT EXISTS motivo_punicao VARCHAR(255) NULL;

DROP PROCEDURE IF EXISTS sp_criar_post;
DROP PROCEDURE IF EXISTS sp_editar_post;
DROP PROCEDURE IF EXISTS sp_denunciar_post;
DROP PROCEDURE IF EXISTS sp_moderar_post;
DROP PROCEDURE IF EXISTS sp_alterar_status_usuario;
DROP PROCEDURE IF EXISTS sp_relatorio_usuario;

DELIMITER $$

CREATE PROCEDURE sp_criar_post(
    IN p_usuario_id INT,
    IN p_conteudo VARCHAR(280)
)
BEGIN
    DECLARE v_status VARCHAR(20);

    SELECT status_conta
    INTO v_status
    FROM usuarios
    WHERE id = p_usuario_id;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário não encontrado.';

    ELSEIF v_status <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário não pode publicar porque a conta não está ativa.';

    ELSEIF p_conteudo IS NULL OR TRIM(p_conteudo) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'O conteúdo do post não pode estar vazio.';

    ELSE
        INSERT INTO posts (usuario_id, conteudo)
        VALUES (p_usuario_id, p_conteudo);
    END IF;
END $$


CREATE PROCEDURE sp_editar_post(
    IN p_usuario_id INT,
    IN p_post_id INT,
    IN p_novo_conteudo VARCHAR(280)
)
BEGIN
    DECLARE v_autor_id INT;
    DECLARE v_status_post VARCHAR(20);
    DECLARE v_status_usuario VARCHAR(20);

    SELECT status_conta
    INTO v_status_usuario
    FROM usuarios
    WHERE id = p_usuario_id;

    SELECT usuario_id, status_post
    INTO v_autor_id, v_status_post
    FROM posts
    WHERE id = p_post_id;

    IF v_status_usuario IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário não encontrado.';

    ELSEIF v_status_usuario <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário não pode editar posts porque a conta não está ativa.';

    ELSEIF v_autor_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Post não encontrado.';

    ELSEIF v_autor_id <> p_usuario_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário só pode editar os próprios posts.';

    ELSEIF v_status_post <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Não é possível editar um post que não está ativo.';

    ELSEIF p_novo_conteudo IS NULL OR TRIM(p_novo_conteudo) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'O novo conteúdo não pode estar vazio.';

    ELSE
        UPDATE posts
        SET
            conteudo = p_novo_conteudo,
            data_atualizacao = CURRENT_TIMESTAMP
        WHERE id = p_post_id;
    END IF;
END $$


CREATE PROCEDURE sp_denunciar_post(
    IN p_denunciante_id INT,
    IN p_post_id INT,
    IN p_motivo VARCHAR(255)
)
BEGIN
    DECLARE v_usuario_status VARCHAR(20);
    DECLARE v_post_status VARCHAR(20);

    SELECT status_conta
    INTO v_usuario_status
    FROM usuarios
    WHERE id = p_denunciante_id;

    SELECT status_post
    INTO v_post_status
    FROM posts
    WHERE id = p_post_id;

    IF v_usuario_status IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário denunciante não encontrado.';

    ELSEIF v_usuario_status NOT IN ('ativo', 'suspenso') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário banido não pode denunciar posts.';

    ELSEIF v_post_status IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Post não encontrado.';

    ELSEIF v_post_status <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Não é possível denunciar um post que não está ativo.';

    ELSEIF p_motivo IS NULL OR TRIM(p_motivo) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'O motivo da denúncia não pode estar vazio.';

    ELSE
        INSERT INTO denuncias (post_id, denunciante_id, motivo)
        VALUES (p_post_id, p_denunciante_id, p_motivo);
    END IF;
END $$


CREATE PROCEDURE sp_moderar_post(
    IN p_moderador_id INT,
    IN p_post_id INT,
    IN p_acao VARCHAR(20),
    IN p_justificativa VARCHAR(255)
)
BEGIN
    DECLARE v_perfil_executor VARCHAR(50);
    DECLARE v_perfil_autor VARCHAR(50);
    DECLARE v_status_executor VARCHAR(20);
    DECLARE v_status_post VARCHAR(20);

    SELECT pf.nome, u.status_conta
    INTO v_perfil_executor, v_status_executor
    FROM usuarios u
    INNER JOIN perfis pf ON u.perfil_id = pf.id
    WHERE u.id = p_moderador_id;

    SELECT posts.status_post, perfil_autor.nome
    INTO v_status_post, v_perfil_autor
    FROM posts
    INNER JOIN usuarios autor ON posts.usuario_id = autor.id
    INNER JOIN perfis perfil_autor ON autor.perfil_id = perfil_autor.id
    WHERE posts.id = p_post_id;

    IF v_perfil_executor NOT IN ('moderador', 'admin') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Apenas moderadores ou administradores podem moderar posts.';

    ELSEIF v_status_executor <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário executor não está ativo.';

    ELSEIF v_status_post IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Post não encontrado.';

    ELSEIF v_perfil_executor = 'moderador' AND v_perfil_autor IN ('moderador', 'admin') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Moderadores não podem moderar posts de moderadores ou administradores.';

    ELSEIF p_acao NOT IN ('ocultar', 'remover') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ação inválida. Use ocultar ou remover.';

    ELSEIF p_justificativa IS NULL OR TRIM(p_justificativa) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A justificativa é obrigatória.';

    ELSE
        IF p_acao = 'ocultar' THEN
            UPDATE posts
            SET status_post = 'oculto'
            WHERE id = p_post_id;
        ELSE
            UPDATE posts
            SET status_post = 'removido'
            WHERE id = p_post_id;
        END IF;

        UPDATE denuncias
        SET status_denuncia = 'analisada'
        WHERE post_id = p_post_id
          AND status_denuncia = 'pendente';

        INSERT INTO logs_moderacao (
            moderador_id,
            post_id,
            acao,
            justificativa
        )
        VALUES (
            p_moderador_id,
            p_post_id,
            p_acao,
            p_justificativa
        );
    END IF;
END $$


CREATE PROCEDURE sp_alterar_status_usuario(
    IN p_moderador_id INT,
    IN p_usuario_alvo_id INT,
    IN p_novo_status VARCHAR(20),
    IN p_justificativa VARCHAR(255)
)
BEGIN
    DECLARE v_perfil_executor VARCHAR(50);
    DECLARE v_perfil_alvo VARCHAR(50);
    DECLARE v_status_executor VARCHAR(20);
    DECLARE v_total_executor INT DEFAULT 0;
    DECLARE v_total_alvo INT DEFAULT 0;

    SELECT COUNT(*) INTO v_total_executor
    FROM usuarios
    WHERE id = p_moderador_id;

    IF v_total_executor = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário executor não encontrado.';
    END IF;

    SELECT COUNT(*) INTO v_total_alvo
    FROM usuarios
    WHERE id = p_usuario_alvo_id;

    IF v_total_alvo = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário alvo não encontrado.';
    END IF;

    SELECT p.nome, u.status_conta
    INTO v_perfil_executor, v_status_executor
    FROM usuarios u
    INNER JOIN perfis p ON u.perfil_id = p.id
    WHERE u.id = p_moderador_id;

    SELECT p.nome
    INTO v_perfil_alvo
    FROM usuarios u
    INNER JOIN perfis p ON u.perfil_id = p.id
    WHERE u.id = p_usuario_alvo_id;

    IF v_perfil_executor NOT IN ('moderador', 'admin') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Apenas moderadores e administradores podem alterar status de usuários.';
    END IF;

    IF v_status_executor <> 'ativo' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário executor não está ativo.';
    END IF;

    IF p_novo_status NOT IN ('ativo', 'suspenso', 'banido') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Status informado é inválido.';
    END IF;

    IF p_justificativa IS NULL OR TRIM(p_justificativa) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A justificativa é obrigatória.';
    END IF;

    IF p_moderador_id = p_usuario_alvo_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Um usuário não pode alterar o próprio status.';
    END IF;

    IF v_perfil_executor = 'moderador' AND v_perfil_alvo IN ('moderador', 'admin') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Moderadores não podem suspender, banir ou reativar moderadores ou administradores.';
    END IF;

    IF p_novo_status = 'suspenso' THEN
        UPDATE usuarios
        SET
            status_conta = 'suspenso',
            suspenso_ate = DATE_ADD(NOW(), INTERVAL 1 DAY),
            motivo_punicao = p_justificativa
        WHERE id = p_usuario_alvo_id;

    ELSEIF p_novo_status = 'banido' THEN
        UPDATE usuarios
        SET
            status_conta = 'banido',
            suspenso_ate = NULL,
            motivo_punicao = p_justificativa
        WHERE id = p_usuario_alvo_id;

    ELSE
        UPDATE usuarios
        SET
            status_conta = 'ativo',
            suspenso_ate = NULL,
            motivo_punicao = NULL
        WHERE id = p_usuario_alvo_id;
    END IF;

    INSERT INTO logs_moderacao (
        moderador_id,
        usuario_alvo_id,
        acao,
        justificativa
    )
    VALUES (
        p_moderador_id,
        p_usuario_alvo_id,
        CONCAT('alterar_status_usuario_para_', p_novo_status),
        p_justificativa
    );
END $$


CREATE PROCEDURE sp_relatorio_usuario(
    IN p_usuario_id INT
)
BEGIN
    SELECT
        u.id AS usuario_id,
        u.nome,
        u.username,
        u.status_conta,
        u.suspenso_ate,
        u.motivo_punicao,
        COUNT(DISTINCT p.id) AS total_posts,
        COUNT(DISTINCT c.id) AS total_comentarios,
        COUNT(DISTINCT curt.id) AS total_curtidas_recebidas,
        COUNT(DISTINCT d.id) AS total_denuncias_recebidas
    FROM usuarios u
    LEFT JOIN posts p ON u.id = p.usuario_id
    LEFT JOIN comentarios c ON u.id = c.usuario_id
    LEFT JOIN curtidas curt ON p.id = curt.post_id
    LEFT JOIN denuncias d ON p.id = d.post_id
    WHERE u.id = p_usuario_id
    GROUP BY
        u.id,
        u.nome,
        u.username,
        u.status_conta,
        u.suspenso_ate,
        u.motivo_punicao;
END $$

DELIMITER ;