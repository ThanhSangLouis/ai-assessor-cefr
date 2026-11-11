"""What other services may ask the identity service (D043).

Accounts by id or email, how many students there are, whose data may be
used in research (D058: those who accepted the terms). Answers are plain JSON:
an account is a small dict with no password hash and no session.
"""

from __future__ import annotations

from aicefr.platform.rpc import exposed
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import AuthRepository, Role

ACCOUNT_FIELDS = (
    "account_id", "role", "disabled", "email", "full_name", "email_verified",
)  # fmt: skip
FLAGS = ("disabled", "email_verified")


def _account(row) -> dict | None:
    if row is None:
        return None
    return {k: (bool(row[k]) if k in FLAGS else row[k]) for k in ACCOUNT_FIELDS}


class IdentityFacade:
    def __init__(self, auth: AuthRepository, audit: AuditLog) -> None:
        self.auth = auth
        self.audit = audit

    @exposed
    def account(self, account_id: str) -> dict | None:
        return _account(self.auth.get(account_id))

    @exposed
    def delete_account(self, account_id: str) -> bool:
        """Delete the account itself, once its data elsewhere is erased (D101)."""
        row = self.auth.get(account_id)
        if row is None:
            return False
        deleted = self.auth.delete_account(account_id)
        if deleted:
            self.audit.write(account_id, "account.delete", account_id, "by=self")
        return deleted

    @exposed
    def by_email(self, email: str) -> dict | None:
        """The enabled account that signs in with this email, or None."""
        return _account(self.auth.get_by_email(email))

    @exposed
    def display_names(self, account_ids: list[str]) -> dict[str, str]:
        """What a teacher reads for each account: the full name, else the email (D071)."""
        return self.auth.display_names(account_ids)

    @exposed
    def accounts(self, roles: list[str] | None = None, enabled_only: bool = True) -> list[dict]:
        """Accounts of the given roles (every role when none), enabled ones by default."""
        return [
            {k: a[k] for k in ACCOUNT_FIELDS}
            for a in self.auth.list_accounts()
            if (roles is None or a["role"] in roles) and not (enabled_only and a["disabled"])
        ]

    @exposed
    def count_role(self, role: str) -> int:
        """Enabled accounts of one role: the seats a plan counts (D033)."""
        return self.auth.count_role(Role(role))

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.audit.recent(limit)
