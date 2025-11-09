import os
import subprocess
import time
from typing import Optional


WAN_REPO_DIR = "/root/Wan2.2"
WAN_CKPT_DIR = "/root/Wan2.2-TI2V-5B"
CONDABIN = "/root/miniconda/bin/conda"
CONDA_ENV = "wanenv"


def run_wan_ti2v(prompt: str, width: int = 1280, height: int = 704, fps: int = 24) -> str:
	"""
	Запускает Wan2.2 TI2V-5B через их generate.py в conda-окружении.
	Возвращает путь к сгенерированному видео (mp4).
	"""
	size = f"{width}*{height}"
	timestamp = int(time.time())
	out_dir = f"/root/wan-video-app/outputs"
	os.makedirs(out_dir, exist_ok=True)
	save_file = os.path.join(out_dir, f"wan_{timestamp}.mp4")
	cmd = (
		f"eval \"$({CONDABIN} shell.bash hook)\" && "
		f"conda run -n {CONDA_ENV} python generate.py "
		f"--task ti2v-5B --size {size} --ckpt_dir {WAN_CKPT_DIR} "
		f"--offload_model True --convert_model_dtype --t5_cpu "
		f"--save_file {save_file} --infer_frames 16 --sample_steps 8 "
		f"--prompt {subprocess.list2cmdline([prompt])}"
	)
	# Выполняем в каталоге репозитория
	proc = subprocess.run(cmd, cwd=WAN_REPO_DIR, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
	if proc.returncode != 0:
		raise RuntimeError(f"WAN generate failed: {proc.stdout[-2000:]}")
	if os.path.exists(save_file):
		return save_file
	# Ищем mp4 в выходной папке на случай, если имя изменилось
	for root, _, files in os.walk(out_dir):
		for name in files:
			if name.lower().endswith(".mp4"):
				return os.path.join(root, name)
	raise FileNotFoundError("WAN generation finished but no MP4 found")


