import re, os, hou

node = hou.pwd()
geo = node.geometry()
hda = node.parent()

SUFFIX_RULES = {
    "_bc": "basecolor",
    "_basecolor": "basecolor",
    "_base_color": "basecolor",
    "_diffuse": "basecolor",
    "_albedo": "basecolor",
    "_d": "basecolor",
    "_color": "basecolor",
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
PACKED_SLOTS = {"roughness", "metallic"}

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
    overrides[name] = {
        "base_color": hda.parm("base_color%d" % i).eval(),
        "normal": hda.parm("normal%d" % i).eval(),
        "roughness": hda.parm("roughness%d" % i).eval(),
        "metallic": hda.parm("metallic%d" % i).eval(),
    }

textures_dir_parm = hda.parm("textures_dir")
textures_dir = textures_dir_parm.eval() if textures_dir_parm else ""

mats_net = hou.node("/mat")
shader = None
resolved = {}
for mat in sorted(mats):
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", mat)
    shader = mats_net.node("mat_" + clean)
    if shader is None:
        shader = mats_net.createNode("principledshader::2.0", "mat_" + clean)

    override = overrides.get(mat, {})

    for slot in ("basecolor", "normal", "roughness", "metallic"):
        path = override.get(slot, "")
        if not path and textures_dir:
            for suffix, target in SUFFIX_RULES.items():
                if target != slot and not (target == "packed" and slot in PACKED_SLOTS):
                    continue
                expected = (mat + suffix).lower()
                for filename in os.listdir(textures_dir):
                    stem = os.path.splitext(filename)[0].lower()
                    if stem == expected:
                        path = os.path.join(textures_dir, filename)
                        break
                if path:
                    break
        if path:
            resolved[slot] = path
        else:
            node.addWarning("Brak tekstury %s dla %s" % (slot, mat))

        shader.parm("basecolor_useTexture").set(1 if resolved.get("basecolor") else 0)
        shader.parm("basecolor_texture").set(resolved.get("basecolor", ""))
        shader.parm("baseNormal_useTexture").set(1 if resolved.get("normal") else 0)
        shader.parm("baseNormal_texture").set(resolved.get("normal", ""))
        shader.parm("rough_useTexture").set(1 if resolved.get("roughness") else 0)
        shader.parm("rough_texture").set(resolved.get("roughness", ""))
        shader.parm("metallic_useTexture").set(1 if resolved.get("metallic") else 0)
        shader.parm("metallic_texture").set(resolved.get("metallic", ""))

