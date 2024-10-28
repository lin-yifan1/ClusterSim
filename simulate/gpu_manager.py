import json
from collections import Counter


class GPUManager:
    def __init__(self, num_gpu=3072):
        # List to keep track of each GPU's job_name
        self.gpu_usage = [None] * num_gpu
        self.job_deployed_time = {}
        self.job_released_time = {}

    def assign_gpu_to_job(self, assign_job_name, job_gpu_num, time):
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
            self.job_deployed_time[assign_job_name] = time
            return True

    def release_gpu(self, release_job_name, time):
        for id, job_name in enumerate(self.gpu_usage):
            if job_name == release_job_name:
                self.gpu_usage[id] = None
        self.job_released_time[release_job_name] = time

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


if __name__ == "__main__":
    gpu_manager = GPUManager(num_gpu=8)

    gpu_manager.assign_gpu_to_job("job_1", 3, time=1)
    gpu_manager.assign_gpu_to_job("job_2", 2, time=2)

    gpu_manager.release_gpu("job_1", time=5)

    gpu_manager.assign_gpu_to_job("job_3", 1, time=6)

    deployment = gpu_manager.get_job_deployment()
    print("Current GPU deployment:", deployment)

    npu_occupied = gpu_manager.get_job_npu_occupied()
    print("Job GPU usage count:", npu_occupied)

    job_description = gpu_manager.get_job_description(time=10)
    print("Job descriptions:", job_description)

    gpu_manager.save_snapshot("snapshot.json", time=10)
    print("Snapshot saved to 'snapshot.json'")
