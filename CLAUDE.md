# CLAUDE.md — project context

## What this is

Isaac Sim hands-on study repo. Purpose: honest, verifiable exposure to NVIDIA AI software
(Isaac Sim) ahead of an NVIDIA **Developer Relations Manager — Robotics/Physical AI (APAC)**
application. The owner's resume anchors on 42dot (UE4/CARLA AV sensor-validation simulator),
Havok physics middleware, and Varjo GPU pipelines — this repo adds the missing
"Exposure to NVIDIA AI Software" piece. Style: learning-in-public, same as
github.com/Hakhyun-Kim/deep-learning-study — every experiment scripted, reproducible,
documented in README.md **including failures**.

## Current status (as of 2026-07-11)

- Scaffold complete: README, .gitignore, two experiment scripts. **Isaac Sim NOT installed yet** —
  stopped before the ~8–10 GB download / EULA step; work moved to a different machine (this one).
- Task plan remaining:
  1. Create venv + install Isaac Sim (commands below)
  2. Run `scripts/01_hello_physics.py` (headless falling-cube physics test)
  3. Run `scripts/02_synthetic_camera.py` (Replicator RGB capture → output/synthetic_rgb.png)
  4. Update README "Experiments" table + "Notes & findings" with real results

## Verified install facts (checked 2026-07-11 against official docs)

- Current version: **Isaac Sim 5.1.0**, requires **Python 3.11** (exact minor matters)
- Install (from repo root; `uv` recommended, plain `py -3.11 -m venv` also fine):

```powershell
uv venv --python 3.11 .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install "isaacsim[all,extscache]==5.1.0" --extra-index-url https://pypi.nvidia.com
```

- EULA: running requires accepting the NVIDIA Omniverse EULA. Both scripts already set
  `os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"` at the top — **get the user's explicit OK
  before first run** (it's a legal agreement), then no further action needed.
- Windows: enable long-path support if install errors mention path length
  (`HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled` = 1).
- Verify install: `python -c "import os; os.environ['OMNI_KIT_ACCEPT_EULA']='YES'; from isaacsim import SimulationApp; app=SimulationApp({'headless': True}); print('OK'); app.close()"`
- Docs: https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_python.html

## Hardware notes

- Original machine: RTX 3050 Ti Laptop **4 GB VRAM** — below the 8 GB minimum spec; that
  constraint is part of the story in README. On this (new) machine, run `nvidia-smi` first
  and update the README hardware table with the actual GPU/driver before running experiments.
- Keep everything **headless** (`SimulationApp({"headless": True})`) to minimize VRAM.

## Code notes / gotchas

- Isaac Sim 5.x renamed modules: use `isaacsim.core.api` (World, objects.DynamicCuboid),
  not the old `omni.isaac.core`. `SimulationApp` must be constructed **before** importing
  any other isaacsim/omni module.
- `02_synthetic_camera.py` uses `omni.replicator.core` (camera → render_product → rgb
  annotator). The Replicator API details were written from docs, not yet executed — expect
  to iterate (e.g., `rep.orchestrator.step()` signature, annotator data format).
- First launch compiles shaders and downloads extension registry data — slow (minutes);
  don't mistake it for a hang.
- If 4 GB-class VRAM fails outright, document the failure mode in README and pivot:
  smaller render size, `isaacsim[all]` without extscache, or note cloud/Isaac Lab
  alternatives as next steps.

## Conventions

- One script per experiment, numbered (`01_`, `02_`, …), self-contained, with a docstring
  explaining what it proves. Outputs go to `output/` (gitignored except when a result
  image is worth committing as evidence).
- After each experiment, update the README table (planned → ✅ / ❌ + one-line result)
  and add findings (VRAM usage via nvidia-smi, wall-clock time, errors hit and fixes).
- Commit messages: imperative, one experiment per commit where practical.
