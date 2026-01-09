import argparse
import os
import time
from datetime import datetime, timezone
# from minio import Minio
# from minio.error import S3Error
from tqdm import tqdm
import requests
from urllib.parse import urljoin
import calendar


class SwiftFileDownloader:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/") + "/"
        self.objects_file_name = "file_list.txt"

    # ---------------------------------------------------------
    # Convert timestamps to YYYY/MM prefixes in range
    # ---------------------------------------------------------
    def generate_prefixes(self, start_ts, end_ts):
        prefixes = []
        start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        end = datetime.fromtimestamp(end_ts, tz=timezone.utc)

        year = start.year
        month = start.month

        while (year < end.year) or (year == end.year and month <= end.month):
            prefixes.append(f"{year:04d}/{month:02d}")
            month += 1
            if month > 12:
                month = 1
                year += 1

        return prefixes

    def download_files(self, start_time, end_time, destination_folder, time_format="human"):
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder, exist_ok=True)

        # Convert times
        if time_format == "human":
            start_ts = calendar.timegm(time.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
            end_ts = calendar.timegm(time.strptime(end_time, "%Y-%m-%d %H:%M:%S"))
        else:
            start_ts = start_time
            end_ts = end_time

        print(f"Start TS: {start_ts}, End TS: {end_ts}")

        # -----------------------------------------------------
        # Fetch file list list.txt at runtime
        # -----------------------------------------------------
        objects_url = urljoin(self.base_url, self.objects_file_name)
        resp = requests.get(objects_url)

        if resp.status_code != 200:
            print(f"Failed to fetch {self.objects_file_name}: HTTP {resp.status_code}")
            return

        all_files = resp.text.splitlines()
        print(f"Loaded {len(all_files)} filenames")

        # -----------------------------------------------------
        # Prefix filtering
        # -----------------------------------------------------
        prefixes = self.generate_prefixes(start_ts, end_ts)

        candidate_files = [
            fname for fname in all_files
            if any(fname.startswith(prefix) for prefix in prefixes)
        ]

        # -----------------------------------------------------
        # Timestamp filtering
        # -----------------------------------------------------
        target_files = []
        for fname in candidate_files:
            filename = fname.split("/")[-1]
            if not filename.startswith("ALL"):
                continue
            try:
                ts = int(filename.split("_")[1].split(".")[0])
            except:
                continue

            if start_ts <= ts <= end_ts:
                target_files.append((fname, ts))

        print(f"{len(target_files)} files match the timestamp range")

        # -----------------------------------------------------
        # Download loop
        # -----------------------------------------------------
        for fname, ts in target_files:
            local_path = os.path.join(destination_folder, fname.split("/")[-1])

            if os.path.exists(local_path):
                print(f"Skipping {fname}, already exists.")
                continue

            file_url = urljoin(self.base_url, fname)
            print(f"Downloading {fname}")

            # Stream download
            with requests.get(file_url, stream=True) as r:
                if r.status_code != 200:
                    print(f"Failed downloading {fname}: HTTP {r.status_code}")
                    continue

                total_size = int(r.headers.get("Content-Length", 0))

                with open(local_path, "wb") as f, tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=fname,
                    leave=True
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            human_time = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Finished {fname} ({human_time} UTC)")

        print("All requested files downloaded.")


class MinioFileDownloader:
    def __init__(self, endpoint="airlab-share-01.andrew.cmu.edu:9000", bucket_name="ameliaswim"):
        self.client = Minio(endpoint, secure=True)
        self.bucket_name = bucket_name

    def download_files(self, start_time, end_time, destination_folder, time_format="human"):
        # Create destination folder if it doesn't exist
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
        if time_format == "human":
            start_timestamp = int(time.mktime(time.strptime(start_time, '%Y-%m-%d %H:%M:%S')))
            end_timestamp = int(time.mktime(time.strptime(end_time, '%Y-%m-%d %H:%M:%S')))
        elif time_format == "unix":
            start_timestamp = start_time
            end_timestamp = end_time
        else:
            print("Time format invalid..")
            raise ValueError("Invalid time format. Use 'human' or 'unix'.")

        pbar = tqdm(range(1, 9), desc="Downloading")
        for i in pbar:
            prefix = f'ALL{i}_'
            pbar.set_postfix({"iteration": i})
            print("For Prefix", prefix, "in 1 to 8")
            objects = self.client.list_objects(self.bucket_name, prefix=prefix)
            for obj in (objects):
                file_timestamp = int(obj.object_name.split('_')[1].split('.')[0])
                # print("Checking", file_timestamp)
                if start_timestamp <= file_timestamp <= end_timestamp:
                    self._download_file(obj.object_name, destination_folder)

    def _download_file(self, object_name, destination_folder):
        file_path = os.path.join(destination_folder, object_name)
        if not os.path.exists(file_path):
            try:
                response = self.client.get_object(self.bucket_name, object_name)
                with open(file_path, "wb") as file_data:
                    for d in response.stream(32 * 1024):
                        file_data.write(d)
                response.close()
                response.release_conn()
                # Get timestamp from the object name and convert it to human-readable format
                timestamp = int(object_name.split('_')[1].split('.')[0])
                human_readable_time = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                print(f"\nDownloaded {object_name} ({human_readable_time})")
            except S3Error as err:
                print(f"Failed to download {object_name}: {err}")
        else:
            print(f"File {object_name} already exists, skipping download.")


def main():
    parser = argparse.ArgumentParser(
        description='Download files from a MinIO bucket within a specified time range.')
    parser.add_argument('--base_url', required=False,
                        default="https://airlab-cloud.andrew.cmu.edu:8080/swift/v1/AUTH_ac8533a83cff4d48bc8c608ad222d330/amelia_swim/", help='MinIO server endpoint')
    parser.add_argument('--start_time', default='2026-01-01 00:00:00',
                        help='Start time in the format YYYY-MM-DD HH:MM:SS (default: 2026-01-01 00:00:00)')
    parser.add_argument('--end_time', default='2026-01-01 01:00:00',
                        help='End time in the format YYYY-MM-DD HH:MM:SS (default: 2026-01-01 01:00:00)')
    parser.add_argument('--destination', required=False, default="datasets/amelia/raw_data",
                        help='Local directory to save the downloaded files')

    args = parser.parse_args()

    downloader = SwiftFileDownloader(args.base_url)
    downloader.download_files(args.start_time, args.end_time, args.destination)


if __name__ == '__main__':
    main()
