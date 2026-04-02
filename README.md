# Primerch — KIE nano-banana-2 demo (FastAPI + test frontend)

## Что есть

- FastAPI API (обертка над KIE `nano-banana-2`):
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

4) Создай сайт (подставь свой username):

```bash
pa website create --domain YOURUSERNAME.pythonanywhere.com --command '~/.virtualenvs/primerch/bin/uvicorn --env-file ~/primerch/backend/.env --app-dir ~/primerch/backend --uds ${DOMAIN_SOCKET} app.main:app'
```

5) После изменений в коде:

```bash
pa website reload --domain YOURUSERNAME.pythonanywhere.com
```

Логи: `/var/log/YOURUSERNAME.pythonanywhere.com.error.log`, `/var/log/YOURUSERNAME.pythonanywhere.com.server.log`.

## Важно про callback

KIE шлёт callback на `callBackUrl`. Локальный `localhost` обычно недоступен снаружи.
Для callback выстави публичный адрес:

```bash
export PUBLIC_BASE_URL="https://your-public-domain.com"
```

Важно: в этой реализации логотип/картинки сначала загружаются в KIE File Upload API, поэтому для локально загруженного
логотипа (`/api/uploads`) публичный URL не нужен. Для внешних картинок (например, с gifts.ru) URL должен быть публичным.

Если callback недоступен — UI работает через polling `GET /api/tasks/{taskId}`.
