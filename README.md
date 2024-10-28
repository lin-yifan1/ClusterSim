# ClusterSim

## Overview
This project requires [SCIP](https://scipopt.org/) to solve certain optimization problems. Please follow the steps below to install SCIP and configure the project properly.

## Prerequisites
- SCIP (installation instructions in [SCIP_README.md](./SCIP_README.md))

## Installation

### 1. Install SCIP
To run this project, you first need to install SCIP. Please refer to [SCIP_README.md](./SCIP_README.md) for detailed installation instructions.

### 2. Configure `config.py`
After successfully installing SCIP, you need to update the `scipstp_path_full` in the `config.py` file to point to your local SCIP binary. 

1. Open the `config.py` file.
2. Find the line that defines `scipstp_path_full`:
    ```python
    scipstp_path_full = "/path/to/your/scip/binary"
    ```
3. Modify the path to the full path of the SCIP executable on your system.

For example, if your SCIP binary is located at `/usr/local/bin/scip`, the line should look like:
```python
scipstp_path_full = "/usr/local/bin/scip"
