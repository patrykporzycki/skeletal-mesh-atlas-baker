import hou, re, random

CHANNEL_OVERRIDE_PARMS  = {
    "roughness": "roughness_channel",
     "metallic": "metallic_channel",}
SLOTS = ("base_color", "normal", "roughness", "metallic")
DEFAULT_CHANNEL = "RGBA"
CHANNEL_INDEX = {"RGBA": 1, "R": 1, "G": 2, "B": 3, "A": 4}
SLOT_TYPE_NAMES = ("base_color", "normal", "roughness", "metallic", "opacity", "custom")
TYPE_NORMALIZE = {"0":"base_color","1":"normal","2":"roughness","3":"metallic","4":"opacity","5":"custom"}
CHANNEL_NORMALIZE = {"0":"RGBA","1":"R","2":"G","3":"B","4":"A"}
CHANNEL_MAP = {"R": 0, "G": 1, "B": 2, "A": 3, "RGBA": -1, "RGB": -1}

def build_preview_shaders(hda_node):
    materials_network = hou.node("/mat")
    mesh_count = hda_node.parm("meshes").evalAsInt()
    for mesh in range(1, mesh_count + 1):
        material_count_parm = hda_node.parm("material_overrides%d" % mesh)
        if material_count_parm is None:
            continue
        for material in range(1, material_count_parm.evalAsInt() + 1):
            material_name = hda_node.parm("mat_name%d_%d" % (mesh, material)).eval()
            if not material_name:
                continue

            resolved = {}
            slot_count_parm = hda_node.parm("texture_slots%d_%d" % (mesh, material))
            slot_count = slot_count_parm.evalAsInt() if slot_count_parm is not None else 0
            for slot_index in range(1, slot_count + 1):
                slot_type = hda_node.parm("slot_type%d_%d_%d" % (mesh, material, slot_index)).eval()
                slot_type = TYPE_NORMALIZE.get(slot_type, slot_type)
                texture = hda_node.parm("slot_texture%d_%d_%d" % (mesh, material, slot_index)).eval()
                channel = hda_node.parm("slot_channel%d_%d_%d" % (mesh, material, slot_index)).eval()
                channel = CHANNEL_NORMALIZE.get(channel, channel)
                if texture:
                    resolved[slot_type] = (texture, CHANNEL_MAP.get(channel.upper(), -1))

            clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", material_name)
            shader_name = "mat_%d_%s" % (mesh - 1, clean_name)
            shader = materials_network.node(shader_name)
            if shader is None:
                shader = materials_network.createNode("principledshader::2.0", shader_name)

            base_color = resolved.get("base_color")
            shader.parm("basecolor_useTexture").set(1 if base_color else 0)
            shader.parm("basecolorr").set(1.0)
            shader.parm("basecolorg").set(1.0)
            shader.parm("basecolorb").set(1.0)
            shader.parm("basecolor_usePointColor").set(0)
            shader.parm("basecolor_texture").set(base_color[0] if base_color else "")

            normal = resolved.get("normal")
            shader.parm("baseNormal_useTexture").set(1 if normal else 0)
            shader.parm("baseNormal_texture").set(normal[0] if normal else "")

            roughness = resolved.get("roughness")
            shader.parm("rough_useTexture").set(1 if roughness else 0)
            shader.parm("rough_texture").set(roughness[0] if roughness else "")
            shader.parm("rough_monoChannel").set(1 if (not roughness or roughness[1] < 0) else roughness[1] + 1)

            metallic = resolved.get("metallic")
            shader.parm("metallic_useTexture").set(1 if metallic else 0)
            shader.parm("metallic_texture").set(metallic[0] if metallic else "")
            shader.parm("metallic_monoChannel").set(1 if (not metallic or metallic[1] < 0) else metallic[1] + 1)

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
    uvs = (hda_node.node("uvlayout_max"), hda_node.node("uvlayout_fixed"), hda_node.node("uvlayout_rects"))
    for uv in uvs:
        if uv is None:
            return

    for uv in uvs:
        if uv is not None:
            uv.parm("randseed").set(random.randint(0, 100000))

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
    meshes = node.parm("meshes")
    mesh_count = meshes.evalAsInt() if meshes else 0
    for i in range(1, mesh_count + 1):
        inner = node.parm("material_overrides%d" % i)
        if inner is None:
            continue
        for j in range(1, inner.evalAsInt() + 1):
            name = node.parm("mat_name%d_%d" % (i, j)).eval()
            if name:
                materials.append((i - 1, name))
    materials = sorted(set(materials))

    used = set()
    for r in range(node.parm("rects").evalAsInt()):
        for m in range(1, node.parm("mats%d" % r).evalAsInt() + 1):
            value = node.parm("material_name%d_%d" % (r, m)).eval()
            if value:
                used.add(value)

    menu = ["", "(none)"]
    for part, name in materials:
        key = "%d:%s" % (part, name)
        label = "mesh%d / %s" % (part, name)
        if key == current_value or key not in used:
            menu += [key, label]
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
    uvs = (hda_node.node("uvlayout_max"), hda_node.node("uvlayout_fixed"))
    for uv in uvs:
        if uv is None:
            return
    count = hda_node.parm("rects").evalAsInt()

    for uv in uvs:
        uv.parm("rects").set(count + 1)

        uv.parm("rect_use0").set(1)
        uv.parm("rect_center0x").set(0.01)
        uv.parm("rect_center0y").set(0.01)
        uv.parm("rect_size0x").set(0.02)
        uv.parm("rect_size0y").set(0.02)

    for uv_index in range(1, count + 1):
        hda_index = uv_index - 1
        for uv in uvs:
            uv.parm("rect_use%d" % uv_index).setExpression("ch('../rect_use%d')" % hda_index)
            for axis in ("x", "y"):
                uv.parm("rect_size%d%s" % (uv_index, axis)).setExpression(
                    "min(1, ch('../rect_center%d%s') + ch('../rect_size%d%s')/2) - max(0, ch('../rect_center%d%s') - ch('../rect_size%d%s')/2)" % (hda_index, axis, hda_index, axis, hda_index, axis, hda_index, axis)
                )
                uv.parm("rect_center%d%s" % (uv_index, axis)).setExpression(
                    "(max(0, ch('../rect_center%d%s') - ch('../rect_size%d%s')/2) + min(1, ch('../rect_center%d%s') + ch('../rect_size%d%s')/2)) / 2" % (hda_index, axis, hda_index, axis, hda_index, axis, hda_index, axis)
                )

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
    output_node = hda_node.node("null_original_with_mats")
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
    input_node = hda_node.node("switch_skin")
    if input_node is not None:
        try:
            geometry = input_node.geometry()
        except hou.Error:
            geometry = None
        if geometry is None or geometry.findPrimAttrib("fbx_material_name") is None:
            input_node = hda_node.node("fuse_fbx_import")
    else:
        input_node = hda_node.node("fuse_fbx_import")
    if input_node is None:
        return
    input_node.cook(force=True)
    try:
        geo = input_node.geometry()
    except hou.Error:
        return
    if geo is None or geo.findPrimAttrib("fbx_material_name") is None:
        print("[sync_material_overrides] brak fbx_material_name na geometrii!")
        return

    has_part = geo.findPointAttrib("part_id") is not None
    has_name = geo.findPrimAttrib("name") is not None

    mesh_info = {}
    for prim in geo.prims():
        part = 0
        if has_part and len(prim.points()) > 0:
            part = prim.points()[0].attribValue("part_id")
        info = mesh_info.setdefault(part, {"name": "", "materials": set()})
        if has_name and not info["name"]:
            nm = prim.attribValue("name")
            if nm:
                info["name"] = nm
        name = prim.attribValue("fbx_material_name")
        if name:
            info["materials"].add(name)

    old = {}
    old_names = {}
    for i in range(1, hda_node.parm("meshes").evalAsInt() + 1):
        old_names[i - 1] = hda_node.parm("mesh_name%d" % i).eval()
        inner = hda_node.parm("material_overrides%d" % i)
        if inner is None:
            continue
        for j in range(1, inner.evalAsInt() + 1):
            name = hda_node.parm("mat_name%d_%d" % (i, j)).eval()
            if not name:
                continue
            slots = []
            inner = hda_node.parm("texture_slots%d_%d" % (i, j))
            if inner is not None:
                for k in range(1, inner.evalAsInt() + 1):
                    slots.append({
                        "type": hda_node.parm("slot_type%d_%d_%d" % (i, j, k)).eval(),
                        "texture": hda_node.parm("slot_texture%d_%d_%d" % (i, j, k)).eval(),
                        "channel": hda_node.parm("slot_channel%d_%d_%d" % (i, j, k)).eval(),
                    })
            old[(i - 1, name)] = slots

    if mesh_info:
        mesh_total = max(mesh_info) + 1
    else:
        mesh_total = max(1, len(old_names))

    p = hda_node.parm("meshes")
    p.lock(False)
    p.set(mesh_total)
    p.lock(True)

    for part in range(mesh_total):
        idx = part + 1
        info = mesh_info.get(part, {"name": "", "materials": set()})

        p = hda_node.parm("mesh_name%d" % idx)
        p.lock(False)
        p.set(info["name"] if info["name"] else old_names.get(part, ""))
        p.lock(True)

        names = sorted(info["materials"])
        p = hda_node.parm("material_overrides%d" % idx)
        if p is None:
            continue
        p.lock(False)
        p.set(len(names))
        p.lock(True)

        for j, name in enumerate(names, 1):
            p = hda_node.parm("mat_name%d_%d" % (idx, j))
            p.lock(False)
            p.set(name)
            p.lock(True)

            slots = old.get((part, name), [])
            p = hda_node.parm("texture_slots%d_%d" % (idx, j))
            p.lock(False)
            p.set(len(slots))
            for k, slot in enumerate(slots, 1):
                if not isinstance(slot, dict):
                    continue
                hda_node.parm("slot_type%d_%d_%d" % (idx, j, k)).set(slot.get("type", "base_color"))
                hda_node.parm("slot_texture%d_%d_%d" % (idx, j, k)).set(slot.get("texture", ""))
                hda_node.parm("slot_channel%d_%d_%d" % (idx, j, k)).set(slot.get("channel", "RGBA"))

    build_preview_shaders(hda_node)
    dev_view_3d(hda_node)

