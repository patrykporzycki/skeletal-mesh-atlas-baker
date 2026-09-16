import hou, json

CHANNEL_OVERRIDE_PARMS  = {
    "roughness": "roughness_channel",
     "metallic": "metallic_channel",}
SLOTS = ("base_color", "normal", "roughness", "metallic")
DEFAULT_CHANNEL = 1

def start_paint(hda_node):
    paint_node = hda_node.node("paint_preserve")
    if paint_node is None:
        return
    for pane_tab in hou.ui.paneTabs():
        pane_type = pane_tab.type()
        if pane_type == hou.paneTabType.Parm:
            pane_tab.setCurrentNode(hda_node)
            pane_tab.setPin(True)
        elif pane_type == hou.paneTabType.NetworkEditor:
            pane_tab.setPin(True)
    paint_node.setSelected(True, clear_all_selected=True, show_asset_if_selected=True)
    paint_node.setDisplayFlag(True)
    scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    if scene_viewer is not None:
        scene_viewer.enterCurrentNodeState()


def stop_paint(hda_node):
    output_node = hda_node.node("null_reduced_geo")
    if output_node is None:
        return
    output_node.setDisplayFlag(True)
    scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    if scene_viewer is not None:
        scene_viewer.enterViewState()
    hda_node.setSelected(True, clear_all_selected=True)
    for pane_tab in hou.ui.paneTabs():
        if pane_tab.type() in (hou.paneTabType.Parm, hou.paneTabType.NetworkEditor):
            pane_tab.setPin(False)

def reset_paint(hda_node):
    paint_node = hda_node.node("paint_preserve")
    if paint_node is None:
        return
    reset_parm = paint_node.parm("reset")
    if reset_parm is None:
        return
    reset_parm.pressButton()

def preview_vertex_color(hda_node):
    scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    if scene_viewer is None:
        return
    viewport = scene_viewer.curViewport()
    if viewport is None:
        return
    for existing in hou.viewportVisualizers.visualizers(
            category=hou.viewportVisualizerCategory.Scene):
        if existing.name() == "preview_vertex_color":
            existing.destroy()
            return
    attrib_name = hda_node.parm("vertex_color_attrib").evalAsString()
    visualizer = hou.viewportVisualizers.createVisualizer(
        hou.viewportVisualizers.type("vis_color"),
        category=hou.viewportVisualizerCategory.Scene)
    visualizer.setName("preview_vertex_color")
    visualizer.setLabel("Preview Vertex Color")
    visualizer.setParm("colortype", "attribramped")
    visualizer.setParm("attrib", attrib_name)
    visualizer.setIsActive(True, viewport=viewport)

def hide_preview(hda_node):
    for existing in hou.viewportVisualizers.visualizers(
            category=hou.viewportVisualizerCategory.Scene):
        if existing.name() == "preview_vertex_color":
            existing.destroy()
            return

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


def sync_vertex_attribs():
    hda = hou.pwd()
    items = []
    source = hda.node("resolve_materials")
    if source is not None:
        try:
            geo = source.geometry()
            for attrib in geo.pointAttribs():
                name = attrib.name()
                if name == "Cd" or (name.startswith("Cd") and name[2:].isdigit()):
                    items.append(name)
        except hou.Error:
            pass

    items = sorted(set(items), key=lambda n: 0 if n == "Cd" else int(n[2:]))

    if not items:
        return ["none", "No vertex color"]

    menu = []
    for item in items:
        menu.append(item)
        menu.append(item)
    return menu