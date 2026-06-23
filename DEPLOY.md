# Деплой

Архитектура: **FastAPI (backend) на сервере Selectel** + **Streamlit (frontend) на Streamlit Community Cloud**.

---

## 0. Подготовка: репозиторий на GitHub

Репозиторий уже инициализирован локально (с Git LFS для весов). Создайте пустой репозиторий на GitHub и запушьте:

```bash
cd fastapi-streamlit-deploy
git remote add origin https://github.com/<USER>/<REPO>.git
git push -u origin main
```

> Веса моделей (`*.pth`, `*.safetensors`) хранятся через **Git LFS** — иначе GitHub
> отклонит файл `model.safetensors` (116 МБ > лимита 100 МБ). Убедитесь, что `git lfs` установлен.

---

## 1. Аренда сервера Selectel

> Это делается вручную в личном кабинете — оплата и доступ привязаны к вашему аккаунту.

1. Зайдите на https://my.selectel.ru → **Облачная платформа** → **Серверы** → **Создать сервер**.
2. Параметры (минимально достаточные для CPU-инференса):
   - **ОС:** Ubuntu 22.04 LTS
   - **Конфигурация:** 2 vCPU / 4 ГБ RAM / 20+ ГБ диск (модели + зависимости ~3–4 ГБ).
   - **Сеть:** включить **публичный IPv4-адрес** (он понадобится фронту).
   - **SSH-ключ:** добавьте свой публичный ключ (`~/.ssh/id_ed25519.pub`) — это нужно и для VSCode Remote-SSH.
3. После создания запишите **публичный IP** сервера, напр. `203.0.113.10`.
4. В настройках **firewall / security group** откройте порты:
   - `22` (SSH)
   - `8000` (FastAPI)

---

## 2. Запуск backend на сервере

Подключитесь по SSH:

```bash
ssh root@203.0.113.10
```

### Вариант A — Docker (рекомендуется)

```bash
# установка docker
curl -fsSL https://get.docker.com | sh

# клонирование репозитория (с подтягиванием LFS-весов)
apt-get update && apt-get install -y git git-lfs && git lfs install
git clone https://github.com/<USER>/<REPO>.git
cd <REPO>/api

# сборка и запуск
docker build -t clf-api .
docker run -d --restart unless-stopped -p 8000:8000 --name clf-api clf-api
```

### Вариант B — без Docker

```bash
apt-get update && apt-get install -y python3-venv git git-lfs && git lfs install
git clone https://github.com/<USER>/<REPO>.git
cd <REPO>/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# фоновый запуск
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
```

### Проверка

С локальной машины:

```bash
curl http://203.0.113.10:8000/
# {"status":"ok","message":"Sport & News Classifier API"}
```

Документация API: `http://203.0.113.10:8000/docs`

---

## 3. Деплой frontend на Streamlit Community Cloud

1. Откройте https://share.streamlit.io → **Create app** → **From existing repo**.
2. Укажите:
   - **Repository:** `<USER>/<REPO>`
   - **Branch:** `main`
   - **Main file path:** `front/streamlit_app.py`
3. В **Advanced settings → Secrets** добавьте адрес вашего backend:
   ```toml
   BACKEND_URL = "http://203.0.113.10:8000"
   ```
4. **Deploy**. Зависимости подтянутся из корневого `requirements.txt` (streamlit + requests).

> Фронт читает `BACKEND_URL` из секретов (приоритет), затем из переменной окружения,
> иначе `http://127.0.0.1:8000`. См. `front/streamlit_app.py`.

⚠️ Streamlit Cloud работает по HTTPS, а backend — по HTTP. Современные браузеры это
пропускают, т.к. запросы идут с сервера Streamlit, а не из браузера. Если позже захотите
HTTPS на backend — поставьте перед FastAPI nginx + Let's Encrypt и пропишите домен в `BACKEND_URL`.

---

## 4. Подключение VSCode к серверу (после локальной отладки)

1. Установите расширение **Remote - SSH** (Microsoft).
2. Добавьте хост в `~/.ssh/config`:
   ```
   Host selectel-clf
       HostName 203.0.113.10
       User root
       IdentityFile ~/.ssh/id_ed25519
   ```
3. В VSCode: `Cmd+Shift+P` → **Remote-SSH: Connect to Host** → `selectel-clf`.
4. Откройте папку с репозиторием на сервере — можно править код и перезапускать
   контейнер/uvicorn прямо из VSCode.

Перезапуск backend после изменений:

```bash
# Docker
docker restart clf-api
# или без docker: убить процесс uvicorn и снова nohup ... &
```
```
