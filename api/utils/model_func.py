"""
Загрузка и инференс двух обученных моделей:
  1. Классификация изображений  — ResNet18, 100 классов видов спорта (датасет "100 Sports").
  2. Классификация текста        — BERT (rubert-tiny2), 5 категорий новостей Telegram.

Пути к весам строятся относительно расположения этого файла, поэтому код
работает одинаково и при локальном запуске, и внутри Docker-контейнера.
"""

from pathlib import Path

import joblib
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as T
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# .../api/weights
WEIGHTS_DIR = Path(__file__).resolve().parent.parent / "weights"

IMAGE_WEIGHTS = WEIGHTS_DIR / "sport_resnet18.pth"
CLASS_NAMES_FILE = WEIGHTS_DIR / "class_names.txt"
TEXT_MODEL_DIR = WEIGHTS_DIR / "text_model"
LABEL_ENCODER_FILE = TEXT_MODEL_DIR / "label_encoder.pkl"

# Инференс на CPU — облачный сервер обычно без GPU
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Стандартная нормализация ImageNet (как при обучении модели спорта)
_MEAN = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)

_image_transform = T.Compose(
    [
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(_MEAN, _STD),
    ]
)


# ------------------------- Классификация изображений -------------------------
def load_class_names():
    """Список из 100 названий видов спорта (по строкам файла)."""
    with open(CLASS_NAMES_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def load_image_model():
    """ResNet18 с подменённым классификатором на num_classes выходов."""
    class_names = load_class_names()
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(class_names))
    model.load_state_dict(torch.load(IMAGE_WEIGHTS, map_location=DEVICE))
    model.to(DEVICE)
    model.eval()
    return model


def transform_image(img):
    """PIL.Image -> батч-тензор (1, 3, 224, 224)."""
    return _image_transform(img).unsqueeze(0).to(DEVICE)


def predict_image(model, class_names, img):
    """Возвращает (название_класса, уверенность)."""
    tensor = transform_image(img)
    with torch.inference_mode():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        idx = int(torch.argmax(probs, dim=1).item())
    return class_names[idx], float(probs[0, idx].item())


# ---------------------------- Классификация текста ----------------------------
def load_text_model():
    """Возвращает (tokenizer, model, label_encoder) для классификатора новостей."""
    tokenizer = AutoTokenizer.from_pretrained(str(TEXT_MODEL_DIR))
    model = AutoModelForSequenceClassification.from_pretrained(str(TEXT_MODEL_DIR))
    model.to(DEVICE)
    model.eval()
    label_encoder = joblib.load(LABEL_ENCODER_FILE)
    return tokenizer, model, label_encoder


def predict_text(tokenizer, model, label_encoder, text):
    """Возвращает (категория, уверенность)."""
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=256,
    )
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    with torch.inference_mode():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)
        idx = int(torch.argmax(probs, dim=-1).item())
    category = label_encoder.inverse_transform([idx])[0]
    return str(category), float(probs[0, idx].item())
