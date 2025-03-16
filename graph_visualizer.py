"""
graph_visualizer.py

Uses NetworkX and matplotlib to visualize the network model built by
build_network_model.py. Each node/line/link in the model is added to a graph,
and a simple layout is drawn.

Requires:
  pip install networkx matplotlib
"""

import networkx as nx
import matplotlib.pyplot as plt

def visualize_network(model, show_labels=True, title="Network Graph"):
    """
    Visualizes the 'model' as a graph using NetworkX and Matplotlib.

    :param model: Dictionary with "nodes", "lines", "links", etc.
    :param show_labels: If True, display node labels (node names) on the graph.
    :param title: Title to display on the plot.
    """
    # Create a directed or undirected graph (your choice).
    # If you prefer an undirected representation, use nx.Graph().
    G = nx.DiGraph()

    # 1) Add nodes
    #    We can store each node's name as an attribute for labeling.
    for nd in model["nodes"]:
        # nd["id"] is unique
        node_id = nd["id"]
        node_label = nd.get("name", f"Node_{node_id}")
        G.add_node(node_id, label=node_label)

    # 2) Add edges for lines (which have r1, x1, etc.)
    for ln in model["lines"]:
        from_n = ln["from_node"]
        to_n = ln["to_node"]
        edge_label = ln.get("name", f"Line_{ln['id']}")
        G.add_edge(from_n, to_n, label=edge_label)

    # 3) Add edges for links (service lines to buildings, etc.)
    for lk in model["links"]:
        from_n = lk["from_node"]
        to_n = lk["to_node"]
        edge_label = lk.get("name", f"Link_{lk['id']}")
        G.add_edge(from_n, to_n, label=edge_label)

    # Optionally, you could also add edges for "sources" or "shunts" if desired.
    # But typically "sources" and "shunts" are attributes at nodes or lines.

    # --- Draw the graph ---
    pos = nx.spring_layout(G, seed=42)  # spring_layout for a decent layout

    plt.figure(figsize=(8, 6))
    plt.title(title)

    # Draw the network edges and nodes
    nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True, alpha=0.7)
    nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=700)

    # If show_labels is True, we'll draw node labels
    if show_labels:
        node_labels = {n: G.nodes[n]["label"] for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=10)

    # Optionally show edge labels (which might clutter the diagram if many edges)
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red')

    plt.axis("off")
    plt.tight_layout()
    plt.show()
