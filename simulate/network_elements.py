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

    def get_route(self, server_a, server_b):
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
            spine = (tor_a + tor_b) % self.num_spines  # Deterministic Spine selection
            route.append(Link(f"Server-{server_a}", f"ToR-{tor_a}"))
            route.append(Link(f"ToR-{tor_a}", f"Spine-{spine}"))
            route.append(Link(f"Spine-{spine}", f"ToR-{tor_b}"))
            route.append(Link(f"ToR-{tor_b}", f"Server-{server_b}"))

        return route

    def get_server_for_gpu(self, gpu):
        # return the corresponding server for the given GPU
        # gpu should have the form "GPU-{id}"
        _, gpu_id = gpu.split("-")
        gpu_id = int(gpu_id)
        server_id = gpu_id // self.gpus_per_server
        return f"Server-{server_id}"

    def ring_link_list(self, job_gpu_list):
        # job_gpu_list: list of GPUs occupied by the job
        server_list = list({self.get_server_for_gpu(gpu) for gpu in job_gpu_list})
        if len(server_list) == 1:
            return []
        link_set = set()
        for i in range(len(server_list)):
            server_1 = server_list[i]
            server_2 = server_list[(i + 1) % len(server_list)]
            link_set = link_set.union(set(self.get_route(server_1, server_2)))
        return list(link_set)

    def hd_link_list(self, job_gpu_list):
        pass


if __name__ == "__main__":
    topology = ClosTopology()
    print("GPU-0 is under", topology.get_server_for_gpu("GPU-0"))
    print("GPU-120 is under", topology.get_server_for_gpu("GPU-120"))
    route = topology.get_route(
        topology.get_server_for_gpu("GPU-0"), topology.get_server_for_gpu("GPU-120")
    )
    print(route)
