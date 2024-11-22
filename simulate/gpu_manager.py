import json
from collections import Counter
from typing import List, Union, Dict


class GPUManager:
    gpu_usage: List[Union[str, None]]
    job_deployed_time: Dict[str, int]
    job_released_time: Dict[str, int]

    def __init__(self, num_gpu=3072):
        self.gpu_usage = [None] * num_gpu  # List to keep track of each GPU's job_name
        self.job_deployed_time = {}
        self.job_released_time = {}

    def gpu_occupation_rate(self) -> float:
        return sum(1 for job in self.gpu_usage if job is not None) / len(self.gpu_usage)

    def assign_gpu_to_job(self, job_name: str, job_gpu_num: int, time: int) -> bool:
        """
        Try to allocate GPUs to the job requiring a number of GPUs
        """
        num_gpu_available = self.gpu_usage.count(None)
        if num_gpu_available < job_gpu_num:
            return False
        else:
            assigned_count = 0
            for id, job_name in enumerate(self.gpu_usage):
                if job_name is None:
                    self.gpu_usage[id] = assign_job_name
                    assigned_count += 1
                if assigned_count == job_gpu_num:
                    break
            self.job_deployed_time[job_name] = time
            return True

    def release_gpu(self, job_name: str, time: int):
        for id, job_name in enumerate(self.gpu_usage):
            if job_name == job_name:
                self.gpu_usage[id] = None
        self.job_released_time[job_name] = time

    def get_job_npu_occupied(self):
        filtered_gpu_usage = [
            job_name for job_name in self.gpu_usage if job_name is not None
        ]
        counter = dict(Counter(filtered_gpu_usage))
        return dict(sorted(counter.items()))

    def get_job_description(self, time):
        job_description = {}
        for job_name, deployed_time in self.job_deployed_time.items():
            if job_name not in self.job_released_time:
                job_description[job_name] = time - deployed_time
        return dict(sorted(job_description.items()))

    def get_job_deployment(self):
        return self.gpu_usage

    def save_snapshot(self, path, time):
        snapshot = {
            "job_npu_occupied": self.get_job_npu_occupied(),
            "job_description": self.get_job_description(time),
            "job_deployment": self.get_job_deployment(),
        }
        with open(path, "w") as json_file:
            json.dump(snapshot, json_file, indent=4)
