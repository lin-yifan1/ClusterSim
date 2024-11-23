from simulate import TrafficManager


def cal_time_shifts(traffic_manager: TrafficManager):
    # Calculate jobs' time shifts on each link
    # Return: {link: {job_name: time_shift}}
    time_shifts = {}
    for link, jobs in traffic_manager.link_traffic_pattern.items():
        time_shifts[link] = {}

        link_job_num = len(jobs)  # number of jobs on the link
        T_min = min([pattern["T"] for pattern in jobs.values()])  # Min T of the link
        interval_len = T_min // link_job_num  # Interval length between job traffics

        jobs_sorted = list(
            sorted(jobs.items(), key=lambda item: item[1]["T"])
        )  # Deploy jobs with small Ts first

        start_point = 0

        for job_name, pattern in jobs_sorted:
            start_time = traffic_manager.job_time_period[job_name][0]
            interval_start = pattern["intervals"][0][0]
            T = pattern["T"]
            time_shifts[link][job_name] = (
                start_point - (start_time + interval_start)
            ) % T
            start_point += interval_len
    return time_shifts


def cal_time_shifts_cassini(traffic_manager: TrafficManager):
    # Calculate jobs' time shifts on each link
    # Return: {link: {job_name: time_shift}}
    time_shifts = {}
    for link, jobs in traffic_manager.link_traffic_pattern.items():
        time_shifts[link] = {}
        start_point = 0
        for job_name, pattern in jobs.items():
            start_time = traffic_manager.job_time_period[job_name][0]
            interval_start = pattern["intervals"][0][0]
            interval_end = pattern["intervals"][0][1]
            interval_len = interval_start - interval_end
            T = pattern["T"]
            time_shifts[link][job_name] = (
                start_point - (start_time + interval_start)
            ) % T
            start_point += interval_len + 10000 // 3
    return time_shifts
