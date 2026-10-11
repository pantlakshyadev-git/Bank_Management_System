from getpass import getpass
from decimal import Decimal

from .banking import BankingService
from .currency import DEMO_UNITS_PER_USD, convert
from .errors import BankError
from .qr_tools import generate_account_qr, scan_qr_image, scan_qr_webcam
from .reporting import export_reports, financial_insights, plot_transaction_history


def _show_history(service, account_id):
    rows = service.history(account_id)
    if not rows:
        print("No transactions recorded yet.")
        return
    print("\n--- Recent transactions ---")
    for row in rows:
        print(f"{row['created_at']} | {row['transaction_type']:<18} | {row['amount']} {row['currency']} | balance {row['balance_after']} | ref {row['reference_code']}")
        if row.get("note"):
            print(f"    {row['note']}")


def run_cli(db):
    service = BankingService(db)
    session = None
    while True:
        print("\n========== BANK MANAGEMENT SYSTEM ==========")
        print("1. Create account\n2. Log in\n3. Recover PIN\n4. Convert currency (demo rates)\n5. Export reports\n0. Exit")
        choice = input("Choose an option: ").strip().lower()
        try:
            if choice in {"1", "create account"}:
                name = input("Full name: ").strip()
                currency = input("Currency (USD/INR/EUR/JPY): ").strip().upper()
                account_type = input("Account type (savings/checking): ").strip().lower()
                initial = input(f"Initial deposit ({currency}): ").strip()
                pin = getpass("Set a 4-digit PIN: ")
                question = input("Recovery question: ").strip()
                answer = getpass("Recovery answer (case-insensitive): ")
                result = service.create_account(name, pin, currency, account_type, initial, question, answer)
                print(f"Account created. Account number: {result['account_number']}")
                try:
                    print(f"QR code saved to: {generate_account_qr(result['account_number'])}")
                except (RuntimeError, OSError) as exc:
                    print(f"QR generation skipped: {exc}")
            elif choice in {"2", "log in", "login"}:
                number = input("Account number: ").strip()
                pin = getpass("PIN: ")
                session = service.authenticate(number, pin)
                print(f"Welcome, {session['full_name']}! Session started.")
                _account_menu(service, db, session)
                session = None
            elif choice in {"3", "recover pin"}:
                number = input("Account number: ").strip()
                answer = getpass("Recovery answer: ")
                new_pin = getpass("New 4-digit PIN: ")
                service.recover_pin(number, answer, new_pin)
                print("PIN reset successfully. Please log in.")
            elif choice in {"4", "convert currency"}:
                amount = Decimal(input("Amount: ").strip())
                source = input("From currency: ").strip().upper()
                target = input("To currency: ").strip().upper()
                print(f"Demo conversion: {amount} {source} = {convert(amount, source, target)} {target}")
            elif choice in {"5", "export reports"}:
                paths = export_reports(db)
                print("Reports written to:")
                for path in paths:
                    print(f" - {path}")
            elif choice in {"0", "exit", "quit"}:
                print("Thank you for using the Bank Management System.")
                return
            else:
                print("Invalid choice.")
        except BankError as exc:
            print(f"Operation could not be completed: {exc}")
        except (ValueError, ArithmeticError) as exc:
            print(f"Invalid input: {exc}")
        except Exception as exc:
            # Log details in the application entrypoint; don't expose stack traces to users.
            print(f"Unexpected error: {exc}")


