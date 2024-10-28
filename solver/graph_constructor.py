import re
import networkx as nx
from .time_shifts import cal_time_shifts
from simulate import TrafficManager


def construct_bigraph_from_traffic_manager(traffic_manager: TrafficManager):
    # Construct bipartite graph from TrafficManager
    bigraph = nx.Graph()
    link_list = traffic_manager.get_link_list()

    for link in link_list:
        bigraph.add_node(link, category="link")
        for job_name in traffic_manager.link_traffic_pattern[link].keys():
            bigraph.add_node(job_name, category="job")
            bigraph.add_edge(job_name, link)

    # calculate time shifts: {link: {job: shift}}
    time_shifts = cal_time_shifts(traffic_manager)
    for link, jobs in time_shifts.items():
        for job_name in jobs.keys():
            bigraph[link][job_name]["weight"] = time_shifts[link][job_name]

    return bigraph


def construct_bigraph_from_solution_file(subgraph: nx.Graph, solution_file_path):
    job_list = [
        job for job in subgraph.nodes if subgraph.nodes[job]["category"] == "job"
    ]
    link_list = [
        link for link in subgraph.nodes if subgraph.nodes[link]["category"] == "link"
    ]
    node_list = job_list + link_list

    with open(solution_file_path, "r") as file:
        lines = file.readlines()

    link_subset = set()
    edge_pattern = re.compile(r"x_(\d+)_(\d+)\s+1\s+\(obj:\d*\.?\d+\)")
    for line in lines:
        match = edge_pattern.search(line)
        if match:
            node_1 = node_list[int(match.group(1))]  # note that index here is 0-based
            node_2 = node_list[int(match.group(2))]
            if subgraph.nodes[node_1].get("category") == "link":
                link_subset.add(node_1)
            else:
                link_subset.add(node_2)
    bigraph = subgraph.subgraph(link_subset.union(set(job_list)))

    return bigraph
