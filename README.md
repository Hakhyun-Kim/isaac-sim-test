# Isaac Sim Study

Hands-on exploration of [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac/sim) —
physics simulation and synthetic data generation, run headless on modest laptop hardware.

Follows the same learning-in-public approach as my
[deep-learning-study](https://github.com/Hakhyun-Kim/deep-learning-study) repo:
every experiment is scripted, reproducible, and documented — including the failures.

## Why

My background is real-time 3D and simulation: physics middleware support at Havok,
an Unreal Engine 4 / CARLA sensor-validation simulator for autonomous driving at 42dot,
and GPU pipeline optimization for human-eye-resolution VR at Varjo.
Isaac Sim is where that world meets modern Physical AI — this repo documents my first steps.

## Hardware (yes, below min spec)

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 3050 Ti Laptop, **4 GB VRAM** (min spec is 8 GB) |
| Driver | 591.55, CUDA 13.1 |
| OS | Windows 11 Pro |
| Python | 3.11 venv (via `uv`), Isaac Sim 5.1.0 pip install |

Part of the experiment is finding out what a below-min-spec GPU can and cannot do
with headless Isaac Sim.

## Setup

```powershell
uv venv --python 3.11 .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install "isaacsim[all,extscache]==5.1.0" --extra-index-url https://pypi.nvidia.com
```

Running any script requires accepting the NVIDIA Omniverse EULA
(`OMNI_KIT_ACCEPT_EULA=YES`, set inside the scripts).

## Experiments

| # | Script | What it does | Status |
|---|---|---|---|
| 01 | `scripts/01_hello_physics.py` | Headless physics: cube drops onto ground plane, position logged per step | planned |
| 02 | `scripts/02_synthetic_camera.py` | Synthetic data: render the scene to an RGB PNG via Replicator | planned |

## Notes & findings

_(updated as experiments run)_
