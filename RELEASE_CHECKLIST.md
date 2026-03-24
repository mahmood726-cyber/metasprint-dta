# Release Checklist

## Status
- [x] README present
- [x] LICENSE present
- [x] Citation metadata present
- [x] Developer validation dependencies documented (`requirements.txt`)
- [x] Public remote configured
- [x] Test and validation scripts present
- [ ] Working tree cleaned for release
- [ ] DOI minted from tagged release

## Before Publishing
1. Run the Python validation scripts listed in `README.md`.
2. Run the R parity workflow in `R_validation/`.
3. Clean the working tree so the release commit matches the cited version.
4. Create a Git tag and GitHub release.
5. Mint the Zenodo DOI and add it back to `CITATION.cff`.
