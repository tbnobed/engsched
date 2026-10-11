---
name: External API side-effect boundaries
description: Why integration writes do not automatically trigger email or AI.
---

Keep external integration writes free of automatic outbound email, AI execution, and cancellation of unrelated appointments unless an explicit opt-in contract is added.

**Why:** External applications can retry or import large batches. Reusing every interactive UI side effect would risk duplicate messages, unintended AI costs, or changing appointments the caller did not ask to change.

**How to apply:** Preserve atomic data/history writes and retry protection. If notifications or AI triggers are requested later, design explicit permissions and delivery/idempotency behavior rather than silently enabling existing UI side effects for all API callers.
