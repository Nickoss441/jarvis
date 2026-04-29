import sys
import os
from pathlib import Path

try:
    import requests
except ImportError:
    print("The 'requests' library is required. Install it with 'pip install requests'.")
    sys.exit(1)

def download_to_dataset(url: str, filename: str = None):
    dataset_dir = Path("D:/DATASET")
    dataset_dir.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = url.split("/")[-1].split("?")[0]
    target_path = dataset_dir / filename
    print(f"Downloading {url} to {target_path} ...")
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(target_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"Download complete: {target_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_to_dataset.py <url> [filename]")
        sys.exit(1)
    url = sys.argv[1]
    filename = sys.argv[2] if len(sys.argv) > 2 else None
    download_to_dataset(url, filename)
