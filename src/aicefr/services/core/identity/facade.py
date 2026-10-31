"""What other services may ask the identity service (D043).

Accounts by id or pseudonym, how many students there are, whose data may be
used in research (D058: those who accepted the terms). Answers are plain JSON:
an account is a small dict with no password hash and no session.
"""

from __future__ import annotations

from aicefr.platform.rpc import exposed
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import AuthRepository, Role

ACCOUNT_FIELDS = ("account_id", "pseudonym", "role", "disabled", "email", "full_name")


def _account(row) -> dict | None:
    if row is None:
        return None
    return {k: (bool(row[k]) if k == "disabled" else row[k]) for k in ACCOUNT_FIELDS}


class IdentityFacade:
    def __init__(self, auth: AuthRepository, audit: AuditLog) -> None:
        self.auth = auth
        self.audit = audit

    @exposed
    def account(self, account_id: str) -> dict | None:
        return _account(self.auth.get(account_id))

    @exposed
    def by_pseudonym(self, pseudonym: str) -> dict | None:
        return _account(self.auth.get_by_pseudonym(pseudonym))

    @exposed
    def by_sign_in_name(self, identifier: str) -> dict | None:
        """The account an email (or, before D071, a pseudonym) names, or None."""
        return _account(self.auth.by_sign_in_name(identifier))

    @exposed
    def display_names(self, account_ids: list[str]) -> dict[str, str]:
        """What a teacher reads for each account: the full name, else the pseudonym (D071)."""
        return self.auth.display_names(account_ids)

    @exposed
    def pseudonyms(self, account_ids: list[str]) -> dict[str, str]:
        """Pseudonym of each account id, for screens that list other people's work."""
        return self.auth.pseudonyms(account_ids)

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
    def research_allowed(self) -> list[str]:
        """Accounts whose data research may use: every account still switched on (D064)."""
        return sorted(self.auth.active_account_ids())

    @exposed
    def seen_at(self, account_id: str, marker: str) -> str | None:
        """When the owner last looked at `marker` (D028): the account keeps it (D060)."""
        return self.auth.seen_at(account_id, marker)

    @exposed
    def mark_seen(self, account_id: str, marker: str) -> str:
        return self.auth.mark_seen(account_id, marker)

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.audit.recent(limit)
