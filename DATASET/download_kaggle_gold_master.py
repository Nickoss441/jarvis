import shutil
import subprocess
from pathlib import Path

try:
	import kagglehub
except ImportError:  # pragma: no cover - fallback path
	kagglehub = None

DATASET_ID = "aminasalamt/gold-price-master-dataset-2015-2026-lxauusd"
TARGET_ROOT = Path("D:/DATASET")


def _replace_path(src: Path, dst: Path) -> None:
	if dst.exists():
		if dst.is_dir():
			shutil.rmtree(dst)
		else:
			dst.unlink()
	if src.is_dir():
		shutil.copytree(src, dst)
	else:
		dst.parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(src, dst)


def main() -> None:
	TARGET_ROOT.mkdir(parents=True, exist_ok=True)
	target_path = TARGET_ROOT / DATASET_ID.split("/")[-1]

	if kagglehub is not None:
		download_path = Path(kagglehub.dataset_download(DATASET_ID))
		_replace_path(download_path, target_path)
		print("Downloaded cache path:", download_path)
		print("Copied dataset to:", target_path)
		return

	cmd = [
		"kaggle",
		"datasets",
		"download",
		"-d",
		DATASET_ID,
		"--unzip",
		"--path",
		str(target_path),
	]
	try:
		result = subprocess.run(cmd, capture_output=True, text=True)
	except FileNotFoundError as exc:
		raise RuntimeError(
			"Kaggle CLI not found. Install kagglehub with 'pip install kagglehub' "
			"or install Kaggle CLI and ensure 'kaggle' is on PATH."
		) from exc
	if result.returncode != 0:
		raise RuntimeError(
			"kagglehub is not installed and Kaggle CLI download failed. "
			"Install kagglehub with 'pip install kagglehub' or configure Kaggle CLI credentials. "
			f"stderr: {result.stderr.strip()}"
		)
	print("Downloaded dataset to:", target_path)


if __name__ == "__main__":
	main()
