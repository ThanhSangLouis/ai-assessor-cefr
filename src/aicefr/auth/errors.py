"""Safe account and authentication errors exposed at the API boundary."""


class AccountError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


class ValidationError(AccountError):
    def __init__(self, code: str = "validation_error") -> None:
        super().__init__(code)


class ConflictError(AccountError):
    def __init__(self, code: str = "conflict") -> None:
        super().__init__(code)


class AuthorizationError(AccountError):
    _CODES = {
        "access denied": "access_denied",
        "invalid credentials": "invalid_credentials",
        "session unavailable": "session_unavailable",
        "account unavailable": "account_unavailable",
        "consent unavailable": "consent_unavailable",
        "active consent required": "active_consent_required",
        "password_change_required": "password_change_required",
    }

    def __init__(self, code: str = "unauthorized") -> None:
        self.code = self._CODES.get(code, code)
        Exception.__init__(self, code)


class ResourceNotFound(AuthorizationError):
    def __init__(self, code: str = "not_found") -> None:
        AccountError.__init__(self, code)


class LockoutError(AuthorizationError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        AccountError.__init__(self, "login_locked")


class NotFoundError(AccountError):
    def __init__(self, code: str = "not_found") -> None:
        super().__init__(code)
