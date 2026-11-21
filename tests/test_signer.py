"""
Tests for the Mission Control request signer (mc-req-v2).

Run with: pytest tests/test_signer.py -v
"""

import hashlib
import sys
from pathlib import Path

import pytest

# Add signer to path
sys.path.insert(0, str(Path(__file__).parent.parent / "signer"))

from sign_mc_request import (
    base64_decode,
    base64_encode,
    base64url_decode,
    base64url_encode,
    generate_keypair,
    sign_request,
    verify_signature,
)


class TestBase64Encoding:
    """Test base64 and base64url encoding/decoding."""

    def test_base64_encode_decode_roundtrip(self):
        """Test that base64 encode/decode round-trips correctly."""
        data = b"Hello, World!"
        encoded = base64_encode(data)
        decoded = base64_decode(encoded)
        assert decoded == data

    def test_base64url_encode_decode_roundtrip(self):
        """Test that base64url encode/decode round-trips correctly."""
        data = b"Hello, World!"
        encoded = base64url_encode(data)
        decoded = base64url_decode(encoded)
        assert decoded == data

    def test_base64url_no_padding(self):
        """Test that base64url encoding removes padding."""
        # 1 byte → 2 chars with padding (==)
        data = b"A"
        encoded = base64url_encode(data)
        assert "=" not in encoded
        assert encoded == "QQ"

        # 2 bytes → 3 chars with padding (=)
        data = b"AB"
        encoded = base64url_encode(data)
        assert "=" not in encoded
        assert encoded == "QUI"

    def test_base64_decode_handles_missing_padding(self):
        """Test that base64_decode adds padding if missing."""
        # "QQ" is base64url for "A" without padding
        decoded = base64_decode("QQ")
        assert decoded == b"A"

    def test_base64url_decode_handles_missing_padding(self):
        """Test that base64url_decode adds padding if missing."""
        # "QQ" is base64url for "A" without padding
        decoded = base64url_decode("QQ")
        assert decoded == b"A"


class TestKeypairGeneration:
    """Test Ed25519 keypair generation."""

    def test_generate_keypair_produces_valid_keys(self):
        """Test that generate_keypair produces valid Ed25519 keys."""
        private_key, public_key = generate_keypair()

        # Keys should be base64 strings
        assert isinstance(private_key, str)
        assert isinstance(public_key, str)

        # Decode and check lengths
        private_bytes = base64_decode(private_key)
        public_bytes = base64_decode(public_key)

        # Ed25519 keys are 32 bytes
        assert len(private_bytes) == 32
        assert len(public_bytes) == 32

    def test_generate_keypair_produces_different_keys(self):
        """Test that each call produces different keys."""
        private1, public1 = generate_keypair()
        private2, public2 = generate_keypair()

        assert private1 != private2
        assert public1 != public2


class TestRequestSigning:
    """Test request signing with Ed25519."""

    def test_sign_request_produces_valid_headers(self):
        """Test that sign_request produces all required headers."""
        private_key, public_key = generate_keypair()
        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

        headers = sign_request(
            agent_id="test-agent",
            private_key_b64=private_key,
            body=body,
        )

        # Check required headers are present
        assert "X-MC-Agent" in headers
        assert "X-MC-Timestamp" in headers
        assert "X-MC-Nonce" in headers
        assert "X-MC-Signature" in headers
        assert "Content-Type" in headers

        # Check header values
        assert headers["X-MC-Agent"] == "test-agent"
        assert headers["Content-Type"] == "application/json"

        # Timestamp should be ISO 8601 with 'Z' suffix
        assert headers["X-MC-Timestamp"].endswith("Z")
        assert "T" in headers["X-MC-Timestamp"]

        # Nonce should be base64url (no padding)
        assert "=" not in headers["X-MC-Nonce"]
        assert len(headers["X-MC-Nonce"]) >= 32

        # Signature should be base64url (no padding)
        assert "=" not in headers["X-MC-Signature"]

    def test_sign_request_with_custom_timestamp_and_nonce(self):
        """Test that sign_request uses provided timestamp and nonce."""
        private_key, _ = generate_keypair()
        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
        timestamp = "2026-11-21T12:00:00.000Z"
        nonce = "custom-nonce-abcd1234567890ef"

        headers = sign_request(
            agent_id="test-agent",
            private_key_b64=private_key,
            body=body,
            timestamp=timestamp,
            nonce=nonce,
        )

        assert headers["X-MC-Timestamp"] == timestamp
        assert headers["X-MC-Nonce"] == nonce

    def test_sign_request_with_custom_audience(self):
        """Test that sign_request uses custom audience in signature."""
        private_key, public_key = generate_keypair()
        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

        headers = sign_request(
            agent_id="test-agent",
            private_key_b64=private_key,
            body=body,
            audience="https://mc.test",
            timestamp="2026-11-21T12:00:00.000Z",
            nonce="test-nonce-12345678",
        )

        # Reconstruct signing text with custom audience
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        signing_text = (
            f"mc-req-v2\n"
            f"https://mc.test\n"
            f"POST\n"
            f"/mcp\n"
            f"test-agent\n"
            f"2026-11-21T12:00:00.000Z\n"
            f"test-nonce-12345678\n"
            f"{body_hash}\n"
        )

        # Signature should verify
        assert verify_signature(public_key, headers["X-MC-Signature"], signing_text)


