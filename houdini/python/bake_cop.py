import re, hou

RASTER_AOVS = [
    ("uv_original", "vector2"),
    ("material_id", "int"),
    ("N", "vector3"),
    ("tangentu", "vector3"),
    ("tangentv", "vector3"),
    ("src_tangentu", "vector3"),
    ("src_tangentv", "vector3"),
    ("intrinsic:alpha", "float"),
]

OPENCL_INPUTS = [
    ("normal", "float3"),
    ("src_tangentu", "float3"),
    ("src_tangentv", "float3"),
    ("N", "float3"),
    ("tangentu", "float3"),
    ("tangentv", "float3"),
]

STATIC_NODES = ("sopimport1", "rasterizesetup1", "rasterizegeo1")


def _make_branch(copnet, raster, name, tex_path, ch):
    file = copnet.createNode("file", "bake_file_%s" % name)
    file.parm("filename").set(tex_path)
    file.parm("addaovs").pressButton()
    file.cook(force=True)

    sample = copnet.createNode("sample", "bake_sample_%s" % name)

    sample.setInput(0, raster, 0)
    sample.setInput(2, file, 0)

    out = sample

    if ch >= 0:
        channel_extract = copnet.createNode("channelextract", "bake_ce_%s" % name)
        channel_extract.setInput(0, out, 0)
        channel_extract.parm("channel").set(ch)
        out = channel_extract

    return out


def bake_cop(hda_node):
    hda_node.node("null_repacked_uv").cook(force=True)
    geo = hda_node.node("null_repacked_uv").geometry()
    copnet = hda_node.node("copnet_atlas_baker")

    resolution = hda_node.parm("resolution").eval()
    copnet.parm("res1").set(resolution)
    copnet.parm("res2").set(resolution)

    for child in list(copnet.children()):
        if child.name() not in STATIC_NODES:
            child.destroy()

    sop = copnet.node("sopimport1")
    setup = copnet.node("rasterizesetup1")
    raster = copnet.node("rasterizegeo1")
    setup.setInput(0, sop, 0)
    raster.setInput(1, setup, 0)

    raster = copnet.node("rasterizegeo1")
    raster.parm("attributes").set(len(RASTER_AOVS))
    for i, (name, outtype) in enumerate(RASTER_AOVS, 1):
        raster.parm("name%d" % i).set(name)
        raster.parm("outtype%d" % i).set(outtype)

    slots = list(geo.stringListAttribValue("bake_slots"))

    slot_info = {}
    prims = geo.prims()
    for slot in slots:
        a_path = "tex_" + slot
        a_ch = "tex_" + slot + "_ch"
        a_tbn = "tex_" + slot + "_tbn"
        if not geo.findPrimAttrib(a_path):
            slot_info[slot] = []
            continue

        by_path = {}
        for prim in prims:
            path = prim.attribValue(a_path)
            if not path:
                continue
            ch = prim.attribValue(a_ch)
            tbn = prim.attribValue(a_tbn)
            mid = prim.attribValue("material_id")
            entry = by_path.setdefault(path, [ch, tbn, set()])
            entry[2].add(mid)

        slot_info[slot] = [
            (path, entry[0], entry[1], sorted(entry[2]))
            for path, entry in by_path.items()
        ]

    padding = 8
    out_dir = "$HIP/render"
    frmt = "png"
    asset = "atlas"

    for slot in slots:
        entries = slot_info.get(slot, [])
        if not entries:
            continue

        tex_path, ch, is_tbn, mat_ids = entries[0]

        clean = re.sub(r"[^A-Za-z0-9_]", "_", slot)
        if not clean or clean[0].isdigit():
            clean = "s_" + clean

        branches = []
        for idx, (tex_path, ch, is_tbn, mat_ids) in enumerate(entries):
            out = _make_branch(copnet, raster, "%s_%d" % (clean, idx), tex_path, ch)
            branches.append((out, mat_ids))

        if len(entries) > 1:
            masked = []
            for idx, (out_node, mat_ids) in enumerate(branches):
                for mid in mat_ids:
                    mask = copnet.createNode("idtomask", "bake_idmask_%d_%d" % (idx, mid))
                    mask.setInput(0, raster, 1)
                    mask.parm("group").set(str(mid))

                    mult = copnet.createNode("blend", "bake_mult_%d_%d" % (idx, mid))
                    mult.setInput(0, out_node, 0)
                    mult.setInput(1, mask, 0)
                    mult.parm("mode").set("multiply")
                    masked.append(mult)
            result = masked[0]
            for i, extra in enumerate(masked[1:]):
                add = copnet.createNode("blend", "bake_add_%d" % i)
                add.setInput(0, result, 0)
                add.setInput(1, extra, 0)
                add.parm("mode").set("add")
                result = add
            out = result
        else:
            out = branches[0][0]


        if is_tbn:
            rgb = copnet.createNode("rgbatorgb", "bake_rgb2rgb_%s" % clean)
            rgb.setInput(0, out, 0)

            ocl = copnet.createNode("opencl", "bake_ocl_%s" % clean)
            ocl.parm("inputs").set(len(OPENCL_INPUTS))
            for i, (name, typ) in enumerate(OPENCL_INPUTS, 1):
                ocl.parm("input%d_name" % i).set(name)
                ocl.parm("input%d_type" % i).set(typ)

            ocl.parm("outputs").set(1)
            ocl.parm("output1_name").set("outNormal")
            ocl.parm("output1_type").set("float3")
            ocl.parm("output1_metadata").set("first")

            ocl.setInput(0, rgb, 0)
            ocl.setInput(1, raster, 5)
            ocl.setInput(2, raster, 6)
            ocl.setInput(3, raster, 2)
            ocl.setInput(4, raster, 3)
            ocl.setInput(5, raster, 4)

            kernel = open(hou.getenv("HIP") + "/cop/tbn_transfer.cl").read()
            ocl.parm("kernelcode").set(kernel)

            out = ocl

        extrapolate = copnet.createNode("extrapolateboundaries", "bake_extrap_%s" % clean)
        extrapolate.setInput(0, out, 0)
        extrapolate.setInput(1, raster, 7)
        extrapolate.parm("edgepadding").set(padding)
        extrapolate.parm("side").set(1)
        extrapolate.parm("threshold").set(0.5)

        rop = copnet.createNode("rop_image", "bake_rop_%s" % clean)
        rop.parm("coppath").set(extrapolate.path())
        rop.parm("copoutput").set("%s/%s_%s.%s" % (out_dir, asset, slot, frmt))

        copnet.layoutChildren()

        for child in copnet.children():
            if child.type().name() == "rop_image":
                child.parm("execute").pressButton()


