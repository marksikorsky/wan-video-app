import os
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.models.video_generator import TextToVideoGenerator


APP_DIR = "/root/wan-video-app"
OUTPUT_DIR = os.path.join(APP_DIR, "outputs")
WEB_DIR = os.path.join(APP_DIR, "web")
TEMPLATES_DIR = os.path.join(WEB_DIR, "templates")
STATIC_DIR = os.path.join(WEB_DIR, "static")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="T2V Service")

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class GenerateRequest(BaseModel):
	prompt: str
	num_inference_steps: Optional[int] = 25
	guidance_scale: Optional[float] = 6.0
	num_frames: Optional[int] = 32
	height: Optional[int] = 320
	width: Optional[int] = 512
	fps: Optional[int] = 8


# Загружаем генератор при старте
video_generator = TextToVideoGenerator()


@app.get("/", response_class=HTMLResponse)
async def index():
	index_path = os.path.join(TEMPLATES_DIR, "index.html")
	if not os.path.exists(index_path):
		return HTMLResponse("<h1>UI не найден</h1>", status_code=500)
	with open(index_path, "r", encoding="utf-8") as f:
		return HTMLResponse(f.read())


@app.post("/api/generate")
async def generate(req: GenerateRequest):
	if not req.prompt or not req.prompt.strip():
		raise HTTPException(status_code=400, detail="Пустой промпт")
	# Прямой запуск WAN без оптимизации промпта
	prompt = req.prompt.strip()
	save_path = video_generator.generate(
		prompt=prompt,
		num_inference_steps=req.num_inference_steps or 25,
		guidance_scale=req.guidance_scale or 6.0,
		num_frames=req.num_frames or 32,
		height=req.height or 320,
		width=req.width or 512,
		fps=req.fps or 8,
	)
	video_name = os.path.basename(save_path)
	return JSONResponse(
		{
			"video_url": f"/outputs/{video_name}",
			"file_name": video_name,
		}
	)



