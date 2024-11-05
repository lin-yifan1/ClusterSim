import math
from collections import defaultdict
from natsort import natsorted


class Link:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __eq__(self, other):
        return isinstance(other, Link) and (
            {self.start, self.end} == {other.start, other.end}
        )

    def __hash__(self):
        return hash(frozenset([self.start, self.end]))

    def __repr__(self):
        return f"{self.start} <-> {self.end}"


class ClosTopology:
    def __init__(
        self, num_spines=12, num_tors=64, servers_per_tor=6, gpus_per_server=8
    ):
        # Spines, ToRs, Servers and GPUs are denoted as
        # "Spine-{id}", "ToR-{id}", "Server-{id}" and "GPU-{id}" respectively,
        # with id starts from 0
        self.num_spines = num_spines
        self.num_tors = num_tors
        self.servers_per_tor = servers_per_tor
        self.gpus_per_server = gpus_per_server

    def get_server_route(self, server_a, server_b):
        # TODO: to be removed
        # Parse server indices
        _, server_a = server_a.split("-")
        _, server_b = server_b.split("-")
        server_a, server_b = int(server_a), int(server_b)

        # Determine ToR switches for each server
        tor_a = server_a // self.servers_per_tor
        tor_b = server_b // self.servers_per_tor
        route = []

        if tor_a == tor_b:
            # If both servers are under the same ToR, route directly
            route.append(Link(f"ToR-{tor_a}", f"Server-{server_a}"))
            route.append(Link(f"Server-{server_b}", f"ToR-{tor_a}"))
        else:
            # If servers are under different ToRs, go through a Spine switch
            # TODO
            spine = (tor_a + tor_b) % self.num_spines  # Deterministic Spine selection
            route.append(Link(f"Server-{server_a}", f"ToR-{tor_a}"))
            route.append(Link(f"ToR-{tor_a}", f"Spine-{spine}"))
            route.append(Link(f"Spine-{spine}", f"ToR-{tor_b}"))
            route.append(Link(f"ToR-{tor_b}", f"Server-{server_b}"))

        return route

    def get_gpu_route(self, gpu_a, gpu_b):
        # Return route from gpu_a to gpu_b
        _, gpu_a = gpu_a.split("-")
        _, gpu_b = gpu_b.split("-")
        gpu_a, gpu_b = int(gpu_a), int(gpu_b)
        server_a = gpu_a // self.gpus_per_server
        tor_a = gpu_a // (self.servers_per_tor * self.gpus_per_server)
        tor_b = gpu_b // (self.servers_per_tor * self.gpus_per_server)
        route = []
        if tor_a == tor_b:
            return route
        else:
            spine = ((2**31 - 1) * server_a) % self.num_spines
            route.append(Link(f"ToR-{tor_a}", f"Spine-{spine}"))
            route.append(Link(f"Spine-{spine}", f"ToR-{tor_b}"))
        return route

    def get_server_for_gpu(self, gpu):
        # return the corresponding server for the given GPU
        # gpu should have the form "GPU-{id}"
        _, gpu_id = gpu.split("-")
        gpu_id = int(gpu_id)
        server_id = gpu_id // self.gpus_per_server
        return f"Server-{server_id}"

    def get_gpu_local_rank(self, gpu):
        # return the rank of gpu in a server
        # gpu should have the form "GPU-{id}"
        _, gpu_id = gpu.split("-")
        gpu_id = int(gpu_id)
        rank = gpu_id % self.gpus_per_server
        return rank

    def ring_link_list(self, job_gpu_list):
        # job_gpu_list: list of GPUs occupied by the job
        server_list = natsorted(
            list({self.get_server_for_gpu(gpu) for gpu in job_gpu_list})
        )
        if len(server_list) == 1:
            return []
        link_set = set()
        for i in range(len(server_list)):
            server_1 = server_list[i]
            server_2 = server_list[(i + 1) % len(server_list)]
            link_set = link_set.union(set(self.get_route(server_1, server_2)))
        return list(link_set)

    def hd_comm_link_list(self, job_gpu_list):
        # job_gpu_list: list of GPUs occupied by the job
        # Return: Links occupied in HD AllReduce process
        # Note that same link may appear multiple times if it appears in different AllReduce ops
        def hd_comm_pairs(gpu_group):
            # gpu_list: group of GPUs with the same rank
            # return communication pairs of HD AllReduce
            gpu_group = natsorted(gpu_group)
            num_gpus = len(gpu_group)
            if num_gpus == 1:
                return []

            communication_pairs = []
            r = num_gpus - 2 ** (int(math.log2(num_gpus)))
            # Stage 1
            for i in range(0, r):
                communication_pairs.append((gpu_group[2 * i], gpu_group[2 * i + 1]))
                communication_pairs.append((gpu_group[2 * i + 1], gpu_group[2 * i]))
            removed_gpus = [gpu_group[2 * i + 1] for i in range(0, r)]
            remain_gpus = [server for server in gpu_group if server not in removed_gpus]
            # Stage 2
            step = 1
            while step < num_gpus - r:
                for i in range(0, num_gpus - r, step * 2):
                    for j in range(step):
                        communication_pairs.append(
                            (remain_gpus[i + j], remain_gpus[i + j + step])
                        )
                        communication_pairs.append(
                            (remain_gpus[i + j + step], remain_gpus[i + j])
                        )
                step *= 2
            return communication_pairs

        def hd_comm_link_set(gpu_group):
            link_set = set()
            for pair in hd_comm_pairs(gpu_group):
                route = self.get_gpu_route(*pair)
                link_set = link_set.union(set(route))
            return link_set

        max_dp_ways = 4
        total_gpu_num = len(job_gpu_list)
        dp_ways = min(total_gpu_num // self.gpus_per_server, max_dp_ways)
        gpu_num_per_dp_way = total_gpu_num // dp_ways
        job_gpu_list = natsorted(job_gpu_list)
        dp_allreduce_gpu_groups = [
            job_gpu_list[i::gpu_num_per_dp_way] for i in range(gpu_num_per_dp_way)
        ]
        comm_links = []
        for gpu_group in dp_allreduce_gpu_groups:
            comm_links += list(hd_comm_link_set(gpu_group))
        return comm_links


if __name__ == "__main__":
    topology = ClosTopology()
    gpu_list = [f"GPU-{i}" for i in range(0, 128)]
    print(topology.hd_comm_link_list(gpu_list))
