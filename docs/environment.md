# Verified environment

- Evaluation Python: 3.12.10
- Evaluation platform: Windows-11-10.0.26300-SP0
- Full evaluated dependency pins: requirements.lock.txt
- Evaluated source/protocol SHA256: cff4e82bd46badc850eca72cf08fc90a9a5c1c70e0561d00ec2d9ee64c9dba9c
- Evaluation raw directory: results/benchmarks/20261126T074920Z
- Fresh-install verification: Fresh virtual environment on the same Windows machine; not an independent-machine replication
- Browser verification: Chromium-based browser 158.0.4370.33; desktop 1440×1100 and mobile 390×844.
- No Node build step, cloud model, API key or remote asset request is needed at runtime.

Fresh installation needs Python 3.12 and package-index access. The lock records the working Windows environment. Portability beyond tested Python/OS versions is not claimed. Initial installation verification encountered a clock-resolution-dependent test fixture; it was replaced with a deterministic file-counter fixture, then the full fresh-environment check was rerun. The application replay-validation policy was not weakened.
