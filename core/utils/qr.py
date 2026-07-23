from django.utils import timezone
from django.utils.dateparse import parse_datetime


def validate_qr_session(request, token):
    """
    Validates:
    - Session bound to correct table token
    - Session not expired
    """

    session_token = request.session.get("table_token")
    expires_at = request.session.get("qr_expires_at")

    # ✅ Must match token
    if not session_token or session_token != token:
        return False

    # ✅ Must have expiration
    if not expires_at:
        return False

    expires_at = parse_datetime(expires_at)

    # ✅ Expired session
    if not expires_at or timezone.now() > expires_at:
        return False

    return True