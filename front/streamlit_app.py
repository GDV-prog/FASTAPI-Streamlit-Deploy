"""
Streamlit-фронтенд. Сам не загружает модели — только отправляет запросы
к FastAPI-бэкенду и показывает результат.

Адрес бэкенда берётся из (в порядке приоритета):
  1) st.secrets["BACKEND_URL"]   — для деплоя на Streamlit Community Cloud
  2) переменной окружения BACKEND_URL  — для docker-compose / локального запуска
  3) http://127.0.0.1:8000       — значение по умолчанию (локальная отладка)
"""

import os

import requests
import streamlit as st


# set_page_config обязан быть самой первой Streamlit-командой в скрипте.
st.set_page_config(page_title="Sport & News Classifier", page_icon="🤖")


def get_backend_url() -> str:
    # Обращение к st.secrets оборачиваем в try/except: при локальном запуске
    # без файла secrets.toml оно бросает исключение — это нормально.
    try:
        if "BACKEND_URL" in st.secrets:
            return st.secrets["BACKEND_URL"]
    except Exception:
        pass
    return os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


BACKEND_URL = get_backend_url().rstrip("/")

st.title("🤖 Классификатор: спорт по фото и тематика новостей")
st.caption(f"Backend: {BACKEND_URL}")

tab_img, tab_txt = st.tabs(["🏅 Изображение (вид спорта)", "📰 Текст (тематика новости)"])

def classify_image_bytes(img_bytes: bytes):
    """Отправляет байты изображения на backend и показывает результат."""
    st.image(img_bytes, width=300)
    try:
        res = requests.post(f"{BACKEND_URL}/clf_image", files={"file": img_bytes}, timeout=60)
        res.raise_for_status()
        data = res.json()
        st.success(f"Вид спорта: **{data['class_name']}**")
        st.write(f"Уверенность: `{data['confidence']:.2%}`")
    except Exception as e:
        st.error(f"Ошибка запроса к бэкенду: {e}")


with tab_img:
    st.subheader("Классификация изображения")
    source = st.radio(
        "Источник изображения",
        ["Загрузить файл", "Ссылка (URL)"],
        horizontal=True,
        key="img_source",
    )

    if source == "Загрузить файл":
        image = st.file_uploader("Загрузите изображение", type=["jpg", "jpeg", "png"])
        if st.button("Классифицировать изображение", key="btn_img_file"):
            if image is None:
                st.warning("Сначала загрузите изображение.")
            else:
                classify_image_bytes(image.getvalue())
    else:
        url = st.text_input("Вставьте ссылку на изображение (jpg/png)", key="img_url")
        if st.button("Классифицировать изображение", key="btn_img_url"):
            if not url.strip():
                st.warning("Вставьте ссылку на изображение.")
            else:
                try:
                    r = requests.get(url.strip(), timeout=30)
                    r.raise_for_status()
                    classify_image_bytes(r.content)
                except Exception as e:
                    st.error(f"Не удалось загрузить изображение по ссылке: {e}")

with tab_txt:
    st.subheader("Классификация текста")
    txt = st.text_area("Вставьте текст новостного поста:", height=150)
    if st.button("Определить тематику", key="btn_txt"):
        if not txt.strip():
            st.warning("Введите текст.")
        else:
            try:
                res = requests.post(f"{BACKEND_URL}/clf_text", json={"text": txt}, timeout=60)
                res.raise_for_status()
                data = res.json()
                st.success(f"Тематика: **{data['label']}**")
                st.write(f"Уверенность: `{data['confidence']:.2%}`")
            except Exception as e:
                st.error(f"Ошибка запроса к бэкенду: {e}")
