CREATE DATABASE IF NOT EXISTS bank_management CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE bank_management;

CREATE TABLE IF NOT EXISTS accounts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    account_number CHAR(12) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    currency CHAR(3) NOT NULL,
    account_type ENUM('savings','checking') NOT NULL,
    balance DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    pin_salt VARBINARY(16) NOT NULL,
    pin_hash VARBINARY(64) NOT NULL,
    recovery_question VARCHAR(255) NOT NULL,
    recovery_salt VARBINARY(16) NOT NULL,
    recovery_hash VARBINARY(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    failed_attempts INT UNSIGNED NOT NULL DEFAULT 0,
    locked_until DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_accounts_active (is_active)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT UNSIGNED NOT NULL,
    transaction_type ENUM('DEPOSIT','WITHDRAWAL','TRANSFER_OUT','TRANSFER_IN','INTEREST','LOAN_DISBURSEMENT','LOAN_PAYMENT','ACCOUNT_CLOSURE') NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    balance_after DECIMAL(18,2) NOT NULL,
    related_account_id BIGINT UNSIGNED NULL,
    reference_code CHAR(32) NOT NULL,
    note VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_transactions_account FOREIGN KEY (account_id) REFERENCES accounts(id),
    CONSTRAINT fk_transactions_related FOREIGN KEY (related_account_id) REFERENCES accounts(id),
    INDEX idx_transactions_account_date (account_id, created_at),
    INDEX idx_transactions_reference (reference_code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS loans (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT UNSIGNED NOT NULL,
    principal DECIMAL(18,2) NOT NULL,
    outstanding_balance DECIMAL(18,2) NOT NULL,
    annual_rate DECIMAL(7,5) NOT NULL,
    duration_years INT UNSIGNED NOT NULL,
    status ENUM('ACTIVE','PAID') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_loans_account FOREIGN KEY (account_id) REFERENCES accounts(id),
    INDEX idx_loans_account_status (account_id, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS interest_runs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT UNSIGNED NOT NULL,
    period_year SMALLINT UNSIGNED NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_interest_account FOREIGN KEY (account_id) REFERENCES accounts(id),
    UNIQUE KEY uq_interest_account_year (account_id, period_year)
) ENGINE=InnoDB;
