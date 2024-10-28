import os
import config


def clean_tmp_file():
    for dir_path in [config.stp_file_dir, config.stp_solution_dir]:
        if os.path.exists(dir_path):
            for file_name in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print(f"Cleaned all files in: {dir_path}")
        else:
            print(f"Directory does not exist: {dir_path}")


if __name__ == "__main__":
    clean_tmp_file()
