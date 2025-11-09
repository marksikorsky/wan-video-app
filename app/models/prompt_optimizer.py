import os
from typing import Optional

import torch
from transformers import (
	AutoModelForCausalLM,
	AutoTokenizer,
	BitsAndBytesConfig,
)


class PromptOptimizer:
	def __init__(
		self,
		model_id: str = "Qwen/Qwen2.5-7B-Instruct",
		load_in_4bit: bool = True,
		device_preference: Optional[str] = None,
	):
		self.model_id = model_id
		self.device = device_preference or ("cuda" if torch.cuda.is_available() else "cpu")

		quant_config = None
		if load_in_4bit:
			quant_config = BitsAndBytesConfig(
				load_in_4bit=True,
				bnb_4bit_use_double_quant=True,
				bnb_4bit_quant_type="nf4",
				bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float16,
			)

		try:
			self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
			self.model = AutoModelForCausalLM.from_pretrained(
				self.model_id,
				device_map="auto" if self.device == "cuda" else None,
				quantization_config=quant_config if self.device == "cuda" else None,
				torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
				trust_remote_code=True,
			)
			if self.device == "cpu":
				self.model.to(self.device)
		except Exception:
			# Fallback на более совместимую версию Qwen2 7B Instruct
			fallback_id = "Qwen/Qwen2-7B-Instruct"
			self.tokenizer = AutoTokenizer.from_pretrained(fallback_id, trust_remote_code=True)
			self.model = AutoModelForCausalLM.from_pretrained(
				fallback_id,
				device_map="auto" if self.device == "cuda" else None,
				quantization_config=quant_config if self.device == "cuda" else None,
				torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
				trust_remote_code=True,
			)
			if self.device == "cpu":
				self.model.to(self.device)

	def optimize(self, user_prompt: str, max_new_tokens: int = 256) -> str:
		system_prompt = (
			"Ты — оптимизатор промптов для генерации видео. "
			"Переформулируй запрос пользователя в чёткий, детальный и структурированный промпт, "
			"максимально подходящий для текст-видео диффузионной модели. "
			"Добавь конкретику: стиль, композицию, движения камеры, окружение, освещение, длительность, FPS. "
			"Отвечай только итоговым промптом без пояснений."
		)
		messages = [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		]
		prompt_text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
		inputs = self.tokenizer([prompt_text], return_tensors="pt")
		if self.device == "cuda":
			inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

		with torch.no_grad():
			output_ids = self.model.generate(
				**inputs,
				max_new_tokens=max_new_tokens,
				do_sample=True,
				top_p=0.9,
				temperature=0.7,
				pad_token_id=self.tokenizer.eos_token_id,
				eos_token_id=self.tokenizer.eos_token_id,
			)
		output_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
		# Возвращаем только добавленную ассистентом часть после шаблона
		return output_text.split(user_prompt, 1)[-1].strip() or output_text.strip()



