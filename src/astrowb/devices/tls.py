"""HTTPS for the observatory API with a self-signed certificate.

Nobody issues certificates for a telescope computer, so the client does not ask a certificate authority:
it pins the certificate's SHA-256 fingerprint, which the observatory shows (and the set-up stores). A
different certificate means a different machine or someone in between, and the client refuses it.
"""

import datetime
import hashlib
import os
import ssl
from pathlib import Path


def fingerprint(der: bytes) -> str:
    return hashlib.sha256(der).hexdigest()


def ensure_certificate(folder) -> tuple[Path, Path, str]:
    """(certificate, key, fingerprint) in folder; made once (EC P-256, 20 years) and reused afterwards."""
    folder = Path(folder)
    cert, key = folder / "observatory-cert.pem", folder / "observatory-key.pem"
    if not (cert.exists() and key.exists()):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import NameOID

        private = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "observatory")])
        now = datetime.datetime.now(datetime.UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(private.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=20 * 365))
            .sign(private, hashes.SHA256())
        )
        folder.mkdir(parents=True, exist_ok=True)
        key_bytes = private.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # the key is readable by its owner only
        with os.fdopen(fd, "wb") as f:
            f.write(key_bytes)
        cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    der = ssl.PEM_cert_to_DER_cert(cert.read_text(encoding="ascii"))
    return cert, key, fingerprint(der)


def server_context(cert, key) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert, key)
    return ctx
