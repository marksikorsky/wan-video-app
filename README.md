# WAN 2.2 TI2V-5B + Qwen 7B: API + Telegram Bot

Минимальный сервис для генерации видео:
- Оптимизация промпта: Qwen 7B (через `transformers`)
- Генерация видео: Wan2.2 TI2V-5B (официальный `Wan-Video/Wan2.2` + веса с HF)
- Веб-API (FastAPI) и простой HTML UI
- Telegram-бот (по токену)

## Структура
```
wan-video-app/
  app/                 # FastAPI, модули моделей
  bot/                 # Telegram-бот (polling)
  web/                 # HTML + статика
  requirements.txt     # зависимости API/бота
  wan-watch.sh         # монитор прогресса генерации в терминале
```

Внешние артефакты (не входят в репозиторий):
- `/root/Wan2.2` — официальный код генератора (git clone)
- `/root/Wan2.2-TI2V-5B` — веса модели (HF snapshot)

## Быстрый старт на новом сервере
1) Системные зависимости:
```bash
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git ffmpeg build-essential
```

2) Клонируйте этот репозиторий:
```bash
git clone <ваш_repo_url>.git
cd wan-video-app
```

3) Python-окружение для API/бота:
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

4) WAN окружение (рекомендуемо через conda для Torch 2.4+):
```bash
# Miniconda (если нет)
cd /root
curl -fsSL -o miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash miniconda.sh -b -p /root/miniconda
eval "$(/root/miniconda/bin/conda shell.bash hook)"
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# env с Python 3.10
conda create -y -n wanenv python=3.10

# Код и веса WAN2.2
git clone https://github.com/Wan-Video/Wan2.2.git /root/Wan2.2
conda run -n wanenv pip install --no-cache-dir torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu121
conda run -n wanenv pip install --no-cache-dir diffusers==0.35.2 transformers==4.51.3 tokenizers==0.21.0 accelerate==1.11.0 easydict ftfy dashscope imageio-ffmpeg decord einops opencv-python huggingface_hub sentencepiece protobuf peft==0.17.1 librosa soundfile imageio importlib-metadata regex requests safetensors

# Веса модели (HF)
conda run -n wanenv python - << 'PY'
from huggingface_hub import snapshot_download
snapshot_download(repo_id="Wan-AI/Wan2.2-TI2V-5B", local_dir="/root/Wan2.2-TI2V-5B", local_dir_use_symlinks=False)
print("WAN2.2-TI2V-5B downloaded")
PY
```

5) FastAPI (локально):
```bash
cd /root/wan-video-app
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080
```
UI: `http://<ip>:8080/`

6) Telegram-бот (polling):
```bash
. .venv/bin/activate
export TELEGRAM_BOT_TOKEN="ВАШ_ТОКЕН"
nohup python bot/bot.py > /root/tg_bot.log 2>&1 &
```
Команды в боте: `/status`, `/cancel`.

## Прогресс генерации в терминале
```bash
nohup /root/wan-video-app/wan-watch.sh > /root/wan_progress.log 2>&1 &
tail -f /root/wan_progress.log
tail -f /root/wan_wip.log
```

## Советы по скорости (RTX 4090)
- Для стабильности на 5B используйте `--offload_model True --t5_cpu`.
- Smoke-test: `--infer_frames 12 --sample_steps 6` (быстрее)
- Полноценная 5с@24fps 720p (1280x704): 50 шагов, ~8–12 минут.

## Секреты
Не коммитьте токены. Используйте `.env` или переменные окружения. В репозитории есть `.gitignore`.