def _account_menu(service, db, account):
    account_id = account["id"]
    while True:
        print(f"\n--- Account: {account['account_number']} | {account['currency']} ---")
        print("1. Balance\n2. Deposit\n3. Withdraw\n4. Transfer by account number\n5. Transfer via QR image\n6. Scan QR with webcam and transfer\n7. Transaction history\n8. Plot transaction history\n9. Annual interest (demo)\n10. Apply for loan\n11. Make loan payment\n12. Generate account QR\n13. Deactivate account\n14. Financial insights\n15. Guided banking assistant\n0. Log out")
        choice = input("Choose an option: ").strip().lower()
        try:
            if choice in {"1", "balance"}:
                row = service.balance(account_id)
                print(f"Balance: {row['balance']} {row['currency']} | Type: {row['account_type']}")
            elif choice in {"2", "deposit"}:
                print(f"New balance: {service.deposit(account_id, input('Amount: '))} {account['currency']}")
            elif choice in {"3", "withdraw"}:
                print(f"New balance: {service.withdraw(account_id, input('Amount: '))} {account['currency']}")
            elif choice in {"4", "transfer"}:
                recipient = input("Recipient account number: ").strip()
                result = service.transfer(account_id, recipient, input(f"Amount to send ({account['currency']}): "))
                print(f"Sent {result['sent']} {result['sent_currency']}; recipient receives {result['received']} {result['received_currency']}.")
                print(f"Transfer reference: {result['reference']}")
            elif choice in {"5", "transfer via qr"}:
                path = input("Path to recipient QR image: ").strip()
                recipient = scan_qr_image(path)
                result = service.transfer(account_id, recipient, input(f"Amount to send ({account['currency']}): "))
                print(f"Transfer complete. Reference: {result['reference']}")
            elif choice in {"6", "webcam"}:
                recipient = scan_qr_webcam()
                if recipient:
                    result = service.transfer(account_id, recipient, input(f"Amount to send ({account['currency']}): "))
                    print(f"Transfer complete. Reference: {result['reference']}")
                else:
                    print("QR scan cancelled or no valid QR detected.")
            elif choice in {"7", "history"}:
                _show_history(service, account_id)
            elif choice in {"8", "plot"}:
                plot_transaction_history(db, account_id)
            elif choice in {"9", "interest"}:
                interest = service.apply_interest(account_id)
                print(f"Credited {interest} {account['currency']} at the demo annual rate.")
            elif choice in {"10", "loan"}:
                amount = input(f"Loan amount ({account['currency']}): ")
                years = input("Duration in whole years (1-30): ")
                result = service.apply_for_loan(account_id, amount, years)
                print(f"Loan ID {result['loan_id']} created. Principal {result['principal']}; demo total payable {result['total_payable']} {account['currency']}.")
            elif choice in {"11", "loan payment"}:
                remaining = service.pay_loan(account_id, input("Payment amount: "))
                print(f"Loan payment recorded. Remaining loan balance: {remaining} {account['currency']}.")
            elif choice in {"12", "qr"}:
                print(f"QR code saved to: {generate_account_qr(account['account_number'])}")
            elif choice in {"13", "deactivate"}:
                confirm = input("Deactivate this account? This disables access but preserves history and balance. Type YES to confirm: ")
                if confirm == "YES":
                    service.deactivate(account_id)
                    print("Account deactivated. Contact an administrator to restore access.")
                    return
                print("Deactivation cancelled.")
            elif choice in {"14", "insights", "financial insights"}:
                report = financial_insights(db, account_id)
                print(f"\nBalance: {report['balance']} {report['currency']}")
                for tip in report["tips"]:
                    print(f"- {tip}")
                print("These are simple rules-based observations, not financial advice.")
            elif choice in {"15", "assistant", "guided banking assistant"}:
                _guided_assistant(service, db, account)
            elif choice in {"0", "logout", "log out"}:
                return
            else:
                print("Invalid choice.")
        except BankError as exc:
            print(f"Operation could not be completed: {exc}")
        except (ValueError, ArithmeticError, RuntimeError, OSError) as exc:
            print(f"Could not complete that action: {exc}")


def _guided_assistant(service, db, account):
    """Keyword-based helper adapted from the original project; not a generative AI."""
    print("Guided assistant: try 'balance', 'deposit', 'withdraw', 'history', 'insights', or 'exit'.")
    while True:
        query = input("Assistant> ").strip().lower()
        try:
            if query in {"exit", "quit", "back"}:
                return
            if "balance" in query:
                row = service.balance(account["id"])
                print(f"Balance: {row['balance']} {row['currency']}")
            elif "deposit" in query:
                print(f"New balance: {service.deposit(account['id'], input('Amount: '))} {account['currency']}")
            elif "withdraw" in query:
                print(f"New balance: {service.withdraw(account['id'], input('Amount: '))} {account['currency']}")
            elif "history" in query or "transaction" in query:
                _show_history(service, account["id"])
            elif "insight" in query or "suggest" in query:
                report = financial_insights(db, account["id"])
                for tip in report["tips"]:
                    print(f"- {tip}")
            else:
                print("I can help with balance, deposits, withdrawals, transaction history, or insights. Type exit to return.")
        except BankError as exc:
            print(f"Operation could not be completed: {exc}")
        except (ValueError, ArithmeticError) as exc:
            print(f"Invalid input: {exc}")
