# Rich Publication Rehearsal Contract Note — 2026-09-09

The first Rich Publication Contract Rehearsal correctly failed closed on missing Metals rich source families, but its MTG pass criterion was incomplete because it checked only file existence and row count.

The governed MTG presentation projectors require exact certified byte-level SHA-256 values. The rehearsal is therefore tightened to require both row-count and SHA parity for Secret Lair premium, Collector, Collector horizon, Pre-Collector, and Pre-Collector scenario sidecars.

The first hosted rehearsal observed the Secret Lair premium sidecar SHA as `6ed7f46d52f01bfb0ba80dfb923a9f438dd899641280bf52d887b1fc0dd956fe`, while the governed projector remains pinned to `296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333`.

No portability correction for that difference has been found. Until the source authority explains or corrects the mismatch, the rich MTG source contract must fail closed.

No PostgreSQL write, staging, or activation is authorized by this change.