class TestSignatureVerification:
    """Test signature verification."""

    def test_verify_signature_with_valid_signature(self):
        """Test that verify_signature accepts valid signatures."""
        private_key, public_key = generate_keypair()
        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

        headers = sign_request(
            agent_id="test-agent",
            private_key_b64=private_key,
            body=body,
            timestamp="2026-11-21T12:00:00.000Z",
            nonce="test-nonce-12345678",
        )

        # Reconstruct signing text
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        signing_text = (
            f"mc-req-v2\n"
            f"https://api.mc.hugeai.co\n"
            f"POST\n"
            f"/mcp\n"
            f"test-agent\n"
            f"2026-11-21T12:00:00.000Z\n"
            f"test-nonce-12345678\n"
            f"{body_hash}\n"
        )

        # Verify signature
        assert verify_signature(public_key, headers["X-MC-Signature"], signing_text)

    def test_verify_signature_with_wrong_key(self):
        """Test that verify_signature rejects signatures with wrong key."""
        private_key1, public_key1 = generate_keypair()
        private_key2, public_key2 = generate_keypair()
        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

        headers = sign_request(
            agent_id="test-agent",
            private_key_b64=private_key1,
            body=body,
            timestamp="2026-11-21T12:00:00.000Z",
            nonce="test-nonce-12345678",
        )

        # Reconstruct signing text
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        signing_text = (
            f"mc-req-v2\n"
            f"https://api.mc.hugeai.co\n"
            f"POST\n"
            f"/mcp\n"
            f"test-agent\n"
            f"2026-11-21T12:00:00.000Z\n"
            f"test-nonce-12345678\n"
            f"{body_hash}\n"
        )

        # Verify with wrong key should fail
        assert not verify_signature(
            public_key2, headers["X-MC-Signature"], signing_text
        )

    def test_verify_signature_with_tampered_signing_text(self):
        """Test that verify_signature rejects tampered signing text."""
        private_key, public_key = generate_keypair()
        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

        headers = sign_request(
            agent_id="test-agent",
            private_key_b64=private_key,
            body=body,
            timestamp="2026-11-21T12:00:00.000Z",
            nonce="test-nonce-12345678",
        )

        # Tampered signing text (different agent ID)
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        tampered_signing_text = (
            f"mc-req-v2\n"
            f"https://api.mc.hugeai.co\n"
            f"POST\n"
            f"/mcp\n"
            f"evil-agent\n"  # Changed
            f"2026-11-21T12:00:00.000Z\n"
            f"test-nonce-12345678\n"
            f"{body_hash}\n"
        )

        # Verify with tampered text should fail
        assert not verify_signature(
            public_key, headers["X-MC-Signature"], tampered_signing_text
        )


class TestDeterministicSigning:
    """Test that Ed25519 signing is deterministic."""

    def test_same_inputs_produce_same_signature(self):
        """Test that signing the same inputs produces the same signature."""
        # TEST ONLY keypair (same as in sign_mc_request.py test)
        test_private_key = "OiyrXwfAGw9VpGzCVsBCsxx9NRDd9+dArCQLPvs1upM="
        test_public_key = "bwr23BMmdgJLIAj9U1LbGUmV4Ts7BkqZsf2Jtt3EHs8="

        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
        timestamp = "2026-11-21T12:00:00.000Z"
        nonce = "test-nonce-abcd1234567890ef"

        # Sign twice with the same inputs
        headers1 = sign_request(
            agent_id="test-agent",
            private_key_b64=test_private_key,
            body=body,
            timestamp=timestamp,
            nonce=nonce,
        )

        headers2 = sign_request(
            agent_id="test-agent",
            private_key_b64=test_private_key,
            body=body,
            timestamp=timestamp,
            nonce=nonce,
        )

        # Signatures should be identical (Ed25519 is deterministic)
        assert headers1["X-MC-Signature"] == headers2["X-MC-Signature"]

        # Verify both signatures
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        signing_text = (
            f"mc-req-v2\n"
            f"https://api.mc.hugeai.co\n"
            f"POST\n"
            f"/mcp\n"
            f"test-agent\n"
            f"{timestamp}\n"
            f"{nonce}\n"
            f"{body_hash}\n"
        )

        assert verify_signature(
            test_public_key, headers1["X-MC-Signature"], signing_text
        )
        assert verify_signature(
            test_public_key, headers2["X-MC-Signature"], signing_text
        )


