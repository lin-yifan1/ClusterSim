from collections import defaultdict
from utils import cal_job_conflicts
from simulate.network_elements import Link, ClosTopology


class TrafficManager:
    def __init__(self):
        self.current_time = 0
        self.link_traffic_pattern = {}  # A {link: {job_name: pattern}} dict
        self.job_time_period = (
            {}
        )  # Start and end time of each job, {job_name: (start_time, end_time)}
        self.ended_jobs = []  # jobs that already ended

    def add_traffic_pattern(
        self, link: Link, job_name, intervals, T, start_time, end_time
    ):
        # Add traffic pattern to a specific link for a given job
        if link not in self.link_traffic_pattern:
            self.link_traffic_pattern[link] = {}
        pattern = {
            # List of 2-lists representing the intervals in the first period,
            # starting from 0
            #  e.g. [[0,1],[2,3]] -> [[0,1),[2,3)]
            "intervals": intervals,
            "T": T,
        }
        self.link_traffic_pattern[link][job_name] = pattern
        self.job_time_period[job_name] = [start_time, end_time]

    def get_traffic_pattern(self, link: Link):
        return self.link_traffic_pattern[link]

    def release_job(self, job_name):
        # Release job from links
        for jobs in self.link_traffic_pattern.values():
            if job_name in jobs:
                del jobs[job_name]
        self.link_traffic_pattern = {
            link: jobs for link, jobs in self.link_traffic_pattern.items() if jobs != {}
        }  # filter out links with no flows

    def update_job_time_periods(self, delay_dict):
        # Update the intervals for each job based on the provided delay dictionary
        # delay_dict: {job_name: delay}
        for job_name, delay in delay_dict.items():
            T = 0
            for jobs in self.link_traffic_pattern.values():
                if job_name in jobs:
                    T = jobs[job_name]["T"]
            self.job_time_period[job_name][0] += delay % T
            self.job_time_period[job_name][1] += delay % T

    def update_traffic(self, new_time):
        job_conflicts = cal_job_conflicts(
            self.link_traffic_pattern, self.job_time_period, self.current_time, new_time
        )

        # Update each job's end time based on the calculated delay
        for job_name, conflict in job_conflicts.items():
            for jobs in self.link_traffic_pattern.values():
                if job_name in jobs:
                    T = jobs[job_name]["T"]
            if job_name in self.job_time_period:
                self.job_time_period[job_name][0] += conflict % T
                self.job_time_period[job_name][1] += conflict

        ended_jobs = []  # jobs end in time period [current_time, new_time)
        for job_name, time_period in self.job_time_period.items():
            if job_name not in self.ended_jobs and time_period[1] <= new_time:
                self.release_job(job_name)
                ended_jobs.append(job_name)
        self.ended_jobs += ended_jobs
        self.current_time = new_time
        return ended_jobs

    def get_job_list(self):
        return list(
            {
                job_name
                for jobs in self.link_traffic_pattern.values()
                for job_name in jobs
            }
        )

    def get_link_list(self):
        return list(self.link_traffic_pattern.keys())

    def get_job_duration(self):
        job_duration = defaultdict(lambda: defaultdict(int))  # {link: {job: duration}}
        for link, jobs in self.link_traffic_pattern.items():
            for job, pattern in jobs.items():
                job_duration[link][job] = sum(
                    end - start for start, end in pattern["intervals"]
                )
        return job_duration


if __name__ == "__main__":
    topology = ClosTopology()
    traffic_manager = TrafficManager()

    server_a = "Server-5"
    server_b = "Server-20"
    route = topology.get_route(server_a, server_b)
    print(f"Route between {server_a} and {server_b}: {route}")

    traffic_manager.add_traffic_pattern(
        route[0], "Trainingjob1", intervals=[[0, 2]], T=10, start_time=0, end_time=30
    )
    traffic_manager.add_traffic_pattern(
        route[0], "Trainingjob2", intervals=[[1, 4]], T=10, start_time=0, end_time=30
    )
    traffic_manager.add_traffic_pattern(
        route[0], "Trainingjob3", intervals=[[4, 6]], T=10, start_time=0, end_time=30
    )

    print("Initial job time periods: ", traffic_manager.job_time_period)

    # Update job intervals directly using a delay dictionary
    delay_dict = {"Trainingjob1": 2, "Trainingjob2": 1}
    traffic_manager.update_job_time_periods(delay_dict)
    print(
        "Job time periods after direct modification: ", traffic_manager.job_time_period
    )

    # Update traffic based on conflicts
    traffic_manager.update_traffic(20)

    # Print updated traffic patterns
    print("Job time periods after update: ", traffic_manager.job_time_period)
