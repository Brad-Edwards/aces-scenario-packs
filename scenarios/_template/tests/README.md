# `tests/` — range-path tests (reference)

Scripts that run every path against the **live golden AWS range** and confirm
each flag. The tests target the golden range, not an abstraction.
**Required-if-present** with the rest of the reference triangle (`build/` +
`docs/walkthroughs/`).

Each test path should have a matching human walkthrough under
`docs/walkthroughs/` — same commands, same expected output, same flag.