def cache_menu_data(hda, source_name, cache_key, collect):
    source = hda.node(source_name)
    if source is not None and not source.needsToCook():
        try:
            geometry = source.geometry()
        except hou.Error:
            geometry = None
        if geometry is not None:
            hda.setCachedUserData(cache_key, collect(geometry))
    return hda.cachedUserData(cache_key)

def collect_color_names(geometry):
    names = []
    for attrib in geometry.pointAttribs() + geometry.vertexAttribs():
        name = attrib.name()
        if name == "Cd" or (name.startswith("Cd") and name[2:].isdigit()):
            names.append(name)
    return sorted(set(names))

def sync_vertex_attribs():
    hda = hou.pwd()

    names = cache_menu_data(hda, "attribpromote_cd_vert_to_point", "vertex_attribs", collect_color_names)
    if not names:
        return ["none", "No vertex color"]

    menu = []
    for item in names:
        menu.append(item)
        menu.append(item)
    return menu

def collect_uv_channels(geometry):
    names = []
    seen = set()
    for attrib in geometry.vertexAttribs() + geometry.pointAttribs():
        name = attrib.name()
        if name == "uv" or (len(name) > 2 and name.startswith("uv") and name[2:].isdigit()):
            if name not in seen:
                names.append(name)
                seen.add(name)
    return sorted(set(names))

