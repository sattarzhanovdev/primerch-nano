# Primerch — KIE gpt-image/1.5-image-to-image demo (FastAPI + test frontend)

## Что есть

- FastAPI API (обертка над KIE `gpt-image/1.5-image-to-image`):
  - `POST /api/uploads` — загрузка картинки → возвращает ссылку
  - `GET /api/products` — товары из `base.json` (фильтр по полу/поиску)
  - `POST /api/generate` — создаёт задачу в KIE `jobs/createTask`
  - `GET /api/tasks/{taskId}` — проверка статуса через `record-info`
  - `POST /api/callback` — callback (если ваш URL публичный)
- Простой frontend без сборки: `frontend/index.html` (открывается через backend)

## Запуск

1) Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export KIE_API_KEY="YOUR_API_KEY"
cd backend
uvicorn app.main:app --reload --port 8000
```

2) Открыть UI

- `http://localhost:8000/`

## Деплой на PythonAnywhere (ASGI beta)

FastAPI требует ASGI, на PythonAnywhere это делается через их `pa` CLI (ASGI beta).

1) Залей код в домашнюю папку (например `~/primerch`) любым способом:
- `git clone ...` (если репозиторий на GitHub)
- или загрузка через Files → Upload

2) В консоли PythonAnywhere:

```bash
pip install --upgrade pythonanywhere
python3 -m venv ~/.virtualenvs/primerch
~/.virtualenvs/primerch/bin/pip install -r ~/primerch/backend/requirements.txt
```

3) Создай файл `~/primerch/backend/.env`:

```bash
KIE_API_KEY=YOUR_TOKEN
DEBUG_ROUTES=0
```

4) Создай сайт (подставь свой username).
Важно: внутри `--command` не используйте `~` — укажите абсолютные пути `/home/YOURUSERNAME/...`:

```bash
pa website create --domain YOURUSERNAME.pythonanywhere.com --command '/home/YOURUSERNAME/.virtualenvs/primerch/bin/python -m uvicorn --env-file /home/YOURUSERNAME/primerch/backend/.env --app-dir /home/YOURUSERNAME/primerch/backend --uds ${DOMAIN_SOCKET} app.main:app'
```

5) После изменений в коде:

```bash
pa website reload --domain YOURUSERNAME.pythonanywhere.com
```

Логи: `/var/log/YOURUSERNAME.pythonanywhere.com.error.log`, `/var/log/YOURUSERNAME.pythonanywhere.com.server.log`.

## Деплой на DigitalOcean

### Вариант A: App Platform (проще всего)

1) Залей репозиторий в GitHub.

2) DigitalOcean → **App Platform** → **Create App** → GitHub → выбери репо.

3) Выбери сборку из **Dockerfile** (он в корне проекта).

4) Добавь переменные окружения (App → Settings → Environment Variables):

- `KIE_API_KEY=...` (обязательно)
- `PUBLIC_BASE_URL=https://your-domain.com` (рекомендуется, если есть домен)
- опционально: `IMAGE_PROXY_ENABLED=1`, `EXTERNAL_IMAGE_PROXY_BASE=...`

5) В разделе **Domains** добавь домен — HTTPS включится автоматически.

⚠️ Папка `uploads/` по умолчанию хранится на файловой системе сервиса. В App Platform она может быть непостоянной
(загрузки могут пропасть при redeploy). Если нужна гарантированная сохранность — лучше **Droplet** + volume/бэкапы
или подключи persistent storage.

### Вариант B: Droplet (больше контроля)

1) Создай Ubuntu Droplet и привяжи домен к IP (A-record).

2) Установи Docker и Compose на сервере.

3) На сервере:

```bash
git clone <your-repo-url> primerch
cd primerch
cp backend/.env.example backend/.env
nano backend/.env
docker compose up -d --build
```

4) Проверка:

- `http://<server-ip>:8000/`

Дальше поставь reverse-proxy (Nginx/Caddy) на 80/443 и проксируй на `localhost:8000` для HTTPS.

## Важно про callback

KIE шлёт callback на `callBackUrl`. Локальный `localhost` обычно недоступен снаружи.
Для callback выстави публичный адрес:

```bash
export PUBLIC_BASE_URL="https://your-public-domain.com"
```

Важно: в этой реализации логотип/картинки сначала загружаются в KIE File Upload API, поэтому для локально загруженного
логотипа (`/api/uploads`) публичный URL не нужен. Для внешних картинок (например, с gifts.ru) URL должен быть публичным.

Если callback недоступен — UI работает через polling `GET /api/tasks/{taskId}`.