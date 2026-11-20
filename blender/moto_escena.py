"""
Escena procedural para Blender (probado en 4.0):
una persona camina hacia una moto cruiser (estilo "Harley", sin marcas),
se sube y arranca por una carretera del desierto al atardecer.

Uso (sin interfaz):
  blender -b --factory-startup --python moto_escena.py -- [opciones]

Opciones:
  --out DIR          carpeta de salida (por defecto ./render junto al script)
  --stills 1,90,200  renderiza solo esos fotogramas como PNG
  --res 100          porcentaje de resolución (base 1280x720)
  --samples 32       muestras de EEVEE
  --blend            guarda también el .blend en la carpeta de salida
"""
import bpy
import math
import os
import random
import sys
from mathutils import Matrix, Vector

# ---------------------------------------------------------------- argumentos
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            return argv[i + 1]
        return True
    return default


HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.abspath(arg("--out", os.path.join(HERE, "render")))
STILLS = arg("--stills")
RES = int(arg("--res", "100"))
SAMPLES = int(arg("--samples", "32"))
SAVE_BLEND = bool(arg("--blend", False))
os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
D, C = bpy.data, bpy.context
scene = C.scene
random.seed(7)

# ---------------------------------------------------------------- utilidades


def set_input(node, names, val):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = val
            return node.inputs[n]
    return None


def mat(name, color, metal=0.0, rough=0.5, coat=0.0, emit=None, strength=0.0):
    m = D.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if coat:
        set_input(b, ["Coat Weight", "Clearcoat"], coat)
    if emit:
        set_input(b, ["Emission Color", "Emission"], (*emit, 1))
        set_input(b, ["Emission Strength"], strength)
    return m


