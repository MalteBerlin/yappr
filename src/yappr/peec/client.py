from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

import httpx

from yappr.peec.models import (
    AIModel,
    Brand,
    DomainSource,
    PeecData,
    Project,
    TabularResponse,
    Topic,
    TopicCoverage,
    URLSource,
)


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
        return [Project.model_validate(row) for row in self._extract_rows(payload)]

    def list_brands(self, project_id: str | None = None) -> list[Brand]:
        payload = self._request("GET", "/brands", params=self._project_params(project_id))
        return [Brand.model_validate(row) for row in self._extract_rows(payload)]

    def list_topics(self, project_id: str | None = None) -> list[Topic]:
        payload = self._request("GET", "/topics", params=self._project_params(project_id))
        return [Topic.model_validate(row) for row in self._extract_rows(payload)]

    def list_models(self, project_id: str | None = None) -> list[AIModel]:
        payload = self._request("GET", "/models", params=self._project_params(project_id))
        return [AIModel.model_validate(row) for row in self._extract_rows(payload)]

    def list_chats(
        self,
        *,
        start_date: str,
        end_date: str,
        project_id: str | None = None,
        brand_id: str | None = None,
        limit: int = 1,
    ) -> int:
        params: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": 0,
        }
        params.update(self._project_params(project_id))
        if brand_id:
            params["brand_id"] = brand_id

        payload = self._request("GET", "/chats", params=params)
        if isinstance(payload, dict):
            total_count = payload.get("totalCount")
            if isinstance(total_count, int):
                return total_count

        return len(self._extract_rows(payload))

    def get_brand_report(
        self,
        *,
        start_date: str,
        end_date: str,
        project_id: str | None = None,
        dimensions: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        payload = self._request(
            "POST",
            "/reports/brands",
            json=self._report_payload(
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
                dimensions=dimensions,
                filters=filters,
                limit=limit,
            ),
        )
        return self._extract_rows(payload)

    def get_domain_report(
        self,
        *,
        start_date: str,
        end_date: str,
        project_id: str | None = None,
        dimensions: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 1000,
    ) -> list[DomainSource]:
        payload = self._request(
            "POST",
            "/reports/domains",
            json=self._report_payload(
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
                dimensions=dimensions,
                filters=filters,
                limit=limit,
            ),
        )
        return [self._parse_domain_source(row) for row in self._extract_rows(payload)]

    def get_url_report(
        self,
        *,
        start_date: str,
        end_date: str,
        project_id: str | None = None,
        dimensions: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 1000,
    ) -> list[URLSource]:
        payload = self._request(
            "POST",
            "/reports/urls",
            json=self._report_payload(
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
                dimensions=dimensions,
                filters=filters,
                limit=limit,
            ),
        )
        return [self._parse_url_source(row) for row in self._extract_rows(payload)]

    def fetch_audit_data(
        self,
        *,
        project_id: str | None,
        project_name: str | None,
        project_scope: str,
        target_domain: str,
        own_brand: Brand,
        brands: list[Brand],
        start_date: str,
        end_date: str,
    ) -> PeecData:
        topics = self.list_topics(project_id=project_id)
        models = self.list_models(project_id=project_id)
        total_chats = self.list_chats(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
        )
        brand_rows = self.get_brand_report(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
        )
        topic_rows = self.get_brand_report(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            dimensions=["topic_id"],
        )
        all_domain_sources = self.get_domain_report(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
        )
        gap_sources = self.get_domain_report(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            filters=[{"field": "gap", "operator": "gte", "value": 1}],
        )
        gap_url_sources = self.get_url_report(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            filters=[{"field": "gap", "operator": "gte", "value": 1}],
        )

        brands_by_id = {brand.id: brand.model_copy() for brand in brands}
        for row in brand_rows:
            brand_id = self._nested_id(row.get("brand")) or self._string_value(row, "brand_id")
            if brand_id is None or brand_id not in brands_by_id:
                continue

            current = brands_by_id[brand_id]
            brands_by_id[brand_id] = current.model_copy(
                update={
                    "visibility": self._float_value(row, "visibility"),
                    "sentiment": self._float_value(row, "sentiment"),
                    "position": self._float_value(row, "position"),
                    "share_of_voice": self._float_value(row, "share_of_voice"),
                    "mention_count": self._int_value(row, "mention_count"),
                    "visibility_count": self._int_value(row, "visibility_count"),
                    "visibility_total": self._int_value(row, "visibility_total"),
                }
            )

        own_brand_metrics = brands_by_id[own_brand.id]
        competitors = [brands_by_id[brand.id] for brand in brands if brand.id != own_brand.id]
        domain_sources = [
            source for source in all_domain_sources if own_brand.id in source.mentioned_brand_ids
        ]

        topics_by_id = {
            topic.id: TopicCoverage(topic_id=topic.id, topic_name=topic.name) for topic in topics
        }
        for row in topic_rows:
            topic_id = self._nested_id(row.get("topic")) or self._string_value(row, "topic_id")
            brand_id = self._nested_id(row.get("brand")) or self._string_value(row, "brand_id")
            if topic_id is None or brand_id is None or topic_id not in topics_by_id:
                continue

            visibility = self._float_value(row, "visibility")
            current = topics_by_id[topic_id]
            if brand_id == own_brand.id:
                topics_by_id[topic_id] = current.model_copy(update={"visibility": visibility})
                continue

            if visibility > current.competitor_max_visibility:
                competitor_name = brands_by_id.get(brand_id)
                topics_by_id[topic_id] = current.model_copy(
                    update={
                        "competitor_max_visibility": visibility,
                        "top_competitor_name": competitor_name.name if competitor_name else None,
                    }
                )

        derived_total_chats = total_chats
        if own_brand_metrics.visibility_total > 0:
            derived_total_chats = own_brand_metrics.visibility_total
        elif brand_rows:
            derived_total_chats = max(
                self._int_value(row, "visibility_total") for row in brand_rows
            )

        return PeecData(
            project_id=project_id or "project-scoped",
            project_name=project_name,
            project_scope=project_scope,
            domain=target_domain,
            own_brand=own_brand_metrics,
            competitors=competitors,
            topics=list(topics_by_id.values()),
            all_domain_sources=all_domain_sources,
            domain_sources=domain_sources,
            gap_sources=gap_sources,
            gap_url_sources=gap_url_sources,
            active_models=[model.name for model in models if model.is_active],
            total_chats=derived_total_chats,
            date_range=(start_date, end_date),
        )

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

        raise PeecClientError("Peec API returned an unexpected response shape.")

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

    def _project_params(self, project_id: str | None) -> dict[str, Any]:
        return {"project_id": project_id} if project_id else {}

    def _report_payload(
        self,
        *,
        project_id: str | None,
        start_date: str,
        end_date: str,
        dimensions: list[str] | None,
        filters: list[dict[str, Any]] | None,
        limit: int,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": 0,
        }
        if project_id:
            payload["project_id"] = project_id
        if dimensions:
            payload["dimensions"] = dimensions
        if filters:
            payload["filters"] = filters
        return payload

    def _parse_domain_source(self, row: dict[str, Any]) -> DomainSource:
        return DomainSource(
            domain=self._string_value(row, "domain") or "",
            classification=self._string_value(row, "classification"),
            retrieved_percentage=self._float_value(row, "retrieved_percentage"),
            retrieval_rate=self._float_value(row, "retrieval_rate"),
            citation_rate=self._float_value(row, "citation_rate"),
            mentioned_brand_ids=self._mentioned_brand_ids(row.get("mentioned_brands"))
            or self._string_list(row.get("mentioned_brand_ids")),
        )

    def _parse_url_source(self, row: dict[str, Any]) -> URLSource:
        url = self._string_value(row, "url") or ""
        return URLSource(
            url=url,
            classification=self._string_value(row, "classification"),
            title=self._string_value(row, "title"),
            channel_title=self._string_value(row, "channel_title"),
            retrievals=self._int_value(row, "retrievals"),
            citation_count=self._int_value(row, "citation_count"),
            citation_rate=self._float_value(row, "citation_rate"),
            mentioned_brand_ids=self._mentioned_brand_ids(row.get("mentioned_brands"))
            or self._string_list(row.get("mentioned_brand_ids")),
        )

    def _mentioned_brand_ids(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        brand_ids = []
        for item in value:
            if isinstance(item, dict):
                brand_id = self._nested_id(item)
                if brand_id:
                    brand_ids.append(brand_id)
        return brand_ids

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]

    def _nested_id(self, value: Any) -> str | None:
        if isinstance(value, dict):
            nested_id = value.get("id")
            if isinstance(nested_id, str):
                return nested_id
        return None

    def _string_value(self, row: dict[str, Any], key: str) -> str | None:
        value = row.get(key)
        if isinstance(value, str):
            return value
        return None

    def _float_value(self, row: dict[str, Any], key: str) -> float:
        value = row.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    def _int_value(self, row: dict[str, Any], key: str) -> int:
        value = row.get(key)
        if isinstance(value, (int, float)):
            return int(value)
        return 0

    def url_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()
