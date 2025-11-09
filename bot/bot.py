import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Tuple

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import subprocess
import datetime

# Обеспечиваем импорт из проекта
ROOT_DIR = Path("/root/wan-video-app")
if str(ROOT_DIR) not in sys.path:
	sys.path.append(str(ROOT_DIR))

from app.models.video_generator import TextToVideoGenerator


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("tg-bot")

outputs_dir = ROOT_DIR / "outputs"
outputs_dir.mkdir(parents=True, exist_ok=True)

# Глобальные объекты (инициализация может занять время)
generator = TextToVideoGenerator()

executor = ThreadPoolExecutor(max_workers=1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await update.message.reply_text(
		"Привет! Пришлите текстовый промпт — я сгенерирую видео на WAN 2.2 TI2V‑5B. "
		"Генерация может занять несколько минут.\n"
		"Команды: /status — показать прогресс, /cancel — отменить текущую генерацию."
	)


def _generate_sync(prompt: str) -> Tuple[str, str]:
	# Прямая генерация без оптимизации промпта
	video_path = generator.generate(prompt=prompt)
	return prompt, video_path


def _maybe_compress(path: str, target_mb: int = 48) -> str:
	size_mb = os.path.getsize(path) / (1024 * 1024)
	if size_mb <= target_mb:
		return path
	# Сжать через ffmpeg, уменьшая битрейт/разрешение до ширины 720
	compressed = str(outputs_dir / (Path(path).stem + "_tg.mp4"))
	os.system(
		f"ffmpeg -y -i {path} -vf \"scale='min(720,iw)':-2\" -c:v libx264 -preset veryfast -crf 28 -c:a aac -b:a 96k {compressed} >/dev/null 2>&1"
	)
	return compressed if os.path.exists(compressed) else path


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if not update.message or not update.message.text:
		return
	prompt = update.message.text.strip()
	log.info("handle_text: received message length=%d", len(prompt))
	if not prompt:
		return
	await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
	await update.message.reply_text("Запускаю видеогенерацию. Это может занять 5–15 минут…")
	try:
		log.info("handle_text: start generation")
		optimized, video_path = await asyncio.get_running_loop().run_in_executor(executor, _generate_sync, prompt)
		log.info("handle_text: generation finished path=%s", video_path)
		out_path = await asyncio.get_running_loop().run_in_executor(executor, _maybe_compress, video_path)
		await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
		caption = f"Промпт:\n{optimized}"
		with open(out_path, "rb") as f:
			await update.message.reply_video(video=f, caption=caption)
	except Exception as e:
		log.exception("generation failed")
		await update.message.reply_text(f"Ошибка генерации: {e}")


def _get_status_text() -> str:
	# PID и время работы
	ps = subprocess.run(
		"pgrep -fa '/root/Wan2.2/generate.py' || true",
		shell=True, stdout=subprocess.PIPE, text=True
	).stdout.strip()
	lines = ps.splitlines() if ps else []
	pids_info = []
	for ln in lines:
		try:
			pid = int(ln.split()[0])
			u = subprocess.run(f"ps -o etimes= -p {pid}", shell=True, stdout=subprocess.PIPE, text=True)
			secs = int((u.stdout or '0').strip() or 0)
		except Exception:
			pid, secs = None, 0
		if pid:
			pids_info.append((pid, secs, ln))

	# GPU
	gpu = subprocess.run(
		"nvidia-smi --query-gpu=memory.total,memory.used,utilization.gpu --format=csv,noheader || true",
		shell=True, stdout=subprocess.PIPE, text=True
	).stdout.strip()

	# Логи и последний файл
	log_tail = subprocess.run("tail -n 5 /root/wan_wip.log 2>/dev/null || true", shell=True, stdout=subprocess.PIPE, text=True).stdout.strip()
	last_file = ""
	try:
		last_file = subprocess.run(
			"ls -1t /root/wan-video-app/outputs/*.mp4 2>/dev/null | head -n 1",
			shell=True, stdout=subprocess.PIPE, text=True
		).stdout.strip()
	except Exception:
		last_file = ""
	size_line = ""
	if last_file:
		size_line = subprocess.run(f"ls -lh {last_file} 2>/dev/null | awk '{{print $5, $6, $7, $8}}'", shell=True, stdout=subprocess.PIPE, text=True).stdout.strip()

	now = datetime.datetime.utcnow().strftime("%H:%M:%S UTC")
	text = [f"Время: {now}"]
	if pids_info:
		for pid, secs, ln in pids_info[:3]:
			text.append(f"Генерация PID {pid}, прошло ~{secs}s\n{ln}")
	else:
		text.append("Процесс генерации не найден.")
	if gpu:
		text.append(f"GPU: {gpu}")
	if last_file:
		text.append(f"Последний файл: {last_file} ({size_line})")
	if log_tail:
		text.append("Лог:\n" + log_tail)
	return "\n\n".join(text)


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	txt = await asyncio.get_running_loop().run_in_executor(executor, _get_status_text)
	await update.message.reply_text(txt or "Нет данных.")


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	subprocess.run("pkill -f '/root/Wan2.2/generate.py' || true", shell=True)
	await update.message.reply_text("Отмена отправлена. Проверьте /status через несколько секунд.")


def main():
	token = os.environ.get("TELEGRAM_BOT_TOKEN")
	if not token:
		print("TELEGRAM_BOT_TOKEN not set")
		sys.exit(1)
	app = Application.builder().token(token).build()
	app.add_handler(CommandHandler("start", start))
	app.add_handler(CommandHandler("status", status_cmd))
	app.add_handler(CommandHandler("cancel", cancel_cmd))
	app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
	print("Bot started")
	app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
	main()


