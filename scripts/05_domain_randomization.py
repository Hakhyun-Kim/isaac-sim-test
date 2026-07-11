"""Domain randomization: randomized cube poses and colors across frames.

Five cubes live in a World scene (whose default ground plane brings working
lighting - pure replicator-native scenes render black without explicit,
correctly-composed lights; see README findings). A registered Replicator
randomizer re-rolls cube positions, rotations, and colors on every trigger;
8 RGB frames become a 2x4 contact sheet - the data-diversity technique that
makes sim-trained perception models survive the real world.

Run:  python scripts/05_domain_randomization.py
"""

import os

os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import numpy as np
import omni.replicator.core as rep
from isaacsim.core.api import World
from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.utils.prims import get_prim_at_path
from isaacsim.core.utils.semantics import add_update_semantics
from PIL import Image

NUM_FRAMES = 8
W, H = 960, 540

world = World()
world.scene.add_default_ground_plane()

for i in range(5):
    world.scene.add(
        DynamicCuboid(
            prim_path=f"/World/cube_{i}",
            name=f"cube_{i}",
            position=np.array([i - 2.0, 0.0, 0.5]),
            size=0.5,
            color=np.array([0.7, 0.7, 0.7]),
        )
    )
    add_update_semantics(get_prim_at_path(f"/World/cube_{i}"), semantic_label="cube")

camera = rep.create.camera(position=(5.0, 5.0, 3.0), look_at=(0.0, 0.0, 0.3))
render_product = rep.create.render_product(camera, (W, H))
rgb_anno = rep.AnnotatorRegistry.get_annotator("rgb")
rgb_anno.attach(render_product)

world.reset()


def randomize_cubes():
    shapes = rep.get.prims(semantics=[("class", "cube")])
    with shapes:
        rep.modify.pose(
            position=rep.distribution.uniform((-2.5, -2.5, 0.3), (2.5, 2.5, 1.5)),
            rotation=rep.distribution.uniform((0.0, 0.0, 0.0), (360.0, 360.0, 360.0)),
        )
        rep.randomizer.color(colors=rep.distribution.uniform((0.05, 0.05, 0.05), (1.0, 1.0, 1.0)))
    return shapes.node


rep.randomizer.register(randomize_cubes)

with rep.trigger.on_frame(num_frames=NUM_FRAMES + 2):  # +2: warm-up steps may yield empty data
    rep.randomizer.randomize_cubes()

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
os.makedirs(out_dir, exist_ok=True)

frames = []
attempts = 0
while len(frames) < NUM_FRAMES and attempts < NUM_FRAMES + 4:
    rep.orchestrator.step(rt_subframes=8)
    img = np.asarray(rgb_anno.get_data())
    attempts += 1
    if img.ndim == 3 and img.shape[0] > 0:
        frames.append(img[..., :3].copy())
        print(f"frame {len(frames) - 1}: captured {img.shape}")
    else:
        print(f"warm-up step {attempts}: empty annotator output, skipping")

if len(frames) < NUM_FRAMES:
    print(f"ERROR: only {len(frames)}/{NUM_FRAMES} valid frames captured")
    simulation_app.close()
    raise SystemExit(1)

# 2x4 contact sheet
rows = [np.concatenate(frames[r * 4 : (r + 1) * 4], axis=1) for r in range(2)]
sheet = np.concatenate(rows, axis=0)
sheet_path = os.path.abspath(os.path.join(out_dir, "domain_randomization.png"))
Image.fromarray(sheet).save(sheet_path)
print(f"saved {sheet_path}  sheet shape={sheet.shape}")

simulation_app.close()
print("done.")
