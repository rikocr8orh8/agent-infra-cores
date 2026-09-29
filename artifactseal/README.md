# ArtifactSeal Kit core

Authenticate a file-tree manifest and detect added, removed or changed artifacts.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

Shared-secret HMAC is not public-key signing or nonrepudiation. Freeze or snapshot the tree before sealing: this library does not eliminate filesystem races or bind later execution to the verified bytes. File permissions and executable modes are not included. Do not place the manifest inside the sealed root. Empty directories and hard links are not represented in the manifest, a directory the verifier cannot read is an error, and the limits are 1000 files, 16 MiB per file and 64 MiB in total.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
