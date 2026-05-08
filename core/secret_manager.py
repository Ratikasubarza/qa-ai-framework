"""
Secret Manager — single access point for all credentials.
Development: reads from .env via Settings.
Production:  extend get() to pull from Vault/AWS Secrets Manager.
"""
from config.settings import settings


class SecretManager:
    def get(self, key: str) -> str:
        """
        Returns the secret value for the given key.
        Key maps directly to a Settings field name (snake_case).
        """
        value = getattr(settings, key.lower(), None)
        if value is None:
            raise KeyError(
                f"Secret '{key}' not found. "
                f"Check your .env file and config/settings.py."
            )
        return value


secret_manager = SecretManager()
