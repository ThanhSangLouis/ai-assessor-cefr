"""Signed, organization-bound licenses and shared entitlement writes."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from aicefr.auth.contracts import ActorRole
from aicefr.billing.errors import BillingError
from aicefr.billing.plans import PLANS
from aicefr.billing.secrets import KeyRing
from aicefr.storage.billing import ensure_organization_binding
from aicefr.storage.sqlite import SQLiteStore

LICENSE_VERSION = 1
LICENSE_ORGANIZATION = "local-demo"
_IDEM_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")
FEATURE_ALLOWLIST = frozenset(
    {
        "learning",
        "practice",
        "personal_data",
        "lesson_authoring",
        "class_insights",
        "blind_rating",
        "advanced_reports",
        "bulk_operations",
    }
)
_LICENSE_FIELDS = frozenset(
    {
        "version",
        "organization",
        "plan_code",
        "features",
        "student_limit",
        "expires_at",
        "issued_at",
        "nonce",
        "key_version",
    }
)


class LicenseError(BillingError):
    """Safe error; never includes signed content or key material."""

    def __init__(self, code: str = "license_invalid") -> None:
        self.code = code
        status_code = (
            403
            if code == "admin_required"
            else 409
            if code in {"license_nonce_replayed", "idempotency_key_reused"}
            else 500
            if code == "idempotency_record_invalid"
            else 422
        )
        super().__init__(code, status_code)


def _utc(value: datetime | str | None, *, optional: bool = False) -> datetime | None:
    if value is None and optional:
        return None
    try:
        if isinstance(value, str):
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif isinstance(value, datetime):
            result = value
        else:
            raise ValueError
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError
        return result.astimezone(UTC)
    except (ValueError, TypeError, OverflowError) as exc:
        raise LicenseError("license_invalid_time") from exc


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value is not None else None


def _canonical(payload: Mapping[str, Any]) -> bytes:
    try:
        result = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise LicenseError("license_invalid_payload") from exc
    if len(result) > 16_384:
        raise LicenseError("license_payload_too_large")
    return result


def _features(value: Sequence[str] | set[str] | frozenset[str]) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (Sequence, set, frozenset)):
        raise LicenseError("license_invalid_features")
    values = list(value)
    if len(values) > len(FEATURE_ALLOWLIST) or any(
        not isinstance(item, str) or item not in FEATURE_ALLOWLIST for item in values
    ):
        raise LicenseError("license_invalid_features")
    if len(set(values)) != len(values):
        raise LicenseError("license_invalid_features")
    return tuple(sorted(values))


def _safe_artifact(license_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "license_id": license_id,
        "organization": payload["organization"],
        "plan_code": payload["plan_code"],
        "features": list(payload["features"]),
        "student_limit": payload["student_limit"],
        "expires_at": payload["expires_at"],
        "issued_at": payload["issued_at"],
        "key_version": payload["key_version"],
    }


class LicenseService:
    def __init__(
        self,
        auth: Any,
        store: SQLiteStore,
        keyring: KeyRing,
        organization: str = LICENSE_ORGANIZATION,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.auth = auth
        self.store = store
        self.keyring = keyring
        self.clock = clock or (lambda: datetime.now(UTC))
        with self.store.transaction() as db:
            self.organization = ensure_organization_binding(
                db, organization, self.clock().astimezone(UTC)
            )

    def issue(
        self,
        token: str,
        plan_code: str,
        *,
        features: Sequence[str] | set[str] | frozenset[str] | None = None,
        student_limit: int | None = None,
        expires_at: datetime | str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor = self._admin(token)
        now = self.clock().astimezone(UTC)
        issue_key = (
            self._issue_key(actor.actor_id, idempotency_key)
            if idempotency_key is not None
            else None
        )
        request_hash = (
            self._issue_request_hash(plan_code, features, student_limit, expires_at)
            if issue_key is not None
            else None
        )
        replay = (
            self._read_issue_replay(self.store.connection, issue_key, request_hash)
            if issue_key is not None
            else None
        )
        if replay is not None:
            with self.store.transaction() as db:
                self._assert_admin_session(db, token, actor.actor_id, now)
            return replay
        payload = self._build_payload(plan_code, features, student_limit, expires_at)
        signature = self.keyring.sign_license(_canonical(payload))
        license_id = "lic_" + uuid.uuid4().hex
        with self.store.transaction() as db:
            self._assert_admin_session(db, token, actor.actor_id, now)
            if issue_key is not None:
                replay = self._read_issue_replay(db, issue_key, request_hash)
                if replay is not None:
                    return replay
            self._insert_license(db, license_id, actor.actor_id, payload, signature, now)
            self.apply_entitlement(
                db,
                plan_code=payload["plan_code"],
                features=payload["features"],
                student_limit=payload["student_limit"],
                warning_quota=PLANS[plan_code].warning_quota,
                effective_at=payload["issued_at"],
                expires_at=payload["expires_at"],
                grace_until=None,
                source_order=None,
                organization_id=self.organization,
                account_id=actor.actor_id,
            )
            self._audit(db, actor.actor_id, "billing_license_issued", license_id, now)
            self._remember_nonce(db, payload["nonce"], signature, license_id, now)
            if issue_key is not None:
                db.execute(
                    "INSERT INTO runtime_settings(key,payload,revision,version,updated_by,"
                    "updated_at) "
                    "VALUES(?,?,1,'v1','billing-license',?)",
                    (
                        issue_key,
                        json.dumps(
                            {"input_hash": request_hash, "license_id": license_id},
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        now.isoformat(),
                    ),
                )
        return {
            "license": _safe_artifact(license_id, payload),
            "signed_license": {"payload": payload, "signature": signature},
        }

    def install(self, token: str, signed_license: Mapping[str, Any]) -> dict[str, Any]:
        actor = self._admin(token)
        now = self.clock().astimezone(UTC)
        payload, signature = self._validate_signed(signed_license, now=now)
        raw = _canonical(payload)
        if not self.keyring.verify_license(raw, signature):
            raise LicenseError("license_invalid_signature")
        license_id = "lic_" + uuid.uuid4().hex
        with self.store.transaction() as db:
            self._assert_admin_session(db, token, actor.actor_id, now)
            prior = db.execute(
                "SELECT license_id,payload,signature,revoked_at FROM licenses WHERE signature=?",
                (signature,),
            ).fetchone()
            if prior and prior[1] == raw.decode("utf-8") and prior[3] is None:
                return _safe_artifact(str(prior[0]), payload)
            nonce_key = self._nonce_setting_key(payload["nonce"])
            nonce_row = db.execute(
                "SELECT payload FROM runtime_settings WHERE key=?", (nonce_key,)
            ).fetchone()
            if nonce_row:
                remembered = json.loads(nonce_row[0])
                if remembered.get("signature") == signature:
                    return _safe_artifact(str(remembered["license_id"]), payload)
                raise LicenseError("license_nonce_replayed")
            self._insert_license(db, license_id, actor.actor_id, payload, signature, now)
            self.apply_entitlement(
                db,
                plan_code=payload["plan_code"],
                features=payload["features"],
                student_limit=payload["student_limit"],
                warning_quota=PLANS[payload["plan_code"]].warning_quota,
                effective_at=payload["issued_at"],
                expires_at=payload["expires_at"],
                grace_until=None,
                source_order=None,
                organization_id=self.organization,
                account_id=actor.actor_id,
            )
            self._audit(db, actor.actor_id, "billing_license_installed", license_id, now)
            self._remember_nonce(db, payload["nonce"], signature, license_id, now)
        return _safe_artifact(license_id, payload)

    def status(self, token: str) -> dict[str, Any]:
        self._admin(token)
        row = self.store.connection.execute(
            "SELECT plan_code,features_json,student_limit,effective_at,expires_at,grace_until "
            "FROM entitlements WHERE effective_at<=? "
            "ORDER BY effective_at DESC,created_at DESC LIMIT 1",
            (self.clock().astimezone(UTC).isoformat(),),
        ).fetchone()
        license_count = self.store.connection.execute(
            "SELECT COUNT(*) FROM licenses WHERE revoked_at IS NULL"
        ).fetchone()[0]
        if row is None:
            return {"organization": self.organization, "license_count": int(license_count)}
        try:
            features = json.loads(row[1])
        except (TypeError, json.JSONDecodeError):
            features = []
        return {
            "organization": self.organization,
            "license_count": int(license_count),
            "plan_code": str(row[0]),
            "features": features,
            "student_limit": int(row[2]),
            "effective_at": str(row[3]),
            "expires_at": row[4],
            "grace_until": row[5],
        }

    def apply_entitlement(
        self,
        connection: sqlite3.Connection,
        *,
        plan_code: str,
        effective_at: datetime | str,
        expires_at: datetime | str | None,
        grace_until: datetime | str | None,
        source_order: str | None,
        organization_id: str,
        account_id: str,
        features: Sequence[str] | set[str] | frozenset[str] | None = None,
        student_limit: int | None = None,
        warning_quota: int | None = None,
    ) -> str:
        """Insert entitlement and audit rows into a caller-owned transaction."""
        if organization_id != self.organization or plan_code not in PLANS:
            raise LicenseError("license_invalid")
        plan = PLANS[plan_code]
        selected_features = _features(features if features is not None else plan.features)
        if not set(selected_features).issubset(plan.features):
            raise LicenseError("license_invalid_features")
        limit = plan.student_limit if student_limit is None else student_limit
        quota = plan.warning_quota if warning_quota is None else warning_quota
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (limit, quota)
        ):
            raise LicenseError("license_invalid_limits")
        if limit > plan.student_limit or quota > plan.warning_quota:
            raise LicenseError("license_invalid_limits")
        effective = _utc(effective_at)
        expires = _utc(expires_at, optional=True)
        grace = _utc(grace_until, optional=True)
        if expires is not None and expires <= effective:
            raise LicenseError("license_invalid_time")
        if grace is not None and (expires is None or grace < expires):
            raise LicenseError("license_invalid_time")
        if not isinstance(account_id, str) or not account_id or len(account_id) > 200:
            raise LicenseError("license_invalid")
        if source_order is not None and (
            not isinstance(source_order, str) or len(source_order) > 200
        ):
            raise LicenseError("license_invalid")
        entitlement_id = "ent_" + uuid.uuid4().hex
        now = self.clock().astimezone(UTC)
        connection.execute(
            "INSERT INTO entitlements(entitlement_id,account_id,plan_code,features_json,"
            "student_limit,warning_quota,effective_at,expires_at,grace_until,source_order,"
            "created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                entitlement_id,
                account_id,
                plan_code,
                json.dumps(list(selected_features), separators=(",", ":")),
                limit,
                quota,
                effective.isoformat(),
                _iso(expires),
                _iso(grace),
                source_order,
                now.isoformat(),
            ),
        )
        self._audit(connection, account_id, "billing_entitlement_applied", entitlement_id, now)
        return entitlement_id

    def _build_payload(
        self,
        plan_code: str,
        features: Sequence[str] | set[str] | frozenset[str] | None,
        student_limit: int | None,
        expires_at: datetime | str | None,
    ) -> dict[str, Any]:
        if not isinstance(plan_code, str) or plan_code not in PLANS:
            raise LicenseError("license_invalid_plan")
        plan = PLANS[plan_code]
        chosen = _features(features if features is not None else plan.features)
        limit = plan.student_limit if student_limit is None else student_limit
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 0
            or limit > plan.student_limit
        ):
            raise LicenseError("license_invalid_limits")
        if not set(chosen).issubset(plan.features):
            raise LicenseError("license_invalid_features")
        now = self.clock().astimezone(UTC)
        expires = _utc(expires_at)
        if expires <= now:
            raise LicenseError("license_expired")
        if expires > now + timedelta(days=3650):
            raise LicenseError("license_invalid_time")
        return {
            "version": LICENSE_VERSION,
            "organization": self.organization,
            "plan_code": plan_code,
            "features": list(chosen),
            "student_limit": limit,
            "expires_at": _iso(expires),
            "issued_at": now.isoformat(),
            "nonce": secrets.token_urlsafe(24),
            "key_version": str(self.keyring.version),
        }

    def _validate_signed(
        self, value: Mapping[str, Any], *, now: datetime
    ) -> tuple[dict[str, Any], str]:
        if not isinstance(value, Mapping) or set(value) != {"payload", "signature"}:
            raise LicenseError("license_invalid_payload")
        payload = value["payload"]
        signature = value["signature"]
        if not isinstance(payload, Mapping) or set(payload) != _LICENSE_FIELDS:
            raise LicenseError("license_invalid_payload")
        if not isinstance(signature, str) or len(signature) != 64:
            raise LicenseError("license_invalid_signature")
        if payload.get("version") != LICENSE_VERSION or payload.get("key_version") != str(
            self.keyring.version
        ):
            raise LicenseError("license_wrong_version")
        if payload.get("organization") != self.organization:
            raise LicenseError("license_wrong_organization")
        plan_code = payload.get("plan_code")
        if not isinstance(plan_code, str) or plan_code not in PLANS:
            raise LicenseError("license_invalid_plan")
        chosen = _features(payload.get("features"))
        plan = PLANS[plan_code]
        limit = payload.get("student_limit")
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 0
            or limit > plan.student_limit
            or not set(chosen).issubset(plan.features)
        ):
            raise LicenseError("license_invalid_limits")
        expires = _utc(payload.get("expires_at"))
        issued = _utc(payload.get("issued_at"))
        nonce = payload.get("nonce")
        if not isinstance(nonce, str) or not 20 <= len(nonce) <= 128:
            raise LicenseError("license_invalid_nonce")
        if issued > now + timedelta(minutes=5):
            raise LicenseError("license_invalid_time")
        if expires <= now:
            raise LicenseError("license_expired")
        if expires <= issued or expires > issued + timedelta(days=3650):
            raise LicenseError("license_invalid_time")
        normalized = {
            "version": LICENSE_VERSION,
            "organization": self.organization,
            "plan_code": plan_code,
            "features": list(chosen),
            "student_limit": limit,
            "expires_at": _iso(expires),
            "issued_at": _iso(issued),
            "nonce": nonce,
            "key_version": str(self.keyring.version),
        }
        if _canonical(payload) != _canonical(normalized):
            raise LicenseError("license_invalid_payload")
        return normalized, signature.lower()

    def _admin(self, token: str) -> Any:
        try:
            return self.auth.resolve(token, allowed_roles=frozenset({ActorRole.ADMIN}))
        except Exception as exc:
            raise LicenseError("admin_required") from exc

    @staticmethod
    def _assert_admin_session(
        db: sqlite3.Connection, token: str, actor_id: str, now: datetime
    ) -> None:
        try:
            digest = hashlib.sha256(token.encode("ascii", "strict")).hexdigest()
        except (AttributeError, UnicodeError) as exc:
            raise LicenseError("admin_required") from exc
        row = db.execute(
            "SELECT s.actor_id,s.role,s.idle_expires_at,s.absolute_expires_at,a.role,a.disabled "
            "FROM sessions s JOIN accounts a ON a.actor_id=s.actor_id WHERE s.token_digest=?",
            (digest,),
        ).fetchone()
        if (
            row is None
            or row[0] != actor_id
            or row[1] != "admin"
            or row[4] != "admin"
            or bool(row[5])
        ):
            raise LicenseError("admin_required")
        try:
            idle_expiry = datetime.fromisoformat(row[2]).astimezone(UTC)
            absolute_expiry = datetime.fromisoformat(row[3]).astimezone(UTC)
        except (TypeError, ValueError) as exc:
            raise LicenseError("admin_required") from exc
        if now >= idle_expiry or now >= absolute_expiry:
            raise LicenseError("admin_required")

    @staticmethod
    def _insert_license(
        db: sqlite3.Connection,
        license_id: str,
        account_id: str,
        payload: Mapping[str, Any],
        signature: str,
        now: datetime,
    ) -> None:
        db.execute(
            "INSERT INTO licenses(license_id,account_id,key_version,payload,signature,"
            "expires_at,created_at,revoked_at) "
            "VALUES(?,?,?,?,?,?,?,NULL)",
            (
                license_id,
                account_id,
                str(payload["key_version"]),
                _canonical(payload).decode("utf-8"),
                signature,
                payload["expires_at"],
                now.isoformat(),
            ),
        )

    def _remember_nonce(
        self,
        db: sqlite3.Connection,
        nonce: str,
        signature: str,
        license_id: str,
        now: datetime,
    ) -> None:
        key = self._nonce_setting_key(nonce)
        payload = json.dumps(
            {"signature": signature, "license_id": license_id},
            sort_keys=True,
            separators=(",", ":"),
        )
        db.execute(
            "INSERT INTO runtime_settings(key,payload,revision,version,updated_by,updated_at) "
            "VALUES(?,?,1,'v1','billing-license',?)",
            (key, payload, now.isoformat()),
        )

    @staticmethod
    def _nonce_setting_key(nonce: str) -> str:
        return "billing.license.nonce." + hashlib.sha256(nonce.encode("utf-8")).hexdigest()

    @staticmethod
    def _issue_key(actor_id: str, idempotency_key: str) -> str:
        if (
            not isinstance(idempotency_key, str)
            or not 8 <= len(idempotency_key) <= 128
            or any(char not in _IDEM_CHARS for char in idempotency_key)
        ):
            raise LicenseError("invalid_idempotency_key")
        digest = hashlib.sha256(
            b"aicefr:license-issue-idempotency:v1:"
            + actor_id.encode("utf-8")
            + b"\0"
            + idempotency_key.encode("ascii")
        ).hexdigest()
        return "billing.license.issue." + digest

    @staticmethod
    def _issue_request_hash(
        plan_code: str,
        features: Sequence[str] | set[str] | frozenset[str] | None,
        student_limit: int | None,
        expires_at: datetime | str | None,
    ) -> str:
        if not isinstance(plan_code, str) or plan_code not in PLANS:
            raise LicenseError("license_invalid_plan")
        plan = PLANS[plan_code]
        selected = _features(features if features is not None else plan.features)
        if not set(selected).issubset(plan.features):
            raise LicenseError("license_invalid_features")
        limit = plan.student_limit if student_limit is None else student_limit
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 0
            or limit > plan.student_limit
        ):
            raise LicenseError("license_invalid_limits")
        expires = _utc(expires_at)
        request = {
            "plan_code": plan_code,
            "features": list(selected),
            "student_limit": limit,
            "expires_at": _iso(expires),
        }
        return hashlib.sha256(_canonical(request)).hexdigest()

    @staticmethod
    def _read_issue_replay(
        db: sqlite3.Connection, issue_key: str, request_hash: str | None
    ) -> dict[str, Any] | None:
        row = db.execute(
            "SELECT payload FROM runtime_settings WHERE key=?", (issue_key,)
        ).fetchone()
        if row is None:
            return None
        try:
            remembered = json.loads(row[0])
            if remembered.get("input_hash") != request_hash:
                raise LicenseError("idempotency_key_reused")
            stored = db.execute(
                "SELECT payload,signature,revoked_at FROM licenses WHERE license_id=?",
                (remembered["license_id"],),
            ).fetchone()
            if stored is None or stored[2] is not None:
                raise LicenseError("idempotency_record_invalid")
            prior_payload = json.loads(stored[0])
            return {
                "license": _safe_artifact(remembered["license_id"], prior_payload),
                "signed_license": {"payload": prior_payload, "signature": str(stored[1])},
            }
        except LicenseError:
            raise
        except (ValueError, KeyError, TypeError) as exc:
            raise LicenseError("idempotency_record_invalid") from exc

    @staticmethod
    def _audit(
        db: sqlite3.Connection, actor_id: str, action: str, object_id: str, now: datetime
    ) -> None:
        db.execute(
            "INSERT INTO audit(event_id,actor_id,action,object_id,recorded_at,reason) "
            "VALUES(?,?,?,?,?,NULL)",
            (uuid.uuid4().hex, actor_id, action, object_id, now.isoformat()),
        )
