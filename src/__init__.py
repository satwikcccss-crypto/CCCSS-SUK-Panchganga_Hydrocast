"""HydroCast compatibility shim.

Re-exports the public API from the canonical ``backend/`` package so that
existing documentation, Dockerfiles, Windows setup scripts, and
``python -m src.*`` invocations continue to work while the canonical
import path is ``backend.<module>``.
"""