def sync_uv_channels():
    hda = hou.pwd()

    names = cache_menu_data(hda, "detect_lods", "uv_channels", collect_uv_channels)
    if not names:
        return ["none", "No UV channel"]

    menu = []
    for item in names:
        menu.append(item)
        menu.append(item)
    return menu

def bake_textures(hda_node):
    baker = hda_node.node("maps_baker1")
    if baker is None:
        return
    baker.parm("execute").pressButton()

def collect_lod_source(geometry):
    max_lod = 0
    try:
        if geometry is not None:
            for prim in geometry.prims():
                max_lod = max(max_lod, int(prim.attribValue("source_lod")))
    except hou.Error:
        return max_lod
    return max_lod

def create_lod_source_menu(parm):
    node = parm.node()
    max_lod = cache_menu_data(node, "detect_lods", "lod_source", collect_lod_source)
    if not max_lod:
        max_lod = 0

    menu = ["0", "Generate (polyreduce)"]
    for i in range(1, max_lod + 1):
        menu += [str(i), "Import LOD%d" % i]
    return menu

def import_lods(hda_node):
    detect = hda_node.node("detect_lods")
    if detect is None:
        return
    try:
        geo = detect.geometry()
    except hou.Error:
        return
    if geo is None:
        return

    max_lod = max(geo.primIntAttribValues("source_lod"))

    levels = hda_node.parm("lod_levels")
    if levels is None:
        return
    levels.set(max_lod)

    for i in range(1, max_lod + 1):
        source = hda_node.parm("lod_source%d" % i)
        if source is not None:
            source.set(str(i))

