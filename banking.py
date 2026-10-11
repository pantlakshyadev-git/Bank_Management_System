"""Banking use-cases. All balance-changing operations use SQL transactions."""
from datetime import datetime, timedelta
from decimal import Decimal
import secrets
import string

from mysql.connector import IntegrityError
from .currency import DEMO_UNITS_PER_USD, convert, money, positive_money
from .errors import AuthenticationError, InsufficientFundsError, NotFoundError, ValidationError
from .security import hash_secret, validate_pin, verify_secret


def _account_number() -> str:
    # The UNIQUE constraint is the final collision guard.
    return "".join(secrets.choice(string.digits) for _ in range(12))


def _reference() -> str:
    return secrets.token_hex(16)


class BankingService:
    def __init__(self, db):
        self.db = db

    def create_account(self, full_name, pin, currency, account_type, initial_balance,
                       recovery_question, recovery_answer):
        full_name = full_name.strip()
        currency = currency.strip().upper()
        account_type = account_type.strip().lower()
        if not full_name or len(full_name) > 120:
            raise ValidationError("Name is required and must be at most 120 characters.")
        validate_pin(pin)
        if currency not in DEMO_UNITS_PER_USD:
            raise ValidationError("Unsupported currency. Use USD, INR, EUR, or JPY.")
        if account_type not in {"savings", "checking"}:
            raise ValidationError("Account type must be savings or checking.")
        amount = money(initial_balance)
        if amount < 0:
            raise ValidationError("Initial deposit cannot be negative.")
        if amount > Decimal("1000000.00"):
            raise ValidationError("Initial deposit exceeds the demo limit of 1,000,000 units.")
        if not recovery_question.strip() or not recovery_answer.strip():
            raise ValidationError("A recovery question and answer are required.")
        pin_salt, pin_hash = hash_secret(pin)
        recovery_salt, recovery_hash = hash_secret(recovery_answer.strip().casefold())
        for _ in range(3):
            account_number = _account_number()
            try:
                with self.db.transaction() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """INSERT INTO accounts
                        (account_number, full_name, currency, account_type, balance,
                         pin_salt, pin_hash, recovery_question, recovery_salt, recovery_hash)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (account_number, full_name, currency, account_type, amount,
                         pin_salt, pin_hash, recovery_question.strip(), recovery_salt, recovery_hash),
                    )
                    account_id = cur.lastrowid
                    if amount > 0:
                        self._record(cur, account_id, "DEPOSIT", amount, currency, amount,
                                     reference=_reference(), note="Initial deposit")
                    cur.close()
                return {"id": account_id, "account_number": account_number}
            except IntegrityError:
                continue
        raise RuntimeError("Could not generate a unique account number. Please retry.")

    def authenticate(self, account_number, pin):
        failure_message = None
        result = None
        with self.db.transaction() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM accounts WHERE account_number=%s FOR UPDATE", (account_number.strip(),))
            account = cur.fetchone()
            if not account or not account["is_active"]:
                failure_message = "Invalid account credentials or inactive account."
            else:
                now = datetime.now()
                if account["locked_until"] and account["locked_until"] > now:
                    failure_message = "Account temporarily locked after failed attempts. Try again later."
                elif not verify_secret(pin, account["pin_salt"], account["pin_hash"]):
                    attempts = account["failed_attempts"] + 1
                    lock_until = now + timedelta(minutes=5) if attempts >= 3 else None
                    cur2 = conn.cursor()
                    cur2.execute("UPDATE accounts SET failed_attempts=%s, locked_until=%s WHERE id=%s",
                                 (0 if lock_until else attempts, lock_until, account["id"]))
                    cur2.close()
                    failure_message = "Incorrect PIN. Three failed attempts trigger a five-minute lock."
                else:
                    cur2 = conn.cursor()
                    cur2.execute("UPDATE accounts SET failed_attempts=0, locked_until=NULL WHERE id=%s", (account["id"],))
                    cur2.close()
                    result = {"id": account["id"], "account_number": account["account_number"],
                              "full_name": account["full_name"], "currency": account["currency"],
                              "account_type": account["account_type"], "balance": account["balance"]}
        # Raise only after transaction commits so failed-attempt counters persist.
        if failure_message:
            raise AuthenticationError(failure_message)
        return result

    def recover_pin(self, account_number, recovery_answer, new_pin):
        validate_pin(new_pin)
        with self.db.transaction() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, recovery_salt, recovery_hash, is_active FROM accounts WHERE account_number=%s FOR UPDATE", (account_number.strip(),))
            account = cur.fetchone()
            if not account or not account["is_active"]:
                raise AuthenticationError("Account not found or inactive.")
            if not verify_secret(recovery_answer.strip().casefold(), account["recovery_salt"], account["recovery_hash"]):
                raise AuthenticationError("Recovery answer is incorrect.")
            salt, digest = hash_secret(new_pin)
            cur2 = conn.cursor()
            cur2.execute("UPDATE accounts SET pin_salt=%s, pin_hash=%s, failed_attempts=0, locked_until=NULL WHERE id=%s",
                         (salt, digest, account["id"]))
            cur2.close()

    def _get_account(self, cur, account_id, lock=False):
        sql = "SELECT * FROM accounts WHERE id=%s" + (" FOR UPDATE" if lock else "")
        cur.execute(sql, (account_id,))
        account = cur.fetchone()
        if not account:
            raise NotFoundError("Account not found.")
        if not account["is_active"]:
            raise ValidationError("This account is inactive.")
        return account

    @staticmethod
    def _record(cur, account_id, kind, amount, currency, balance_after,
                related_account_id=None, reference=None, note=None):
        cur.execute(
            """INSERT INTO transactions
            (account_id, transaction_type, amount, currency, balance_after,
             related_account_id, reference_code, note)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (account_id, kind, amount, currency, balance_after, related_account_id,
             reference or _reference(), note),
        )

    def _change_balance(self, account_id, amount, kind):
        with self.db.transaction() as conn:
            cur = conn.cursor(dictionary=True)
            account = self._get_account(cur, account_id, lock=True)
            current = Decimal(str(account["balance"]))
            if kind == "WITHDRAWAL" and current < amount:
                raise InsufficientFundsError("Insufficient available balance.")
            new_balance = current + amount if kind == "DEPOSIT" else current - amount
            cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (new_balance, account_id))
            self._record(cur, account_id, kind, amount, account["currency"], new_balance)
            return new_balance

    def deposit(self, account_id, amount):
        return self._change_balance(account_id, positive_money(amount), "DEPOSIT")

    def withdraw(self, account_id, amount):
        return self._change_balance(account_id, positive_money(amount), "WITHDRAWAL")

    def balance(self, account_id):
        with self.db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT account_number, full_name, currency, account_type, balance, is_active FROM accounts WHERE id=%s", (account_id,))
            row = cur.fetchone()
            if not row:
                raise NotFoundError("Account not found.")
            if not row["is_active"]:
                raise ValidationError("This account is inactive.")
            return row

    def transfer(self, sender_id, recipient_account_number, amount):
        amount = positive_money(amount)
        with self.db.transaction() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM accounts WHERE account_number=%s", (recipient_account_number.strip(),))
            recipient_pre = cur.fetchone()
            if not recipient_pre:
                raise NotFoundError("Recipient account not found.")
            recipient_id = recipient_pre["id"]
            if recipient_id == sender_id:
                raise ValidationError("You cannot transfer money to your own account.")
            # Lock accounts in stable ID order to reduce deadlock risk.
            ids = sorted([sender_id, recipient_id])
            cur.execute(f"SELECT * FROM accounts WHERE id IN (%s,%s) ORDER BY id FOR UPDATE", tuple(ids))
            rows = {row["id"]: row for row in cur.fetchall()}
            sender, recipient = rows.get(sender_id), rows.get(recipient_id)
            if not sender or not recipient:
                raise NotFoundError("Sender or recipient account not found.")
            if not sender["is_active"] or not recipient["is_active"]:
                raise ValidationError("Both accounts must be active.")
            sender_balance = Decimal(str(sender["balance"]))
            recipient_balance = Decimal(str(recipient["balance"]))
            if sender_balance < amount:
                raise InsufficientFundsError("Insufficient available balance.")
            converted = convert(amount, sender["currency"], recipient["currency"])
            sender_new, recipient_new = sender_balance - amount, recipient_balance + converted
            cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (sender_new, sender_id))
            cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (recipient_new, recipient_id))
            reference = _reference()
            self._record(cur, sender_id, "TRANSFER_OUT", amount, sender["currency"], sender_new,
                         recipient_id, reference, "Transfer sent")
            self._record(cur, recipient_id, "TRANSFER_IN", converted, recipient["currency"], recipient_new,
                         sender_id, reference, "Transfer received; demo exchange rate if currencies differ")
            return {"reference": reference, "sent": amount, "sent_currency": sender["currency"],
                    "received": converted, "received_currency": recipient["currency"]}

    def history(self, account_id, limit=100):
        limit = max(1, min(int(limit), 500))
        with self.db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT transaction_type, amount, currency, balance_after, related_account_id, reference_code, note, created_at FROM transactions WHERE account_id=%s ORDER BY created_at DESC, id DESC LIMIT %s", (account_id, limit))
            return cur.fetchall()

    def apply_interest(self, account_id, year=None):
        year = int(year or datetime.now().year)
        if year < 2000 or year > 9999:
            raise ValidationError("Interest year must be a valid four-digit year.")
        try:
            with self.db.transaction() as conn:
                cur = conn.cursor(dictionary=True)
                account = self._get_account(cur, account_id, lock=True)
                rate = Decimal("0.04") if account["account_type"] == "savings" else Decimal("0.02")
                balance = Decimal(str(account["balance"]))
                interest = (balance * rate).quantize(Decimal("0.01"))
                if interest <= 0:
                    raise ValidationError("No interest is due on a zero balance.")
                cur.execute("INSERT INTO interest_runs (account_id, period_year, amount) VALUES (%s,%s,%s)", (account_id, year, interest))
                new_balance = balance + interest
                cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (new_balance, account_id))
                self._record(cur, account_id, "INTEREST", interest, account["currency"], new_balance,
                             note=f"Demo annual interest for {year}; applied once per account/year")
                return interest
        except IntegrityError as exc:
            raise ValidationError(f"Annual interest has already been applied for {year}.") from exc

    def apply_for_loan(self, account_id, amount, duration_years, annual_rate=Decimal("0.05")):
        amount = positive_money(amount)
        try:
            years = int(duration_years)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Loan duration must be a positive whole number of years.") from exc
        if years < 1 or years > 30:
            raise ValidationError("Loan duration must be between 1 and 30 years.")
        with self.db.transaction() as conn:
            cur = conn.cursor(dictionary=True)
            account = self._get_account(cur, account_id, lock=True)
            max_loan = convert(Decimal("100000"), "USD", account["currency"])
            if amount > max_loan:
                raise ValidationError(f"Demo loan limit is {max_loan} {account['currency']}.")
            cur.execute("SELECT COUNT(*) AS n FROM loans WHERE account_id=%s AND status='ACTIVE'", (account_id,))
            if cur.fetchone()["n"]:
                raise ValidationError("Pay off existing active loans before applying for another.")
            total_payable = (amount * ((Decimal("1") + annual_rate) ** years)).quantize(Decimal("0.01"))
            cur.execute("INSERT INTO loans (account_id, principal, outstanding_balance, annual_rate, duration_years) VALUES (%s,%s,%s,%s,%s)",
                        (account_id, amount, total_payable, annual_rate, years))
            loan_id = cur.lastrowid
            new_balance = Decimal(str(account["balance"])) + amount
            cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (new_balance, account_id))
            self._record(cur, account_id, "LOAN_DISBURSEMENT", amount, account["currency"], new_balance,
                         note=f"Loan ID {loan_id}")
            return {"principal": amount, "total_payable": total_payable, "loan_id": loan_id}

    def pay_loan(self, account_id, payment):
        payment = positive_money(payment)
        with self.db.transaction() as conn:
            cur = conn.cursor(dictionary=True)
            account = self._get_account(cur, account_id, lock=True)
            cur.execute("SELECT * FROM loans WHERE account_id=%s AND status='ACTIVE' ORDER BY id FOR UPDATE", (account_id,))
            loan = cur.fetchone()
            if not loan:
                raise ValidationError("No active loan was found.")
            balance = Decimal(str(account["balance"]))
            outstanding = Decimal(str(loan["outstanding_balance"]))
            if payment > outstanding:
                raise ValidationError(f"Payment exceeds outstanding loan balance ({outstanding}).")
            if payment > balance:
                raise InsufficientFundsError("Insufficient available balance for this loan payment.")
            new_balance, remaining = balance - payment, outstanding - payment
            cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (new_balance, account_id))
            cur.execute("UPDATE loans SET outstanding_balance=%s, status=%s WHERE id=%s",
                        (remaining, "PAID" if remaining == 0 else "ACTIVE", loan["id"]))
            self._record(cur, account_id, "LOAN_PAYMENT", payment, account["currency"], new_balance,
                         note=f"Loan ID {loan['id']}; remaining {remaining}")
            return remaining

    def deactivate(self, account_id):
        """Disable access without destroying the balance or historical records."""
        with self.db.transaction() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM accounts WHERE id=%s FOR UPDATE", (account_id,))
            account = cur.fetchone()
            if not account:
                raise NotFoundError("Account not found.")
            cur.execute("UPDATE accounts SET is_active=FALSE WHERE id=%s", (account_id,))
