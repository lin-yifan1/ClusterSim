import os
import subprocess


def run_scipstp(scipstp_path, stp_file, sol_file):
    """
    Runs the scipstp command on a single .stp file and writes the solution to the specified file.

    Parameters:
    scipstp_path (str): The full path to the scipstp executable.
    stp_file (str): The full path to the .stp file.
    sol_file (str): The full path where the solution file will be stored.
    """
    # Ensure the directory for the solution file exists
    os.makedirs(os.path.dirname(sol_file), exist_ok=True)

    # Build the scipstp command
    scipstp_executable = os.path.join(scipstp_path, "scipstp")
    cmd = [
        scipstp_executable,
        "-c",
        "set stp reduction 0",
        "-c",
        f"read {stp_file}",
        "-c",
        "optimize",
        "-c",
        f"write solution {sol_file}",
        "-c",
        "quit",
    ]

    # Run the scipstp command
    print(f"[INFO] Solving STP: Problem file located at '{stp_file}'...")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[INFO] STP Solving Complete: Solution file saved at '{stp_file}'.")
