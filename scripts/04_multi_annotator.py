"""Multi-annotator synthetic data: RGB + depth + semantic segmentation.

The three-cube scene from script 02, with semantic class labels on each cube.
One render product feeds three Replicator annotators, producing pixel-aligned
RGB / depth / segmentation images - the ground-truth triplet used to train
perception models.

Run:  python scripts/04_multi_annotator.py
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

world = World()
world.scene.add_default_ground_plane()

cubes = [
    ("cube_red", (0.0, 0.0), (1.0, 0.2, 0.2)),
    ("cube_blue", (0.8, 0.3), (0.2, 0.4, 1.0)),
    ("cube_yellow", (-0.6, 0.5), (1.0, 0.8, 0.1)),
]
for i, (label, (x, y), color) in enumerate(cubes):
    world.scene.add(
        DynamicCuboid(
            prim_path=f"/World/cube_{i}",
            name=label,
            position=np.array([x, y, 0.5 + i * 0.7]),
            size=0.4,
            color=np.array(color),
        )
    )
    add_update_semantics(get_prim_at_path(f"/World/cube_{i}"), semantic_label=label)

camera = rep.create.camera(position=(3.0, 3.0, 2.5), look_at=(0.0, 0.0, 0.3))
render_product = rep.create.render_product(camera, (1280, 720))

rgb_anno = rep.AnnotatorRegistry.get_annotator("rgb")
depth_anno = rep.AnnotatorRegistry.get_annotator("distance_to_image_plane")
seg_anno = rep.AnnotatorRegistry.get_annotator("semantic_segmentation", init_params={"colorize": True})
for anno in (rgb_anno, depth_anno, seg_anno):
    anno.attach(render_product)

world.reset()

for _ in range(120):  # let the cubes fall and settle
    world.step(render=True)

rep.orchestrator.step(rt_subframes=4)

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
os.makedirs(out_dir, exist_ok=True)


def save(name, array):
    path = os.path.abspath(os.path.join(out_dir, name))
    Image.fromarray(array).save(path)
    print(f"saved {path}")


rgb = np.asarray(rgb_anno.get_data())
save("multi_rgb.png", rgb[..., :3])

depth = np.asarray(depth_anno.get_data())
finite = np.isfinite(depth)
print(f"depth range: {depth[finite].min():.2f} .. {depth[finite].max():.2f} m")
clipped = np.clip(np.nan_to_num(depth, nan=8.0, posinf=8.0), 0.0, 8.0)
save("multi_depth.png", (255 - clipped / 8.0 * 255).astype(np.uint8))  # near = bright

seg = seg_anno.get_data()
seg_img = np.asarray(seg["data"])
labels = seg["info"].get("idToLabels", {})
print(f"segmentation labels: {labels}")
save("multi_semantic.png", seg_img[..., :3] if seg_img.ndim == 3 else seg_img)

simulation_app.close()
print("done.")