def noisy(m, c1, c2, scale=8.0, detail=6.0):
    """Mezcla dos colores con ruido para romper superficies planas."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


def set_parent(obj, parent):
    C.view_layer.update()
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()


def finish(obj, m=None, smooth=True, parent=None, name=None):
    if name:
        obj.name = name
    if m is not None:
        obj.data.materials.clear()
        obj.data.materials.append(m)
    if smooth and obj.type == "MESH":
        for p in obj.data.polygons:
            p.use_smooth = True
        if hasattr(obj.data, "use_auto_smooth"):
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = math.radians(50)
    if parent is not None:
        set_parent(obj, parent)
    return obj


def apply_scale(o):
    for x in C.selected_objects:
        x.select_set(False)
    o.select_set(True)
    C.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def cube(loc, size, m, rot=(0, 0, 0), bevel=0.0, **kw):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = C.active_object
    o.scale = size
    if bevel:
        apply_scale(o)
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    kw.setdefault("smooth", bool(bevel))
    return finish(o, m, **kw)


def cyl(loc, r, depth, m, rot=(0, 0, 0), verts=32, **kw):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth,
                                        location=loc, rotation=rot)
    return finish(C.active_object, m, **kw)


def sphere(loc, scale, m, segs=32, rings=16, rot=(0, 0, 0), **kw):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=1,
                                         location=loc, rotation=rot)
    o = C.active_object
    o.scale = scale if hasattr(scale, "__len__") else (scale,) * 3
    return finish(o, m, **kw)


def tube(p1, p2, r, m, r2=None, verts=20, **kw):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    mid = (p1 + p2) / 2
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length,
                                            location=mid, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2,
                                        depth=d.length, location=mid, rotation=rot)
    return finish(C.active_object, m, **kw)


def path(points, r, m, **kw):
    objs = [tube(a, b, r, m, **kw) for a, b in zip(points, points[1:])]
    kw.pop("verts", None)
    for p in points[1:-1]:
        objs.append(sphere(p, r, m, segs=16, rings=8, **kw))
    return objs


def torus(loc, R, r, m, rot=(0, 0, 0), **kw):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=48,
                                     minor_segments=14, location=loc, rotation=rot)
    return finish(C.active_object, m, **kw)


def arc(name, center, r, width, a0, a1, m, segs=32, **kw):
    """Guardabarros: franja curva alrededor de un eje Y."""
    cx, cy, cz = center
    verts, faces = [], []
    for i in range(segs + 1):
        a = math.radians(a0 + (a1 - a0) * i / segs)
        ca, sa = math.cos(a), math.sin(a)
        re = r - 0.035
        verts += [(cx + re * ca, cy - width / 2, cz + re * sa),
                  (cx + r * ca, cy, cz + r * sa),
                  (cx + re * ca, cy + width / 2, cz + re * sa)]
    for i in range(segs):
        k = 3 * i
        faces += [(k, k + 1, k + 4, k + 3), (k + 1, k + 2, k + 5, k + 4)]
    me = D.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = D.objects.new(name, me)
    C.collection.objects.link(o)
    sol = o.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.012
    o.modifiers.new("sub", "SUBSURF").levels = 1
    return finish(o, m, **kw)


def empty(name, loc=(0, 0, 0), size=0.1):
    o = D.objects.new(name, None)
    o.empty_display_size = size
    o.location = loc
    C.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- materiales
M = {
    "paint": mat("Pintura", (0.32, 0.015, 0.02), metal=0.55, rough=0.22, coat=1.0),
    "chrome": mat("Cromo", (0.92, 0.92, 0.94), metal=1.0, rough=0.07),
    "alu": mat("Aluminio", (0.65, 0.65, 0.66), metal=1.0, rough=0.3),
    "black": mat("NegroBrillo", (0.012, 0.012, 0.014), metal=0.2, rough=0.25, coat=0.6),
    "frame": mat("Chasis", (0.02, 0.02, 0.022), metal=0.4, rough=0.35),
    "rubber": mat("Goma", (0.018, 0.018, 0.02), rough=0.85),
    "leather": mat("CueroAsiento", (0.03, 0.02, 0.015), rough=0.55),
    "lamp": mat("Faro", (1.0, 0.95, 0.85), emit=(1.0, 0.92, 0.75), strength=0.0),
    "tail": mat("Piloto", (0.5, 0.0, 0.0), emit=(1.0, 0.02, 0.0), strength=0.0),
    "amber": mat("Intermitente", (1.0, 0.45, 0.0), rough=0.2),
    "jeans": noisy(mat("Jeans", (0.08, 0.12, 0.25), rough=0.8), (0.06, 0.09, 0.2), (0.11, 0.16, 0.3), 60),
    "jacket": mat("Chaqueta", (0.035, 0.026, 0.022), rough=0.42, coat=0.3),
    "shirt": mat("Camiseta", (0.8, 0.8, 0.78), rough=0.8),
    "skin": mat("Piel", (0.72, 0.48, 0.36), rough=0.5),
    "beard": mat("Barba", (0.09, 0.06, 0.04), rough=0.9),
    "helmet": mat("Casco", (0.015, 0.015, 0.017), metal=0.1, rough=0.2, coat=1.0),
    "glasses": mat("Gafas", (0.01, 0.01, 0.01), metal=0.8, rough=0.05),
    "glove": mat("Guantes", (0.02, 0.018, 0.016), rough=0.5),
    "boot": mat("Botas", (0.12, 0.06, 0.03), rough=0.55),
    "belt": mat("Cinturon", (0.09, 0.05, 0.03), rough=0.5),
    "sand": noisy(mat("Arena", (0.6, 0.4, 0.26), rough=1.0), (0.5, 0.32, 0.2), (0.68, 0.48, 0.32), 0.15),
    "asphalt": noisy(mat("Asfalto", (0.05, 0.05, 0.055), rough=0.75), (0.035, 0.035, 0.04), (0.08, 0.078, 0.08), 3),
    "yellow": mat("LineaAmarilla", (0.85, 0.6, 0.05), rough=0.6),
    "white": mat("LineaBlanca", (0.8, 0.8, 0.78), rough=0.6),
    "mesa": noisy(mat("Meseta", (0.45, 0.2, 0.1), rough=1.0), (0.38, 0.15, 0.08), (0.55, 0.27, 0.14), 0.05),
    "cactus": noisy(mat("Cactus", (0.12, 0.25, 0.1), rough=0.8), (0.08, 0.18, 0.07), (0.15, 0.3, 0.12), 4),
    "rock": noisy(mat("Roca", (0.35, 0.25, 0.2), rough=0.95), (0.25, 0.18, 0.14), (0.45, 0.33, 0.26), 3),
    "wood": mat("Madera", (0.18, 0.11, 0.06), rough=0.9),
    "wire": mat("Cable", (0.02, 0.02, 0.02), rough=0.6),
}

# ================================================================= MOTO
# Ejes locales: +X = adelante, +Y = izquierda del piloto, Z = arriba.
moto = empty("Moto", size=0.5)
RA = Vector((-0.78, 0, 0.34))   # eje trasero
FA = Vector((0.89, 0, 0.34))    # eje delantero
WHEEL_R = 0.34


def wheel(name, center, front=False):
    w = empty(name, center, 0.3)
    set_parent(w, moto)
    rot = (math.pi / 2, 0, 0)
    torus(center, 0.27, 0.07, M["rubber"], rot=rot, parent=w)            # neumático
    torus(center, 0.205, 0.018, M["chrome"], rot=rot, parent=w)          # llanta
    cyl(center, 0.055, 0.16 if not front else 0.2, M["chrome"], rot=rot, parent=w)  # buje
    n = 16
    for i in range(n):
        a = 2 * math.pi * i / n
        side = 0.04 if i % 2 else -0.04
        hub = center + Vector((0.045 * math.cos(a), side, 0.045 * math.sin(a)))
        rim = center + Vector((0.2 * math.cos(a + 0.25), side * 0.3, 0.2 * math.sin(a + 0.25)))
        tube(hub, rim, 0.004, M["chrome"], verts=6, smooth=False, parent=w)
    if front:   # disco de freno
        cyl(center + Vector((0, 0.09, 0)), 0.15, 0.008, M["alu"], rot=rot, parent=w)
    return w


rear_wheel = wheel("RuedaTrasera", RA)
front_wheel = wheel("RuedaDelantera", FA, front=True)
P = moto  # atajo para parent

# Chasis
path([(0.56, 0, 1.0), (-0.05, 0, 0.86), (-0.42, 0, 0.72)], 0.028, M["frame"], parent=P)
tube((0.56, 0, 1.05), (0.64, 0, 0.86), 0.04, M["frame"], parent=P)       # pipa de dirección
for sy in (1, -1):
    path([(0.62, 0, 0.9), (0.38, 0.07 * sy, 0.32), (0.3, 0.07 * sy, 0.16),
          (-0.35, 0.07 * sy, 0.16), (-0.42, 0.07 * sy, 0.4), (-0.42, 0.07 * sy, 0.72)],
         0.022, M["frame"], parent=P)
    tube((-0.42, 0.09 * sy, 0.72), (-0.98, 0.11 * sy, 0.74), 0.018, M["frame"], parent=P)
    tube((-0.38, 0.12 * sy, 0.32), (-0.78, 0.12 * sy, 0.34), 0.025, M["frame"], parent=P)   # basculante
    tube((-0.72, 0.15 * sy, 0.4), (-0.5, 0.14 * sy, 0.7), 0.028, M["chrome"], parent=P)     # amortiguador
    for k in range(6):  # muelle del amortiguador
        t = 0.2 + k * 0.1
        c = Vector((-0.72, 0.15 * sy, 0.4)).lerp(Vector((-0.5, 0.14 * sy, 0.7)), t)
        torus(c, 0.036, 0.007, M["black"], rot=(0, -0.63, 0), parent=P)

# Motor V-twin
cyl((0.02, 0, 0.3), 0.15, 0.24, M["alu"], rot=(math.pi / 2, 0, 0), parent=P)       # cárter
cube((-0.24, 0, 0.3), (0.24, 0.17, 0.16), M["alu"], bevel=0.02, parent=P)           # caja de cambios
base = Vector((0.02, 0, 0.36))
for ang in (25, -25):
    a = Vector((math.sin(math.radians(ang)), 0, math.cos(math.radians(ang))))
    tube(base, base + a * 0.3, 0.062, M["black"], parent=P)
    for k in range(9):
        s = 0.05 + k * 0.025
        tube(base + a * s, base + a * (s + 0.01), 0.092 - k * 0.002, M["black"], parent=P)
    top = base + a * 0.3
    sphere(top + a * 0.015, (0.08, 0.075, 0.035), M["chrome"],
           rot=(0, math.radians(ang), 0), parent=P)     # tapa de balancines
cyl((0.03, -0.17, 0.56), 0.1, 0.05, M["chrome"], rot=(math.pi / 2, 0, 0), parent=P)  # filtro de aire
sphere((-0.12, 0.14, 0.3), (0.22, 0.04, 0.13), M["chrome"], parent=P)               # tapa primaria
cube((-0.5, 0.13, 0.33), (0.6, 0.02, 0.05), M["black"], rot=(0, 0.02, 0), parent=P)  # correa

# Escapes (lado derecho)
path([(0.18, -0.06, 0.6), (0.3, -0.15, 0.46), (0.24, -0.2, 0.26),
      (-0.35, -0.22, 0.22), (-0.65, -0.235, 0.27)], 0.03, M["chrome"], parent=P)
path([(-0.15, -0.06, 0.6), (-0.22, -0.18, 0.46), (-0.38, -0.235, 0.4),
      (-0.62, -0.25, 0.41)], 0.03, M["chrome"], parent=P)
for y, z0, z1 in ((-0.235, 0.27, 0.33), (-0.25, 0.41, 0.45)):
    tube((-0.65, y, z0), (-1.12, y, z1), 0.046, M["chrome"], parent=P)               # silenciador
    cyl((-1.125, y, z1), 0.04, 0.012, M["black"], rot=(0, math.pi / 2, 0), parent=P)

# Depósito y asiento
sphere((0.26, 0, 0.88), (0.3, 0.16, 0.12), M["paint"], rot=(0, math.radians(-6), 0), parent=P)
cube((0.27, 0, 1.0), (0.4, 0.035, 0.012), M["chrome"], rot=(0, math.radians(-6), 0), parent=P)
cyl((0.4, 0, 1.01), 0.04, 0.02, M["chrome"], rot=(0, math.radians(-12), 0), parent=P)  # velocímetro
sphere((-0.24, 0, 0.76), (0.27, 0.17, 0.05), M["leather"], parent=P)                # asiento
sphere((-0.04, 0, 0.8), (0.07, 0.15, 0.05), M["leather"], parent=P)
sphere((-0.6, 0, 0.8), (0.16, 0.14, 0.045), M["leather"], parent=P)                 # pasajero
path([(-0.82, 0.11, 0.74), (-0.86, 0.1, 1.12), (-0.86, -0.1, 1.12), (-0.82, -0.11, 0.74)],
     0.014, M["chrome"], parent=P)                                                   # respaldo
sphere((-0.85, 0, 1.03), (0.04, 0.1, 0.09), M["leather"], parent=P)

# Guardabarros y alforjas
arc("GuardabarrosT", RA, 0.41, 0.27, 25, 205, M["paint"], parent=P)
arc("GuardabarrosD", FA, 0.39, 0.18, 25, 150, M["paint"], parent=P)
for sy in (1, -1):
    cube((-0.74, 0.25 * sy, 0.62), (0.4, 0.12, 0.25), M["leather"], bevel=0.035, parent=P)
    cube((-0.74, 0.312 * sy, 0.68), (0.03, 0.006, 0.1), M["chrome"], parent=P)
sphere((-1.19, 0, 0.47), (0.02, 0.06, 0.03), M["tail"], parent=P)                    # piloto
cube((-1.16, 0, 0.36), (0.012, 0.16, 0.09), M["alu"], parent=P)                      # matrícula

# Horquilla, faro y manillar
for sy in (1, -1):
    tube((0.60, 0.1 * sy, 1.02), (0.89, 0.1 * sy, 0.34), 0.03, M["chrome"], parent=P)
    tube((0.70, 0.1 * sy, 0.79), (0.89, 0.1 * sy, 0.34), 0.038, M["alu"], parent=P)
    sphere((0.72, 0.17 * sy, 0.84), 0.05, M["chrome"], parent=P)                    # faros auxiliares
    cyl((0.765, 0.17 * sy, 0.84), 0.04, 0.01, M["lamp"], rot=(0, math.pi / 2, 0), parent=P)
    tube((0.6, 0.06 * sy, 0.97), (0.62, 0.22 * sy, 0.98), 0.008, M["chrome"], parent=P)
    sphere((0.63, 0.23 * sy, 0.98), (0.03, 0.02, 0.02), M["amber"], parent=P)       # intermitentes
cube((0.6, 0, 1.01), (0.09, 0.28, 0.04), M["chrome"], rot=(0, math.radians(23), 0), bevel=0.01, parent=P)
cube((0.67, 0, 0.86), (0.09, 0.28, 0.04), M["chrome"], rot=(0, math.radians(23), 0), bevel=0.01, parent=P)
cyl((0.73, 0, 0.95), 0.1, 0.14, M["chrome"], rot=(0, math.pi / 2, 0), parent=P)
cyl((0.802, 0, 0.95), 0.088, 0.012, M["lamp"], rot=(0, math.pi / 2, 0), parent=P)
tube((0.58, 0, 1.03), (0.56, 0, 1.1), 0.02, M["chrome"], parent=P)
for sy in (1, -1):
    path([(0.56, 0, 1.1), (0.5, 0.2 * sy, 1.13), (0.36, 0.33 * sy, 1.14), (0.3, 0.355 * sy, 1.135)],
         0.014, M["chrome"], parent=P)
    tube((0.3, 0.355 * sy, 1.135), (0.15, 0.37 * sy, 1.125), 0.02, M["rubber"], parent=P)  # puño
    tube((0.45, 0.28 * sy, 1.13), (0.42, 0.34 * sy, 1.34), 0.007, M["chrome"], parent=P)   # espejo
    sphere((0.42, 0.345 * sy, 1.36), (0.012, 0.05, 0.035), M["chrome"], parent=P)
    cube((0.3, 0.29 * sy, 0.34), (0.3, 0.12, 0.02), M["black"], bevel=0.008, parent=P)     # plataforma
    tube((0.3, 0.07 * sy, 0.3), (0.3, 0.24 * sy, 0.33), 0.015, M["frame"], parent=P)

# Pata de cabra (lado izquierdo)
kick = empty("PataCabra", (0.05, 0.12, 0.22), 0.1)
set_parent(kick, moto)
tube((0.05, 0.12, 0.22), (0.17, 0.33, 0.012), 0.014, M["frame"], parent=kick)

# ================================================================= PERSONAJE
rig_data = D.armatures.new("RigData")
rig = D.objects.new("Persona", rig_data)
C.collection.objects.link(rig)
C.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = rig_data.edit_bones


def bone(name, head, tail, parent=None, connect=False):
    b = eb.new(name)
    b.head, b.tail, b.roll = head, tail, 0.0
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    return b


bone("hips", (0, 0, 0.95), (0, 0, 1.05))
bone("spine", (0, 0, 1.05), (0, 0, 1.42), "hips", True)
bone("neck", (0, 0, 1.42), (0, 0, 1.53), "spine", True)
bone("head", (0, 0, 1.53), (0, 0, 1.78), "neck", True)
for s, sy in (("L", 1), ("R", -1)):
    bone(f"shoulder.{s}", (0, 0.06 * sy, 1.38), (0, 0.19 * sy, 1.40), "spine")
    bone(f"upperarm.{s}", (0, 0.2 * sy, 1.40), (-0.03, 0.22 * sy, 1.12), f"shoulder.{s}")
    bone(f"forearm.{s}", (-0.03, 0.22 * sy, 1.12), (0.03, 0.22 * sy, 0.87), f"upperarm.{s}", True)
    bone(f"hand.{s}", (0.03, 0.22 * sy, 0.87), (0.05, 0.22 * sy, 0.77), f"forearm.{s}", True)
    bone(f"thigh.{s}", (0, 0.1 * sy, 0.93), (0.03, 0.1 * sy, 0.5), "hips")
    bone(f"shin.{s}", (0.03, 0.1 * sy, 0.5), (0, 0.1 * sy, 0.08), f"thigh.{s}", True)
    bone(f"foot.{s}", (0, 0.1 * sy, 0.08), (0.16, 0.1 * sy, 0.02), f"shin.{s}", True)

# Ángulos de polo (para que rodillas y codos apunten donde deben)
KNEE_POLE = {"L": Vector((0.8, 0.12, 0.5)), "R": Vector((0.8, -0.12, 0.5))}
ELBOW_POLE = {"L": Vector((-0.6, 0.45, 1.05)), "R": Vector((-0.6, -0.45, 1.05))}


def pole_angle(base, tip, pole):
    normal = (tip.tail - base.head).cross(pole - base.head)
    proj = normal.cross(base.tail - base.head)
    a = base.x_axis.angle(proj)
    if base.x_axis.cross(proj).dot(base.tail - base.head) < 0:
        a = -a
    return a


POLE_ANG = {}
for s in "LR":
    POLE_ANG["leg" + s] = pole_angle(eb[f"thigh.{s}"], eb[f"shin.{s}"], KNEE_POLE[s])
    POLE_ANG["arm" + s] = pole_angle(eb[f"upperarm.{s}"], eb[f"forearm.{s}"], ELBOW_POLE[s])
bpy.ops.object.mode_set(mode="OBJECT")
rig.select_set(False)

# Cuerpo: piezas sueltas que luego se unen en una malla con grupos de vértices
parts = []


def part(obj, bone_name):
    vg = obj.vertex_groups.new(name=bone_name)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    parts.append(obj)
    return obj


part(sphere((0, 0, 0.93), (0.14, 0.18, 0.12), M["jeans"]), "hips")
part(cyl((0, 0, 1.0), 0.155, 0.05, M["belt"]), "hips")
part(cube((0.155, 0, 1.0), (0.012, 0.06, 0.04), M["chrome"]), "hips")
part(sphere((0, 0, 1.2), (0.14, 0.2, 0.22), M["jacket"]), "spine")
part(sphere((0.005, 0, 1.31), (0.14, 0.22, 0.13), M["jacket"]), "spine")
part(cyl((0, 0, 1.47), 0.052, 0.12, M["skin"]), "neck")
part(sphere((0.01, 0, 1.63), (0.1, 0.092, 0.115), M["skin"]), "head")
part(sphere((-0.012, 0, 1.685), (0.118, 0.108, 0.098), M["helmet"]), "head")
part(cube((0.098, 0, 1.645), (0.02, 0.16, 0.035), M["glasses"], bevel=0.006), "head")
part(sphere((0.112, 0, 1.615), 0.017, M["skin"]), "head")
part(sphere((0.06, 0, 1.56), (0.06, 0.075, 0.05), M["beard"]), "head")
for s, sy in (("L", 1), ("R", -1)):
    part(sphere((0, 0.19 * sy, 1.39), 0.068, M["jacket"]), f"upperarm.{s}")
    part(tube((0, 0.2 * sy, 1.4), (-0.03, 0.22 * sy, 1.12), 0.055, M["jacket"], r2=0.047), f"upperarm.{s}")
    part(sphere((-0.03, 0.22 * sy, 1.12), 0.047, M["jacket"]), f"forearm.{s}")
    part(tube((-0.03, 0.22 * sy, 1.12), (0.03, 0.22 * sy, 0.89), 0.046, M["jacket"], r2=0.04), f"forearm.{s}")
    part(sphere((0.04, 0.22 * sy, 0.83), (0.04, 0.032, 0.065), M["glove"]), f"hand.{s}")
    part(sphere((0, 0.1 * sy, 0.92), 0.08, M["jeans"]), f"thigh.{s}")
    part(tube((0, 0.1 * sy, 0.93), (0.03, 0.1 * sy, 0.5), 0.08, M["jeans"], r2=0.06), f"thigh.{s}")
    part(sphere((0.03, 0.1 * sy, 0.5), 0.06, M["jeans"]), f"shin.{s}")
    part(tube((0.03, 0.1 * sy, 0.5), (0.0, 0.1 * sy, 0.16), 0.058, M["jeans"], r2=0.054), f"shin.{s}")
    part(cyl((0, 0.1 * sy, 0.12), 0.056, 0.13, M["boot"]), f"shin.{s}")
    part(sphere((0.055, 0.1 * sy, 0.045), (0.13, 0.058, 0.05), M["boot"]), f"foot.{s}")

for o in C.selected_objects:
    o.select_set(False)
for o in parts:
    o.select_set(True)
C.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = C.active_object
body.name = "Cuerpo"
body.parent = rig
body.modifiers.new("Esqueleto", "ARMATURE").object = rig

# Controladores IK (en espacio mundo, animados fotograma a fotograma)
E = {}
for s in "LR":
    for kind in ("foot", "hand", "knee", "elbow"):
        E[f"{kind}_{s}"] = empty(f"ctrl_{kind}_{s}", size=0.05)
    E[f"foot_{s}"].rotation_mode = "XYZ"
for s in "LR":
    pb = rig.pose.bones[f"shin.{s}"]
    c = pb.constraints.new("IK")
    c.target, c.pole_target = E[f"foot_{s}"], E[f"knee_{s}"]
    c.pole_angle, c.chain_count = POLE_ANG["leg" + s], 2
    pb = rig.pose.bones[f"forearm.{s}"]
    c = pb.constraints.new("IK")
    c.target, c.pole_target = E[f"hand_{s}"], E[f"elbow_{s}"]
    c.pole_angle, c.chain_count = POLE_ANG["arm" + s], 2
    c = rig.pose.bones[f"foot.{s}"].constraints.new("COPY_ROTATION")
    c.target = E[f"foot_{s}"]
FOOT_REST = {s: rig.data.bones[f"foot.{s}"].matrix_local.to_3x3() for s in "LR"}

# ================================================================= ENTORNO
bpy.ops.mesh.primitive_plane_add(size=800, location=(40, 0, 0))
finish(C.active_object, M["sand"], name="Suelo")
ROAD_Y, ROAD_W = 1.3, 7.6
cube((50, ROAD_Y, 0.002), (240, ROAD_W, 0.004), M["asphalt"], name="Carretera")
for dy in (-0.09, 0.09):
    cube((50, ROAD_Y + dy, 0.0045), (240, 0.1, 0.002), M["yellow"])
for y in (ROAD_Y - ROAD_W / 2 + 0.3, ROAD_Y + ROAD_W / 2 - 0.3):
    cube((50, y, 0.0045), (240, 0.12, 0.002), M["white"])

for i in range(22):   # mesetas lejanas
    x = random.uniform(-90, 220)
    y = random.uniform(-90, -190)
    r = random.uniform(10, 26)
    h = random.uniform(7, 22)
    o = cyl((x, y, h / 2), r, h, M["mesa"], verts=random.choice((7, 8, 9)), smooth=False)
    o.scale = (random.uniform(0.8, 1.8), random.uniform(0.6, 1.1), 1)
    o.rotation_euler.z = random.uniform(0, math.pi)


def cactus(x, y, h):
    cyl((x, y, h / 2), 0.13, h, M["cactus"], verts=12)
    sphere((x, y, h), 0.13, M["cactus"], segs=12, rings=6)
    for side, hh in ((1, random.uniform(0.35, 0.55)), (-1, random.uniform(0.45, 0.65))):
        ax = x + random.uniform(-0.05, 0.05)
        path([(ax, y, h * hh), (ax, y + 0.35 * side, h * hh), (ax, y + 0.35 * side, h * hh + 0.6)],
             0.09, M["cactus"], verts=12)
        sphere((ax, y + 0.35 * side, h * hh + 0.6), 0.09, M["cactus"], segs=12, rings=6)


for i in range(26):
    cactus(random.uniform(-25, 120), random.uniform(-7.5, -40), random.uniform(1.6, 3.6))
for i in range(40):   # rocas
    sphere((random.uniform(-25, 120), random.uniform(-5, -45), 0), (random.uniform(0.3, 1.4),
           random.uniform(0.3, 1.2), random.uniform(0.2, 0.7)), M["rock"], segs=10, rings=6, smooth=False)
for x in range(-28, 180, 14):  # postes de teléfono (dan sensación de velocidad)
    cyl((x, -4.6, 4.0), 0.11, 8.0, M["wood"], verts=10)
    cube((x, -4.6, 7.6), (0.12, 1.6, 0.12), M["wood"])
for dy in (-0.7, 0.7):
    tube((-40, -4.6 + dy, 7.72), (190, -4.6 + dy, 7.72), 0.012, M["wire"], verts=6)

# Cielo y sol
world = D.worlds.new("Cielo")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
sky = wn.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(9)
sky.sun_rotation = math.radians(-70)
sky.sun_disc = False
sky.altitude = 200
world.node_tree.links.new(sky.outputs["Color"], wn["Background"].inputs["Color"])
wn["Background"].inputs["Strength"].default_value = 0.35

sun_data = D.lights.new("Sol", "SUN")
sun_data.energy = 3.2
sun_data.color = (1.0, 0.78, 0.55)
sun_data.angle = math.radians(1.5)
sun = D.objects.new("Sol", sun_data)
C.collection.objects.link(sun)
sun.rotation_euler = (math.radians(76), 0, math.radians(110))

# Cámara
cam_data = D.cameras.new("Camara")
cam_data.lens = 32
cam_data.clip_end = 1000
cam = D.objects.new("Camara", cam_data)
C.collection.objects.link(cam)
scene.camera = cam
cam_target = empty("ObjetivoCamara")
tt = cam.constraints.new("TRACK_TO")
tt.target, tt.track_axis, tt.up_axis = cam_target, "TRACK_NEGATIVE_Z", "UP_Y"

# ================================================================= ANIMACIÓN
FPS = 24
F_WALK, F_TURN = 72, 88               # camina, se gira hacia la moto
F_REACH0, F_REACH1 = 84, 100          # agarra el manillar
F_SW0, F_SW1 = 100, 136               # pasa la pierna por encima
F_LF0, F_LF1 = 140, 152               # pie izquierdo a la plataforma
F_KS0, F_KS1 = 144, 154               # recoge la pata de cabra
F_LIGHT = 150                         # enciende la moto
F_RF0, F_RF1 = 160, 170               # pie derecho a la plataforma
F_GO = 172                            # ¡arranca!
F_END = 288

START = Vector((-2.6, 2.6, 0))
STAND = Vector((-0.05, 0.58, 0))
SEAT = Vector((-0.24, 0, -0.06))      # origen del rig sentado (cadera a 0.89 m)
WALK_YAW = math.atan2(STAND.y - START.y, STAND.x - START.x)
WALK_D = (STAND - START).length
STRIDE = 1.3


def clamp01(x):
    return max(0.0, min(1.0, x))


def sstep(a, b, f):
    t = clamp01((f - a) / (b - a))
    return t * t * (3 - 2 * t)


def V(*a):
    return Vector(a)


def spline(pts, t):
    """Catmull-Rom por una lista de puntos, t en [0,1]."""
    pts = [Vector(p) for p in pts]
    n = len(pts) - 1
    u = clamp01(t) * n
    i = min(int(u), n - 1)
    s = u - i
    p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
    p3 = pts[min(i + 2, n)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3)


def bike_x(f):
    if f <= F_GO:
        return 0.0
    t = (f - F_GO) / FPS
    return 1.5 * t * t if t < 3 else 13.5 + 9.0 * (t - 3)


def walk_state(f):
    u = clamp01((f - 1) / (F_WALK - 1))
    d = WALK_D * (1 - (1 - u) ** 1.6)
    amp = 1 - sstep(0.8, 1.0, u)
    phi = 2 * math.pi * d / STRIDE + 0.6
    return d, amp, phi


def state(f):
    s = {}
    d, amp, phi = walk_state(f)
    sp, cp = math.sin(phi), math.cos(phi)
    yaw = WALK_YAW + (0 - WALK_YAW) * sstep(F_WALK - 4, F_TURN, f)
    loc = START + (STAND - START) * (d / WALK_D)
    loc.z -= 0.035 * sp * sp * amp
    Rz = Matrix.Rotation(yaw, 3, "Z")

    def W(p, base=None, R=None):
        return (base if base is not None else loc) + (R or Rz) @ Vector(p)

    # pies y manos mientras camina (espacio local del personaje)
    foot = {"L": W((0.3 * sp * amp, 0.1, 0.08 + 0.11 * max(0, cp) * amp)),
            "R": W((-0.3 * sp * amp, -0.1, 0.08 + 0.11 * max(0, -cp) * amp))}
    hand = {"L": W((0.04 - 0.17 * sp * amp, 0.25, 0.9)),
            "R": W((0.04 + 0.17 * sp * amp, -0.25, 0.9))}
    lean = 4.0

    # se agarra al manillar
    k = sstep(F_REACH0, F_REACH1, f)
    hand["L"] = hand["L"].lerp(V(0.16, 0.36, 1.16), k)
    hand["R"] = hand["R"].lerp(V(0.15, 0.1, 1.06), k)
    lean += 10 * k

    # pasa la pierna derecha por encima y se sienta
    th = sstep(F_SW0 + 6, F_SW1, f)
    if f > F_SW0:
        loc = spline([STAND, STAND + V(-0.1, -0.28, 0.07), SEAT], th)
    tr = sstep(F_SW0, F_SW1 - 4, f)
    if f > F_SW0:
        foot["R"] = spline([STAND + V(0, -0.1, 0.08), V(-0.45, 0.42, 0.62), V(-0.7, 0.12, 1.18),
                            V(-0.55, -0.26, 0.9), V(-0.26, -0.42, 0.3), V(-0.12, -0.44, 0.08)], tr)
        tl = sstep(F_SW0 + 14, F_SW1, f)
        lift = 0.05 * math.sin(math.pi * tl)
        foot["L"] = (STAND + V(0, 0.1, 0.08)).lerp(V(-0.12, 0.44, 0.08), tl) + V(0, 0, lift)
    lean -= 4 * sstep(F_SW0, F_SW1, f)
    hr = sstep(F_SW1 - 14, F_SW1 + 4, f)
    if hr > 0:
        hand["R"] = spline([V(0.15, 0.1, 1.06), V(0.24, -0.16, 1.22), V(0.16, -0.36, 1.16)], hr)

    # pies a las plataformas
    if f > F_LF0:
        foot["L"] = spline([V(-0.12, 0.44, 0.08), V(0.05, 0.44, 0.3), V(0.28, 0.27, 0.4)],
                           sstep(F_LF0, F_LF1, f))
    if f > F_RF0:
        foot["R"] = spline([V(-0.12, -0.44, 0.08), V(0.08, -0.44, 0.3), V(0.28, -0.27, 0.4)],
                           sstep(F_RF0, F_RF1, f))
    lean += -2 * sstep(F_LF0, F_RF1, f) + 3 * sstep(F_GO, F_GO + 20, f)

    # polos: rodillas hacia delante y afuera al ir sentado
    seated = sstep(F_SW0 + 10, F_LF1, f)
    for side, sy in (("L", 1), ("R", -1)):
        walk_pole = W(KNEE_POLE[side])
        ride_pole = V(0.9, 0.5 * sy, 1.0)
        s["knee_" + side] = walk_pole.lerp(ride_pole, seated)
        s["elbow_" + side] = W(ELBOW_POLE[side] + V(0, 0.1 * sy, 0))

    # moto en marcha
    bx = bike_x(f)
    vib = 0.0025 * math.sin(f * 2.9) * (f >= F_LIGHT)
    off = V(bx, 0, vib)
    if f >= F_SW0:  # a partir de aquí todo es relativo a la moto
        loc = loc + off
        foot = {k2: v + off for k2, v in foot.items()}
        hand = {k2: v + off for k2, v in hand.items()}
        for kk in ("knee_L", "knee_R", "elbow_L", "elbow_R"):
            s[kk] = s[kk] + V(bx, 0, 0)

    s.update(loc=loc, yaw=yaw, foot=foot, hand=hand, lean=lean, bx=bx, vib=vib)
    return s


def key(obj, path_, f):
    obj.keyframe_insert(path_, frame=f)


spine_rest = rig.data.bones["spine"].matrix_local.to_3x3()
head_rest = rig.data.bones["head"].matrix_local.to_3x3()
for pbn in ("spine", "head"):
    rig.pose.bones[pbn].rotation_mode = "QUATERNION"
lamp_nodes = [M["lamp"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"],
              M["tail"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]]

prev_eul = {}
C0, T0 = V(3.1, 3.5, 1.45), V(-0.35, 0.55, 0.85)
for f in range(1, F_END + 1):
    s = state(f)
    rig.location = s["loc"]
    rig.rotation_euler = (0, 0, s["yaw"])
    key(rig, "location", f)
    key(rig, "rotation_euler", f)
    for side in "LR":
        E["foot_" + side].location = s["foot"][side]
        m3 = Matrix.Rotation(s["yaw"], 3, "Z") @ FOOT_REST[side]
        rot = m3.to_euler("XYZ", prev_eul[side]) if side in prev_eul else m3.to_euler("XYZ")
        prev_eul[side] = rot
        E["foot_" + side].rotation_euler = rot
        E["hand_" + side].location = s["hand"][side]
        E["knee_" + side].location = s["knee_" + side]
        E["elbow_" + side].location = s["elbow_" + side]
        for kind in ("foot", "hand", "knee", "elbow"):
            key(E[f"{kind}_{side}"], "location", f)
        key(E["foot_" + side], "rotation_euler", f)
    # inclinación del torso y mirada
    R = Matrix.Rotation(math.radians(s["lean"]), 3, "Y")
    rig.pose.bones["spine"].rotation_quaternion = (spine_rest.inverted() @ R @ spine_rest).to_quaternion()
    look = math.radians(-12 * sstep(F_LIGHT, F_GO, f) * (1 - sstep(F_GO, F_GO + 12, f))
                        + 10 * (1 - sstep(60, F_WALK, f)) - 6 * sstep(F_GO, F_GO + 10, f))
    Rh = Matrix.Rotation(math.radians(-s["lean"] * 0.6), 3, "Y") @ Matrix.Rotation(look, 3, "Z")
    rig.pose.bones["head"].rotation_quaternion = (head_rest.inverted() @ Rh @ head_rest).to_quaternion()
    rig.pose.bones["spine"].keyframe_insert("rotation_quaternion", frame=f)
    rig.pose.bones["head"].keyframe_insert("rotation_quaternion", frame=f)

    # moto, ruedas, pata de cabra, luces
    moto.location = (s["bx"], 0, s["vib"])
    key(moto, "location", f)
    for w in (rear_wheel, front_wheel):
        w.rotation_euler = (0, s["bx"] / WHEEL_R, 0)
        key(w, "rotation_euler", f)
    ks = sstep(F_KS0, F_KS1, f)
    kick.rotation_euler = (math.radians(-35) * ks, math.radians(95) * ks, 0)
    key(kick, "rotation_euler", f)
    on = sstep(F_LIGHT, F_LIGHT + 3, f)
    lamp_nodes[0].default_value = 40 * on
    lamp_nodes[1].default_value = 12 * on
    for n in lamp_nodes:
        n.keyframe_insert("default_value", frame=f)

    # cámara: fija durante la subida, luego acompaña a la moto
    bx = s["bx"]
    w = sstep(F_GO + 4, F_GO + 50, f)
    cam.location = C0 + V(bx * w, 0.5 * sstep(F_GO, F_GO + 60, f), -0.32 * sstep(F_GO, F_GO + 60, f))
    walk_t = s["loc"] + V(0, 0, 0.95)
    tgt = walk_t.lerp(T0, sstep(30, 95, f))
    tgt = tgt.lerp(V(bx + 0.15, 0, 0.8), sstep(F_GO - 6, F_GO + 30, f))
    cam_target.location = tgt
    key(cam, "location", f)
    key(cam_target, "location", f)

# ================================================================= RENDER
scene.frame_start, scene.frame_end = 1, F_END
scene.render.fps = FPS
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.resolution_percentage = RES
ee = scene.eevee
ee.taa_render_samples = SAMPLES
for attr, val in (("use_gtao", True), ("gtao_distance", 0.6), ("use_bloom", True),
                  ("bloom_intensity", 0.04), ("bloom_threshold", 1.2), ("use_ssr", True),
                  ("use_soft_shadows", True), ("shadow_cascade_size", "2048"),
                  ("shadow_cube_size", "1024")):
    if hasattr(ee, attr):
        setattr(ee, attr, val)
sun_data.shadow_cascade_max_distance = 60
for vt, look in (("AgX", "AgX - Punchy"), ("Filmic", "Medium High Contrast")):
    try:
        scene.view_settings.view_transform = vt
        scene.view_settings.look = look
        break
    except TypeError:
        continue
scene.render.image_settings.file_format = "PNG"

if SAVE_BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "moto_escena.blend"))

if STILLS:
    for f in [int(x) for x in str(STILLS).split(",")]:
        scene.frame_set(f)
        scene.render.filepath = os.path.join(OUT_DIR, f"still_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    os.makedirs(os.path.join(OUT_DIR, "frames"), exist_ok=True)
    scene.render.filepath = os.path.join(OUT_DIR, "frames", "f_")
    bpy.ops.render.render(animation=True)
