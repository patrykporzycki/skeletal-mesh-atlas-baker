import re, os, hou

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

SUFFIX_RULES = {
    "_bc": "_base_color",
    "_base_color": "_base_color",
    "_basecolor": "_base_color",
    "_diffuse": "_base_color",
    "_albedo": "_base_color",
    "_d": "_base_color",
    "_color": "_base_color",
    "_n": "normal",
    "_normal": "normal",
    "_r": "roughness",
    "_roughness": "roughness",
    "_metallic": "metallic",
    "_arm": "packed",
    "_orm": "packed",
    "_masks": "packed",
    "_mask": "packed",
    "_m": "packed",
}

fbx_material_name = geo.findPrimAttrib("fbx_material_name")
if fbx_material_name is None:
    raise hou.NodeError("Brak materiału na wejściu!")

mats = set()
for prim in geo.prims():
    name = prim.attribValue("fbx_material_name")
    if name:
        mats.add(name)

textures_dir = hda.parm("textures_dir").eval()

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
            entry[slot_type] = texture
            channel_key = CHANNEL_OVERRIDE_PARMS.get(slot_type)
            if channel_key:
                entry[channel_key] = channel
    overrides[name] = entry

textures_dir_parm = hda.parm("textures_dir")
textures_dir = textures_dir_parm.eval() if textures_dir_parm else ""

mats_net = hou.node("/mat")
shader = None

for mat in sorted(mats):
    resolved = {}
    resolved_channel = {}

    clean = re.sub(r"[^a-zA-Z0-9_]", "_", mat)
    shader = mats_net.node("mat_" + clean)
    if shader is None:
        shader = mats_net.createNode("principledshader::2.0", "mat_" + clean)

    override = overrides.get(mat, {})

    channel = DEFAULT_CHANNEL
    for slot in SLOTS:

        path = override.get(slot, "")
        if path:
            channel_override_key = CHANNEL_OVERRIDE_PARMS.get(slot)
            if channel_override_key:
                channel = override.get(channel_override_key, DEFAULT_CHANNEL)
        elif textures_dir:
            expected_slot = None
            for suffix, target in SUFFIX_RULES.items():
                if target != slot:
                    continue
                expected = (mat + suffix).lower()
                for filename in os.listdir(textures_dir):
                    stem = os.path.splitext(filename)[0].lower()
                    if stem == expected:
                        path = os.path.join(textures_dir, filename)
                        expected_slot = target
                        break
                if path:
                    break
        if path:
            resolved[slot] = path
            resolved_channel[slot] = channel
        else:
            node.addWarning("Brak tekstury %s dla %s" % (slot, mat))

    shader.parm("basecolor_useTexture").set(1 if resolved.get("base_color") else 0)
    shader.parm("basecolorr").set(1.0)
    shader.parm("basecolorg").set(1.0)
    shader.parm("basecolorb").set(1.0)
    shader.parm("basecolor_usePointColor").set(0)
    shader.parm("basecolor_texture").set(resolved.get("base_color", ""))
    shader.parm("baseNormal_useTexture").set(1 if resolved.get("normal") else 0)
    shader.parm("baseNormal_texture").set(resolved.get("normal", ""))
    shader.parm("rough_useTexture").set(1 if resolved.get("roughness") else 0)
    shader.parm("rough_texture").set(resolved.get("roughness", ""))
    shader.parm("rough_monoChannel").set(CHANNEL_INDEX.get(resolved_channel.get("roughness", DEFAULT_CHANNEL), 1))
    shader.parm("metallic_useTexture").set(1 if resolved.get("metallic") else 0)
    shader.parm("metallic_texture").set(resolved.get("metallic", ""))
    shader.parm("metallic_monoChannel").set(CHANNEL_INDEX.get(resolved_channel.get("metallic", DEFAULT_CHANNEL), 1))




