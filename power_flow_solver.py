"""
power_flow_solver.py

A dummy "power flow solver" that can:
  - read input JSON from a file and write sym_output.json / asym_output.json
  - or, solve in memory (no disk files) and return results as dict

In a real scenario, you'd parse the input more thoroughly,
run a real solver, and produce real results.
"""

import json
import random

def run_power_flow_sym(input_data, params_data=None):
    """
    Runs a dummy symmetrical power flow solution,
    returns a dict matching a 'sym_output.json' structure.

    input_data: a dict (the parsed JSON "input" with data.node, data.line, etc.)
    params_data: solver settings (ignored here, but in real solver you'd use them)
    """
    sym_output = {
        "version": "1.0",
        "type": "sym_output",
        "data": {
            "node": [],
            "line": [],
            "shunt": []
        }
    }

    # For each node in input_data["data"]["node"], create dummy results
    for nd in input_data["data"].get("node", []):
        node_id = nd["id"]
        # random p.u. voltage
        u_pu = round(random.uniform(0.90, 1.06), 3)
        # random injection
        p_dummy = round(random.uniform(-1e6, 2e6), 1)

        node_entry = {
            "id": node_id,
            "u_pu": u_pu
        }
        if random.random() < 0.7:
            node_entry["p"] = p_dummy

        sym_output["data"]["node"].append(node_entry)

    # lines
    for ln in input_data["data"].get("line", []):
        line_id = ln["id"]
        i_from = round(random.uniform(10, 200), 3)
        line_entry = {
            "id": line_id,
            "i_from": i_from
        }
        sym_output["data"]["line"].append(line_entry)

    # shunts
    for sh in input_data["data"].get("shunt", []):
        shunt_id = sh["id"]
        i_shunt = round(random.uniform(1, 50), 3)
        p_shunt = round(i_shunt * 14600, 1)
        shunt_entry = {
            "id": shunt_id,
            "i": i_shunt,
            "p": p_shunt
        }
        sym_output["data"]["shunt"].append(shunt_entry)

    return sym_output


def run_power_flow_asym(input_data, params_data=None):
    """
    Runs a dummy unbalanced (three-phase) power flow.
    Returns a dict shaped like 'asym_output.json'.

    We'll store 3-phase arrays for voltages, power, etc.
    """
    asym_output = {
        "version": "1.0",
        "type": "asym_output",
        "data": {
            "node": [],
            "line": [],
            "shunt": []
        }
    }

    for nd in input_data["data"].get("node", []):
        node_id = nd["id"]
        u_phases = [round(random.uniform(0.90, 1.05), 3) for _ in range(3)]
        p_phases = [round(random.uniform(-500000, 700000), 1) for _ in range(3)]

        node_entry = {
            "id": node_id,
            "u_pu": u_phases
        }
        if random.random() < 0.8:
            node_entry["p"] = p_phases

        asym_output["data"]["node"].append(node_entry)

    for ln in input_data["data"].get("line", []):
        line_id = ln["id"]
        i_phases = [round(random.uniform(5, 150), 3) for _ in range(3)]
        line_entry = {
            "id": line_id,
            "i_from": i_phases
        }
        asym_output["data"]["line"].append(line_entry)

    for sh in input_data["data"].get("shunt", []):
        shunt_id = sh["id"]
        i_shunt_phases = [round(random.uniform(1, 30), 3) for _ in range(3)]
        p_shunt_phases = [round(i * 18000, 1) for i in i_shunt_phases]
        shunt_entry = {
            "id": shunt_id,
            "i": i_shunt_phases,
            "p": p_shunt_phases
        }
        asym_output["data"]["shunt"].append(shunt_entry)

    return asym_output


def solve_power_flow_in_memory(input_dict, params_data=None):
    """
    Runs the power flow solver *in memory* (no files). 
    Returns:
      {
        "sym": {... sym_output ...},
        "asym": {... asym_output ...}
      }

    :param input_dict: the 'input.json' structure as a Python dict
    :param params_data: optional solver parameters
    """
    sym_results = run_power_flow_sym(input_dict, params_data)
    asym_results = run_power_flow_asym(input_dict, params_data)
    return {"sym": sym_results, "asym": asym_results}


def solve_power_flow(input_json_path, params_json_path=None,
                     sym_out_path="sym_output.json",
                     asym_out_path="asym_output.json"):
    """
    High-level function:
      1) Reads the input JSON (network model or input data) from file
      2) (Optional) reads solver params
      3) Runs symmetrical and asymmetrical PF
      4) Writes the results to sym_out_path, asym_out_path
    """
    # 1) Read input JSON
    with open(input_json_path, "r") as f:
        input_data = json.load(f)

    # 2) If we have solver params
    params_data = None
    if params_json_path:
        with open(params_json_path, "r") as f:
            params_data = json.load(f)

    # 3) Run symmetrical PF
    sym_results = run_power_flow_sym(input_data, params_data)

    # 4) Run asymmetrical PF
    asym_results = run_power_flow_asym(input_data, params_data)

    # 5) Write results
    with open(sym_out_path, "w") as f_sym:
        json.dump(sym_results, f_sym, indent=2)

    with open(asym_out_path, "w") as f_asym:
        json.dump(asym_results, f_asym, indent=2)

    print(f"Symmetrical results written to: {sym_out_path}")
    print(f"Asymmetrical results written to: {asym_out_path}")


# Example usage
if __name__ == "__main__":
    # If you run: python power_flow_solver.py
    # We'll do a quick demonstration of the in-memory function
    dummy_input = {
        "version": "1.0",
        "type": "input",
        "data": {
            "node": [{"id": 1}, {"id": 2}],
            "line": [{"id": 3, "from_node": 1, "to_node": 2}],
            "shunt": []
        }
    }

    results = solve_power_flow_in_memory(dummy_input)
    print("In-memory PF results:\n", results)

    # Or the file-based approach:
    # solve_power_flow("network_model.json", params_json_path=None)
