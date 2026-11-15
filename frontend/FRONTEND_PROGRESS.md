# Frontend Progress Log

## Current task

Frontend Task 1: Page skeleton (not started)

## Done

- (nothing yet)

## In progress

- (nothing)

## Next step

Frontend Task 1 (TODO_LIST.md Section 2)

## Decisions made

- Plain HTML + CSS + JS in frontend/. No framework.
- The page only displays PNGs made by the server (see PROGRESS.md "Decisions").
- All settings live in the URL (?ra=&dec=&fov=...).

## Requests for backend

- (none yet)

## Known problems

- (none yet)

## How to run and test

- Backend: venv active, python data_mock.py (once), python cache.py clear,
  uvicorn main:app --reload
- Open http://127.0.0.1:8000/ (serves frontend/index.html)
- API docs: http://127.0.0.1:8000/docs
