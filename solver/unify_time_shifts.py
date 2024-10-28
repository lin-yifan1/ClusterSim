from collections import deque


def bfs_unify_time_shift(graph):
    unified_time_shifts = {}  # {job_name: shift}
    job_list = [job for job in graph.nodes if graph.nodes[job]["category"] == "job"]
    start_job_name = job_list[0]

    unified_time_shifts[start_job_name] = 0

    queue = deque([start_job_name])
    while queue:
        current_node = queue.popleft()
        current_shift = unified_time_shifts[current_node]

        for neighbor1 in graph.neighbors(current_node):
            for neighbor2 in graph.neighbors(neighbor1):
                if neighbor2 not in unified_time_shifts:
                    edge_weight1 = graph.get_edge_data(current_node, neighbor1).get(
                        "weight", 0
                    )
                    edge_weight2 = graph.get_edge_data(neighbor1, neighbor2).get(
                        "weight", 0
                    )
                    unified_time_shifts[neighbor2] = (
                        current_shift + edge_weight2 - edge_weight1
                    )
                    queue.append(neighbor2)

    return unified_time_shifts
