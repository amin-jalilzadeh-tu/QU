"""
json_generator.py

Converts the 'model' (dict with nodes, lines, links, sources, loads, shunts)
into the requested JSON structure:

{
  "version": "1.0",
  "type": "input",
  "data": {
    "node": [...],
    "line": [...],
    "link": [...],
    "source": [...],
    "sym_load": [...],
    "asym_load": [...],
    "shunt": [...]
  }
}
"""

def generate_json_data(model):
    """
    Transforms the internal model into the required JSON format.
    Returns a Python dict that can be dumped via json.dumps().
    """
    output = {
        "version": "1.0",
        "type": "input",
        "data": {
            "node": [],
            "line": [],
            "link": [],
            "source": [],
            "sym_load": [],
            "asym_load": [],
            "shunt": []
        }
    }

    # 1) Map model["nodes"] -> "node"
    for nd in model["nodes"]:
        # Example node format:
        # { "id": 1, "u_rated": 10000, "extra": "First Node" }
        output["data"]["node"].append({
            "id": nd["id"],
            "u_rated": nd["u_rated"],
            "extra": nd["name"]  # store the node's "name" in 'extra'
        })

    # 2) Map model["lines"] -> "line"
    #    lines have r1, x1, i_n, from_node, to_node
    for ln in model["lines"]:
        # Example line format:
        # {
        #   "id": 4, "from_node": 1, "to_node": 2,
        #   "r1": 10.0, "x1": 0.0, "i_n": 1000
        # }
        output["data"]["line"].append({
            "id": ln["id"],
            "from_node": ln["from_node"],
            "to_node": ln["to_node"],
            "r1": ln.get("r1", 0.0),
            "x1": ln.get("x1", 0.0),
            "i_n": ln.get("i_n", 9999)
        })

    # 3) Map model["links"] -> "link"
    #    links are simpler, no R/X. Example format:
    #    { "id": 5, "from_node": 2, "to_node": 3 }
    for lk in model["links"]:
        output["data"]["link"].append({
            "id": lk["id"],
            "from_node": lk["from_node"],
            "to_node": lk["to_node"]
        })

    # 4) Map model["sources"] -> "source"
    #    Format from example:
    #    { "id": 6, "node": 1, "status": 1, "u_ref": 1.05 }
    for s in model["sources"]:
        output["data"]["source"].append({
            "id": s["id"],
            "node": s["node"],
            "status": s.get("status", 1),
            "u_ref": s.get("u_ref", 1.0)
        })

    # 5) Map model["loads"] -> "sym_load"
    #    Format from example:
    #    {
    #      "id": 7, "node": 3, "status": 1, "type": 1,
    #      "p_specified": 500000
    #    }
    #    We'll treat 'p_kW' as p_specified in watts.
    for ld in model["loads"]:
        p_watts = ld.get("p_kW", 0.0) * 1000.0
        output["data"]["sym_load"].append({
            "id": ld["id"],
            "node": ld["node"],
            "status": ld.get("status", 1),
            "type": ld.get("type", 1),
            "p_specified": p_watts
        })

    # 6) Map model["shunts"] -> "shunt"
    #    Format from example:
    #    { "id": 9, "node": 3, "status": 1, "g1": 0.015 }
    for sh in model["shunts"]:
        output["data"]["shunt"].append({
            "id": sh["id"],
            "node": sh["node"],
            "status": sh.get("status", 1),
            "g1": sh.get("g1", 0.0)
        })

    return output
