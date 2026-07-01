# Security

Report security issues through the standard GitHub private vulnerability
reporting channel when available, or contact the maintainers directly.

Scenario packs can contain synthetic credentials, flags, service defaults, and
participant-facing artifacts. Those values are training content, not production
secrets. Do not commit real credentials, customer data, private keys, or
operator tokens to this repository.

Local Ground Control tokens belong in `.env`, which is ignored by Git.
