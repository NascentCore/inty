# Python style: subscription rollback visibility

Fixed the highest-risk open Google Python Style Guide exception violation in
subscription usage accounting.

- Scanned Python code for broad exception suppression, mutable defaults, `None`
  comparisons, and mutable module state.
- Recorded the 2026-05-13 findings in both the requested maintenance path and
  the prioritized maintenance ledger.
- Replaced silent rollback suppression in subscription usage recording with
  structured exception logs for both the primary usage-write failure and the
  secondary rollback failure.

Follow-ups:

- Fix the newly recorded Live Chat prefill flush silent wait failure.
- Fix the matching voice cache rollback suppression sites.

