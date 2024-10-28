import networkx as nx
from simulate import TrafficManager


def generate_stp_file(
    subgraph: nx.Graph, traffic_manager: TrafficManager, stp_file_path: str
):
    job_list = [
        job for job in subgraph.nodes if subgraph.nodes[job]["category"] == "job"
    ]
    link_list = [
        link for link in subgraph.nodes if subgraph.nodes[link]["category"] == "link"
    ]
    job_duration = traffic_manager.get_job_duration()

    # write to .stp file
    with open(stp_file_path, "w") as stp_file:
        stp_file.write("33d32945 STP File, STP Format Version  1.00\n\n")
        stp_file.write("SECTION Graph\n")
        stp_file.write(f"Nodes {subgraph.number_of_nodes()}\n")
        stp_file.write(f"Edges {subgraph.number_of_edges()}\n")

        # write edge information
        for job_id, job_name in enumerate(job_list, start=1):
            for link_id, link in enumerate(link_list, start=len(job_list) + 1):
                duration = job_duration[link][job_name]
                if duration == 0:
                    continue  # I dont know why there are 0s
                inversed_duration = 1 / duration
                stp_file.write(f"E {job_id} {link_id} {inversed_duration}\n")
        stp_file.write("END\n\n")

        stp_file.write("SECTION Terminals\n")
        stp_file.write(f"Terminals {len(job_list)}\n")
        for job_id in range(1, len(job_list) + 1):
            stp_file.write(f"T {job_id}\n")
        stp_file.write("END\n\n")

        stp_file.write("SECTION MaximumDegrees\n")
        for _ in range(len(job_list)):
            stp_file.write(f"MD {len(link_list)}\n")
        for _ in range(len(link_list)):
            stp_file.write(f"MD {len(job_list)}\n")
        stp_file.write("END\n\n")

        stp_file.write("EOF")
