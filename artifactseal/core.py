"""SPDX-License-Identifier: MIT. Shared-key authenticated exact-tree manifests."""
import hashlib
import hmac
import json
import os
from pathlib import Path


def _entries(root):
    def unreadable(error):
        raise ValueError("A directory in the tree could not be read") from error
    found = []
    for directory, names, files in os.walk(root, onerror=unreadable, followlinks=False):
        found.extend(Path(directory, name) for name in names + files)
    return sorted(found)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Root must be a real directory, not a symlink")
    result = {}
    total = 0
    for path in _entries(root):
        if path.is_symlink():
            raise ValueError("Symlinks are not supported")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("Only regular files are supported")
        size = path.stat().st_size
        total += size
        if size > 16 * 1024 * 1024 or total > 64 * 1024 * 1024 or len(result) >= 1000:
            raise ValueError("Tree exceeds file, count or total size limit")
        body = path.read_bytes()
        if len(body) != size:
            raise ValueError("File changed during inventory")
        result[path.relative_to(root).as_posix()] = {"size": size, "sha256": hashlib.sha256(body).hexdigest()}
    return result


def seal(root, secret, key_id="default"):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError("Key must be at least 32 bytes")
    if not isinstance(key_id, str) or not 1 <= len(key_id) <= 100:
        raise ValueError("Key ID must be a bounded string")
    manifest = {"format": "artifactseal-v1", "key_id": key_id, "files": inventory(root)}
    return {"manifest": manifest, "hmac_sha256": hmac.new(secret, canonical(manifest), hashlib.sha256).hexdigest()}


def verify(root, envelope, secret, expected_key_id="default"):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError("Key must be at least 32 bytes")
    if type(envelope) is not dict or set(envelope) != {"manifest", "hmac_sha256"}:
        raise ValueError("Invalid envelope")
    manifest, supplied = envelope["manifest"], envelope["hmac_sha256"]
    if type(manifest) is not dict or set(manifest) != {"format", "key_id", "files"}:
        raise ValueError("Invalid manifest")
    if manifest["format"] != "artifactseal-v1" or manifest["key_id"] != expected_key_id:
        raise ValueError("Wrong manifest format or key ID")
    if not isinstance(supplied, str) or len(supplied) != 64:
        raise ValueError("Invalid signature")
    expected = hmac.new(secret, canonical(manifest), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode(), supplied.encode()):
        raise ValueError("Manifest authentication failed")
    actual = inventory(root)
    if actual != manifest["files"]:
        raise ValueError("Artifact tree differs from authenticated manifest")
    return {"valid": True, "files": len(actual), "key_id": expected_key_id}
