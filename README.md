# FastAPI + Streamlit: классификатор спорта и тематики новостей

Связка из двух обученных моделей (Фаза 2):

| Модель | Тип | Архитектура | Классы |
|--------|-----|-------------|--------|
| Изображения | классификация изображений | ResNet18 (transfer learning) | 100 видов спорта |
| Текст | классификация текста | BERT (rubert-tiny2) | крипта, мода, спорт, технологии, финансы |

**Архитектура деплоя:**

```
┌────────────────────────┐         HTTP/JSON        ┌──────────────────────────┐
│  Streamlit Cloud        │ ───────────────────────> │  Selectel (облачный VM)   │
│  front/streamlit_app.py │   POST /clf_image        │  FastAPI (api/main.py)    │
│  (только UI + requests) │   POST /clf_text         │  + веса моделей           │
└────────────────────────┘ <─────────────────────── └──────────────────────────┘
                              {class_name, confidence}
```

- **Backend (FastAPI)** — на арендованном сервере Selectel (модели и инференс здесь).
- **Frontend (Streamlit)** — на Streamlit Community Cloud, обращается к бэкенду по публичному IP.

## Структура

```
fastapi-streamlit-deploy/
├── api/                      # FastAPI backend (деплой на Selectel)
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── utils/model_func.py   # загрузка и инференс моделей
│   └── weights/
│       ├── sport_resnet18.pth
│       ├── class_names.txt
│       └── text_model/       # HF-модель + tokenizer + label_encoder.pkl
├── front/                    # Streamlit frontend (деплой на Streamlit Cloud)
│   ├── streamlit_app.py
│   ├── requirements.txt
│   └── Dockerfile
├── requirements.txt          # для Streamlit Cloud (= front/requirements.txt)
└── docker-compose.yaml       # локальный запуск обоих сервисов
```

## API

| Метод | Путь | Вход | Выход |
|-------|------|------|-------|
| GET | `/` | — | `{"status": "ok", ...}` |
| POST | `/clf_image` | multipart-файл `file` | `{"class_name": str, "confidence": float}` |
| POST | `/clf_text` | JSON `{"text": str}` | `{"label": str, "confidence": float}` |

## Локальный запуск

### Вариант 1 — без Docker (две консоли)

```bash
# 1) Backend
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # http://127.0.0.1:8000  (документация: /docs)

# 2) Frontend (в новой консоли)
cd front
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py   # http://localhost:8501
```

Фронт по умолчанию ходит в `http://127.0.0.1:8000`. Чтобы указать другой адрес:

```bash
BACKEND_URL=http://<IP>:8000 streamlit run streamlit_app.py
```

### Вариант 2 — Docker Compose

```bash
docker compose up --build
# frontend: http://localhost:8501   backend: http://localhost:8000
```

## Деплой

См. [DEPLOY.md](DEPLOY.md) — аренда сервера Selectel, запуск FastAPI и публикация Streamlit.
