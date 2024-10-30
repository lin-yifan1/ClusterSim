import random
import params
from . import TrafficManager, GPUManager, ClosTopology
from utils import generate_start_times, sample_from_cdf
from solver import solve, solve_by_cassini


class Simulator:
    def __init__(self):
        self.traffic_manager = TrafficManager()
        self.gpu_manager = GPUManager()
        self.topology = ClosTopology()
        self.method = "ours"  # "ours", "cassini", or None

    def generate_random_jobs(self):
        job_names = [str(i) for i in range(1, params.job_num + 1)]
        arrival_times = generate_start_times(params.job_num, params.arrival_rate)
        durations = sample_from_cdf(
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
        self.waiting_jobs = self.jobs.copy()

    def deploy_job(self, job_name, time):
        return self.gpu_manager.assign_gpu_to_job(
            job_name, self.jobs[job_name]["size"], time
        )

    def release_job(self, job_name, time):
        self.gpu_manager.release_gpu(job_name, time)

    def allocate_flows(self, job_name, time):
        pattern = params.model_types[self.jobs[job_name]["model_type"]]
        job_gpu_list = [
            f"GPU-{id}"
            for id, occupying_job_name in enumerate(self.gpu_manager.gpu_usage)
            if occupying_job_name == job_name
        ]  # GPUs occupied by job_name
        if params.all_reduce_implement == "ring":
            link_list = self.topology.ring_link_list(job_gpu_list)
        else:
            link_list = self.topology.hd_link_list(job_gpu_list)
        for link in link_list:
            self.traffic_manager.add_traffic_pattern(
                link,
                job_name,
                pattern["intervals"],
                pattern["T"],
                time,
                time + self.jobs[job_name]["duration"],
            )

    def run(self):
        time = 0
        self.generate_random_jobs()
        while len(self.waiting_jobs) > 0:
            # operate within timewindow: [time, time_next]
            time_next = time + params.update_time_interval
            job_list = [
                job_name
                for job_name, value in self.waiting_jobs.items()
                if value["arrival_time"] < time_next
            ]  # jobs arrive before time_next
            for job_name in job_list:
                deploy_time = max(self.waiting_jobs[job_name]["arrival_time"], time)
                if self.deploy_job(job_name, deploy_time):
                    # if deployment success
                    self.allocate_flows(job_name, deploy_time)
                    del self.waiting_jobs[job_name]
                else:
                    break
            released_jobs = self.traffic_manager.update_traffic(time_next)
            for job_name in released_jobs:
                self.gpu_manager.release_gpu(job_name, time_next)
            if self.method == "ours":
                solve(self.traffic_manager)
            elif self.method == "cassini":
                solve_by_cassini(self.traffic_manager)
            time = time_next  # proceed to the next time window
