import os
import networkx as nx
from itertools import combinations
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from utils import cal_job_conflicts
from simulate.network_elements import Link, ClosTopology


class TrafficManager:
    def __init__(self):
        self.current_time = 0
        self.link_traffic_pattern = {}  # A {link: {job_name: pattern}} dict
        self.job_traffic_pattern = {}  # {job_name: pattern}
        self.job_time_period = (
            {}
        )  # Start and end time of each job, {job_name: (start_time, end_time)}
        self.running_jobs = []
        self.ended_jobs = []  # jobs that already ended
        self.penalty_time = {}  # amount of time each job's JCT should be added

    def add_job(self, job_name, start_time, end_time):
        self.running_jobs.append(job_name)
        self.job_time_period[job_name] = [start_time, end_time]

    def add_traffic_pattern(
        self, link: Link, job_name, intervals, T, start_time, end_time
    ):
        # Add traffic pattern to a specific link for a given job
        if link not in self.link_traffic_pattern:
            self.link_traffic_pattern[link] = {}
        pattern = {
            # List of 2-lists representing the intervals in the first period,
            # starting from 0
            #  e.g. [[0,1],[2,3]] -> [[0,1),[2,3)]
            "intervals": intervals,
            "T": T,
        }
        if job_name not in self.link_traffic_pattern[link]:
            self.link_traffic_pattern[link][job_name] = pattern
        else:
            # if job_name already has flow going through the link
            # then modify intervals
            intervals_new = []
            for interval_1, interval_2 in zip(
                self.link_traffic_pattern[link][job_name]["intervals"], intervals
            ):
                low_1, high_1 = interval_1
                low_2, high_2 = interval_2
                length = high_2 - low_2
                intervals_new.append([low_1 - length, high_1])
            self.link_traffic_pattern[link][job_name]["intervals"] = intervals_new

    def unify_traffic_pattern(self):
        self.job_traffic_pattern = {}
        for link, jobs in self.link_traffic_pattern.items():
            for job_name, pattern in jobs.items():
                if job_name not in self.job_traffic_pattern:
                    self.job_traffic_pattern[job_name] = pattern
                elif (
                    pattern["intervals"][0][0]
                    < self.job_traffic_pattern[job_name]["intervals"][0][0]
                ):
                    self.job_traffic_pattern[job_name]["intervals"][0][0] = pattern[
                        "intervals"
                    ][0][0]
        for link, jobs in self.link_traffic_pattern.items():
            for job_name, pattern in jobs.items():
                if (
                    pattern["intervals"][0][0]
                    > self.job_traffic_pattern[job_name]["intervals"][0][0]
                ):
                    self.link_traffic_pattern[link][job_name]["intervals"][0][0] = (
                        self.job_traffic_pattern[job_name]["intervals"][0][0]
                    )

    def release_single_job(self, job_name):
        # Release job from links
        for jobs in self.link_traffic_pattern.values():
            if job_name in jobs:
                del jobs[job_name]
        self.link_traffic_pattern = {
            link: jobs for link, jobs in self.link_traffic_pattern.items() if jobs != {}
        }  # filter out links with no flows
        self.running_jobs.remove(job_name)
        self.ended_jobs.append(job_name)

    def update_job_time_periods(self, delay_dict):
        # Update the intervals for each job based on the provided delay dictionary
        # delay_dict: {job_name: delay}
        for job_name, delay in delay_dict.items():
            T = 0
            # find T
            for jobs in self.link_traffic_pattern.values():
                if job_name in jobs:
                    T = jobs[job_name]["T"]
                    break
            self.job_time_period[job_name][0] += delay % T
            self.job_time_period[job_name][1] += delay % T

    def update_traffic(self, new_time):
        job_conflicts = cal_job_conflicts(
            self.link_traffic_pattern, self.job_time_period, self.current_time, new_time
        )
        # Update each job's end time based on the calculated delay
        for job_name, conflict in job_conflicts.items():
            if job_name not in self.penalty_time:
                self.penalty_time[job_name] = conflict
            else:
                self.penalty_time[job_name] += conflict
        self.update_job_time_periods(job_conflicts)
        self.current_time = new_time

    def release_jobs(self, new_time):
        ended_jobs = []  # jobs end in time period [current_time, new_time)
        for job_name in self.running_jobs.copy():
            if self.job_time_period[job_name][1] <= new_time:
                self.release_single_job(job_name)
                ended_jobs.append(job_name)
        return ended_jobs

    def get_job_list(self):
        return list(
            {
                job_name
                for jobs in self.link_traffic_pattern.values()
                for job_name in jobs
            }
        )

    def get_link_list(self):
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
        pos = nx.spring_layout(conflict_graph, seed=10396953)

        fig, ax = plt.subplots(figsize=(8, 8))

        nx.draw_networkx_nodes(conflict_graph, pos, ax=ax, node_size=20)
        label_pos = {node: (x, y + 0.03) for node, (x, y) in pos.items()}
        nx.draw_networkx_labels(conflict_graph, label_pos, ax=ax, font_size=8)

        nx.draw_networkx_edges(conflict_graph, pos, ax=ax, alpha=0.4)
        edge_labels = nx.get_edge_attributes(conflict_graph, "weight")
        nx.draw_networkx_edge_labels(
            conflict_graph, pos, edge_labels=edge_labels, ax=ax
        )

        ax.set_title("Conflict Graph")
        ax.set_axis_off()

        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file_path = os.path.join(file_dir, f"{self.current_time}.png")
        fig.savefig(file_path, format="png")


if __name__ == "__main__":
    topology = ClosTopology()
    traffic_manager = TrafficManager()

    server_a = "Server-5"
    server_b = "Server-20"
    route = topology.get_route(server_a, server_b)
    print(f"Route between {server_a} and {server_b}: {route}")

    traffic_manager.add_traffic_pattern(
        route[0], "Trainingjob1", intervals=[[0, 2]], T=10, start_time=0, end_time=30
    )
    traffic_manager.add_traffic_pattern(
        route[0], "Trainingjob2", intervals=[[1, 4]], T=10, start_time=0, end_time=30
    )
    traffic_manager.add_traffic_pattern(
        route[0], "Trainingjob3", intervals=[[4, 6]], T=10, start_time=0, end_time=30
    )

    print("Initial job time periods: ", traffic_manager.job_time_period)

    # Update job intervals directly using a delay dictionary
    delay_dict = {"Trainingjob1": 2, "Trainingjob2": 1}
    traffic_manager.update_job_time_periods(delay_dict)
    print(
        "Job time periods after direct modification: ", traffic_manager.job_time_period
    )

    # Update traffic based on conflicts
    traffic_manager.update_traffic(20)

    # Print updated traffic patterns
    print("Job time periods after update: ", traffic_manager.job_time_period)
