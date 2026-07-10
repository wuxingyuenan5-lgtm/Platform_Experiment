CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NULL,
    role ENUM('guest','employee','admin') NOT NULL DEFAULT 'guest',
    department VARCHAR(100) NULL,
    managed_strategies JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS accounts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    account_type ENUM('puridia','mt5_exam','bybit','trader_a','trader_b') NOT NULL,
    account_address VARCHAR(255) NOT NULL,
    initial_capital DECIMAL(20,8) NOT NULL,
    parent_id BIGINT NULL,
    arbitrary_flag TINYINT(1) NOT NULL DEFAULT 0,
    api_key_encrypted VARCHAR(500) NULL,
    api_secret_encrypted VARCHAR(500) NULL,
    owner_id BIGINT NULL,
    status ENUM('active','inactive') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY owner_id (owner_id),
    CONSTRAINT accounts_ibfk_1 FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS assets (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    total_asset DECIMAL(20,8) NOT NULL,
    available_fund DECIMAL(20,8) NOT NULL,
    bybit_positions JSON NULL,
    update_frequency VARCHAR(20) NOT NULL DEFAULT '5m',
    data_source VARCHAR(50) NOT NULL DEFAULT 'system',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY account_id (account_id),
    CONSTRAINT assets_ibfk_1 FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
