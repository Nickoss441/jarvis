import kagglehub

# Download latest version
path = kagglehub.dataset_download("aminasalamt/gold-price-master-dataset-2015-2026-lxauusd")

print("Path to dataset files:", path)
