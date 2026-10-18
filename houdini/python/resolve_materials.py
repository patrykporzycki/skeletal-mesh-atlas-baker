import re, hou

node = hou.pwd()
geo = node.geometry()
hda = node.parent()
mod = hda.hdaModule()
SLOTS = mod.SLOTS
CHANNEL_OVERRIDE_PARMS = mod.CHANNEL_OVERRIDE_PARMS
DEFAULT_CHANNEL = mod.DEFAULT_CHANNEL
CHANNEL_INDEX = mod.CHANNEL_INDEX
TYPE_NORMALIZE = mod.TYPE_NORMALIZE
CHANNEL_NORMALIZE = mod.CHANNEL_NORMALIZE

CHANNEL_MAP = {"R": 0, "G": 1, "B": 2, "A": 3, "RGBA": -1, "RGB": -1}
TBN_SLOTS = {"normal"}

fbx_material_name = geo.findPrimAttrib("fbx_material_name")
if fbx_material_name is None:
    raise hou.NodeError("Couldn't find materials!")

has_part = geo.findPointAttrib("part_id") is not None

def part_of(prim):
    if has_part and len(prim.points()) > 0:
        return prim.points()[0].attribValue("part_id")
    return 0

mats = set()
for prim in geo.prims():
    name = prim.attribValue("fbx_material_name")
    if name:
        mats.add((part_of(prim), name))

overrides = {}
meshes = hda.parm("meshes")
mesh_count = meshes.evalAsInt() if meshes else 0
for i in range(1, mesh_count + 1):
    inner = hda.parm("material_overrides%d" % i)
    if inner is None:
        continue
    for j in range(1, inner.evalAsInt() + 1):
        name = hda.parm("mat_name%d_%d" % (i, j)).eval()
        if not name:
            continue
        entry = {}
        ts = hda.parm("texture_slots%d_%d" % (i, j))
        if ts is not None:
            for k in range(1, ts.evalAsInt() + 1):
                slot_type = hda.parm("slot_type%d_%d_%d" % (i, j, k)).eval()
                slot_type = TYPE_NORMALIZE.get(slot_type, slot_type)
                texture = hda.parm("slot_texture%d_%d_%d" % (i, j, k)).eval()
                channel = hda.parm("slot_channel%d_%d_%d" % (i, j, k)).eval()
                channel = CHANNEL_NORMALIZE.get(channel, channel)
                if not texture:
                    continue
                entry[slot_type] = texture
                channel_key = CHANNEL_OVERRIDE_PARMS.get(slot_type)
                if channel_key:
                    entry[channel_key] = channel
        overrides[(i - 1, name)] = entry

mats_net = hou.node("/mat")
shader = None

all_slots_names = set()

for mat in sorted(mats):
    part, name = mat
    resolved = {}

    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    shader_name = "mat_%d_%s" % (part, clean)
    shader = mats_net.node(shader_name)
    if shader is None:
        shader = mats_net.createNode("principledshader::2.0", shader_name)

    override = overrides.get(mat, {})

    for slot_name, path in override.items():
        if slot_name.startswith("_") or slot_name.endswith("_channel"):
            continue
        ch_key = CHANNEL_OVERRIDE_PARMS.get(slot_name)
        ch_str = override.get(ch_key, DEFAULT_CHANNEL) if ch_key else DEFAULT_CHANNEL
        ch_idx = CHANNEL_MAP.get(ch_str.upper(), -1)
        is_tbn = 1 if slot_name in TBN_SLOTS else 0
        resolved[slot_name] = (path, ch_idx, is_tbn)

    bc = resolved.get("base_color")
    shader.parm("basecolor_useTexture").set(1 if bc else 0)
    shader.parm("basecolorr").set(1.0)
    shader.parm("basecolorg").set(1.0)
    shader.parm("basecolorb").set(1.0)
    shader.parm("basecolor_usePointColor").set(0)
    shader.parm("basecolor_texture").set(bc[0] if bc else "")
    norm = resolved.get("normal")
    shader.parm("baseNormal_useTexture").set(1 if norm else 0)
    shader.parm("baseNormal_texture").set(norm[0] if norm else "")
    rough = resolved.get("roughness")
    shader.parm("rough_useTexture").set(1 if rough else 0)
    shader.parm("rough_texture").set(rough[0] if rough else "")
    rough_ch = 1 if (not rough or rough[1] < 0) else (rough[1] + 1)
    shader.parm("rough_monoChannel").set(rough_ch)
    metal = resolved.get("metallic")
    shader.parm("metallic_useTexture").set(1 if metal else 0)
    shader.parm("metallic_texture").set(metal[0] if metal else "")
    metal_ch = 1 if (not metal or metal[1] < 0) else (metal[1] + 1)
    shader.parm("metallic_monoChannel").set(metal_ch)

if not geo.findGlobalAttrib("bake_slots"):
    geo.addArrayAttrib(hou.attribType.Global, "bake_slots", hou.attribData.String, 1)
geo.setGlobalAttribValue("bake_slots", list(sorted(all_slots_names)))