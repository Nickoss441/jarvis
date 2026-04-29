import requests
import os

# Output directory
output_dir = r"d:\DATASET"
os.makedirs(output_dir, exist_ok=True)

# URLs and output filenames
endpoints = [
    {
        "url": "https://datasets-server.huggingface.co/rows?dataset=google%2FWaxalNLP&config=ach_asr&split=train&offset=0&length=100",
        "filename": "WaxalNLP_ach_asr_train_rows.json"
    },
    {
        "url": "https://datasets-server.huggingface.co/splits?dataset=google%2FWaxalNLP",
        "filename": "WaxalNLP_splits.json"
    },
    {
        "url": "https://huggingface.co/api/datasets/google/WaxalNLP/parquet/ach_asr/train",
        "filename": "WaxalNLP_ach_asr_train.parquet.json"
    }
]

def download_and_save(url, filename):
    print(f"Downloading {url} ...")
    response = requests.get(url)
    response.raise_for_status()
    out_path = os.path.join(output_dir, filename)
    with open(out_path, "wb") as f:
        f.write(response.content)
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    for ep in endpoints:
        download_and_save(ep["url"], ep["filename"])
    print("All downloads complete.")