class TestCanonicalStringFormat:
    """Test canonical signing string format."""

    def test_canonical_string_has_correct_format(self):
        """Test that the canonical string format matches the spec."""
        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

        expected_signing_text = (
            f"mc-req-v2\n"
            f"https://api.mc.hugeai.co\n"
            f"POST\n"
            f"/mcp\n"
            f"test-agent\n"
            f"2026-11-21T12:00:00.000Z\n"
            f"test-nonce-12345678\n"
            f"{body_hash}\n"
        )

        # Check line count (8 lines)
        lines = expected_signing_text.split("\n")
        assert len(lines) == 9  # 8 lines + empty string after final \n

        # Check each line
        assert lines[0] == "mc-req-v2"
        assert lines[1] == "https://api.mc.hugeai.co"
        assert lines[2] == "POST"
        assert lines[3] == "/mcp"
        assert lines[4] == "test-agent"
        assert lines[5] == "2026-11-21T12:00:00.000Z"
        assert lines[6] == "test-nonce-12345678"
        assert lines[7] == body_hash
        assert lines[8] == ""  # Empty string after final \n

    def test_body_hash_is_lowercase_hex(self):
        """Test that body hash is lowercase hexadecimal."""
        body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

        # SHA-256 produces 64 hex characters
        assert len(body_hash) == 64

        # All characters should be lowercase hex
        assert all(c in "0123456789abcdef" for c in body_hash)

        # Verify the hash
        expected_hash = (
            "d16a023a230994645542469f3c501c38bb3abd6cca7c33e9d1de2158fb9bb244"
        )
        assert body_hash == expected_hash


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_sign_and_verify_flow(self):
        """Test the complete sign and verify flow."""
        # Generate keypair
        private_key, public_key = generate_keypair()

        # Create request body
        body = '{"jsonrpc":"2.0","id":42,"method":"mc_brief","params":{"jobId":"test-job"}}'

        # Sign request
        headers = sign_request(
            agent_id="integration-test-agent",
            private_key_b64=private_key,
            body=body,
            timestamp="2026-11-21T15:30:00.000Z",
            nonce="integration-test-nonce-abc123",
        )

        # Reconstruct signing text
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        signing_text = (
            f"mc-req-v2\n"
            f"https://api.mc.hugeai.co\n"
            f"POST\n"
            f"/mcp\n"
            f"{headers['X-MC-Agent']}\n"
            f"{headers['X-MC-Timestamp']}\n"
            f"{headers['X-MC-Nonce']}\n"
            f"{body_hash}\n"
        )

        # Verify signature
        assert verify_signature(public_key, headers["X-MC-Signature"], signing_text)

        # Headers should be ready for HTTP request
        assert headers["X-MC-Agent"] == "integration-test-agent"
        assert headers["X-MC-Timestamp"] == "2026-11-21T15:30:00.000Z"
        assert headers["X-MC-Nonce"] == "integration-test-nonce-abc123"
        assert headers["Content-Type"] == "application/json"

    def test_multiple_requests_with_same_key(self):
        """Test signing multiple requests with the same key."""
        private_key, public_key = generate_keypair()

        # Sign 10 different requests
        for i in range(10):
            body = f'{{"jsonrpc":"2.0","id":{i},"method":"mc_whoami","params":{{}}}}'
            timestamp = f"2026-11-21T12:00:{i:02d}.000Z"
            nonce = f"test-nonce-{i:010d}"

            headers = sign_request(
                agent_id="multi-request-agent",
                private_key_b64=private_key,
                body=body,
                timestamp=timestamp,
                nonce=nonce,
            )

            # Reconstruct and verify
            body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            signing_text = (
                f"mc-req-v2\n"
                f"https://api.mc.hugeai.co\n"
                f"POST\n"
                f"/mcp\n"
                f"multi-request-agent\n"
                f"{timestamp}\n"
                f"{nonce}\n"
                f"{body_hash}\n"
            )

            assert verify_signature(
                public_key, headers["X-MC-Signature"], signing_text
            )
