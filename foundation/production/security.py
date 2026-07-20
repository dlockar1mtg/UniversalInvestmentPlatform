"""Authentication, authorization, secret references, and redaction."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import hmac
from types import MappingProxyType
from typing import Mapping


class Permission(str, Enum):
    RUN_READ = "RUN_READ"
    RUN_SUBMIT = "RUN_SUBMIT"
    OPERATIONS_ADMIN = "OPERATIONS_ADMIN"


_ROLE_PERMISSIONS = {
    "viewer": frozenset({Permission.RUN_READ}),
    "operator": frozenset({Permission.RUN_READ, Permission.RUN_SUBMIT}),
    "admin": frozenset(Permission),
}


@dataclass(frozen=True)
class Principal:
    principal_id: str
    roles: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.principal_id.strip() or not self.roles:
            raise ValueError("principal identity and roles are required")
        unknown = set(self.roles) - set(_ROLE_PERMISSIONS)
        if unknown:
            raise ValueError(f"unknown roles: {', '.join(sorted(unknown))}")
        object.__setattr__(self, "roles", tuple(sorted(set(self.roles))))

    def permits(self, permission: Permission) -> bool:
        return any(permission in _ROLE_PERMISSIONS[role] for role in self.roles)


@dataclass(frozen=True)
class SecretReference:
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip() or any(character.isspace() for character in self.name):
            raise ValueError("secret reference name must be nonblank and contain no whitespace")

    def resolve(self, source: Mapping[str, str]) -> str:
        value = source.get(self.name, "")
        if not value:
            raise ValueError(f"required secret reference is unavailable: {self.name}")
        return value


class APIKeyAuthenticator:
    """Authenticate keys by constant-time comparison against stored SHA-256 digests."""

    def __init__(self, principals: Mapping[str, tuple[str, ...]], credential_hashes: Mapping[str, str]):
        if set(principals) != set(credential_hashes):
            raise ValueError("every principal must have exactly one credential hash")
        self._principals = MappingProxyType({key: Principal(key, principals[key]) for key in sorted(principals)})
        self._hashes = MappingProxyType(dict(credential_hashes))

    @staticmethod
    def hash_credential(credential: str) -> str:
        if not credential:
            raise ValueError("credential must not be empty")
        return sha256(credential.encode()).hexdigest()

    def authenticate(self, credential: str | None) -> Principal | None:
        if not credential:
            return None
        supplied = self.hash_credential(credential)
        for principal_id in sorted(self._hashes):
            if hmac.compare_digest(supplied, self._hashes[principal_id]):
                return self._principals[principal_id]
        return None


_SENSITIVE_PARTS = ("authorization", "credential", "password", "secret", "token", "api_key")


def redact(values: Mapping[str, object]) -> Mapping[str, object]:
    result = {}
    for key in sorted(values, key=str):
        normalized = str(key).lower()
        value = values[key]
        if any(part in normalized for part in _SENSITIVE_PARTS):
            result[str(key)] = "[REDACTED]"
        elif isinstance(value, Mapping):
            result[str(key)] = dict(redact(value))
        else:
            result[str(key)] = value
    return MappingProxyType(result)
