from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from yappr.peec.models import Brand, Project, TabularResponse


class PeecClientError(RuntimeError):
    """Raised when the Peec client cannot complete a request."""


class PeecAPIError(PeecClientError):
    """Raised when the Peec API returns an error response."""


class PeecClient:
    def __init__(self, api_key: str, base_url: str = "https://api.peec.ai/customer/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.http = httpx.Client(
            base_url=self.base_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-Key": api_key,
            },
            timeout=30.0,
        )

    def __enter__(self) -> PeecClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        self.http.close()

    def list_projects(self) -> list[Project]:
        payload = self._request("GET", "/projects")
        rows = self._extract_rows(payload)
        return [Project.model_validate(row) for row in rows]

    def list_brands(self, project_id: str | None = None) -> list[Brand]:
        params = {"project_id": project_id} if project_id else None
        payload = self._request("GET", "/brands", params=params)
        rows = self._extract_rows(payload)
        return [Brand.model_validate(row) for row in rows]

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self.http.request(method, path, params=params, json=json)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            message = self._error_message(exc.response)
            raise PeecAPIError(message) from exc
        except httpx.HTTPError as exc:
            raise PeecClientError(f"Could not reach Peec API at {self.base_url}: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise PeecClientError("Peec API returned a non-JSON response.") from exc

    def _extract_rows(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            if "rows" in payload:
                table = TabularResponse.model_validate(payload)
                return table.rows

            for key in ("data", "projects", "items"):
                rows = payload.get(key)
                if isinstance(rows, Iterable) and not isinstance(rows, (str, bytes, dict)):
                    return [item for item in rows if isinstance(item, dict)]

        raise PeecClientError("Peec API returned an unexpected response shape for /projects.")

    def _error_message(self, response: httpx.Response) -> str:
        detail: str | None = None
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            for key in ("message", "error", "detail"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    detail = value.strip()
                    break

        if response.status_code == 401:
            return "Peec API rejected the API key. Check PEEC_API_KEY and try again."

        if detail:
            return f"Peec API error ({response.status_code}): {detail}"

        return f"Peec API error ({response.status_code})."
