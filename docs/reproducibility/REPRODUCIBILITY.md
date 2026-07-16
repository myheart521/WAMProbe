# Reproducibility guide

## Levels of reproduction

The dependency-free core, the simulator tier, and the real-model tier have different
requirements and must not be conflated.

| Level | Hardware | External assets | Expected evidence |
|---|---|---|---|
| CPU core | Python 3.11–3.13 CPU | none | 72+ tests, toy reports, video/control and closed-loop studies |
| LIBERO-CF-Mini | Linux GPU renderer | pinned LIBERO checkout/assets | exact restore, repeated/order-reversed branches, checksummed images/states |
| StarWAM | RTX-class CUDA GPU | pinned StarWAM, Wan2.2 and LIBERO files | cached action matrix, execution index, structured report |

## CPU reproduction

```bash
git clone https://github.com/myheart521/WAMProbe.git
cd WAMProbe
git checkout <release-tag-or-commit>
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

ruff format --check .
ruff check .
mypy
pytest --cov=wamprobe --cov-report=term-missing --cov-fail-under=85

wamprobe demo --benchmark pointmass --contexts 12 --seed 7 \
  --output runs/pointmass-reproduction
wamprobe video-control-study --contexts 12 --seed 7 \
  --output runs/video-control-reproduction
wamprobe closed-loop-study --contexts 12 --seed 7 --execute-prefix 1 \
  --resamples 1000 --output runs/closed-loop-reproduction
```

Compare generated video/control and closed-loop JSON files byte-for-byte with the committed
examples. The canonical SHA256 values are `1de2009f...cf4` and `19d2a010...89b3`.

## Simulator and real-model reproduction

Follow the isolated environment recipes in `environments/libero/README.md` and
`environments/starwam/README.md`. Run `wamprobe doctor --verify-hashes` before importing
upstream model code. The release evidence manifest pins upstream revisions, configuration
files, committed reports, and the locally retained prediction/execution index hashes.

Generated RGB, simulator state, model weights and raw predictions remain outside Git.
Their reports contain hashes and explicit availability labels; absence is an error, not a
reason to synthesize substitute results. Candidate-action metrics remain skipped for the
released StarWAM interface because it accepts observations and emits an action chunk, not
an action-conditioned future for each proposed candidate.

## Candidate package reproduction

Run `scripts/build_release_candidate.py` from a clean commit. A valid candidate has two
byte-reproducible distributions, a `release-manifest.json`, a passing offline clean-wheel
install, and matching evidence hashes. See
[`release/README.md`](https://github.com/myheart521/WAMProbe/blob/main/release/README.md).

## Maintainer acceptance and optional independent reports

The `v0.1.0` release uses a documented maintainer clean-install check as its package
acceptance gate. The report must record the Git tag, operating system, Python version,
install command, exact smoke command, exit status, output JSON SHA256, elapsed time, and
any deviation. Issue #2 preserves the public record.

Independent reports remain welcome as additional evidence. A template is provided in
[`EXTERNAL_REPRODUCTION_TEMPLATE.md`](EXTERNAL_REPRODUCTION_TEMPLATE.md). A maintainer-run
check must always be labeled as maintainer evidence and never described as independent.
