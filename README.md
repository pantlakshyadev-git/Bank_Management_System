# Modular Bank Management System (MySQL)

A portfolio-oriented, command-line banking simulation that combines the core operations from `cbse_bank_management.py` with the advanced features from `Bank_Management_Project.py`. It is an educational project, **not production banking software**.

## Included features

- Account creation with unique 12-digit account numbers
- PIN hashing with per-secret random salts; bounded login attempts and temporary lockout
- MySQL as the sole source of truth (no split-brain JSON/MySQL writes)
- Deposits, withdrawals, balance checks and account-to-account transfers
- Atomic transfer transactions with account row locks and a shared transfer reference
- Transaction history with timestamps, balance-after values and related account IDs
- Demo currency conversion for USD, INR, EUR and JPY
- QR generation, QR image scanning, and optional webcam scanning
- Annual interest credited at most once per account/year
- Loan application and loan payment with balance/loan validation
- PIN recovery using a hashed recovery answer
- Account deactivation without deleting its balance or transaction history
- CSV account/transaction reports, transaction graphs, application logging
- Input validation and basic unit tests

## Project layout

```text
merged_bank_project/
├── bank_app/
│   ├── banking.py       # Core banking rules and SQL transactions
│   ├── cli.py           # Terminal menus and user interaction
│   ├── config.py        # Environment-based configuration
│   ├── currency.py      # Decimal money handling and demo FX rates
│   ├── database.py      # MySQL connection pool and transaction context
│   ├── errors.py        # Expected application exceptions
│   ├── qr_tools.py      # QR generation and optional scanning
│   ├── reporting.py     # CSV exports and plotting
│   └── security.py      # PIN/recovery hashing and OTP helper
├── tests/
├── schema.sql
├── .env.example
├── requirements.txt
└── main.py
```

## 1. Requirements

- Python 3.10 or newer
- MySQL Server 8.0+ (recommended)
- Optional system ZBar library for `pyzbar` QR decoding, depending on OS

## 2. Create the database

Open a MySQL client as an administrator and run:

```sql
SOURCE /absolute/path/to/merged_bank_project/schema.sql;
```

If your MySQL installation does not support the `utf8mb4_0900_ai_ci` collation, change it in `schema.sql` to a supported `utf8mb4` collation such as `utf8mb4_unicode_ci`.

Create a restricted application user. Replace the password with a strong unique value:

```sql
CREATE USER 'bank_app_user'@'localhost' IDENTIFIED BY 'replace-with-a-strong-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON bank_management.* TO 'bank_app_user'@'localhost';
FLUSH PRIVILEGES;
```

The schema file creates the database and tables. The application user should not be the MySQL root account.

## 3. Install and configure

From the project directory:

```bash
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Install dependencies and configure credentials:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`. Never commit `.env` or real credentials to Git.

## 4. Run

```bash
python main.py
```

Use **Create account** first. Log in using the displayed account number and your PIN. Account QR images, logs, and CSV reports are stored in the configured output directory (default: `output/`).

## 5. Run tests

Install pytest in your virtual environment, then run:

```bash
python -m pip install pytest
python -m pytest -q
```

The included unit tests cover money validation, demo conversion and secret hashing. Database integration tests should be run against a dedicated test database before a release.

## Design notes and known limitations

- **Educational simulation only.** Do not use this application to hold, transfer or manage real funds.
- The FX table in `currency.py` is deliberately labeled as approximate demo data. Cross-currency transfers use those fixed rates; they are not live quotes and do not model fees or spreads.
- OTP delivery is not implemented. `generate_otp()` is only a secure random-code helper and is not wired into a delivery/verification workflow. Do not claim that an OTP was sent.
- PIN and recovery answers are salted and hashed, but a production service would need a stronger identity/recovery process, MFA delivery, rate limits per IP/device, audit monitoring, secrets management and formal threat modelling.
- Interest and loan formulas are illustrative. They do not model a real bank's contract, amortization schedule, regulatory requirements or taxes. Interest application is protected by a unique account/year key.
- Webcam scanning needs a working camera and OS-level dependencies. QR codes contain the recipient's account number only; scanning is not authorization by itself.
- CSV exports contain financial/account metadata. Protect the output directory and do not publish generated reports.
- MySQL is authoritative. JSON is intentionally not used as a second live store, avoiding the inconsistency in the original first script.
- The application is currently a terminal program. A GUI or web frontend can be added later while reusing `BankingService`.

## Suggested next portfolio milestones

1. Add database integration tests for transfer atomicity, insufficient funds, lockout, interest idempotency and loan payments.
2. Add migrations, structured audit events, and role-based admin/reporting access.
3. Add an exchange-rate provider behind an interface and cache quotes with timestamps.
4. Add a web API/UI only after service and database tests are stable.
5. Add CI (linting, type checking, unit tests) and a threat-model document.
