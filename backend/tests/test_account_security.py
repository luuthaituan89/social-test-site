from app.models import User
from app.services.account_security import (consume_recovery_code, make_recovery_codes,
                                           token_hash, totp_code, verify_totp)


def test_token_hash_does_not_store_raw_token():
    raw = "a-high-entropy-refresh-token"
    assert token_hash(raw) != raw
    assert token_hash(raw) == token_hash(raw)


def test_totp_accepts_current_code_and_rejects_wrong_code():
    secret = "JBSWY3DPEHPK3PXP"
    assert verify_totp(secret, totp_code(secret))
    assert not verify_totp(secret, "000000") or totp_code(secret) == "000000"


def test_recovery_codes_are_single_use():
    codes, stored = make_recovery_codes()
    user = User(email="security@example.com", username="security", name="Security",
                password_hash="unused", recovery_codes=stored)
    assert consume_recovery_code(user, codes[0])
    assert not consume_recovery_code(user, codes[0])
