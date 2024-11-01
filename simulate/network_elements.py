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

    def hd_link_list(self, job_gpu_list):
        # TODO: to be removed
        # job_gpu_list: list of GPUs occupied by the job
        # return link list the job occupies for HD AllReduce
        server_list = natsorted(
            list({self.get_server_for_gpu(gpu) for gpu in job_gpu_list})
        )
        num_servers = len(server_list)
        if num_servers == 1:
            return []

        communication_pairs = []
        r = num_servers - 2 ** (int(math.log2(num_servers)))
        # Stage 1
        for i in range(0, r):
            communication_pairs.append((server_list[2 * i], server_list[2 * i + 1]))
        removed_servers = [server_list[2 * i + 1] for i in range(0, r)]
        remain_servers = [
            server for server in server_list if server not in removed_servers
        ]
        # Stage 2
        step = 1
        while step < num_servers - r:
            for i in range(0, num_servers - r, step * 2):
                for j in range(step):
                    communication_pairs.append(
                        (remain_servers[i + j], remain_servers[i + j + step])
                    )
            step *= 2
        link_set = set()
        for server_1, server_2 in communication_pairs:
            link_set = link_set.union(set(self.get_route(server_1, server_2)))
        return list(link_set)

    def group_by_rank(self, job_gpu_list, rank_list):
        # group GPUs into lists by their ranks
        rank_dict = defaultdict(list)
        for gpu, rank in zip(job_gpu_list, rank_list):
            rank_dict[rank].append(gpu)
        return list(rank_dict.values())

    def hd_communication_pairs(self, job_gpu_list):
        # job_gpu_list: list of GPUs occupied by the job
        # Return GPU communication pairs in HD AllReduce
        # Note that pairs are ordered,
        # (GPU-0, GPU-1) and (GPU-0, GPU-1) are two different pairs
        def hd_comm_pairs(gpu_list):
            # gpu_list: group of GPUs with the same rank
            # return communication pairs of HD AllReduce
            gpu_list = natsorted(gpu_list)
            num_gpus = len(gpu_list)
            if num_gpus == 1:
                return []

            communication_pairs = []
            r = num_gpus - 2 ** (int(math.log2(num_gpus)))
            # Stage 1
            for i in range(0, r):
                communication_pairs.append((gpu_list[2 * i], gpu_list[2 * i + 1]))
                communication_pairs.append((gpu_list[2 * i + 1], gpu_list[2 * i]))
            removed_gpus = [gpu_list[2 * i + 1] for i in range(0, r)]
            remain_gpus = [server for server in gpu_list if server not in removed_gpus]
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

        rank_list = [self.get_gpu_local_rank(gpu) for gpu in job_gpu_list]
        comm_pairs = []
        for gpu_group in self.group_by_rank(job_gpu_list, rank_list):
            comm_pairs += hd_comm_pairs(gpu_group)
        return comm_pairs


if __name__ == "__main__":
    topology = ClosTopology()
    print("GPU-0 is under", topology.get_server_for_gpu("GPU-0"))
    print("GPU-120 is under", topology.get_server_for_gpu("GPU-120"))
    route = topology.get_route(
        topology.get_server_for_gpu("GPU-0"), topology.get_server_for_gpu("GPU-120")
    )
    print(route)
