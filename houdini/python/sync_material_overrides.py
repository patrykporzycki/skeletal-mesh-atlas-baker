import hou, json, re

CHANNEL_OVERRIDE_PARMS  = {
    "roughness": "roughness_channel",
     "metallic": "metallic_channel",}
SLOTS = ("base_color", "normal", "roughness", "metallic")
DEFAULT_CHANNEL = "RGBA"
CHANNEL_INDEX = {"RGBA": 1, "R": 1, "G": 2, "B": 3, "A": 4}
SLOT_TYPE_NAMES = ("base_color", "normal", "roughness", "metallic", "opacity", "custom")
TYPE_NORMALIZE = {"0":"base_color","1":"normal","2":"roughness","3":"metallic","4":"opacity","5":"custom"}
CHANNEL_NORMALIZE = {"0":"RGBA","1":"R","2":"G","3":"B","4":"A"}

def dev_view_3d(hda_node):
    node = hda_node.node("wrangle_uv_region_color")
    if node:
        node.setDisplayFlag(True)
        node.setRenderFlag(True)

def dev_view_uv(hda_node):
    node = hda_node.node("switch_uv_guide")
    if node:
        node.setDisplayFlag(True)
        node.setRenderFlag(True)

def repack_uv(hda_node):
    filecache = hda_node.node("filecache_uv")
    if filecache is None:
        return
    filecache.parm("loadfromdisk").set(0)
    filecache.parm("execute").pressButton()
    filecache.parm("loadfromdisk").set(1)

def create_rect_materials_menu(parm):
    node = parm.node()
    current_value = parm.eval()

    materials = []
    count = node.parm("material_overrides").evalAsInt()
    for index in range(1, count + 1):
        name = node.parm("material_name%d" % index).eval()
        if name:
            materials.append(name)
    materials = sorted(set(materials))

    used = set()
    for r in range(node.parm("rects").evalAsInt()):
        for m in range(1, node.parm("mats%d" % r).evalAsInt() + 1):
            value = node.parm("material_name%d_%d" % (r, m)).eval()
            if value:
                used.add(value)

    menu = ["", "(none)"]
    for material in materials:
        if material == current_value or material not in used:
            menu += [material, material]
    return menu

def create_slot_type_menu(parm):
    node = parm.node()
    current_value = TYPE_NORMALIZE.get(parm.eval(), parm.eval())

    match = re.match(r"slot_type(\d+)_(\d+)", parm.name())
    if not match:
        menu = []
        for t in SLOT_TYPE_NAMES:
            menu += [t, t.replace("_", " ").title()]
        return menu
    mat_idx = int(match.group(1))
    current_j = int(match.group(2))

    used = set()
    inner = node.parm("texture_slots%d" % mat_idx)
    if inner:
        for j in range(1, inner.evalAsInt() + 1):
            if j == current_j:
                continue
            val = node.parm("slot_type%d_%d" % (mat_idx, j)).eval()
            val = TYPE_NORMALIZE.get(val, val)
            if val:
                used.add(val)
    labels = {"base_color": "Base Color", "normal": "Normal", "roughness": "Roughness",
              "metallic": "Metallic", "opacity": "Opacity", "custom": "Custom"}
    menu = []
    for token in SLOT_TYPE_NAMES:
        if token == current_value or token not in used:
            menu += [token, labels[token]]
    return menu


def sync_rects_to_uv(hda_node):
    uv = hda_node.node("uvlayout1")
    if uv is None:
        return
    count = hda_node.parm("rects").evalAsInt()
    uv.parm("rects").set(count + 1)

    uv.parm("rect_use0").set(1)
    uv.parm("rect_center0x").set(0.01)
    uv.parm("rect_center0y").set(0.01)
    uv.parm("rect_size0x").set(0.02)
    uv.parm("rect_size0y").set(0.02)

    for uv_index in range(1, count + 1):
        hda_index = uv_index - 1
        uv.parm("rect_use%d" % uv_index).setExpression("ch('../rect_use%d')" % hda_index)
        for props in ("center", "size"):
            for axis in ("x", "y"):
                uv.parm("rect_%s%d%s" % (props, uv_index, axis)).setExpression(
                    "ch('../rect_%s%d%s')" % (props, hda_index, axis))


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

