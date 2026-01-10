import argparse
import os
import time
from datetime import datetime, timezone
import requests
from tqdm import tqdm
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
            start_time = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            end_time = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        print(f"Downloading files from {start_time} to {end_time}")
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

            human_time = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            if os.path.exists(local_path):
                print(f"Skipping {fname} ({human_time} UTC), already exists.")
                continue

            file_url = urljoin(self.base_url, fname)

            # Stream download
            with requests.get(file_url, stream=True) as r:
                if r.status_code != 200:
                    print(f"Failed downloading {fname} ({human_time} UTC): HTTP {r.status_code}")
                    continue

                total_size = int(r.headers.get("Content-Length", 0))

                with open(local_path, "wb") as f, tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=f"{fname} ({human_time} UTC)",
                    leave=True
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        print("All requested files downloaded.")


def main():
    parser = argparse.ArgumentParser(description="Download SWIM files using prefix + timestamp filtering.")
    parser.add_argument("--base_url",
                        required=False, default="https://airlab-cloud.andrew.cmu.edu:8080/swift/v1/AUTH_ac8533a83cff4d48bc8c608ad222d330/amelia_swim/")
    parser.add_argument("--start_time", default="2023-01-01 00:00:00",
                        help='Start time in UTC in the format YYYY-MM-DD HH:MM:SS (default: 2023-01-01 00:00:00)')
    parser.add_argument("--end_time", default="2023-01-02 00:00:00",
                        help='End time in UTC in the format YYYY-MM-DD HH:MM:SS (default: 2023-01-02 00:00:00)')
    parser.add_argument("--destination", default="datasets/amelia/raw_swim",
                        help='Local directory to save the downloaded files')
    args = parser.parse_args()

    downloader = SwiftFileDownloader(args.base_url)
    downloader.download_files(
        args.start_time,
        args.end_time,
        args.destination
    )


if __name__ == "__main__":
    main()
