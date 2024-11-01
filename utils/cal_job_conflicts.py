import time
import numpy as np


def cal_overlap(
    pattern_1,
    pattern_2,
    start_time_1,
    end_time_1,
    start_time_2,
    end_time_2,
    current_time,
    new_time,
):
    # calculate overlap between two jobs in a given time period (estimated)
    intervals_1 = pattern_1["intervals"]
    T_1 = pattern_1["T"]
    intervals_2 = pattern_2["intervals"]
    T_2 = pattern_2["T"]

    array_1 = np.zeros(new_time - current_time, dtype=bool)
    array_2 = np.zeros(new_time - current_time, dtype=bool)

    for start, end in intervals_1:
        while start + start_time_1 < min(end_time_1, new_time):
            if end + start_time_1 <= current_time:
                start += T_1
                end += T_1
                continue
            else:
                low = max(current_time, start + start_time_1) - current_time
                high = min(new_time, end + start_time_1) - current_time
                array_1[low:high] = 1
                start += T_1
                end += T_1
    for start, end in intervals_2:
        while start + start_time_2 < min(end_time_2, new_time):
            if end + start_time_2 <= current_time:
                start += T_2
                end += T_2
                continue
            else:
                low = max(current_time, start + start_time_2) - current_time
                high = min(new_time, end + start_time_2) - current_time
                array_2[low:high] = 1
                start += T_2
                end += T_2

    return np.sum(array_1 & array_2)


def cal_link_job_conflicts(jobs, job_time_period, current_time, new_time):
    # Calculate job traffic conflicts on a single link
    # jobs: {job_name: pattern}
    # job_time_period: {job_name: (start_time, end_time)}
    # return: {job_name: conflict}
    link_job_conflicts = {job_name: 0 for job_name in jobs.keys()}
    calculated_pairs = set()
    # Iterate over each job and calculate its conflict within the time range
    for job_name, pattern in jobs.items():
        for other_job_name, other_pattern in jobs.items():
            if other_job_name == job_name:
                continue
            pair = frozenset([job_name, other_job_name])
            if pair in calculated_pairs:
                continue
            start_time = time.time()
            conflict_value = cal_overlap(
                pattern,
                other_pattern,
                *job_time_period[job_name],
                *job_time_period[other_job_name],
                current_time,
                new_time,
            )
            print(f"Cal link job conflicts: {time.time()-start_time}")
            link_job_conflicts[job_name] += conflict_value
            link_job_conflicts[other_job_name] += conflict_value
            calculated_pairs.add(pair)

    return link_job_conflicts


def cal_job_conflicts(link_traffic_pattern, job_time_period, current_time, new_time):
    # Calculate max conflict of each job on each link
    # from current_time to new_time
    # link_traffic_patter: {link: {job_name: pattern}}
    # Return a {job_name: conflict} dict
    job_conflicts = {}
    start_time = time.time()
    for link, jobs in link_traffic_pattern.items():
        link_job_conflicts = cal_link_job_conflicts(
            jobs, job_time_period, current_time, new_time
        )  # # the conflict of each job on link: {job_name: conflict}}
        for job_name, conflict in link_job_conflicts.items():
            if job_name in job_conflicts:
                job_conflicts[job_name] = max(job_conflicts[job_name], conflict)
            else:
                job_conflicts[job_name] = conflict
    print(f"Cal job conflicts: {time.time()-start_time}")
    return job_conflicts


if __name__ == "__main__":
    jobs_1 = {
        "job1": {"intervals": [[0, 2]], "T": 10},
        "job2": {"intervals": [[1, 3]], "T": 10},
    }

    link_traffic_pattern = {"link1": jobs_1}

    job_time_period = {
        "job1": [0, 100],
        "job2": [0, 100],
    }

    current_time = 12
    new_time = 22

    conflicts = cal_job_conflicts(
        link_traffic_pattern, job_time_period, current_time, new_time
    )
    print("job Conflicts:", conflicts)
