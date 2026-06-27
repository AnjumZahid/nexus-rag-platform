# backend/app/main.py


from backend.app.api.app import create_app


app = create_app()


# =================================
# Open another PowerShell window in the project and run:
# uv run python -m scripts.create_dev_token `
#     --user-id test-user `
#     --organization-id test-org `
#     --expires-minutes 60


# uv run alembic revision --autogenerate -m "add authentication tables"

# =================================

# how to run backend
# uv run uvicorn backend.app.main:app --reload
# http://127.0.0.1:8000/docs

# =================================

# how to run fronted:
# run from frontend folder.

# corepack pnpm@11.9.0 run dev

# http://localhost:3000

# =================================