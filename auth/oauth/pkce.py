import base64
import hashlib
import os


def generate_code_verifier(length: int = 64) -> str:
    verifier = base64.urlsafe_b64encode(os.urandom(length))
    return verifier.rstrip(b"=").decode()


def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest)
    return challenge.rstrip(b"=").decode()