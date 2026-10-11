import csv
from pathlib import Path
from .config import settings


def export_reports(db):
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    with db.connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, account_number, full_name, currency, account_type, balance, is_active, created_at FROM accounts ORDER BY id")
        accounts = cur.fetchall()
        cur.execute("SELECT t.id, a.account_number, t.transaction_type, t.amount, t.currency, t.balance_after, t.reference_code, t.note, t.created_at FROM transactions t JOIN accounts a ON a.id=t.account_id ORDER BY t.created_at, t.id")
        transactions = cur.fetchall()
    for filename, rows in (("accounts.csv", accounts), ("transactions.csv", transactions)):
        path = settings.output_dir / filename
        fields = list(rows[0].keys()) if rows else (["id", "account_number", "full_name", "currency", "account_type", "balance", "is_active", "created_at"] if filename == "accounts.csv" else ["id", "account_number", "transaction_type", "amount", "currency", "balance_after", "reference_code", "note", "created_at"])
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    return settings.output_dir / "accounts.csv", settings.output_dir / "transactions.csv"


def plot_transaction_history(db, account_id):
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install matplotlib to use transaction charts.") from exc
    with db.connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT transaction_type, amount, created_at FROM transactions WHERE account_id=%s ORDER BY created_at, id", (account_id,))
        rows = cur.fetchall()
    if not rows:
        print("No transactions to plot yet.")
        return
    dates, values, labels = [], [], []
    inflows = {"DEPOSIT", "TRANSFER_IN", "INTEREST", "LOAN_DISBURSEMENT"}
    for row in rows:
        dates.append(row["created_at"])
        value = float(row["amount"])
        values.append(value if row["transaction_type"] in inflows else -value)
        labels.append(row["transaction_type"])
    plt.figure(figsize=(11, 5))
    plt.plot(dates, values, marker="o")
    for x, y, label in zip(dates, values, labels):
        plt.annotate(label, (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7)
    plt.title("Transaction amounts (inflows positive, outflows negative)")
    plt.xlabel("Date")
    plt.ylabel("Amount in transaction currency")
    plt.xticks(rotation=35)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def financial_insights(db, account_id):
    """Simple transparent heuristics; not financial advice or an AI prediction."""
    with db.connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT balance, currency FROM accounts WHERE id=%s AND is_active=TRUE", (account_id,))
        account = cur.fetchone()
        if not account:
            raise ValueError("Active account not found.")
        cur.execute("SELECT transaction_type, amount, created_at FROM transactions WHERE account_id=%s ORDER BY created_at DESC, id DESC LIMIT 30", (account_id,))
        transactions = cur.fetchall()
    balance = float(account["balance"])
    deposits = [float(t["amount"]) for t in transactions if t["transaction_type"] == "DEPOSIT"]
    withdrawals = [float(t["amount"]) for t in transactions if t["transaction_type"] == "WITHDRAWAL"]
    tips = []
    if balance < 500:
        tips.append("Your balance is below 500 units of your account currency. Review upcoming expenses before making optional purchases.")
    if len(transactions) < 3:
        tips.append("There is limited transaction history, so meaningful trend analysis is not available yet.")
    if len(withdrawals) >= 3 and sum(withdrawals) > sum(deposits):
        tips.append("In the latest 30 transactions, recorded withdrawals exceed recorded deposits. Review the history to understand the pattern.")
    if not tips:
        tips.append("No simple warning rule was triggered. Continue reviewing your balance and transaction history regularly.")
    return {"currency": account["currency"], "balance": account["balance"], "tips": tips}
