"""RTX LiDAR hello: scan a simple scene and dump a point cloud.

Four cubes are placed around an RTX rotary LiDAR (Example_Rotary config).
After the scan accumulates, the point cloud is saved to output/lidar_points.npy
and rasterized into a top-down scatter image at output/lidar_topdown.png.

The miniature version of the sensor-validation workflow I built at 42dot on
CARLA — here with Isaac Sim's ray-traced (RTX) LiDAR instead of raycasts.

Run:  python scripts/06_lidar_pointcloud.py
"""

import os

os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import numpy as np
import omni.kit.commands
import omni.replicator.core as rep
from isaacsim.core.api import World
from isaacsim.core.api.objects import DynamicCuboid
from PIL import Image
from pxr import Gf

world = World()
world.scene.add_default_ground_plane()

# four cubes at different ranges/bearings around the origin
layout = [
    ((2.0, 0.0), (1.0, 0.2, 0.2)),
    ((0.0, 3.0), (0.2, 0.4, 1.0)),
    ((-2.5, -1.0), (1.0, 0.8, 0.1)),
    ((1.5, -2.0), (0.2, 0.8, 0.3)),
]
for i, ((x, y), color) in enumerate(layout):
    world.scene.add(
        DynamicCuboid(
            prim_path=f"/World/cube_{i}",
            name=f"cube_{i}",
            position=np.array([x, y, 0.5]),
            size=1.0,
            color=np.array(color),
        )
    )

# Canonical RTX lidar creation (docs pattern); attach the annotator BEFORE
# the timeline starts so the SDG graph is wired from the first frame.
_, lidar_prim = omni.kit.commands.execute(
    "IsaacSensorCreateRtxLidar",
    path="/World/lidar",
    parent=None,
    config="Example_Rotary",
    translation=(0.0, 0.0, 1.0),
    orientation=Gf.Quatd(1.0, 0.0, 0.0, 0.0),
)
print(f"lidar prim: {lidar_prim.GetPath()}")

render_product = rep.create.render_product(lidar_prim.GetPath(), [1, 1])
# 5.1: the ScanBuffer annotator is deprecated and stayed empty in testing;
# poll the per-frame extractor every step (polling forces graph evaluation)
# and accumulate the rotating scan ourselves. ScanBuffer kept as fallback.
per_frame = rep.AnnotatorRegistry.get_annotator("IsaacExtractRTXSensorPointCloudNoAccumulator")
per_frame.attach(render_product)
scan_buffer = rep.AnnotatorRegistry.get_annotator("IsaacCreateRTXLidarScanBuffer")
scan_buffer.attach(render_product)

world.reset()

chunks = []
for step in range(300):
    world.step(render=True)
    f = per_frame.get_data()
    d = np.asarray(f.get("data", np.empty(0)))
    if d.size:
        chunks.append(d.reshape(-1, 3).copy())
    if step % 50 == 0:
        total = int(sum(c.shape[0] for c in chunks))
        print(f"step {step:3d}: accumulated points = {total}")

points = np.concatenate(chunks, axis=0) if chunks else np.empty((0, 3))
if points.shape[0] == 0:
    sb = scan_buffer.get_data()
    d = np.asarray(sb.get("data", np.empty(0)))
    if d.size:
        points = d.reshape(-1, 3)
    print(f"fallback scan-buffer points: {points.shape[0]}")

print(f"total accumulated points: {points.shape[0]}")
if points.shape[0] == 0:
    print("ERROR: no lidar returns from either annotator")
    simulation_app.close()
    raise SystemExit(1)
finite = points[np.isfinite(points).all(axis=1)]
nonzero = finite[np.linalg.norm(finite, axis=1) > 1e-3]
print(f"point cloud: raw={points.shape[0]} finite={finite.shape[0]} nonzero={nonzero.shape[0]}")

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
os.makedirs(out_dir, exist_ok=True)
npy_path = os.path.abspath(os.path.join(out_dir, "lidar_points.npy"))
np.save(npy_path, nonzero)
print(f"saved {npy_path}")

# top-down rasterization: x/y in [-6, 6] onto 900x900, brightness by height
size, half_range = 900, 6.0
img = np.zeros((size, size, 3), dtype=np.uint8)
pts = nonzero[(np.abs(nonzero[:, 0]) < half_range) & (np.abs(nonzero[:, 1]) < half_range)]
px = ((pts[:, 0] + half_range) / (2 * half_range) * (size - 1)).astype(int)
py = ((half_range - pts[:, 1]) / (2 * half_range) * (size - 1)).astype(int)
z = np.clip((pts[:, 2] + 1.0) / 2.5, 0.0, 1.0)
img[py, px, 0] = (80 + 175 * z).astype(np.uint8)   # height -> warm channel
img[py, px, 1] = (200 * z).astype(np.uint8)
img[py, px, 2] = 90                                 # base tint
img[size // 2 - 3 : size // 2 + 4, size // 2 - 3 : size // 2 + 4] = (255, 255, 255)  # sensor origin
png_path = os.path.abspath(os.path.join(out_dir, "lidar_topdown.png"))
Image.fromarray(img).save(png_path)
print(f"saved {png_path}")

simulation_app.close()
print("done.")
