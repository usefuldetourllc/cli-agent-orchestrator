# Current libtmux qualification

The protected AgentOps delivery runtime uses libtmux 0.62.0 with CAO 2.5.0 and
tmux 3.8. The dependency floor is `libtmux>=0.62.0`; the old `<0.53.1` workaround
is removed. No parser monkey patch or fallback to an old version is installed.

The earlier diagnosis overstated the fixed-schema problem for 0.62.0. Its
`get_output_format` selects fields by listing-command scope and live tmux
version. Strict width validation remains intentional: malformed rows must be
unknown, rather than silently padded into an apparent absent session. CAO's
existing one-retry `TmuxLookupError` boundary preserves that distinction.

Qualification includes actual current-parser rows with empty fields and invalid
widths; real private-socket reads while 20 sessions are created and deleted;
listing/teardown regressions; protected implementer/reviewer launch admission,
revocation and deadline cleanup; and the automatic implementation, rejection,
correction, re-review, trusted-check and PR-publication loop from AgentOps #324.
The provider executables and GitHub HTTP transport in that loop are synthetic;
Git operations, CAO/tmux, process ownership and cleanup are real. These tests do
not establish real-model production acceptance.

The previously qualified terminal JSON-input change is included on top of the
fork's current main so the installed runtime can submit a complete task once,
without putting long prompt text in a query string.

Production admission remains paused until merge/closure and terminal retirement
are implemented and the complete fresh pilot is qualified. See
https://github.com/usefuldetourllc/AgentOps/issues/323 and #314.
