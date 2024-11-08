import pulp
import networkx as nx
from simulate import TrafficManager


def max_k_cut_networkx(G, K=8):
    """
    Solves the Max K-Cut problem for a given NetworkX graph.
    Ensures that every node is assigned to a partition.

    Parameters:
    - G: A NetworkX graph where edge weights are stored in the 'weight' attribute.
    - K: The number of partitions to divide the graph into. Default is 5.

    Returns:
    - partitions: A dictionary where keys are partition numbers and values are lists of nodes in each partition.
    """
    # Extract nodes and edges information
    nodes = list(G.nodes())
    num_nodes = len(nodes)

    # If the number of nodes is less than or equal to K, assign each node to its own partition
    if num_nodes <= K:
        partitions = {k: [] for k in range(1, K + 1)}
        for idx, node in enumerate(nodes):
            partitions[idx + 1].append(node)
        return partitions

    edges = []
    for i, j in G.edges():
        weight = G[i][j].get("weight", 1)  # Default weight is 1 if not specified
        edges.append((i, j, weight))

    # Create the optimization problem instance
    prob = pulp.LpProblem("MaxKCut", pulp.LpMaximize)

    # Define variables: y[i][k], whether node i is assigned to partition k
    y = {
        i: {k: pulp.LpVariable(f"y_{i}_{k}", cat="Binary") for k in range(1, K + 1)}
        for i in nodes
    }

    # Each node must be assigned to exactly one partition
    for i in nodes:
        prob += (
            pulp.lpSum([y[i][k] for k in range(1, K + 1)]) == 1,
            f"OneClusterPerNode_{i}",
        )

    # Each partition must contain at least one node
    for k in range(1, K + 1):
        prob += pulp.lpSum([y[i][k] for i in nodes]) >= 1, f"NonEmptyCluster_{k}"

    # Define auxiliary variables: s[i][j][k], indicating both nodes i and j are in partition k
    s = {}
    for i, j, _ in edges:
        for k in range(1, K + 1):
            s[i, j, k] = pulp.LpVariable(f"s_{i}_{j}_{k}", cat="Binary")
            # Linearize y[i][k] * y[j][k]
            prob += s[i, j, k] <= y[i][k], f"s_leq_yi_{i}_{j}_{k}"
            prob += s[i, j, k] <= y[j][k], f"s_leq_yj_{i}_{j}_{k}"
            prob += s[i, j, k] >= y[i][k] + y[j][k] - 1, f"s_geq_{i}_{j}_{k}"

    # Define variables w[i][j], indicating whether edge (i, j) is cut
    w = {}
    for i, j, _ in edges:
        w[i, j] = pulp.LpVariable(f"w_{i}_{j}", cat="Binary")
        # w[i][j] + sum_k s[i][j][k] == 1
        prob += (
            w[i, j] + pulp.lpSum([s[i, j, k] for k in range(1, K + 1)]) == 1,
            f"w_eq_{i}_{j}",
        )

    # Objective function: Maximize the total weight of cut edges
    prob += pulp.lpSum([w[i, j] * weight for (i, j, weight) in edges]), "TotalCutWeight"

    # Solve the problem without solver output
    prob.solve(pulp.PULP_CBC_CMD(msg=0))  # Set msg=0 to suppress output

    # Check the solution status
    if pulp.LpStatus[prob.status] != "Optimal":
        print("Optimal solution not found. Status:", pulp.LpStatus[prob.status])
        return None

    # Build the partitioning result
    partitions = {k: [] for k in range(1, K + 1)}
    for i in nodes:
        max_val = -1
        assigned_partition = None
        for k in range(1, K + 1):
            val = pulp.value(y[i][k])
            if val is None:
                val = 0  # Treat None as 0
            if val > max_val:
                max_val = val
                assigned_partition = k
        if assigned_partition is not None:
            partitions[assigned_partition].append(i)
        else:
            # This should not happen due to the constraints, but added as a safeguard
            print(f"Node {i} could not be assigned to any partition.")
            return None

    return partitions


def cal_time_shift_by_max_k_cut(traffic_manager: TrafficManager, G: nx.Graph, K=5):
    time_shifts = {}
    partitions = max_k_cut_networkx(G, K)
    T_min = min(
        [traffic_manager.job_traffic_pattern[job_name]["T"] for job_name in G.nodes]
    )
    for i, job_list in partitions.items():
        time_spot = (i - 1) * T_min // K
        start_time_spot = time_spot
        for job_name in job_list:
            start = traffic_manager.job_time_period[job_name][0]
            pattern = traffic_manager.job_traffic_pattern[job_name]
            T = pattern["T"]
            interval_start = pattern["intervals"][0][0]
            interval_end = pattern["intervals"][0][1]
            interval_len = interval_start - interval_end
            time_shifts[job_name] = (time_spot - (start + interval_start)) % T
            # start_time_spot = start_time_spot + interval_end - interval_start
    return time_shifts
