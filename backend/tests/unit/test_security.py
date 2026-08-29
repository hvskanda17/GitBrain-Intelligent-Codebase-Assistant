from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

import app.core.security as security_module
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_hash_is_salted_differently_each_time():
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2  # different salts -> different hashes for the same input
    assert verify_password("same-password", h1)
    assert verify_password("same-password", h2)


def test_verify_password_rejects_malformed_hash():
    assert not verify_password("anything", "not-a-real-bcrypt-hash")


def test_access_token_round_trips_subject_and_role():
    user_id = uuid4()
    token = create_access_token(user_id, role="developer")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "developer"


def test_refresh_token_has_unique_jti():
    user_id = uuid4()
    payload_a = decode_token(create_refresh_token(user_id), expected_type="refresh")
    payload_b = decode_token(create_refresh_token(user_id), expected_type="refresh")
    assert payload_a["jti"] != payload_b["jti"]


def test_decode_rejects_wrong_token_type():
    access = create_access_token(uuid4(), role="developer")
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(access, expected_type="refresh")


def test_decode_rejects_expired_token():
    # Force an already-expired token instead of sleeping in the test.
    token = security_module._create_token(uuid4(), "access", timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token, expected_type="access")
