import math
from typing import List, Set, Tuple


class Link:
    start: str
    end: str

    def __init__(self, start: str, end: str):
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
        self,
        num_spines: int = 12,
        num_tors: int = 64,
        servers_per_tor: int = 6,
        gpus_per_server: int = 8,
    ):
        # Spines, ToRs, Servers and GPUs are denoted as
        # "Spine-{id}", "ToR-{id}", "Server-{id}" and "GPU-{id}" respectively,
        # with id starts from 0
        self.num_spines = num_spines
        self.num_tors = num_tors
        self.servers_per_tor = servers_per_tor
        self.gpus_per_server = gpus_per_server

    def get_gpu_route(self, gpu_a: str, gpu_b: str) -> List[Link]:
        """
        Return route from gpu_a ("GPU-{ID}") to gpu_b
        """
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
            spine = ((2**31 - 1) * server_a) % self.num_spines  # hash
            route.append(Link(f"ToR-{tor_a}", f"Spine-{spine}"))
            route.append(Link(f"Spine-{spine}", f"ToR-{tor_b}"))
        return route

    def hd_comm_pairs(self, gpu_group: List[str]) -> List[Tuple[str, str]]:
        """
        Return GPU pairs of HD AllReduce
        gpu_group: GPUs in the same communication group
        Note that (GPU-0, GPU-1) and (GPU-1, GPU-0) are two different pairs
        """
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

    def hd_comm_link_list(self, job_gpu_list: List[str]) -> List[Link]:
        """
        Return: Links occupied in HD AllReduce process
        Note that same link may appear multiple times if it appears in different AllReduce ops
        """

        def hd_comm_link_set(gpu_group: List[str]) -> Set[Link]:
            """
            Link set occupied by one HD AllReduce operation
            """
            link_set = set()
            for pair in self.hd_comm_pairs(gpu_group):
                route = self.get_gpu_route(pair[0], pair[1])
                link_set = link_set.union(set(route))
            return link_set

        max_dp_ways = 4
        job_gpu_num = len(job_gpu_list)
        dp_ways = min(job_gpu_num // self.gpus_per_server, max_dp_ways)
        gpu_num_per_dp_way = job_gpu_num // dp_ways
        dp_allreduce_gpu_groups = [
            job_gpu_list[i::gpu_num_per_dp_way] for i in range(gpu_num_per_dp_way)
        ]
        comm_links = []
        for gpu_group in dp_allreduce_gpu_groups:
            comm_links += list(hd_comm_link_set(gpu_group))
        return comm_links

    def rdma_operate_tuples(
        self, gpu_group: List[str], msg_len: int
    ) -> List[List[Tuple[str, str, int]]]:
        """
        Return RDMA 3-tuples: (src_node, dst_node, msg_len) for single AllReduce group
        Only implemented the cases when len(gpu_group)=1, 2, 4
        """
        rdma_operate_tuples = []
        if len(gpu_group) == 1:
            return rdma_operate_tuples
        elif len(gpu_group) == 2:
            t1 = (gpu_group[0], gpu_group[1], msg_len)
            t2 = (gpu_group[1], gpu_group[0], msg_len)
            rdma_operate_tuples.append([t1, t2])
            t1 = (gpu_group[0], gpu_group[1], msg_len * 2)
            t2 = (gpu_group[1], gpu_group[0], msg_len * 2)
            rdma_operate_tuples.append([t1, t2])
        elif len(gpu_group) == 4:
            t1 = (gpu_group[0], gpu_group[1], msg_len)
            t2 = (gpu_group[1], gpu_group[0], msg_len)
            t3 = (gpu_group[2], gpu_group[3], msg_len)
            t4 = (gpu_group[3], gpu_group[2], msg_len)
            rdma_operate_tuples.append([t1, t2, t3, t4])
            t1 = (gpu_group[0], gpu_group[2], msg_len)
            t2 = (gpu_group[2], gpu_group[0], msg_len)
            t3 = (gpu_group[1], gpu_group[3], msg_len)
            t4 = (gpu_group[3], gpu_group[1], msg_len)
            rdma_operate_tuples.append([t1, t2, t3, t4])
            t1 = (gpu_group[0], gpu_group[2], msg_len * 2)
            t2 = (gpu_group[2], gpu_group[0], msg_len * 2)
            t3 = (gpu_group[1], gpu_group[3], msg_len * 2)
            t4 = (gpu_group[3], gpu_group[1], msg_len * 2)
            rdma_operate_tuples.append([t1, t2, t3, t4])
            t1 = (gpu_group[0], gpu_group[1], msg_len * 2)
            t2 = (gpu_group[1], gpu_group[0], msg_len * 2)
            t3 = (gpu_group[2], gpu_group[3], msg_len * 2)
            t4 = (gpu_group[3], gpu_group[2], msg_len * 2)
            rdma_operate_tuples.append([t1, t2, t3, t4])
        return rdma_operate_tuples

    def job_rdma_operates_tuples(
        self, job_gpu_list: List[str], msg_len: int
    ) -> List[List[List[Tuple[str, str, int]]]]:
        """
        Return RDMA 3-tuples: (src_node, dst_node, msg_len) for single job
        The 3-layer lists represent job > AllReduce group > phases in HD
        """
        max_dp_ways = 4
        job_gpu_num = len(job_gpu_list)
        dp_ways = min(job_gpu_num // self.gpus_per_server, max_dp_ways)
        gpu_num_per_dp_way = job_gpu_num // dp_ways
        dp_allreduce_gpu_groups = [
            job_gpu_list[i::gpu_num_per_dp_way] for i in range(gpu_num_per_dp_way)
        ]
        job_rdma_operates_tuples = []
        for gpu_group in dp_allreduce_gpu_groups:
            job_rdma_operates_tuples.append(
                self.rdma_operate_tuples(gpu_group, msg_len)
            )
        return job_rdma_operates_tuples
