import hou, os

node = hou.pwd()
geo = node.geometry()
hda = node.parent()
mod = hda.hdaModule()
CHANNEL_OVERRIDE_PARMS = mod.CHANNEL_OVERRIDE_PARMS
DEFAULT_CHANNEL = mod.DEFAULT_CHANNEL
TYPE_NORMALIZE = mod.TYPE_NORMALIZE
CHANNEL_NORMALIZE = mod.CHANNEL_NORMALIZE

CHANNEL_MAP = {"R": 0, "G": 1, "B": 2, "A": 3, "RGBA": -1, "RGB": -1}
TBN_SLOTS = {"normal"}

fbx_material_name = geo.findPrimAttrib("fbx_material_name")
if fbx_material_name is None:
    raise hou.NodeError("Couldn't find materials!")

mats = set()
for prim in geo.prims():
    name = prim.attribValue("fbx_material_name")
    if name:
        mats.add(name)

overrides = {}
multiparm = hda.parm("material_overrides")
count = multiparm.evalAsInt() if multiparm else 0
for i in range(1, count + 1):
    name = hda.parm("material_name%d" % i).eval()
    if not name:
        continue
    entry = {}
    inner = hda.parm("texture_slots%d" % i)
    if inner is not None:
        for j in range(1, inner.evalAsInt() + 1):
            slot_type = hda.parm("slot_type%d_%d" % (i, j)).eval()
            slot_type = TYPE_NORMALIZE.get(slot_type, slot_type)
            texture = hda.parm("slot_texture%d_%d" % (i, j)).eval()
            channel = hda.parm("slot_channel%d_%d" % (i, j)).eval()
            channel = CHANNEL_NORMALIZE.get(channel, channel)
            if not texture:
                continue
            if not os.path.exists(texture):
                node.addWarning("Brak pliku: %s" % texture)
                continue
            entry[slot_type] = texture
            channel_key = CHANNEL_OVERRIDE_PARMS.get(slot_type)
            if channel_key:
                entry[channel_key] = channel
    overrides[name] = entry

all_slots_names = set()

for mat in sorted(mats):
    resolved = {}

    override = overrides.get(mat, {})

    for slot_name, path in override.items():
        if slot_name.startswith("_") or slot_name.endswith("_channel"):
            continue
        ch_key = CHANNEL_OVERRIDE_PARMS.get(slot_name)
        ch_str = override.get(ch_key, DEFAULT_CHANNEL) if ch_key else DEFAULT_CHANNEL
        ch_idx = CHANNEL_MAP.get(ch_str.upper(), -1)
        is_tbn = 1 if slot_name in TBN_SLOTS else 0
        resolved[slot_name] = (path, ch_idx, is_tbn)

    mat_prims = [p for p in geo.prims() if p.attribValue("fbx_material_name") == mat]

    for slot_name, (path, ch_idx, is_tbn) in resolved.items():
        all_slots_names.add(slot_name)
        attr_path = "tex_" + slot_name
        attr_ch = "tex_" + slot_name + "_ch"
        attr_tbn = "tex_" + slot_name + "_tbn"

        if not geo.findPrimAttrib(attr_path):
            geo.addAttrib(hou.attribType.Prim, attr_path, "")
        if not geo.findPrimAttrib(attr_ch):
            geo.addAttrib(hou.attribType.Prim, attr_ch, -1)
        if not geo.findPrimAttrib(attr_tbn):
            geo.addAttrib(hou.attribType.Prim, attr_tbn, 0)
        for prim in mat_prims:
            prim.setAttribValue(attr_path, path)
            prim.setAttribValue(attr_ch, ch_idx)
            prim.setAttribValue(attr_tbn, is_tbn)

if not geo.findGlobalAttrib("bake_slots"):
    geo.addArrayAttrib(hou.attribType.Global, "bake_slots", hou.attribData.String, 1)
geo.setGlobalAttribValue("bake_slots", list(sorted(all_slots_names)))


if not geo.findPrimAttrib("material_id"):
    geo.addAttrib(hou.attribType.Prim, "material_id", -1)
for idx, mat in enumerate(sorted(mats)):
    for prim in geo.prims():
        if prim.attribValue("fbx_material_name") == mat:
            prim.setAttribValue("material_id", idx)
