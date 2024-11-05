import networkx as nx


def find_max_weight_sum_node(G: nx.Graph):
    max_weight_sum = 0
    max_weight_node = None

    for node in G.nodes():
        weight_sum = sum(data["weight"] for _, _, data in G.edges(node, data=True))
        if weight_sum > max_weight_sum:
            max_weight_sum = weight_sum
            max_weight_node = node
    return max_weight_node


def calculate_boundary_weight_sum(G, S):
    # Calculate the sum of weights for all edges with exactly one endpoint in the set S.
    if len(S) == 0 or len(S) == len(G):
        return 0
    weight_sum = 0
    for u, v, data in G.edges(data=True):
        if (u in S and v not in S) or (v in S and u not in S):
            weight_sum += data.get("weight", 1)
    return weight_sum


def mod_local_search(G: nx.Graph, epsilon=1):
    # Ref: https://www.cs.cmu.edu/afs/cs/academic/class/15854-f05/www/scribe/lec07.pdf
    # Return: set S representing the partition
    S = set()
    S.add(find_max_weight_sum_node(G))
    while True:
        changed = False
        w = calculate_boundary_weight_sum(G, S)
        for node in G.nodes():
            if node in S:
                w_new = calculate_boundary_weight_sum(G, S - {node})
                if w_new >= epsilon * w / len(G):
                    S = S - {node}
                    changed = True
                    break
            else:
                w_new = calculate_boundary_weight_sum(G, S | {node})
                if w_new >= epsilon * w / len(G):
                    S = S | {node}
                    changed = True
                    break
        if not changed:
            break
        print(S)
    return S


if __name__ == "__main__":
    G = nx.Graph()
    G.add_edge(1, 2, weight=3)
    G.add_edge(1, 3, weight=2)
    G.add_edge(2, 3, weight=4)
    G.add_edge(3, 4, weight=5)
    G.add_edge(4, 5, weight=6)
    G.add_edge(5, 6, weight=1)
    G.add_edge(6, 1, weight=2)

    epsilon = 0.1
    result = mod_local_search(G, epsilon)

    print("Resulting set S:", result)
