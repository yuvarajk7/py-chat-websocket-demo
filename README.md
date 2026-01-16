# Python Websocket demo

## Windows  - Allow powershell to activate venv
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser

## UV Package manager & Project setup
uv init
uv add -r requirements.txt
uv add "fastapi[standard]"
uv sync

## Git hub

### Fix - is on a file system that does not record ownership
git config --global --add safe.directory "*"

### Fix - Suppress warning LF will be replaced by CRLF the next time Git touches it
git config --global core.autocrlf false
git config --global core.eol lf

## Support FastAPI Dev support
uv add "fastapi[standard]"

## Run
uv run fastapi dev app/main.py --host 0.0.0.0 --port 8080
uvicorn app.main:app --reload --port 8080
