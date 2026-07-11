"""Articulation hello: drive a Franka Panda arm headless.

Loads the Franka USD from Isaac cloud assets, wraps it as a SingleArticulation,
commands joint position targets, and logs joint positions while the PhysX
reduced-coordinate articulation tracks them. Proves articulation control works
headless on this GPU.

Run:  python scripts/03_articulation_franka.py
"""

import os

os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import numpy as np
import omni.client
from isaacsim.core.api import World
from isaacsim.core.prims import SingleArticulation
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.storage.native import get_assets_root_path

assets_root = get_assets_root_path()
print(f"assets root: {assets_root}")

CANDIDATES = [
    "/Isaac/Robots/FrankaRobotics/FrankaPanda/franka.usd",  # 5.x layout
    "/Isaac/Robots/Franka/franka.usd",                      # 4.x layout
]
franka_usd = None
for rel in CANDIDATES:
    result, _ = omni.client.stat(assets_root + rel)
    if result == omni.client.Result.OK:
        franka_usd = assets_root + rel
        break
if franka_usd is None:
    raise RuntimeError(f"Franka USD not found under {assets_root}; tried {CANDIDATES}")
print(f"loading: {franka_usd}")

world = World()
world.scene.add_default_ground_plane()
add_reference_to_stage(usd_path=franka_usd, prim_path="/World/Franka")
franka = world.scene.add(SingleArticulation(prim_path="/World/Franka", name="franka"))

world.reset()

print(f"DOF count: {franka.num_dof}")
print(f"DOF names: {franka.dof_names}")
start = franka.get_joint_positions()
print(f"start positions: {np.round(start, 3)}")

# A reachable arm pose (7 arm joints + 2 gripper fingers on the standard Panda)
target = np.array(start, dtype=float)
target[:7] = [0.0, -0.6, 0.0, -2.2, 0.0, 1.6, 0.8][: min(7, len(target))]
franka.get_articulation_controller().apply_action(
    ArticulationAction(joint_positions=target)
)

for step in range(240):  # 4 s at 60 Hz
    world.step(render=False)
    if step % 40 == 0:
        q = franka.get_joint_positions()
        err = float(np.max(np.abs(q - target)))
        print(f"step {step:3d}: max joint err = {err:6.4f} rad")

q = franka.get_joint_positions()
err = float(np.max(np.abs(q - target)))
print(f"final     : positions = {np.round(q, 3)}")
print(f"final     : max joint err = {err:6.4f} rad (should be near 0 => targets tracked)")

simulation_app.close()
print("done.")
