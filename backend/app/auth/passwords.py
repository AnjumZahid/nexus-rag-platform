## New file: `backend/app/auth/passwords.py`


from pwdlib import PasswordHash


class PasswordService:
    """Hash and verify account passwords."""

    def __init__(self) -> None:
        self.password_hash = PasswordHash.recommended()

    def hash_password(
        self,
        password: str,
    ) -> str:
        if len(password) < 12:
            raise ValueError(
                "Password must contain at least "
                "12 characters."
            )

        if len(password) > 128:
            raise ValueError(
                "Password cannot exceed 128 characters."
            )

        return self.password_hash.hash(password)

    def verify_password(
        self,
        *,
        password: str,
        password_hash: str,
    ) -> bool:
        try:
            return self.password_hash.verify(
                password,
                password_hash,
            )
        except Exception:
            return False


password_service = PasswordService()

