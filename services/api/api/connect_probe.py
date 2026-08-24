from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from parallax_api.code.production_delivery import VercelConnectGitHubCredentialProvider
from parallax_api.tools.providers.github_client import GitHubRestProviderClient


app = FastAPI()


@app.get("/")
def probe() -> dict[str, object]:
    if os.getenv("VERCEL_ENV") != "preview":
        raise HTTPException(status_code=404, detail="Not found")

    repository_ref = "github:Ryan9876/parallax"
    credentials = VercelConnectGitHubCredentialProvider("github/parallax-runtime")
    client = GitHubRestProviderClient(credentials)
    state = client.resolve_repository(repository_ref)
    return {
        "ready": True,
        "repository": state.repository_ref,
        "default_branch": state.default_branch,
        "head_revision": state.head_revision,
    }
