"""What other services may ask the identity service (D043).

Accounts by id or pseudonym, how many students there are, who allows research
use, a person's consent. Answers are plain JSON: an account is a small dict
with no password hash and no session; a consent is the signature's fields.
"""

from __future__ import annotations

from dataclasses import asdict

from aicefr.platform.rpc import exposed
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import AuthRepository, Role
from aicefr.storage.consent_repository import Consent, ConsentRepository

ACCOUNT_FIELDS = ("account_id", "pseudonym", "role", "disabled")


def _account(row) -> dict | None:
    if row is None:
        return None
    return {k: (bool(row[k]) if k == "disabled" else row[k]) for k in ACCOUNT_FIELDS}


def consent_from(data: dict | None) -> Consent | None:
    """A consent as another service receives it, back into the dataclass."""
    return Consent(**data) if data else None


class IdentityFacade:
    def __init__(self, auth: AuthRepository, consents: ConsentRepository, audit: AuditLog) -> None:
        self.auth = auth
        self.consents = consents
        self.audit = audit

    @exposed
    def account(self, account_id: str) -> dict | None:
        return _account(self.auth.get(account_id))

    @exposed
    def by_pseudonym(self, pseudonym: str) -> dict | None:
        return _account(self.auth.get_by_pseudonym(pseudonym))

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
        """Accounts whose standing consent allows research use."""
        return sorted(self.consents.accounts_allowing_research())

    @exposed
    def consent(self, account_id: str) -> dict | None:
        c = self.consents.current(account_id)
        return asdict(c) if c else None

    @exposed
    def consent_history(self, account_id: str) -> list[dict]:
        return [asdict(c) for c in self.consents.history(account_id)]

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.audit.recent(limit)
