# Technical report claim audit

| Claim | Evidence | Current status |
|---|---|---|
| Reference metrics separate known failure baselines | committed PointMass, BlockPush and Gripper-Catch reports/tests | supported on analytic tasks |
| Traditional pixel fidelity cannot replace control metrics | 12-context two-task appearance-corruption study, JSON SHA `1de2009f...cf4` | supported as a constructed counterexample |
| Offline CRC tracks analytic closed-loop return | five future scorers, two 12-context tasks, JSON SHA `19d2a010...89b3` | descriptive only |
| LIBERO branches restore the same simulator state | four tasks, repeat/order checks, maximum error 0 | supported for the fixed pilot |
| StarWAM inference and action execution are reproducible | 36 predictions, 36 executions, verified cache/index hashes | supported for pinned short-horizon inputs |
| StarWAM improves LIBERO task success | all tested sparse success values are 0 | not supported and not claimed |
| WAMProbe metrics predict real-model closed-loop gain | StarWAM exposes no candidate-conditioned future in this adapter | not yet tested |

Any revision of the abstract, introduction, or conclusion must remain consistent with this
table. New claims require a structured artifact, an applicability statement, and a failure
or uncertainty analysis.
