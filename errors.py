class BankError(Exception):
    """Expected, user-facing banking error."""

class ValidationError(BankError):
    pass

class AuthenticationError(BankError):
    pass

class NotFoundError(BankError):
    pass

class InsufficientFundsError(BankError):
    pass
