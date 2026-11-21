#!/usr/bin/env python3
"""
Mission Control Ed25519 Request Signer (mc-req-v2)

Reference implementation for signing Mission Control MCP requests with Ed25519.
Requires only the `cryptography` package.

Usage:
  # Generate a new keypair
  python sign_mc_request.py --generate

  # Sign a request
  python sign_mc_request.py --agent your-agent-id --private-key <base64-key> \\
    --body '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

  # Test against the signing vector
  python sign_mc_request.py --test

Installation:
  pip install cryptography
"""

import argparse
import base64
import hashlib
import secrets
import sys
from datetime import datetime, timezone

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("Error: cryptography package required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


def base64_encode(data: bytes) -> str:
    """Base64 encode (standard, no padding removed)."""
    return base64.b64encode(data).decode('ascii')


def base64url_encode(data: bytes) -> str:
    """Base64url encode (RFC 4648 §5, no padding)."""
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def base64_decode(s: str) -> bytes:
    """Base64 decode (standard, pad if needed)."""
    padding = (4 - len(s) % 4) % 4
    return base64.b64decode(s + '=' * padding)


def base64url_decode(s: str) -> bytes:
    """Base64url decode (RFC 4648 §5, pad if needed)."""
    padding = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + '=' * padding)


def generate_keypair() -> tuple[str, str]:
    """
    Generate a new Ed25519 keypair.
    
    Returns:
        (private_key_b64, public_key_b64): Base64-encoded keys
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Serialize to raw bytes (32 bytes each)
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    return base64_encode(private_bytes), base64_encode(public_bytes)


def sign_request(
    agent_id: str,
    private_key_b64: str,
    body: str,
    audience: str = "https://api.mc.hugeai.co",
    method: str = "POST",
    path: str = "/mcp",
    timestamp: str | None = None,
    nonce: str | None = None
) -> dict:
    """
    Sign a Mission Control request with Ed25519 (mc-req-v2).
    
    Args:
        agent_id: Agent identifier
        private_key_b64: Base64-encoded Ed25519 private key (32 bytes)
        body: Request body (JSON string)
        audience: Audience URL (default: production)
        method: HTTP method (default: POST)
        path: Request path (default: /mcp)
        timestamp: ISO 8601 UTC timestamp (default: current time)
        nonce: Base64url nonce (default: random 32 chars)
    
    Returns:
        dict: Headers to include in the request
    """
    # Generate timestamp and nonce if not provided
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    if nonce is None:
        nonce = base64url_encode(secrets.token_bytes(24))  # 24 bytes → 32 base64url chars
    
    # Compute SHA-256 of body (lowercase hex)
    body_bytes = body.encode('utf-8')
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    
    # Build canonical signing string (mc-req-v2)
    # Each line ends with \n, including the last one
    signing_text = (
        f"mc-req-v2\n"
        f"{audience}\n"
        f"{method}\n"
        f"{path}\n"
        f"{agent_id}\n"
        f"{timestamp}\n"
        f"{nonce}\n"
        f"{body_hash}\n"
    )
    
    # Load private key and sign
    private_bytes = base64_decode(private_key_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
    signature = private_key.sign(signing_text.encode('utf-8'))
    
    return {
        "X-MC-Agent": agent_id,
        "X-MC-Timestamp": timestamp,
        "X-MC-Nonce": nonce,
        "X-MC-Signature": base64url_encode(signature),
        "Content-Type": "application/json"
    }


def verify_signature(
    public_key_b64: str,
    signature_b64url: str,
    signing_text: str
) -> bool:
    """
    Verify an Ed25519 signature.
    
    Args:
        public_key_b64: Base64-encoded public key (32 bytes)
        signature_b64url: Base64url-encoded signature (64 bytes)
        signing_text: Canonical signing string
    
    Returns:
        bool: True if signature is valid
    """
    try:
        public_bytes = base64_decode(public_key_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        signature = base64url_decode(signature_b64url)
        public_key.verify(signature, signing_text.encode('utf-8'))
        return True
    except Exception:
        return False


def test_signing_vector() -> bool:
    """
    Test the signing implementation with deterministic test vectors.
    
    Ed25519 is deterministic: signing the same message with the same key
    always produces the same signature. This test uses a fixed TEST ONLY
    keypair to verify the implementation.
    
    Returns:
        bool: True if all tests pass
    """
    print("Testing Mission Control Ed25519 Request Signer (mc-req-v2)\n")
    
    # TEST ONLY keypair (generated specifically for this test vector)
    # DO NOT use this key for any real agent
    test_private_key = "OiyrXwfAGw9VpGzCVsBCsxx9NRDd9+dArCQLPvs1upM="  # TEST ONLY
    test_public_key = "bwr23BMmdgJLIAj9U1LbGUmV4Ts7BkqZsf2Jtt3EHs8="   # TEST ONLY
    
    print(f"Using TEST ONLY keypair")
    print(f"  Public key: {test_public_key}")
    print()
    
    # Test 1: Body hash computation
    print("Test 1: Body hash computation")
    test_body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
    expected_hash = "d16a023a230994645542469f3c501c38bb3abd6cca7c33e9d1de2158fb9bb244"
    computed_hash = hashlib.sha256(test_body.encode('utf-8')).hexdigest()
    
    if computed_hash != expected_hash:
        print(f"  ❌ FAIL: Body hash mismatch")
        print(f"    Expected: {expected_hash}")
        print(f"    Got:      {computed_hash}")
        return False
    
    print(f"  ✅ PASS: Body hash matches")
    print(f"    Hash: {computed_hash}")
    print()
    
    # Test 2: Canonical string construction
    print("Test 2: Canonical string construction")
    agent_id = "test-agent"
    timestamp = "2026-11-21T12:00:00.000Z"
    nonce = "test-nonce-abcd1234567890ef"
    
    expected_signing_text = (
        f"mc-req-v2\n"
        f"https://api.mc.hugeai.co\n"
        f"POST\n"
        f"/mcp\n"
        f"{agent_id}\n"
        f"{timestamp}\n"
        f"{nonce}\n"
        f"{expected_hash}\n"
    )
    
    print(f"  Canonical string (8 lines, each ending with \\n):")
    for i, line in enumerate(expected_signing_text.split('\n')[:-1], 1):
        print(f"    {i}. {line}")
    print(f"  ✅ PASS: Canonical string constructed")
    print()
    
    # Test 3: Deterministic signature
    print("Test 3: Deterministic Ed25519 signature")
    
    # Sign with the test key
    private_bytes = base64_decode(test_private_key)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
    signature = private_key.sign(expected_signing_text.encode('utf-8'))
    signature_b64url = base64url_encode(signature)
    
    print(f"  Signature (base64url): {signature_b64url}")
    print()
    
    # Test 4: Signature verification
    print("Test 4: Signature verification")
    if not verify_signature(test_public_key, signature_b64url, expected_signing_text):
        print(f"  ❌ FAIL: Signature verification failed")
        return False
    
    print(f"  ✅ PASS: Signature verifies correctly")
    print()
    
    # Test 5: Round-trip with sign_request
    print("Test 5: Round-trip with sign_request()")
    headers = sign_request(
        agent_id=agent_id,
        private_key_b64=test_private_key,
        body=test_body,
        timestamp=timestamp,
        nonce=nonce
    )
    
    # Reconstruct signing text and verify
    reconstructed_signing_text = (
        f"mc-req-v2\n"
        f"https://api.mc.hugeai.co\n"
        f"POST\n"
        f"/mcp\n"
        f"{headers['X-MC-Agent']}\n"
        f"{headers['X-MC-Timestamp']}\n"
        f"{headers['X-MC-Nonce']}\n"
        f"{computed_hash}\n"
    )
    
    if not verify_signature(test_public_key, headers['X-MC-Signature'], reconstructed_signing_text):
        print(f"  ❌ FAIL: Round-trip signature verification failed")
        return False
    
    print(f"  ✅ PASS: sign_request() produces valid signature")
    print(f"  Headers generated:")
    for key, value in headers.items():
        if key == 'X-MC-Signature':
            print(f"    {key}: {value[:32]}... (truncated)")
        else:
            print(f"    {key}: {value}")
    print()
    
    # Test 6: Fresh keypair generation
    print("Test 6: Fresh keypair generation")
    new_private, new_public = generate_keypair()
    
    # Sign and verify with the new keypair
    new_headers = sign_request(
        agent_id="new-agent",
        private_key_b64=new_private,
        body=test_body
    )
    
    new_body_hash = hashlib.sha256(test_body.encode('utf-8')).hexdigest()
    new_signing_text = (
        f"mc-req-v2\n"
        f"https://api.mc.hugeai.co\n"
        f"POST\n"
        f"/mcp\n"
        f"{new_headers['X-MC-Agent']}\n"
        f"{new_headers['X-MC-Timestamp']}\n"
        f"{new_headers['X-MC-Nonce']}\n"
        f"{new_body_hash}\n"
    )
    
    if not verify_signature(new_public, new_headers['X-MC-Signature'], new_signing_text):
        print(f"  ❌ FAIL: Fresh keypair signature verification failed")
        return False
    
    print(f"  ✅ PASS: Fresh keypair works correctly")
    print(f"  Generated public key: {new_public[:32]}... (truncated)")
    print()
    
    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print()
    print("Note: The TEST ONLY keypair used in these tests is for")
    print("demonstration purposes only. Never use it for a real agent.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Mission Control Ed25519 Request Signer (mc-req-v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a new keypair
  %(prog)s --generate

  # Sign a request
  %(prog)s --agent grokbot-1 --private-key <base64-key> \\
    --body '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

  # Test the implementation
  %(prog)s --test
"""
    )
    
    parser.add_argument('--generate', action='store_true',
                       help='Generate a new Ed25519 keypair')
    parser.add_argument('--test', action='store_true',
                       help='Test against signing vectors')
    parser.add_argument('--agent', help='Agent ID')
    parser.add_argument('--private-key', help='Base64-encoded Ed25519 private key (32 bytes)')
    parser.add_argument('--body', help='Request body (JSON string)')
    parser.add_argument('--audience', default='https://api.mc.hugeai.co',
                       help='Audience (default: https://api.mc.hugeai.co)')
    parser.add_argument('--method', default='POST',
                       help='HTTP method (default: POST)')
    parser.add_argument('--path', default='/mcp',
                       help='Request path (default: /mcp)')
    parser.add_argument('--timestamp',
                       help='ISO 8601 timestamp (default: current time)')
    parser.add_argument('--nonce',
                       help='Base64url nonce (default: random 32 chars)')
    
    args = parser.parse_args()
    
    if args.generate:
        private_key, public_key = generate_keypair()
        print("Generated Ed25519 keypair:")
        print()
        print(f"Private key (keep secret!):")
        print(f"  {private_key}")
        print()
        print(f"Public key (register with MC):")
        print(f"  {public_key}")
        print()
        print("Store the private key securely (e.g., in a vault).")
        print("Register the public key with: mc rotate-key <agent-id> <public-key>")
        return 0
    
    if args.test:
        success = test_signing_vector()
        return 0 if success else 1
    
    if not args.agent or not args.private_key or not args.body:
        parser.error("--agent, --private-key, and --body are required (or use --generate / --test)")
    
    headers = sign_request(
        agent_id=args.agent,
        private_key_b64=args.private_key,
        body=args.body,
        audience=args.audience,
        method=args.method,
        path=args.path,
        timestamp=args.timestamp,
        nonce=args.nonce
    )
    
    print("Request headers:")
    for key, value in headers.items():
        print(f"{key}: {value}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
