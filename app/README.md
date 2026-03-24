# Deprecated app

This directory preserves the old Streamlit app that used to power the public single-object workspace.

Status:

- public deployment retired
- Cloud Run service removed
- code kept in the repository for inspection and possible later revival

If you want to revisit this workflow later, start with:

1. `app/streamlit_app.py`
2. `Dockerfile`
3. `src/run_ranker.py`
4. `deploy/PUBLIC_RELEASE.md`

The maintained public surfaces now live in:

- `site/`
- `scripts/export_site_data_v2.py`
- `paper/`
