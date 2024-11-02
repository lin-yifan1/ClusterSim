import os
import json
import random
import params
from datetime import datetime
from . import TrafficManager, GPUManager, ClosTopology
from utils import generate_start_times, sample_from_cdf, sample_from_cdf_continuous
from solver import solve, solve_by_cassini


class Simulator:
    def __init__(self):
        self.traffic_manager = TrafficManager()
        self.gpu_manager = GPUManager()
        self.topology = ClosTopology()
        self.method = "ours"  # "ours", "cassini", or None
        self.jobs = {}
        self.waiting_jobs = []
        self.running_jobs = []
        self.ended_jobs = []

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

    def deploy_single_job(self, job_name, time):
        return self.gpu_manager.assign_gpu_to_job(
            job_name, self.jobs[job_name]["size"], time
        )

    def allocate_flows(self, job_name, time):
        self.traffic_manager.add_job(
            job_name, time, time + self.jobs[job_name]["duration"]
        )
        pattern = params.model_types[self.jobs[job_name]["model_type"]]
        job_gpu_list = [
            f"GPU-{id}"
            for id, occupying_job_name in enumerate(self.gpu_manager.gpu_usage)
            if occupying_job_name == job_name
        ]  # GPUs occupied by job_name
        if params.all_reduce_implement == "ring":
            # TODO
            link_list = self.topology.ring_link_list(job_gpu_list)
        else:
            gpu_comm_pairs = self.topology.hd_communication_pairs(job_gpu_list)
            for gpu_pair in gpu_comm_pairs:
                for link in self.topology.get_gpu_route(*gpu_pair):
                    self.traffic_manager.add_traffic_pattern(
                        link,
                        job_name,
                        pattern["intervals"],
                        pattern["T"],
                        time,
                        time + self.jobs[job_name]["duration"],
                    )

    def deploy_jobs(self, time, time_next):
        for job_name in self.waiting_jobs.copy():
            if self.jobs[job_name]["arrival_time"] >= time_next:
                break
            deploy_time = max(self.jobs[job_name]["arrival_time"], time)
            if self.deploy_single_job(job_name, deploy_time):
                # if deployment success
                self.allocate_flows(job_name, deploy_time)
                self.waiting_jobs.remove(job_name)
                self.running_jobs.append(job_name)
                print(f"[INFO] Job {job_name} deployed.")
            else:
                break

    def release_jobs(self, time_next):
        released_jobs = self.traffic_manager.release_jobs(time_next)
        for job_name in released_jobs:
            self.gpu_manager.release_gpu(job_name, time_next)
            self.running_jobs.remove(job_name)
            self.ended_jobs.append(job_name)
            print(f"[INFO]Job {job_name} released.")

    def run(self):
        time = 0
        # count = 0
        while len(self.ended_jobs) < len(self.jobs):
            # operate within timewindow: [time, time_next]
            time_next = time + params.update_time_interval
            self.release_jobs(time_next)
            self.deploy_jobs(time, time_next)
            self.traffic_manager.update_traffic(time_next)

            if self.method == "ours":
                solve(self.traffic_manager)
            elif self.method == "cassini":
                solve_by_cassini(self.traffic_manager)
            # if count % 100 == 0:
            #     print(f"Current time: {time}")
            #     print(f"Running jobs: {self.running_jobs}")
            time = time_next  # proceed to the next time window
            # count += 1