def preview_uv_guide_color(hda_node):
    switch_node = hou.node("./switch_uv_guide")

    if switch_node is not None:
        switch_value = switch_node.parm("input").evalAsInt()
        if switch_value == 0:
            switch_node.parm("input").set(switch_value + 1)
        else:
            switch_node.parm("input").set(0)

    scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    if scene_viewer is None:
        return
    viewport = scene_viewer.curViewport()
    if viewport is None:
        return
    for existing in hou.viewportVisualizers.visualizers(
            category=hou.viewportVisualizerCategory.Scene):
        if existing.name() == "preview_uv_guide_color":
            existing.destroy()
            return
    visualizer = hou.viewportVisualizers.createVisualizer(
        hou.viewportVisualizers.type("vis_color"),
        category=hou.viewportVisualizerCategory.Scene)
    visualizer.setName("preview_uv_guide_color")
    visualizer.setLabel("Preview UV Guide Color")
    visualizer.setParm("colortype", "attribasis")
    visualizer.setParm("attrib", "uv_guide_color")
    visualizer.setIsActive(True, viewport=viewport)


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
        all_data = json.loads(store) if store else {}
    except ValueError:
        all_data = {}

    fbx_file = hda_node.parm("fbx_input_file").eval()
    prev_fbx = all_data.get("_last_fbx", "")
    fbx_changed = bool(prev_fbx) and prev_fbx != fbx_file

    if fbx_changed:
        result = {}
        count = hda_node.parm("material_overrides").evalAsInt()
        for i in range(1, count + 1):
            name = hda_node.parm("material_name%d" % i).eval()
            if not name:
                continue
            inner = hda_node.parm("texture_slots%d" % i)
            slots = []
            if inner is not None:
                for j in range(1, inner.evalAsInt() + 1):
                    raw_type = hda_node.parm("slot_type%d_%d" % (i, j)).eval()
                    raw_channel = hda_node.parm("slot_channel%d_%d" % (i, j)).eval()
                    slots.append({
                        "type": TYPE_NORMALIZE.get(raw_type, raw_type),
                        "texture": hda_node.parm("slot_texture%d_%d" % (i, j)).eval(),
                        "channel": CHANNEL_NORMALIZE.get(raw_channel, raw_channel),
                    })
            result[name] = slots
        all_data[prev_fbx] = result
    all_data["_last_fbx"] = fbx_file

    input_node = hda_node.node("fuse_fbx_import")
    if input_node is None:
        return
    try:
        geo = input_node.geometry()
    except hou.Error:
        return
    if geo is None or geo.findPrimAttrib("fbx_material_name") is None:
        print("[sync_material_overrides] brak fbx_material_name na geometrii!")
        return

    materials = sorted(set(
        p.attribValue("fbx_material_name")
        for p in geo.prims()
        if p.attribValue("fbx_material_name")
    ))

    saved = all_data.get(fbx_file, {}) if fbx_changed else {}

    old_mode = hou.updateModeSetting()
    hou.setUpdateMode(hou.updateMode.Manual)
    try:
        hda_node.parm("material_overrides").lock(False)
        hda_node.parm("material_overrides").set(len(materials))
        hda_node.parm("material_overrides").lock(True)

        for index, material_name in enumerate(materials, 1):
            hda_node.parm("material_name%d" % index).lock(False)
            hda_node.parm("material_name%d" % index).set(material_name)
            hda_node.parm("material_name%d" % index).lock(True)

            if fbx_changed:
                slots = saved.get(material_name, [])
                hda_node.parm("texture_slots%d" % index).set(len(slots))
                for j, slot in enumerate(slots, 1):
                    if not isinstance(slot, dict):
                        continue
                    hda_node.parm("slot_type%d_%d" % (index, j)).set(slot.get("type", "base_color"))
                    hda_node.parm("slot_texture%d_%d" % (index, j)).set(slot.get("texture", ""))
                    hda_node.parm("slot_channel%d_%d" % (index, j)).set(slot.get("channel", "RGBA"))

        hda_node.parm("material_overrides_store").set(json.dumps(all_data))
        dev_view_3d(hda_node)
    finally:
        hou.setUpdateMode(old_mode)




def sync_vertex_attribs():
    hda = hou.pwd()
    items = []
    source = hda.node("resolve_materials")
    if source is not None:
        try:
            geo = source.geometry()
            if geo is None:
                return ["none", "No vertex color"]
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

def sync_uv_channels():
    hda = hou.pwd()
    items = []
    source = hda.node("null_reduced_geo")
    if source is not None:
        try:
            geo = source.geometry()
            if geo is None:
                return ["none", "No uv channel"]
            for attrib in geo.vertexAttribs():
                name = attrib.name()
                if name == "uv" or (name.startswith("uv") and name[2:].isdigit()):
                    items.append(name)
        except hou.Error:
            pass

    items = sorted(set(items), key=lambda n: 0 if n == "uv" else int(n[2:]))

    if not items:
        return ["none", "No uv channel"]

    menu = []
    for item in items:
        menu.append(item)
        menu.append(item)
    return menu

def bake_textures(hda_node):
    baker = hda_node.node("maps_baker1")
    if baker is None:
        return
    baker.parm("execute").pressButton()