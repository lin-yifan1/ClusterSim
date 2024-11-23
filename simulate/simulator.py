import os
import json
import random
import params
from datetime import datetime
from . import TrafficManager, GPUManager, ClosTopology
from utils import generate_start_times, sample_from_cdf, sample_from_cdf_continuous
from solver import solve, solve_by_cassini, solve_by_max_cut
from typing import List, Tuple, Dict


class Simulator:
    job_rdma_operate_tuples: Dict[str, List[List[List[Tuple[str, str, int]]]]]
    job_traffic_start_points: Dict[str, List[int]]

    def __init__(self):
        self.traffic_manager = TrafficManager()
        self.gpu_manager = GPUManager()
        self.topology = ClosTopology()
        self.method = "ours"  # "ours", "cassini", or "max_cut"
        self.jobs = {}  # json input
        self.waiting_jobs = []
        self.running_jobs = []
        self.ended_jobs = []
        self.job_traffic_start_points = {}  # {job_name: [...]}
        self.time_count: int = 0
        self.current_time: int = 0
        self.job_rdma_operate_tuples = {}

    def generate_random_jobs(self):
        job_names = [str(i) for i in range(1, params.job_num + 1)]
        arrival_times = generate_start_times(params.job_num, params.arrival_rate)
        durations = sample_from_cdf_continuous(
            params.durations, params.cdf_durations, params.job_num
        )
        sizes = sample_from_cdf(params.sizes, params.cdf_sizes, params.job_num)
        model_types = random.choices(list(params.model_types.keys()), k=params.job_num)
        self.jobs = {
            job_name: {
                "arrival_time": arrival_times[i],
                "duration": durations[i],
                "size": sizes[i],
                "model_type": model_types[i],
            }
            for i, job_name in enumerate(job_names)
        }
        self.waiting_jobs = list(self.jobs.keys())

    def save_jobs_to_json(self, filename=None):
        if filename is None:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jobs_data_{current_time}.json"
        file_path = os.path.join("save/jobs", filename)
        if not os.path.exists("save/jobs"):
            os.makedirs("save/jobs")
        with open(file_path, "w") as file:
            json.dump(self.jobs, file, indent=4)

    def load_jobs_from_json(self, file_path):
        with open(file_path, "r") as file:
            self.jobs = json.load(file)
            self.waiting_jobs = list(self.jobs.keys())

    def deploy_single_job(self, job_name: str, deploy_time: int) -> bool:
        """
        Assign GPUs to a single job then get the corresponding RDMA operates
        """
        flag = self.gpu_manager.assign_gpu_to_job(
            job_name, self.jobs[job_name]["size"], deploy_time
        )
        if flag:
            job_gpu_list = self.gpu_manager.get_job_gpu_list(job_name)
            model_type = self.jobs[job_name]["model_type"]
            msg_len = params.model_types[model_type]["msg_len"]
            self.job_rdma_operate_tuples[job_name] = (
                self.topology.job_rdma_operates_tuples(job_gpu_list, msg_len)
            )
        return flag

    def allocate_flows(self, job_name: str, deploy_time: int):
        """
        Update link traffic patterns.
        """
        self.traffic_manager.add_job(
            job_name, deploy_time, deploy_time + self.jobs[job_name]["duration"]
        )
        pattern = params.model_types[self.jobs[job_name]["model_type"]]
        job_gpu_list = self.gpu_manager.get_job_gpu_list(job_name)
        if params.all_reduce_implement == "ring":
            # TODO
            pass
        elif params.all_reduce_implement == "hd":
            comm_link_list = self.topology.hd_comm_link_list(job_gpu_list)
            for link in comm_link_list:
                self.traffic_manager.add_traffic_pattern(
                    link,
                    job_name,
                    pattern["interval"],
                    pattern["T"],
                )

    def deploy_jobs(self) -> List[str]:
        """
        Try to deploy jobs starting before time_next
        """
        deployed_jobs = []
        time_next = self.current_time + params.update_time_interval
        waiting_jobs = self.waiting_jobs.copy()
        for job_name in waiting_jobs:
            if self.jobs[job_name]["arrival_time"] >= time_next:
                break
            deploy_time = max(self.jobs[job_name]["arrival_time"], self.current_time)
            if self.deploy_single_job(job_name, deploy_time):
                # if deployment success
                self.allocate_flows(job_name, deploy_time)
                self.waiting_jobs.remove(job_name)
                self.running_jobs.append(job_name)
                deployed_jobs.append(job_name)
                print(f"[INFO] Job {job_name} deployed.")
            else:
                break
        self.traffic_manager.unify_traffic_pattern()
        return deployed_jobs

    def release_jobs(self) -> List[str]:
        """
        Release jobs finish in time window [current_time, time_next]
        """
        time_next = self.current_time + params.update_time_interval
        released_jobs = self.traffic_manager.release_jobs(time_next)
        for job_name in released_jobs:
            self.gpu_manager.release_gpu(
                job_name, self.traffic_manager.job_time_period[job_name][1]
            )
            self.running_jobs.remove(job_name)
            self.ended_jobs.append(job_name)
            print(f"[INFO] Job {job_name} released.")
        return released_jobs

    def update_job_traffic_start_points(self, released_jobs: List[str]):
        """
        Update self.job_traffic_start_points in time window [current_time, time_next]
        """
        time_next = self.current_time + params.update_time_interval
        job_list = released_jobs + self.running_jobs
        for job_name in job_list:
            start_time = self.traffic_manager.job_time_period[job_name][0]
            interval_start = self.traffic_manager.job_traffic_pattern[
                job_name
            ].interval[0]
            T = self.traffic_manager.job_traffic_pattern[job_name].T
            traffic_start_point = start_time + interval_start
            while traffic_start_point < time_next:
                if traffic_start_point < self.current_time:
                    traffic_start_point += T
                    continue
                if job_name not in self.job_traffic_start_points:
                    self.job_traffic_start_points[job_name] = [traffic_start_point]
                else:
                    self.job_traffic_start_points[job_name].append(traffic_start_point)
                traffic_start_point += T

    def generate_netsim_input(self, save_dir: str = "save/netsim_input"):
        """
        Generate input for NetSim simulator.
        """
        for job_name in self.jobs.keys():
            if job_name not in self.job_traffic_start_points:
                continue
            if self.jobs[job_name]["size"] == 8:
                continue
            traffic_start_points = self.job_traffic_start_points[job_name]
            traffic_start_points = [0] + traffic_start_points
            rdma_operate_tuples = self.job_rdma_operate_tuples[job_name]

            job_save_dir = os.path.join(save_dir, f"{job_name}")  # dir for each job
            if not os.path.exists(job_save_dir):
                os.makedirs(job_save_dir)

            for i, group in enumerate(rdma_operate_tuples):
                with open(
                    os.path.join(job_save_dir, f"rdma_operate_{i}.txt"), "w"
                ) as file:
                    file.write("stat rdma operate:\n")
                    for i in range(1, len(traffic_start_points)):
                        phase = (
                            traffic_start_points[i] - traffic_start_points[i - 1]
                        ) * 10000000
                        file.write(f"phase:{phase}\n")
                        for it, step in enumerate(group):
                            for t in step:
                                src_node = t[0]
                                dst_node = t[1]
                                msg_len = t[2]
                                file.write(
                                    f"Type:rdma_send, src_node:{src_node}, src_port:0, dst_node:{dst_node}, dst_port:0, priority:4, msg_len:{msg_len}\n"
                                )
                            if it < len(group) - 1:
                                file.write("phase:3000\n")

    def solve(self) -> Dict[str, int]:
        """
        Utilize different solvers to reduce conflicts.
        Return job conflicts after optimization.
        """
        if self.method == "ours":
            solve(self.traffic_manager)
        elif self.method == "cassini":
            solve_by_cassini(self.traffic_manager)
        elif self.method == "max_cut":
            solve_by_max_cut(self.traffic_manager, 8)
        job_conflicts = self.traffic_manager.update_traffic(
            self.current_time + params.update_time_interval
        )
        return job_conflicts

    def step(self):
        """
        Step forward to the next time window.
        """
        self.time_count += 1
        self.current_time += params.update_time_interval

    def run(self):
        while len(self.ended_jobs) < len(self.jobs):
            released_jobs = self.release_jobs()
            deployed_jobs = self.deploy_jobs()
            job_conflicts = self.solve()
            self.update_job_traffic_start_points(released_jobs)
            self.step()
        self.generate_netsim_input()
