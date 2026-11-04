# SRD 5.2.1 import pipeline (staging)

Source: https://www.dndbeyond.com/srd

This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License, available at https://creativecommons.org/licenses/by/4.0/legalcode.

## Stage source text (Windows PowerShell)

```powershell
python -m pip install pymupdf
python scripts/stage_srd.py
```

The script downloads the official PDF, extracts its text page-by-page, records a SHA-256 fingerprint and saves `staging/srd-5.2.1/extracted-pages.json`. To work offline, supply `--pdf path/to/SRD_CC_v5.2.1.pdf`.

**This is a staging utility, not a complete monster converter.** The PDF contains rules, indexes, and many non-monster sections; raw extraction must be mapped and verified against the official stat blocks before anything enters `public/data/published-monsters.json`. In particular, do not silently substitute SRD 5.1 statistics for SRD 5.2.1.

The `staging/` directory is ignored by Git. The published catalog and local custom monster data remain untouched.
