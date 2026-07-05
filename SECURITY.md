# Security

Please report security issues through GitHub's private vulnerability reporting
for this repository, or contact the maintainers directly. Don't open a public
issue for a suspected vulnerability.

Scenario packs can contain synthetic credentials, flags, service defaults, and
participant-facing artifacts. Those are training content, not production secrets.
Never commit real credentials, customer data, private keys, or operator tokens
to this repository — keep local development secrets in `.env`, which is
gitignored.
