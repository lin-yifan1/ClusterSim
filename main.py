from simulate import Simulator

simulator = Simulator()
simulator.method = "cassini"
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
