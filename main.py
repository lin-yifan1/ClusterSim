import params
from simulate import Simulator


# class CustomSimulator(Simulator):
#     max_flow_num = []
#     job_num = []

#     def run(self):
#         time = 0
#         while len(self.waiting_jobs) > 0:
#             # operate within timewindow: [time, time_next]
#             time_next = time + params.update_time_interval
#             job_list = [
#                 job_name
#                 for job_name, value in self.waiting_jobs.items()
#                 if value["arrival_time"] < time_next
#             ]  # jobs arrive before time_next
#             for job_name in job_list:
#                 deploy_time = max(self.waiting_jobs[job_name]["arrival_time"], time)
#                 if self.deploy_job(job_name, deploy_time):
#                     # if deployment success
#                     self.allocate_flows(job_name, deploy_time)
#                     del self.waiting_jobs[job_name]
#                     print(f"[INFO] Job {job_name} deployed.")
#                 else:
#                     break
#             released_jobs = self.traffic_manager.update_traffic(time_next)
#             for job_name in released_jobs:
#                 self.gpu_manager.release_gpu(job_name, time_next)
#                 print(f"[INFO]Job {job_name} released.")
#             job_set = {
#                 job_name
#                 for job_name in self.gpu_manager.gpu_usage
#                 if job_name is not None
#             }
#             self.job_num.append(len(job_set))
#             print(f"[{time}] Total {len(job_set)} jobs in the cluster.")
#             if len(self.traffic_manager.link_traffic_pattern) == 0:
#                 self.max_flow_num.append(0)
#                 print(f"[{time}] Max 0 flows on a single link.")
#             else:
#                 flow_num = max(
#                     len(jobs)
#                     for jobs in self.traffic_manager.link_traffic_pattern.values()
#                 )
#                 self.max_flow_num.append(flow_num)
#                 print(f"[{time}] Max {flow_num} flows on a single link.")
#             time = time_next  # proceed to the next time window


simulator = Simulator()
simulator.method = None
simulator.generate_random_jobs()
simulator.save_jobs_to_json()
simulator.run()

job_time_period = simulator.traffic_manager.job_time_period  # {job_name: [start, end]}
actual_durations = {
    job_name: job_time_period[job_name][1] - job_time_period[job_name][0]
    for job_name in job_time_period.keys()
}
ideal_durations = {
    job_name: simulator.jobs[job_name]["duration"] for job_name in simulator.jobs.keys()
}

percentage_increase = {}
for job_name in ideal_durations.keys() & actual_durations.keys():
    increase = (
        (actual_durations[job_name] - ideal_durations[job_name])
        / ideal_durations[job_name]
    ) * 100
    percentage_increase[job_name] = increase
print(percentage_increase)
