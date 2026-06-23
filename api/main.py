"""
FastAPI-бэкенд с двумя обученными моделями.

Эндпоинты:
  GET  /            — проверка живости
  POST /clf_image   — классификация изображения (вид спорта), вход: файл изображения
  POST /clf_text    — классификация текста (категория новости Telegram), вход: JSON {"text": ...}

Запуск локально:  python main.py   (или: uvicorn main:app --reload)
"""

import logging
from contextlib import asynccontextmanager

import PIL.Image
import uvicorn
from fastapi import FastAPI, UploadFile
from pydantic import BaseModel

from utils.model_func import (
    load_class_names,
    load_image_model,
    load_text_model,
    predict_image,
    predict_text,
)

logger = logging.getLogger("uvicorn.info")


class ImageResponse(BaseModel):
    class_name: str   # предсказанный вид спорта
    confidence: float # уверенность модели [0..1]


class TextInput(BaseModel):
    text: str         # текст новостного поста


class TextResponse(BaseModel):
    label: str        # категория: крипта / мода / спорт / технологии / финансы
    confidence: float # уверенность модели [0..1]


# Глобальные объекты моделей (заполняются в lifespan)
image_model = None
class_names = None
text_tokenizer = None
text_model = None
label_encoder = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Загрузка моделей при старте, освобождение при остановке."""
    global image_model, class_names
    global text_tokenizer, text_model, label_encoder

    class_names = load_class_names()
    image_model = load_image_model()
    logger.info("Image model (ResNet18, %d классов) загружена", len(class_names))

    text_tokenizer, text_model, label_encoder = load_text_model()
    logger.info("Text model (BERT, %d классов) загружена", len(label_encoder.classes_))

    yield

    del image_model, text_model, text_tokenizer, label_encoder


app = FastAPI(title="Sport & News Classifier API", lifespan=lifespan)


@app.get("/")
def root():
    """Проверка живости сервиса."""
    return {"status": "ok", "message": "Sport & News Classifier API"}


@app.post("/clf_image", response_model=ImageResponse)
def classify_image(file: UploadFile):
    """Классификация изображения: предсказывает вид спорта."""
    image = PIL.Image.open(file.file).convert("RGB")
    label, confidence = predict_image(image_model, class_names, image)
    return ImageResponse(class_name=label, confidence=confidence)


@app.post("/clf_text", response_model=TextResponse)
def classify_text(data: TextInput):
    """Классификация текста: предсказывает категорию новости Telegram."""
    label, confidence = predict_text(text_tokenizer, text_model, label_encoder, data.text)
    return TextResponse(label=label, confidence=confidence)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
