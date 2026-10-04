# Repository Guidelines

## Project Structure & Module Organization
`main.py` starts the FastAPI server defined in `web.py`. Core backend logic lives in `core/`, HTTP endpoints in `apis/`, page handlers in `views/`, scheduled jobs in `jobs/`, and WeChat/browser drivers in `driver/`. Frontend source is in `web_ui/src/`; built assets are served from `static/`. HTML templates for the legacy views live in `public/templates/`. Docker and deployment files are under `compose/` and `Dockerfiles/`. Keep new docs in `docs/` and utility scripts in `tools/` or `script/`.

## Build, Test, and Development Commands
Install backend dependencies with `pip install -r requirements.txt`, then copy `config.example.yaml` to `config.yaml`. Run the full backend locally with `python main.py -job True -init True`; this starts FastAPI, jobs, and initialization hooks. Frontend development happens in `web_ui/`: `npm install`, `npm run dev`, and `npm run build`. For the MQTT helper in `qtserver/`, use `npm install` and `npm run start`. Docker development should read runtime settings from `/.env`; use `docker compose -f compose/docker-compose.dev.yaml up -d --force-recreate` and avoid hardcoding credentials or proxy settings in compose files.

## Coding Style & Naming Conventions
Follow the existing style before introducing cleanup. Python uses 4-space indentation, snake_case for modules/functions, and grouped feature folders such as `core/notice/` and `apis/`. Vue files in `web_ui/src/views/` use PascalCase filenames like `AccessKeyManagement.vue`; composable utilities and API wrappers use camelCase or lower-case filenames such as `auth.ts` and `messageTask.ts`. There is no enforced formatter config in the repo, so keep imports tidy, avoid broad refactors, and match surrounding conventions.

## Testing Guidelines
Backend test coverage is minimal and mostly lives near the code, for example `core/lax/test_template_parser.py`. Run it from that directory with `cd core/lax && python -m unittest test_template_parser.py`. When touching API, scraping, or scheduler code, also do a local smoke test by starting `python main.py` and exercising the affected UI or endpoint. Frontend changes should at least pass `npm run build`.

## Commit & Pull Request Guidelines
Recent history includes `feat:` commits alongside ad-hoc messages like `1.4.9-Fix`; use Angular-style commits going forward, for example `fix: handle expired WeChat cookies`. Keep the body as `-` prefixed lines without blank lines. Create a fresh working branch before changes; for Codex-assisted work use `codex/YYYY-MM-DD`. PRs should include a short problem statement, the key changes, linked issues when relevant, config or migration notes, and screenshots for UI changes.
This clone should keep `origin` pointed at your fork and `upstream` pointed at `https://github.com/rachelos/we-mp-rss`. Before pushing or opening a PR, fetch upstream and merge the latest `upstream/main` into your working branch if it has advanced.

## Security & Configuration Tips
Do not commit `config.yaml`, `/.env`, tokens, cookies, or data from `data/`. Start from `config.example.yaml` and `/.env.example`, then keep real secrets in local-only config. For deployment environments where WeChat blocks datacenter IPs, prefer the compose `singbox` sidecar and a single `PROXY_URL=` entry in `/.env` instead of modifying host proxy settings or duplicating proxy fields across files. Review `SECURITY.md` before changing auth, webhooks, or access-key flows.
