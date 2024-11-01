import params
import numpy as np


def generate_start_times(N, arrival_rate):
    inter_arrival_times = np.random.geometric(1 / arrival_rate, size=N)
    start_times = np.cumsum(inter_arrival_times)
    return start_times.tolist()


def sample_from_cdf(values, cdf_values, size=1):
    # only generate values from values list
    u = np.random.uniform(0, 1, size=size)
    indices = np.searchsorted(cdf_values, u, side="right")
    sampled_values = np.array(values)[indices]
    return sampled_values.tolist()


def sample_from_cdf_continuous(values, cdf_values, size=1):
    # able to generate values between the values list
    u = np.random.uniform(0, 1, size=size)
    interpolated_samples = np.interp(u, cdf_values, values)
    rounded_samples = np.round(interpolated_samples).astype(int)
    return rounded_samples.tolist()


if __name__ == "__main__":
    print(sample_from_cdf(params.sizes, params.cdf_sizes, params.job_num))
    print(sample_from_cdf_continuous(params.sizes, params.cdf_sizes, params.job_num))
