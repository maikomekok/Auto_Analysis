import tarfile
import os


def create_tar_gz(archive_name, folder_path):
    # Ensure the folder exists
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    # Open the tar.gz file in write mode
    with tarfile.open(archive_name, "w:gz") as tar:
        # Add the folder to the tar.gz file
        tar.add(folder_path, arcname=os.path.basename(folder_path))
        print(f"Archive '{archive_name}' created successfully.")


# Example usage:
folder_path = "C:/Users/admin/Desktop/data_small"  # Path to the folder you want to archive
archive_name = "btc_raw_2024-07-16.tar.gz"  # Desired archive name

create_tar_gz(archive_name, folder_path)


