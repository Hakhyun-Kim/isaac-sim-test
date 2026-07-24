"""OpenUSD authoring: build a sim-ready scene file-first, validate it, simulate it.

Everything before the simulation phase uses the pxr API alone -- no editor,
no Isaac Sim helpers:

  1. Author a reusable cube asset (07_cube_proto.usda): Cube geometry with a
     UsdPhysics collider and a bound UsdPreviewSurface material.
  2. Author a scene (07_scene.usda): physics scene, static ground collider,
     and three cubes that are *instanceable references* to the asset file,
     each with RigidBodyAPI + MassAPI applied on the instance root.
  3. Validate the scene by pure USD traversal: stage metadata, one shared
     prototype for the three instances, physics schemas, material bindings
     resolved through instance proxies.
  4. Open the authored file as-is in headless Isaac Sim and step physics:
     every cube must settle at z ~= 0.250 m (half the 0.5 m cube size).

This is the USD side of simulation-ready asset preparation: if step 4 works,
the file -- not the Python session -- carries all the simulation semantics.

Run:  python scripts/07_openusd_simready.py
"""

import os

os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output"))
os.makedirs(OUT_DIR, exist_ok=True)
PROTO_PATH = os.path.join(OUT_DIR, "07_cube_proto.usda")
SCENE_PATH = os.path.join(OUT_DIR, "07_scene.usda")
RESULTS_PATH = os.path.join(OUT_DIR, "07_results.txt")

CUBE_SIZE = 0.5
CUBE_POSITIONS = [Gf.Vec3d(0.0, 0.0, 1.0), Gf.Vec3d(0.7, 0.15, 1.6), Gf.Vec3d(-0.6, 0.45, 2.2)]
REST_Z = CUBE_SIZE / 2.0

lines = []


def log(msg):
    print(msg)
    lines.append(msg)


def finish(code):
    with open(RESULTS_PATH, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")
    simulation_app.close()
    print("done.")
    raise SystemExit(code)


# ---------------------------------------------------------------- 1. asset
for path in (PROTO_PATH, SCENE_PATH):
    if os.path.exists(path):
        os.remove(path)

proto_stage = Usd.Stage.CreateNew(PROTO_PATH)
UsdGeom.SetStageUpAxis(proto_stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(proto_stage, 1.0)

proto_root = UsdGeom.Xform.Define(proto_stage, "/CubeProto")
proto_stage.SetDefaultPrim(proto_root.GetPrim())

geom = UsdGeom.Cube.Define(proto_stage, "/CubeProto/geom")
geom.GetSizeAttr().Set(CUBE_SIZE)
geom.CreateDisplayColorAttr([Gf.Vec3f(0.2, 0.4, 1.0)])
UsdPhysics.CollisionAPI.Apply(geom.GetPrim())

material = UsdShade.Material.Define(proto_stage, "/CubeProto/Looks/BlueMat")
shader = UsdShade.Shader.Define(proto_stage, "/CubeProto/Looks/BlueMat/Preview")
shader.CreateIdAttr("UsdPreviewSurface")
shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.2, 0.4, 1.0))
shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
UsdShade.MaterialBindingAPI.Apply(geom.GetPrim()).Bind(material)

proto_stage.GetRootLayer().Save()
log(f"authored asset: {PROTO_PATH}")

# ---------------------------------------------------------------- 2. scene
scene_stage = Usd.Stage.CreateNew(SCENE_PATH)
UsdGeom.SetStageUpAxis(scene_stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(scene_stage, 1.0)

world_xform = UsdGeom.Xform.Define(scene_stage, "/World")
scene_stage.SetDefaultPrim(world_xform.GetPrim())

physics_scene = UsdPhysics.Scene.Define(scene_stage, "/World/physicsScene")
physics_scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
physics_scene.CreateGravityMagnitudeAttr(9.81)

ground = UsdGeom.Cube.Define(scene_stage, "/World/ground")
ground.GetSizeAttr().Set(1.0)
ground.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.05))
ground.AddScaleOp().Set(Gf.Vec3f(20.0, 20.0, 0.1))
ground.CreateDisplayColorAttr([Gf.Vec3f(0.5, 0.5, 0.5)])
UsdPhysics.CollisionAPI.Apply(ground.GetPrim())  # collider without RigidBodyAPI = static

sun = UsdLux.DistantLight.Define(scene_stage, "/World/sun")
sun.CreateIntensityAttr(1000.0)

