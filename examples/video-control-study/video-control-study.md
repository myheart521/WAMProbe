# Traditional video fidelity versus control value

The appearance-corrupted oracle preserves exact state/control predictions while deliberately lowering RGB fidelity. It is a metric counterexample, not a model quality claim: PSNR/global SSIM cannot replace CRC, regret, or state metrics.

## blockpush-2d-v0.1

| Profile | Transform | PSNR dB | Global SSIM | State FDE | CRC | Regret |
|---|---|---:|---:|---:|---:|---:|
| oracle-simulator | identity | 100.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| appearance-corrupted-oracle | invert-rgb | 0.5882 | -0.0790 | 0.0000 | 1.0000 | 0.0000 |
| noisy-dynamics | identity | 39.9549 | 0.9058 | 0.0355 | 1.0000 | 0.0000 |
| copy-last-frame | identity | 38.4547 | 0.7490 | 0.4369 | 0.0000 | 0.3000 |
| wrong-direction | identity | 37.6401 | 0.6928 | 0.7953 | -0.2500 | 0.3000 |
| action-agnostic | identity | 36.6898 | 0.6141 | 0.9391 | 0.0000 | 0.3000 |

PSNR/regret ordering disagreed on 3/9 comparable profile pairs.

## gripper-catch-v0.1

| Profile | Transform | PSNR dB | Global SSIM | State FDE | CRC | Regret |
|---|---|---:|---:|---:|---:|---:|
| oracle-simulator | identity | 100.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| appearance-corrupted-oracle | invert-rgb | 0.5857 | -0.0801 | 0.0000 | 1.0000 | 0.0000 |
| noisy-dynamics | identity | 38.2162 | 0.9047 | 0.0305 | 1.0000 | 0.0000 |
| copy-last-frame | identity | 21.4849 | 0.5927 | 1.0447 | 0.0000 | 1.0000 |
| wrong-direction | identity | 45.1225 | 0.8322 | 0.9663 | 0.0000 | 1.0000 |
| action-agnostic | identity | 42.7141 | 0.7703 | 1.1560 | 0.0000 | 1.0000 |

PSNR/regret ordering disagreed on 5/9 comparable profile pairs.

Global SSIM here is an explicitly labeled whole-frame diagnostic, not the
standard windowed implementation. Exact PSNR matches use a finite 100 dB cap.
