import re
import hou

node = hou.pwd()
geo = node.geometry()

LOD_SUFFIX = re.compile(r"^(.*?)(?:[_\s.])?[Ll][Oo][Dd](\d+)$")

if not geo.findPrimAttrib("source_lod"):
    geo.addAttrib(hou.attribType.Prim, "source_lod", 0)

for prim in geo.prims():
    mesh_name = prim.attribValue("name")
    match = LOD_SUFFIX.match(mesh_name)
    prim.setAttribValue("source_lod", int(match.group(2)) if match else 0)