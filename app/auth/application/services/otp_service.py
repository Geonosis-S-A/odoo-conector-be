from datetime import datetime, timedelta
import random
import string

from app.auth.domain.models import NewOTPCode
from datetime import timezone


class OTPService:
    def _generate_code(self) -> str:
        return "".join(random.choices(string.digits, k=6))

    def create_otp(self, user_id: int) -> NewOTPCode:
        otp_code = self._generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        return NewOTPCode(user_id=user_id, code=otp_code, expires_at=expires_at)
