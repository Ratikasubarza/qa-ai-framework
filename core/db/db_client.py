"""
Database Client — MySQL connection helper untuk test data retrieval.
Hanya untuk READ dan test setup operations.
"""
import os
import pymysql
import structlog
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

logger = structlog.get_logger(__name__)


class DBClient:
    def __init__(self):
        self._conn = None

    def connect(self):
        self._conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            ssl={"ssl": True},
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        logger.info("db_connected", host=os.getenv("DB_HOST"))
        return self

    def disconnect(self):
        if self._conn:
            self._conn.close()
            logger.info("db_disconnected")

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.disconnect()

    def get_user_by_email(self, email: str) -> dict | None:
        """Get user data by email — returns UUID id."""
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT
                    BIN_TO_UUID(id) as id,
                    email,
                    status,
                    verified_at,
                    approved_at,
                    onboarding_completed_at,
                    created_at
                FROM users
                WHERE email = %s
                LIMIT 1
            """, (email,))
            return cur.fetchone()

    def get_latest_pending_user(self) -> dict | None:
        """Get most recently registered PENDING user."""
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT
                    BIN_TO_UUID(id) as id,
                    email,
                    status,
                    verified_at,
                    created_at
                FROM users
                WHERE status = 'PENDING'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            return cur.fetchone()

    def get_user_status(self, email: str) -> str | None:
        """Get current status of user by email."""
        user = self.get_user_by_email(email)
        return user.get("status") if user else None

    def get_latest_user_verification(self, email: str) -> dict | None:
        """Get the latest verification code for a synthetic user's email flow."""
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT
                    uv.unique_code,
                    uv.expired_at,
                    uv.created_at
                FROM user_verifications uv
                INNER JOIN users u ON uv.user_id = u.id
                WHERE u.email = %s
                ORDER BY uv.created_at DESC
                LIMIT 1
            """, (email,))
            return cur.fetchone()

    def expire_user_verification_code(self, unique_code: str) -> bool:
        """Force a synthetic verification code to be expired for negative tests."""
        with self._conn.cursor() as cur:
            cur.execute("""
                UPDATE user_verifications
                SET expired_at = DATE_SUB(NOW(), INTERVAL 1 MINUTE)
                WHERE unique_code = %s
            """, (unique_code,))
            affected = cur.rowcount
            logger.info("db_verification_expired", affected=affected)
            return affected > 0

    def set_verified(self, email: str) -> bool:
        """Simulate email verification — set verified_at timestamp."""
        with self._conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET verified_at = NOW(),
                    updated_at = NOW()
                WHERE email = %s
                AND verified_at IS NULL
            """, (email,))
            affected = cur.rowcount
            logger.info("db_verified_set", email=email, affected=affected)
            return affected > 0

    def update_user_status(self, email: str, status: str) -> bool:
        """Update user status directly in DB — for testing only."""
        with self._conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET status = %s,
                    updated_at = NOW()
                WHERE email = %s
            """, (status, email))
            affected = cur.rowcount
            logger.info("db_status_updated", email=email, status=status)
            return affected > 0
    def set_password(self, email: str, plain_password: str) -> bool:
        """
        Set bcrypt hashed password for user — for testing only.
        Simulates system-generated password after admin approve.
        """
        import bcrypt
        hashed = bcrypt.hashpw(
            plain_password.encode('utf-8'),
            bcrypt.gensalt(rounds=10)
        ).decode('utf-8')

        with self._conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET password = %s,
                    updated_at = NOW()
                WHERE email = %s
            """, (hashed, email))
            affected = cur.rowcount
            logger.info("db_password_set", email=email, affected=affected)
            return affected > 0

    def setup_test_user_for_login(self, email: str, password: str) -> bool:
        """
        Full test setup: verify + approve + set password.
        Simulates complete admin approval flow for testing.
        """
        # Step 1: Set verified
        self.set_verified(email)

        # Step 2: Approve
        with self._conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET status = 'APPROVED',
                    approved_at = NOW(),
                    updated_at = NOW()
                WHERE email = %s
            """, (email,))

        # Step 3: Set known password
        self.set_password(email, password)

        logger.info("test_user_setup_complete", email=email)
        return True
    def get_password_hash(self, email: str) -> str | None:
        """Get current password hash — to verify system set a new one after approve."""
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT password, updated_at
                FROM users WHERE email = %s
            """, (email,))
            row = cur.fetchone()
            return row if row else None

    def setup_approved_user(self, email: str, test_password: str) -> bool:
        """
        Full E2E test setup:
        1. set_verified — simulate email click
        2. Approve via CMS API (caller must do this)
        3. Override password with known test password

        Call order:
            db.set_verified(email)
            → CMS API approve
            → db.setup_approved_user(email, test_password)
        """
        return self.set_password(email, test_password)
