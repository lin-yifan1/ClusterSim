import params
from simulate import Simulator


def weighted_average_increase(penalty_duration_rates, simulator):
    total_weighted_increase = 0
    total_size = 0

    for job_name, rate in penalty_duration_rates.items():
        size = simulator.jobs[job_name]["size"]
        if size > 8:
            total_weighted_increase += rate * size
            total_size += size

    if total_size == 0:
        return 0

    return total_weighted_increase / total_size


simulator = Simulator()
simulator.method = None
# simulator.generate_random_jobs()
# simulator.save_jobs_to_json()
simulator.load_jobs_from_json("save/jobs/jobs_data_20241101_110009.json")
simulator.run()

durations = {
    job_name: simulator.jobs[job_name]["duration"] for job_name in simulator.jobs.keys()
}

penalty = simulator.traffic_manager.penalty_time

penalty_duration_rates = {
    job_name: penalty.get(job_name, 0) / durations[job_name]
    for job_name in durations.keys()
}

print(weighted_average_increase(penalty_duration_rates, simulator))
