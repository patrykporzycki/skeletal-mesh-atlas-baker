import hou, json


CHANNEL_OVERRIDE_PARMS  = {
    "roughness": "roughness_channel",
     "metallic": "metallic_channel",}
SLOTS = ("base_color", "normal", "roughness", "metallic")
DEFAULT_CHANNEL = 1

def sync_material_overrides(hda_node):

    store = hda_node.parm("material_overrides_store").eval()
    try:
        data = json.loads(store) if store else {}
    except ValueError:
        data = {}

    count = hda_node.parm("material_overrides").evalAsInt()
    for i in range(1, count + 1):
        name = hda_node.parm("material_name%d" % i).eval()
        if not name:
            continue
        data[name] = {
            "base_color": hda_node.parm("base_color%d" % i).eval(),
            "normal": hda_node.parm("normal%d" % i).eval(),
            "roughness": hda_node.parm("roughness%d" % i).eval(),
            "roughness_channel": hda_node.parm("roughness_channel%d" % i).evalAsInt(),
            "metallic": hda_node.parm("metallic%d" % i).eval(),
            "metallic_channel": hda_node.parm("metallic_channel%d" % i).evalAsInt(),
        }

    input_node = hda_node.node("fbx_character_import")
    if input_node is None:
        return
    try:
        geo = input_node.geometry()
    except hou.Error:
        return

    materials = sorted(set(p.attribValue("fbx_material_name") for p in geo.prims() if p.attribValue("fbx_material_name")))

    hda_node.parm("material_overrides").lock(False)
    hda_node.parm("material_overrides").set(len(materials))
    hda_node.parm("material_overrides").lock(True)


    for index, material_name in enumerate(materials, 1):
        hda_node.parm("material_name%d" % index).lock(False)
        hda_node.parm("material_name%d" % index).set(material_name)
        hda_node.parm("material_name%d" % index).lock(True)

        values = data.get(material_name, {})
        hda_node.parm("base_color%d" % index).set(values.get("base_color", ""))
        hda_node.parm("normal%d" % index).set(values.get("normal", ""))
        hda_node.parm("roughness%d" % index).set(values.get("roughness", ""))
        hda_node.parm("roughness_channel%d" % index).set(values.get("roughness_channel", DEFAULT_CHANNEL))
        hda_node.parm("metallic%d" % index).set(values.get("metallic", ""))
        hda_node.parm("metallic_channel%d" % index).set(values.get("metallic_channel", DEFAULT_CHANNEL))


    hda_node.parm("material_overrides_store").set(json.dumps(data))
