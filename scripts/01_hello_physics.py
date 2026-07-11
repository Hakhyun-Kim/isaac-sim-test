"""Hello Isaac Sim: headless physics test.

A 0.5 m cube is dropped from 2 m onto the default ground plane.
We step the simulation at 60 Hz and log the cube's height, expecting it
to come to rest at z ~= 0.25 (half the cube size).

Run:  python scripts/01_hello_physics.py
"""

import os

os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"

from isaacsim import SimulationApp

# Headless keeps VRAM usage as low as possible (no viewport).
simulation_app = SimulationApp({"headless": True})

import numpy as np
from isaacsim.core.api import World
from isaacsim.core.api.objects import DynamicCuboid

world = World()
world.scene.add_default_ground_plane()

cube = world.scene.add(
    DynamicCuboid(
        prim_path="/World/cube",
        name="cube",
        position=np.array([0.0, 0.0, 2.0]),
        size=0.5,
        color=np.array([1.0, 0.3, 0.1]),
    )
)

world.reset()

for step in range(180):  # 3 seconds at 60 Hz
    world.step(render=False)
    if step % 20 == 0:
        position, _ = cube.get_world_pose()
        print(f"step {step:3d}: cube z = {position[2]:6.3f} m")

position, _ = cube.get_world_pose()
print(f"final     : cube z = {position[2]:6.3f} m (expected ~0.25, resting on ground)")

simulation_app.close()
print("done.")
