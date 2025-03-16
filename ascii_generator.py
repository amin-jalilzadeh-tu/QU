"""
ascii_generator.py

Generates a simple ASCII schematic diagram (tree-like) from the 'model' dict
produced by build_network_model.py.

Assumptions:
- We have exactly one "HV_Station" node feeding "MV_Node_0".
- From MV_Node_0, there are several feeders (MV_Node_i),
  each with a transformer to an LV_Node_i,
  which then links to building nodes.

If your model is more complex, you'll need to adapt the logic accordingly.
"""

def generate_ascii_diagram(model):
    """
    Returns a multi-line ASCII string representing the hierarchical layout:
      HV_Station -> MV_Node_0 -> feeders -> T(MV->LV) -> LV_Node -> buildings
    """
    # A helper function to get a node dict by ID
    def get_node_by_id(n_id):
        return next((n for n in model["nodes"] if n["id"] == n_id), None)

    # A helper to find lines from a given from_node
    def get_lines_from(src_id):
        return [l for l in model["lines"] if l["from_node"] == src_id]

    # A helper to find links from a given from_node (for buildings, etc.)
    def get_links_from(src_id):
        return [lk for lk in model["links"] if lk["from_node"] == src_id]

    lines = []

    # 1) Find the HV_Station node
    hv_node = None
    for n in model["nodes"]:
        if n["name"] == "HV_Station":
            hv_node = n
            break

    if hv_node is None:
        return "No HV_Station found in the model!"

    hv_str = f"{hv_node['name']} (id={hv_node['id']})"
    lines.append(hv_str)

    # 2) Find the line from HV_Station to MV_Node_0 (the main MV bus)
    hv_to_mv_line = None
    for l in model["lines"]:
        if l["from_node"] == hv_node["id"]:
            hv_to_mv_line = l
            break

    if hv_to_mv_line is None:
        lines.append("  |-> [No HV->MV connection found!]")
        return "\n".join(lines)

    mv_main = get_node_by_id(hv_to_mv_line["to_node"])
    mv_main_str = f"  |-> {mv_main['name']} (id={mv_main['id']}) [Main MV bus]"
    lines.append(mv_main_str)

    # 3) From MV_Node_0, we look for lines that feed MV_Node_i
    #    i.e. from_node = mv_main["id"], plus the MV->LV transformer line
    feeders = []
    for ln in model["lines"]:
        if ln["from_node"] == mv_main["id"] and "Feeder" in ln["name"]:
            feeders.append(ln)

    # Sort feeders by name or ID (for consistent ordering)
    feeders.sort(key=lambda x: x["name"])

    # 4) For each feeder line, get the MV_Node, then the transformer line -> LV_Node, etc.
    for feeder_line in feeders:
        mv_node_id = feeder_line["to_node"]
        mv_node = get_node_by_id(mv_node_id)
        line_str = f"     └─ {feeder_line['name']}: {mv_node['name']} (id={mv_node_id})"
        lines.append(line_str)

        # Now find the transformer line from that MV_Node to an LV_Node
        tx_line = None
        for l in model["lines"]:
            if l["from_node"] == mv_node_id and "MVtoLV" in l["name"]:
                tx_line = l
                break
        
        if tx_line:
            tx_str = f"         └─ {tx_line['name']} (id={tx_line['id']}) [Transformer]"
            lines.append(tx_str)

            lv_node = get_node_by_id(tx_line["to_node"])
            lv_str = f"            -> {lv_node['name']} (id={lv_node['id']}) [LV bus]"
            lines.append(lv_str)

            # Now find building links from the LV node
            bldg_links = get_links_from(lv_node["id"])
            # Sort them by name or ID for consistent ordering
            bldg_links.sort(key=lambda x: x["name"])

            for bl in bldg_links:
                bldg = get_node_by_id(bl["to_node"])
                b_str = f"               └─ {bldg['name']} (id={bldg['id']}) [Building]"
                lines.append(b_str)
        else:
            lines.append("         [No MV->LV transformer found for this feeder!]")

    return "\n".join(lines)
