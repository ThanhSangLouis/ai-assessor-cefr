"""Safe application errors for billing callers and APIs."""


class BillingError(Exception):
    def __init__(self, code: str, status_code: int = 422) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)
