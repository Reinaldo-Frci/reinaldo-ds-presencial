-- =====================================================================
-- Sistema de Gerenciamento de EPIs - Empresa de Construção Civil
-- Script de criação do banco de dados (MySQL 8+)
-- Corresponde ao DER (arquivo DER_Sistema_EPI.drawio)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS sistema_epi
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE sistema_epi;

-- ---------------------------------------------------------------------
-- Tabela: usuario
-- Usuários do sistema (quem opera o software)
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
    id_usuario      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(100)  NOT NULL,
    email           VARCHAR(150)  NOT NULL UNIQUE,
    senha_hash      VARCHAR(255)  NOT NULL,
    perfil          ENUM('ADMINISTRADOR', 'TECNICO_SEGURANCA', 'ALMOXARIFE') NOT NULL DEFAULT 'TECNICO_SEGURANCA',
    ativo           BOOLEAN       NOT NULL DEFAULT TRUE,
    criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Tabela: colaborador
-- Colaboradores da construtora que recebem os EPIs
-- ---------------------------------------------------------------------
CREATE TABLE colaborador (
    id_colaborador  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    matricula       VARCHAR(20)   NOT NULL UNIQUE,
    nome            VARCHAR(100)  NOT NULL,
    cpf             CHAR(11)      NOT NULL UNIQUE,
    data_nascimento DATE          NULL,
    cargo           VARCHAR(60)   NOT NULL,
    setor           VARCHAR(60)   NOT NULL,
    telefone        VARCHAR(15)   NULL,
    email           VARCHAR(150)  NULL,
    ativo           BOOLEAN       NOT NULL DEFAULT TRUE,
    criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Tabela: epi
-- Equipamentos de Proteção Individual (catálogo + estoque)
-- CA = Certificado de Aprovação (obrigatório pela NR-6)
-- ---------------------------------------------------------------------
CREATE TABLE epi (
    id_epi          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(100)  NOT NULL,
    descricao       VARCHAR(255)  NULL,
    categoria       ENUM('PROTECAO_CABECA', 'PROTECAO_AUDITIVA', 'PROTECAO_RESPIRATORIA',
                         'PROTECAO_VISUAL', 'PROTECAO_MAOS', 'PROTECAO_PES',
                         'PROTECAO_TRONCO', 'OUTROS') NOT NULL,
    ca_numero       VARCHAR(20)   NOT NULL,
    ca_validade     DATE          NOT NULL,
    tamanho         VARCHAR(10)   NULL,
    qtd_estoque     INT UNSIGNED  NOT NULL DEFAULT 0,
    qtd_minima      INT UNSIGNED  NOT NULL DEFAULT 5,
    ativo           BOOLEAN       NOT NULL DEFAULT TRUE,
    criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Tabela: emprestimo
-- Cabeçalho do empréstimo (ficha de entrega de EPI - NR-6)
-- ---------------------------------------------------------------------
CREATE TABLE emprestimo (
    id_emprestimo           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_colaborador          INT UNSIGNED NOT NULL,
    id_usuario              INT UNSIGNED NOT NULL,
    data_emprestimo         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_prevista_devolucao DATE         NOT NULL,
    status                  ENUM('ATIVO', 'DEVOLVIDO', 'ATRASADO') NOT NULL DEFAULT 'ATIVO',
    observacao              VARCHAR(255) NULL,

    CONSTRAINT fk_emprestimo_colaborador
        FOREIGN KEY (id_colaborador) REFERENCES colaborador (id_colaborador),
    CONSTRAINT fk_emprestimo_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario)
);

-- ---------------------------------------------------------------------
-- Tabela: item_emprestimo
-- Itens (EPIs) vinculados a cada empréstimo
-- ---------------------------------------------------------------------
CREATE TABLE item_emprestimo (
    id_item             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_emprestimo       INT UNSIGNED NOT NULL,
    id_epi              INT UNSIGNED NOT NULL,
    quantidade          INT UNSIGNED NOT NULL DEFAULT 1,
    data_devolucao      DATETIME     NULL,
    condicao_devolucao  ENUM('BOM_ESTADO', 'DANIFICADO', 'EXTRAVIADO') NULL,

    CONSTRAINT fk_item_emprestimo
        FOREIGN KEY (id_emprestimo) REFERENCES emprestimo (id_emprestimo),
    CONSTRAINT fk_item_epi
        FOREIGN KEY (id_epi) REFERENCES epi (id_epi)
);

-- ---------------------------------------------------------------------
-- Índices de apoio a consultas frequentes
-- ---------------------------------------------------------------------
CREATE INDEX idx_emprestimo_status      ON emprestimo (status);
CREATE INDEX idx_emprestimo_colaborador ON emprestimo (id_colaborador);
CREATE INDEX idx_epi_ca_validade        ON epi (ca_validade);
CREATE INDEX idx_colaborador_nome       ON colaborador (nome);

-- ---------------------------------------------------------------------
-- Dados de exemplo (opcional, para testes)
-- ---------------------------------------------------------------------
INSERT INTO usuario (nome, email, senha_hash, perfil) VALUES
('Administrador', 'admin@empresa.com.br', '$2b$12$exemplo_hash_bcrypt', 'ADMINISTRADOR');

INSERT INTO epi (nome, descricao, categoria, ca_numero, ca_validade, tamanho, qtd_estoque, qtd_minima) VALUES
('Capacete de segurança com jugular', 'Capacete classe B com carneira e jugular', 'PROTECAO_CABECA', 'CA 12345', '2027-05-10', 'Único', 90, 15),
('Botina de segurança com biqueira', 'Botina de couro com biqueira de composite', 'PROTECAO_PES', 'CA 23456', '2026-11-30', '42', 60, 10),
('Cinto de segurança tipo paraquedista', 'Cinturão paraquedista com talabarte duplo para trabalho em altura', 'PROTECAO_TRONCO', 'CA 34567', '2028-01-15', 'Único', 25, 5),
('Luva de vaqueta', 'Luva de raspa/vaqueta para manuseio de materiais', 'PROTECAO_MAOS', 'CA 45678', '2027-03-20', 'M', 120, 20),
('Óculos de proteção incolor', 'Óculos de segurança com lente incolor antirrisco', 'PROTECAO_VISUAL', 'CA 56789', '2028-02-01', 'Único', 80, 10),
('Protetor auricular plug', 'Protetor auricular de silicone com cordão', 'PROTECAO_AUDITIVA', 'CA 67890', '2026-09-01', 'Único', 200, 50);
