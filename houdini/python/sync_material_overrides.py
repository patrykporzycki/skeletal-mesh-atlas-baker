import hou

def sync_material_overrides(hda_node):
    input_node = hda_node.node("fbx_character_import")
    if input_node is None:
        return
    try:
        geo = input_node.geometry()
    except hou.Error:
        return

    materials = sorted(set(p.attribValue("fbx_material_name") for p in geo.prims() if p.attribValue("fbx_material_name")))
    hda_node.parm("material_overrides").set(len(materials))
    for index, material_name in enumerate(materials, 1):
        hda_node.parm("material_name%d" % index).set(material_name)

