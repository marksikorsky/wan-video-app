import os
import time
from typing import Optional

from app.models.wan_runner import run_wan_ti2v


class TextToVideoGenerator:
	def __init__(
		self,
		model_id: str = "Wan-AI/Wan2.2-TI2V-5B",
		output_dir: str = "/root/wan-video-app/outputs",
		device_preference: Optional[str] = None,
	):
		self.model_id = model_id
		self.output_dir = output_dir
		os.makedirs(self.output_dir, exist_ok=True)

	def generate(
		self,
		prompt: str,
		num_inference_steps: int = 25,
		guidance_scale: float = 6.0,
		num_frames: int = 32,
		height: int = 704,
		width: int = 1280,
		fps: int = 24,
	) -> str:
		# WAN2.2 TI2V-5B поддерживает 720p как 1280*704
		try:
			return run_wan_ti2v(prompt=prompt, width=width, height=height, fps=fps)
		except Exception as wan_err:
			# Fallback: сообщаем об ошибке (вместо молчаливого даунгрейда)
			raise wan_err


