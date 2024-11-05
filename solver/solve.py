import os
import networkx as nx
from simulate import TrafficManager
from .generate_stp_file import generate_stp_file
from .graph_constructor import (
    construct_bigraph_from_solution_file,
    construct_bigraph_from_traffic_manager,
)
from .unify_time_shifts import bfs_unify_time_shift
from utils import run_scipstp
from config import stp_file_dir, stp_solution_dir, scipstp_path_full


def solve(traffic_manager: TrafficManager):
    if not os.path.exists(stp_file_dir):
        os.makedirs(stp_file_dir)
    if not os.path.exists(stp_solution_dir):
        os.makedirs(stp_solution_dir)

    bigraph = construct_bigraph_from_traffic_manager(traffic_manager)
    subgraphs = [bigraph.subgraph(c).copy() for c in nx.connected_components(bigraph)]
    time_shifts = {}
    for i, subgraph in enumerate(subgraphs):
        stp_file_path = os.path.join(
            stp_file_dir, f"{traffic_manager.current_time}_{i}.stp"
        )
        stp_file_path_full = os.path.join(os.getcwd(), stp_file_path)
        stp_solution_path = os.path.join(
            stp_solution_dir, f"{traffic_manager.current_time}_{i}.txt"
        )
        stp_solution_path_full = os.path.join(os.getcwd(), stp_solution_path)
        generate_stp_file(subgraph, traffic_manager, stp_file_path)
        run_scipstp(
            scipstp_path_full,
            stp_file_path_full,
            stp_solution_path_full,
        )
        solution_bigraph = construct_bigraph_from_solution_file(
            subgraph, stp_solution_path
        )
        time_shifts.update(bfs_unify_time_shift(solution_bigraph))
    traffic_manager.update_job_time_periods(time_shifts)


def solve_by_cassini(traffic_manager: TrafficManager):
    bigraph = construct_bigraph_from_traffic_manager(traffic_manager)
    subgraphs = [bigraph.subgraph(c).copy() for c in nx.connected_components(bigraph)]
    time_shifts = {}
    for subgraph in subgraphs:
        time_shifts.update(bfs_unify_time_shift(subgraph))
    traffic_manager.update_job_time_periods(time_shifts)


def solve_by_max_cut(traffic_manager: TrafficManager):
    conflict_graph = traffic_manager.get_conflict_graph()
    subgraphs = [
        conflict_graph.subgraph(c).copy()
        for c in nx.connected_components(conflict_graph)
    ]
    for subgraph in subgraphs:
        pass
