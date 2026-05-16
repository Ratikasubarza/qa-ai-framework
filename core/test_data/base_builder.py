"""
PayloadBuilder — base class for all test data builders.

Usage pattern:
    @dataclass
    class RegisterPayload(PayloadBuilder):
        fullname: str = "Test User"
        email: str = field(default_factory=lambda: f"qa+{int(time.time())}@test.com")

    # In tests:
    RegisterPayload().as_dict()                          # default valid payload
    RegisterPayload().without("fullname")                # missing required field
    RegisterPayload().with_field(email="bad@")           # override one field
    RegisterPayload(fullname="Edge" * 100).as_dict()     # explicit override
"""
from dataclasses import dataclass, asdict, fields
from typing import Any


@dataclass
class PayloadBuilder:

    def as_dict(self) -> dict:
        """Return all fields as a plain dict."""
        return asdict(self)

    def without(self, *keys: str) -> dict:
        """Return dict with the given keys removed — for missing-field negative tests."""
        d = self.as_dict()
        for k in keys:
            d.pop(k, None)
        return d

    def with_field(self, **overrides: Any) -> dict:
        """Return dict with specific fields overridden — for boundary/negative tests."""
        d = self.as_dict()
        d.update(overrides)
        return d

    def copy(self, **overrides: Any) -> "PayloadBuilder":
        """Return a new instance of the same class with overrides applied."""
        current = asdict(self)
        current.update(overrides)
        return self.__class__(**{
            f.name: current[f.name]
            for f in fields(self)
            if f.name in current
        })

    def field_names(self) -> list[str]:
        return [f.name for f in fields(self)]
