import os
import subprocess
import time
from typing import Optional


WAN_REPO_DIR = "/root/Wan2.2"
WAN_CKPT_DIR = "/root/Wan2.2-TI2V-5B"
CONDABIN = "/root/miniconda/bin/conda"
CONDA_ENV = "wanenv"
WIP_LOG = "/root/wan_wip.log"


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
	# Команды: сначала пытаемся multi-GPU; при ошибке — single-GPU smoke.
	cmd_multi = (
		f"eval \"$({CONDABIN} shell.bash hook)\" && "
		# Устойчивые настройки NCCL для некоторых сред
		f"export NCCL_P2P_DISABLE=1 NCCL_IB_DISABLE=1 NCCL_SHM_DISABLE=1 NCCL_BLOCKING_WAIT=1 TORCH_NCCL_ASYNC_ERROR_HANDLING=1 && "
		f"CUDA_VISIBLE_DEVICES=0,1,2,3 "
		f"conda run -n {CONDA_ENV} torchrun --standalone --nproc_per_node=4 generate.py "
		f"--task ti2v-5B --size {size} --ckpt_dir {WAN_CKPT_DIR} "
		f"--save_file {save_file} --infer_frames 24 --sample_steps 24 "
		f"--prompt {subprocess.list2cmdline([prompt])}"
	)
	cmd_single = (
		f"eval \"$({CONDABIN} shell.bash hook)\" && "
		# Улучшаем управление памятью и фиксируем одну GPU
		f"export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:256 && "
		f"CUDA_VISIBLE_DEVICES=0 "
		f"conda run -n {CONDA_ENV} python generate.py "
		# Надёжный fallback для ti2v-5B: только 1280*704 или 704*1280 поддерживаются
		f"--task ti2v-5B --size 1280*704 --ckpt_dir {WAN_CKPT_DIR} "
		f"--offload_model True --convert_model_dtype --t5_cpu "
		f"--save_file {save_file} --infer_frames 4 --sample_steps 6 "
		f"--prompt {subprocess.list2cmdline([prompt])}"
	)
	# Выполняем в каталоге репозитория и пишем лог для мониторинга прогресса
	with open(WIP_LOG, "w", encoding="utf-8") as logf:
		logf.write(f"[{time.strftime('%H:%M:%S')}] Start generation (multi-gpu try)\n")
		logf.write(f"CMD: {cmd_multi}\n")
		logf.flush()
		proc = subprocess.run(
			cmd_multi,
			cwd=WAN_REPO_DIR,
			shell=True,
			executable="/bin/bash",
			stdout=logf,
			stderr=subprocess.STDOUT,
			text=True,
		)
	if proc.returncode != 0:
		# Пробуем single-GPU smoke test
		with open(WIP_LOG, "a", encoding="utf-8") as logf:
			logf.write(f"[{time.strftime('%H:%M:%S')}] Multi-GPU failed (code {proc.returncode}), fallback to single-GPU smoke\n")
			logf.write(f"CMD: {cmd_single}\n")
			logf.flush()
			proc2 = subprocess.run(
				cmd_single,
				cwd=WAN_REPO_DIR,
				shell=True,
				executable="/bin/bash",
				stdout=logf,
				stderr=subprocess.STDOUT,
				text=True,
			)
		if proc2.returncode != 0:
			# Возвращаем хвост лога при ошибке
			tail = ""
			try:
				with open(WIP_LOG, "r", encoding="utf-8", errors="ignore") as f:
					lines = f.readlines()[-200:]
					tail = "".join(lines)
			except Exception:
				tail = ""
			raise RuntimeError(f"WAN generate failed (single fallback). See {WIP_LOG}\n{tail}")
	if os.path.exists(save_file):
		return save_file
	# Ищем mp4 в выходной папке на случай, если имя изменилось
	for root, _, files in os.walk(out_dir):
		for name in files:
			if name.lower().endswith(".mp4"):
				return os.path.join(root, name)
	raise FileNotFoundError("WAN generation finished but no MP4 found")


