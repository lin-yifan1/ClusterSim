import os
import networkx as nx
from itertools import combinations
import matplotlib
import params

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from utils import cal_job_conflicts
from simulate.network_elements import Link, ClosTopology
from typing import Tuple, Dict, List


class TrafficPattern:
    interval: Tuple[int, int]
    T: int

    def __init__(self, interval: Tuple[int, int], T: int):
        self.interval = interval
        self.T = T

    def update_interval(self, interval_new: Tuple[int, int]):
        t1, t2 = self.interval
        t1_new, t2_new = interval_new
        t1 = t1 - (t2_new - t1_new)
        self.interval = (t1, t2)


class TrafficManager:
    current_time: int
    link_traffic_pattern: Dict[
        Link, Dict[str, TrafficPattern]
    ]  # A {link: {job_name: pattern}} dict
    job_traffic_pattern: Dict[str, TrafficPattern]  # {job_name: pattern}
    job_time_period: Dict[
        str, Tuple[int, int]
    ]  # Start and end time of each job, {job_name: (start_time, end_time)}
    running_jobs: List[str]
    ended_jobs: List[str]
    penalty_time: Dict[str, int]

    def __init__(self):
        self.current_time = 0
        self.link_traffic_pattern = {}
        self.job_traffic_pattern = {}
        self.job_time_period = {}
        self.running_jobs = []
        self.ended_jobs = []
        self.penalty_time = {}

    def add_job(self, job_name: str, start_time: int, end_time: int):
        self.running_jobs.append(job_name)
        self.job_time_period[job_name] = (start_time, end_time)

    def add_traffic_pattern(
        self, link: Link, job_name: str, interval: Tuple[int, int], T: int
    ):
        """
        Add traffic pattern to a specific link for a given job
        """
        if link not in self.link_traffic_pattern:
            self.link_traffic_pattern[link] = {}
        pattern = TrafficPattern(interval, T)
        if job_name not in self.link_traffic_pattern[link]:
            self.link_traffic_pattern[link][job_name] = pattern
        else:
            # if the job already has flow going through the link
            # then update the interval
            self.link_traffic_pattern[link][job_name].update_interval(pattern.interval)

    def unify_traffic_pattern(self):
        """
        Unify traffic intervals of the same job.
        Should be called after update of link_traffic_pattern.
        """
        self.job_traffic_pattern = {}
        # Update job traffic pattern
        for link, jobs in self.link_traffic_pattern.items():
            for job_name, pattern in jobs.items():
                if job_name not in self.job_traffic_pattern:
                    self.job_traffic_pattern[job_name] = pattern
                elif (
                    pattern.interval[0] < self.job_traffic_pattern[job_name].interval[0]
                ):
                    self.job_traffic_pattern[job_name].interval = pattern.interval
        # Update link traffic pattern
        for link, jobs in self.link_traffic_pattern.items():
            for job_name, pattern in jobs.items():
                if pattern.interval[0] > self.job_traffic_pattern[job_name].interval[0]:
                    pattern.interval = self.job_traffic_pattern[job_name].interval

    def update_job_time_periods(self, delay_dict: Dict[str, int]):
        """
        Update the intervals for each job based on the provided delay dictionary
        Should be called after unify_traffic_pattern
        """
        for job_name, delay in delay_dict.items():
            T = self.job_traffic_pattern[job_name].T
            start_time, end_time = self.job_time_period[job_name]
            start_time += delay % T
            end_time += delay % T
            self.job_time_period[job_name] = (start_time, end_time)

    def update_traffic(self, time_next: int) -> Dict[str, int]:
        """
        Update penalty in time window [current_time, time_next],
        and then update current_time to time_next.
        Return job_conflicts.
        """
        job_conflicts = cal_job_conflicts(
            self.link_traffic_pattern,
            self.job_time_period,
            self.current_time,
            time_next,
        )
        # Update each job's end time based on the calculated delay
        for job_name, conflict in job_conflicts.items():
            if job_name not in self.penalty_time:
                self.penalty_time[job_name] = conflict
            else:
                self.penalty_time[job_name] += conflict
        # Jobs' end_time affected by conflicts
        # self.update_job_time_periods(job_conflicts)
        self.current_time = time_next
        return job_conflicts

    def release_single_job(self, job_name: str):
        """
        Release given job from link traffic pattern
        """
        for jobs in self.link_traffic_pattern.values():
            if job_name in jobs:
                del jobs[job_name]
        self.link_traffic_pattern = {
            link: jobs for link, jobs in self.link_traffic_pattern.items() if jobs != {}
        }  # filter out links with no flows
        self.running_jobs.remove(job_name)
        self.ended_jobs.append(job_name)

    def release_jobs(self, time_next: int) -> List[str]:
        """
        Release jobs finish in time window [current_time, time_next]
        """
        released_jobs = []
        running_jobs = self.running_jobs.copy()
        for job_name in running_jobs:
            if self.job_time_period[job_name][1] <= time_next:
                self.release_single_job(job_name)
                released_jobs.append(job_name)
        return released_jobs

    def get_link_list(self) -> List[Link]:
        """
        Return links that have flows on them
        """
        return list(self.link_traffic_pattern.keys())

    def get_job_duration(self):
        job_duration = defaultdict(lambda: defaultdict(int))  # {link: {job: duration}}
        for link, jobs in self.link_traffic_pattern.items():
            for job, pattern in jobs.items():
                job_duration[link][job] = sum(
                    end - start for start, end in pattern["intervals"]
                )
        return job_duration

    def get_conflict_graph(self):
        conflict_graph = nx.Graph()
        for jobs in self.link_traffic_pattern.values():
            link_job_list = jobs.keys()
            for job_1, job_2 in combinations(link_job_list, 2):
                if conflict_graph.has_edge(job_1, job_2):
                    conflict_graph[job_1][job_2]["weight"] += 1
                else:
                    conflict_graph.add_edge(job_1, job_2, weight=1)
        return conflict_graph

    def draw_conflict_graph(self, file_dir):
        conflict_graph = self.get_conflict_graph()
        pos = nx.spring_layout(conflict_graph, k=0.5, seed=10396953)

        fig, ax = plt.subplots(figsize=(8, 8))

        nx.draw_networkx_nodes(conflict_graph, pos, ax=ax, node_size=40)
        # label_pos = {node: (x, y + 0.03) for node, (x, y) in pos.items()}
        # nx.draw_networkx_labels(conflict_graph, label_pos, ax=ax, font_size=8)

        nx.draw_networkx_edges(conflict_graph, pos, ax=ax, alpha=0.4)
        edge_labels = nx.get_edge_attributes(conflict_graph, "weight")
        nx.draw_networkx_edge_labels(
            conflict_graph, pos, edge_labels=edge_labels, ax=ax
        )

        current_hours = (self.current_time * params.time_slot) / (1000 * 60)
        ax.set_title(f"Conflict Graph (time={current_hours:.1f}h)")
        ax.set_axis_off()

        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file_path = os.path.join(file_dir, f"{self.current_time}.png")
        fig.savefig(file_path, format="png")
