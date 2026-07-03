# Examples

This directory will hold safe ACES-native example scenario packs after the
example-pack issue is implemented.

Examples should demonstrate the contract without requiring private
infrastructure, private data, or downstream catalog assumptions.

## Consumer CI

- [`ci/`](ci/) — a runnable GitHub Actions workflow external adopters can copy to
  validate their pack with the static tooling in [`tools/`](../tools/README.md).
  It requires no secrets or private repository state.