UsdGeom.Scope.Define(scene_stage, "/World/cubes")
for i, pos in enumerate(CUBE_POSITIONS):
    xform = UsdGeom.Xform.Define(scene_stage, f"/World/cubes/cube_{i:02d}")
    prim = xform.GetPrim()
    prim.GetReferences().AddReference("./07_cube_proto.usda")  # relative: both live in output/
    prim.SetInstanceable(True)
    xform.AddTranslateOp().Set(pos)
    UsdPhysics.RigidBodyAPI.Apply(prim)
    UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(1.0)

scene_stage.GetRootLayer().Save()
log(f"authored scene: {SCENE_PATH}")

# ------------------------------------------------------------- 3. validate
del proto_stage, scene_stage
stage = Usd.Stage.Open(SCENE_PATH)
failures = []


def check(name, ok, detail=""):
    log(f"[check] {name:<38} {'OK' if ok else 'FAIL'}  {detail}".rstrip())
    if not ok:
        failures.append(name)


default_prim = stage.GetDefaultPrim()
check("defaultPrim is /World", bool(default_prim) and default_prim.GetPath() == Sdf.Path("/World"))
check("upAxis is Z", UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z)
check("metersPerUnit is 1.0", UsdGeom.GetStageMetersPerUnit(stage) == 1.0)
check("has UsdPhysics.Scene", stage.GetPrimAtPath("/World/physicsScene").IsA(UsdPhysics.Scene))

instances = [p for p in stage.Traverse() if p.IsInstance()]
prototypes = stage.GetPrototypes()
check("3 instanceable cube prims", len(instances) == 3, f"found {len(instances)}")
check("instances share 1 prototype", len(prototypes) == 1, f"{len(prototypes)} prototype(s) on stage")

for i in range(len(CUBE_POSITIONS)):
    root = stage.GetPrimAtPath(f"/World/cubes/cube_{i:02d}")
    proxy = stage.GetPrimAtPath(f"/World/cubes/cube_{i:02d}/geom")
    bound_mat, _ = UsdShade.MaterialBindingAPI(proxy).ComputeBoundMaterial()
    check(f"cube_{i:02d} RigidBodyAPI + MassAPI", root.HasAPI(UsdPhysics.RigidBodyAPI) and root.HasAPI(UsdPhysics.MassAPI))
    check(f"cube_{i:02d} collider via instance proxy", proxy.IsInstanceProxy() and proxy.HasAPI(UsdPhysics.CollisionAPI))
    check(f"cube_{i:02d} material via instance proxy", bool(bound_mat), bound_mat.GetPath().pathString if bound_mat else "none")

total_prims = len(list(stage.Traverse()))
log(f"stage: {total_prims} prims traversed, {len(prototypes)} prototype backing {len(instances)} instances")

if failures:
    log(f"VALIDATION FAILED: {failures}")
    finish(1)
del stage

# ------------------------------------------------------------- 4. simulate
from isaacsim.core.api import World
from isaacsim.core.utils.stage import open_stage

open_stage(SCENE_PATH)
world = World(stage_units_in_meters=1.0)

try:
    from isaacsim.core.prims import SingleRigidPrim
except ImportError:  # pre-5.x namespace fallback
    from omni.isaac.core.prims import RigidPrim as SingleRigidPrim

cubes = [SingleRigidPrim(prim_path=f"/World/cubes/cube_{i:02d}", name=f"cube_{i:02d}") for i in range(len(CUBE_POSITIONS))]

world.reset()
for cube in cubes:
    cube.initialize()

live_stage = world.stage
for step in range(240):  # 4 seconds at 60 Hz
    world.step(render=False)
    if step % 30 == 0:
        rigid_z = [float(c.get_world_pose()[0][2]) for c in cubes]
        usd_z = []
        for i in range(len(cubes)):
            prim = live_stage.GetPrimAtPath(f"/World/cubes/cube_{i:02d}")
            usd_z.append(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()[2])
        log("step {:3d}: rigid z = [{}]  usd z = [{}]".format(
            step,
            ", ".join(f"{z:6.3f}" for z in rigid_z),
            ", ".join(f"{z:6.3f}" for z in usd_z),
        ))

final_z = [float(c.get_world_pose()[0][2]) for c in cubes]
max_err = max(abs(z - REST_Z) for z in final_z)
log("final    : z = [{}]  (expected {:.3f} each, max err {:.4f} m)".format(
    ", ".join(f"{z:6.3f}" for z in final_z), REST_Z, max_err))

if max_err > 0.005:
    log("SIMULATION FAILED: authored scene did not settle at expected height")
    finish(1)

log("PASS: authored USD simulated as-is; all cubes at rest within 5 mm of z = 0.250 m")
finish(0)
