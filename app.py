"""Alias entry point - delegates to Dashboard.py.

Some Streamlit Cloud deployments default to looking for app.py.
This file ensures the same single-page architecture runs regardless
of which entry filename is configured.
"""
exec(open("Dashboard.py", encoding="utf-8").read())
