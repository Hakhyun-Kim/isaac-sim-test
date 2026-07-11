# Physics engines I've actually used: Havok vs PhysX vs CARLA/Unreal — and where Isaac Sim fits

Personal context: I supported **Havok Physics/AI/Vision** middleware integrations across Asia (2010–2014),
shipped **UE4 gameplay physics** at NEXON (UE4's default engine was **PhysX 3**), supported **Unity**
developers (Unity's built-in 3D physics is also PhysX; DOTS-era **Unity Physics** is a separate stateless
deterministic engine, with **Havok Physics for Unity** as the stateful option), and built an
**AV sensor-validation simulator on CARLA/UE4** at 42dot. Isaac Sim closes the loop: it runs **PhysX 5**.
This note organizes what's actually *different* between them, question-bank style, like my
[deep-learning-study](https://github.com/Hakhyun-Kim/deep-learning-study) notes.

## TL;DR

|  | Havok Physics | PhysX 3/4 (game era) | PhysX 5 (Isaac Sim) | CARLA (on Unreal) |
|---|---|---|---|---|
| What it is | Rigid-body middleware (C++ SDK) | Rigid-body engine bundled into UE4/Unity | Simulation engine for robotics/industrial | AV **simulator platform**, not an engine |
| Layer | Engine | Engine | Engine (+ Omniverse/USD stack above it) | Application built on UE (PhysX-era UE4 → Chaos-era UE5) |
| Optimized for | Games: stability, perf, artist workflows | Games: same league, free/default | Accuracy, robotics, GPU-parallel RL | Sensors, scenarios, ground-truth data |
| Compute | CPU (SIMD, job-based multithreading) | CPU rigid bodies (GPU mostly for effects: cloth/particles/APEX) | **GPU rigid bodies + articulations via CUDA**, state stays on GPU (tensor API) | Whatever UE uses underneath |
| Joints/robots | Maximal-coordinate constraints, ragdoll/vehicle kits | Maximal-coordinate constraints | **Reduced-coordinate articulations** (no joint drift → robot arms) | Vehicle-centric (PhysX Vehicles; optional Chrono for high-fidelity dynamics) |
| License | Closed, licensed (Intel → now Microsoft) | Open source (BSD-3, since 4.0 / 2018) | Open source (PhysX 5, since 2022); Isaac Sim itself open-sourced 2025 | Open source (MIT) |
| Where I used it | Havok Korea/Asia support | NEXON UE4, Unity support | This repo | 42dot |

## The four differences that actually matter

### 1. Engine vs simulator (layer confusion)

Havok and PhysX solve the same problem: rigid-body dynamics inside someone else's application.
CARLA is a different species — a *simulation platform* that happens to sit on a game engine:
sensor models (camera/LiDAR/radar/GNSS), OpenDRIVE maps, traffic/scenario runners, ROS bridges,
and pixel-perfect ground truth (segmentation, depth) for synthetic data.
**Isaac Sim is to robotics what CARLA is to AV** — but NVIDIA controls the full stack:
PhysX 5 for dynamics, RTX for physically-based (ray-traced) sensor simulation, USD/Omniverse
for scene description, Replicator for synthetic data, Isaac Lab on top for robot learning.

### 2. Game physics vs robotics physics (different definitions of "good")

Game engines optimize for *plausibility per millisecond*: stable stacking, no visible jitter,
graceful degradation under load, artist-friendly tuning. Getting energy or friction slightly
wrong is fine if it looks right at 60 fps. Robotics simulation optimizes for *transferability*:
contact forces, joint dynamics, and sensor readings must be accurate enough that a policy
trained in sim survives contact with reality (sim-to-real). Same math, opposite tolerances —
this is why "I shipped game physics" does not automatically mean "I can validate a robot sim,"
and why PhysX 5's accuracy features (TGS solver, SDF collision, articulations) exist.

### 3. Joints: maximal vs reduced coordinates

Game engines represent joints as constraints between free 6-DOF bodies (maximal coordinates),
solved iteratively — fast, but joints drift and stretch under load (acceptable for ragdolls,
fatal for a 7-DOF arm holding position). PhysX 4+ added **reduced-coordinate articulations**
(Featherstone-style): the kinematic tree is the state, so joints *cannot* drift.
That single design choice is a big part of why Isaac Sim can simulate manipulators credibly.

### 4. GPU: from eye candy to the core loop

"GPU PhysX" in the game era meant effects — cloth, debris, particles — bolted onto CPU rigid
bodies. PhysX 5 inverts this: rigid bodies, articulations, and soft bodies run *on* the GPU and
the simulation state can stay there, exposed as tensors. That's what makes 1,000+ parallel
environments per GPU possible in Isaac Lab for RL — not just "faster physics," but a different
workflow that CPU engines (Havok included) structurally can't offer.

## Ecosystem timeline (for positioning conversations)

- Havok: Dublin 1998 → Intel 2007 → **Microsoft 2015** (my era: Trinigy → Havok under Intel)
- PhysX: NovodeX/ETH → Ageia → **NVIDIA 2008** → BSD open source 4.0 (2018), PhysX 5 (2022)
- Unreal: PhysX default through UE4 → replaced by Epic's own **Chaos** in UE5 (CARLA 0.10 moved to UE5)
- Unity: built-in 3D = PhysX; DOTS offers stateless deterministic **Unity Physics** + **Havok Physics for Unity**
- Robot learning: DeepMind **MuJoCo** (open-sourced 2021) is the RL research standard;
  **Newton** (NVIDIA + DeepMind + Disney Research, GTC 2025, built on NVIDIA Warp) is the
  open, differentiable, GPU-native next step — watch this space.

## Question bank

Checklist style; ✅ = answered in this note / hands-on, ☐ = open. One experiment per ☐ where possible.

### A. Solvers & accuracy
- ✅ Why do maximal-coordinate joints drift, and what do reduced-coordinate articulations change?
- ☐ What exactly does the TGS (Temporal Gauss-Seidel) solver do differently from PGS, and when does it visibly matter? (experiment idea: tall stack + articulated arm, PGS vs TGS in Isaac Sim)
- ☐ How does SDF collision differ from convex-decomposition collision, and what does it cost? (experiment: non-convex mesh contact in Isaac Sim)
- ☐ How deterministic is PhysX 5 on GPU, and under what settings? Compare with Unity DOTS' stateless-by-design determinism.

### B. GPU-parallel simulation
- ✅ Why can't a CPU engine like Havok simply "add GPU support" for the RL use case? (state residency + tensor API, not raw speed)
- ☐ Run an Isaac Lab example with N parallel envs on this 4 GB GPU; find the practical N.
- ☐ Where is the CPU↔GPU sync boundary in Isaac Sim's pipeline, and what breaks if you read positions every step (like my script 01 does)?

### C. Sensors & synthetic data (CARLA vs Isaac Sim)
- ✅ What does a simulator add on top of a physics engine? (sensors, scenarios, ground truth, maps)
- ☐ CARLA's raycast/shader LiDAR vs Isaac Sim's RTX ray-traced LiDAR: what artifacts differ? (I built LiDAR validation at 42dot — write the comparison from experience + docs)
- ✅ Reproduce my 42dot workflow in miniature: spawn scene → LiDAR sweep → point cloud dump in Isaac Sim. (`scripts/06_lidar_pointcloud.py` — 11.65 M points, occlusion shadows visible; see README findings for the four API gotchas it took to get there)
- ☐ Domain randomization: what does `isaacsim.replicator.domain_randomization` randomize that CARLA can't (materials at the RTX level)?

### D. Ecosystem & positioning (DevRel angle)
- ✅ Why did Epic replace PhysX with Chaos, and what does that mean for NVIDIA's physics strategy? (control of the stack → Omniverse/Isaac rather than middleware-in-someone-else's-engine)
- ☐ When would you honestly recommend MuJoCo over Isaac Sim to a robotics startup? (know the answer a DevRel must give)
- ☐ What is Newton/Warp's differentiable-physics story, and which customers need differentiability?
- ☐ Havok under Microsoft today: where does it still win? (consoles, deterministic multiplayer at scale)

### E. Hands-on TODOs in this repo
- ✅ 03: articulated robot headless — Franka Panda, 9 DOF, joint targets tracked to 0.0044 rad
- ☐ 04: multi-annotator capture (RGB + depth + semantic segmentation)
- ☐ 05: domain randomization pass over the cube scene
- ✅ 06: LiDAR point-cloud capture (ties to C) — RTX Example_Rotary, per-frame annotator polling
