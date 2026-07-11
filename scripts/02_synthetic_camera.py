"""Synthetic data hello: render the physics scene to an RGB image.

Three colored cubes drop onto the ground plane; after the physics settles,
a Replicator camera renders one 1280x720 RGB frame to output/synthetic_rgb.png.

This is the smallest possible version of the synthetic-data workflow
(sim -> sensor -> image) used for training Physical AI models.

Run:  python scripts/02_synthetic_camera.py
"""

import os

os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import numpy as np
from isaacsim.core.api import World
from isaacsim.core.api.objects import DynamicCuboid
import omni.replicator.core as rep
from PIL import Image

world = World()
world.scene.add_default_ground_plane()

cubes = [
    ((0.0, 0.0), (1.0, 0.2, 0.2)),   # red
    ((0.8, 0.3), (0.2, 0.4, 1.0)),   # blue
    ((-0.6, 0.5), (1.0, 0.8, 0.1)),  # yellow
]
for i, ((x, y), color) in enumerate(cubes):
    world.scene.add(
        DynamicCuboid(
            prim_path=f"/World/cube_{i}",
            name=f"cube_{i}",
            position=np.array([x, y, 0.5 + i * 0.7]),
            size=0.4,
            color=np.array(color),
        )
    )

camera = rep.create.camera(position=(3.0, 3.0, 2.5), look_at=(0.0, 0.0, 0.3))
render_product = rep.create.render_product(camera, (1280, 720))
rgb_annotator = rep.AnnotatorRegistry.get_annotator("rgb")
rgb_annotator.attach(render_product)

world.reset()

# Let the cubes fall and settle (render so the frame buffer is up to date).
for _ in range(120):
    world.step(render=True)

rep.orchestrator.step(rt_subframes=4)

data = rgb_annotator.get_data()
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.abspath(os.path.join(out_dir, "synthetic_rgb.png"))
Image.fromarray(np.asarray(data)[..., :3]).save(out_path)
print(f"saved {out_path}  shape={np.asarray(data).shape}")

simulation_app.close()
print("done.")
