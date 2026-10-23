# Security and privacy

Q-One Core is designed to run locally, but the repository does not provide encryption, authentication, or secure deletion. Treat the ledger as sensitive whenever it contains personal decisions.

- Keep `.qone-data/` outside shared or public directories when it contains personal information.
- Never commit API keys, provider tokens, raw model context, health records, financial records, or unredacted personal exports.
- Use a private storage and backup policy appropriate to the data before integrating `q-one-life`.
- Report a suspected credential leak or a reproducible integrity issue privately to the repository maintainer before public disclosure.
