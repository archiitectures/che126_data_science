"""Google Patents acquisition through the public BigQuery dataset."""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from datetime import date as calendar_date
from importlib import import_module
from pathlib import Path
from typing import Any

TABLE = "patents-public-data.patents.publications"
TEXT_FIELDS = ("title", "abstract", "claims", "description")


@dataclass(frozen=True)
class LocalizedText:
    language: str | None
    text: str | None


@dataclass(frozen=True)
class PatentRecord:
    publication_number: str
    family_id: str | None
    country_code: str | None
    publication_date: str | None
    title: tuple[LocalizedText, ...]
    abstract: tuple[LocalizedText, ...]
    assignees: tuple[str, ...]
    classifications: tuple[str, ...]
    url: str
    claims: tuple[LocalizedText, ...] = ()
    description: tuple[LocalizedText, ...] = ()


@dataclass(frozen=True)
class PatentResults:
    records: tuple[PatentRecord, ...]
    query: dict[str, Any]
    retrieved_at: str
    source_table: str = TABLE


@dataclass(frozen=True)
class QueryEstimate:
    bytes_processed: int
    maximum_bytes_billed: int


def export_json(results: PatentResults, path: str | Path) -> None:
    """Write records with acquisition provenance to a caller-selected file."""
    Path(path).write_text(
        json.dumps(asdict(results), indent=2) + "\n", encoding="utf-8"
    )


def _bigquery() -> Any:
    try:
        return import_module("google.cloud.bigquery")
    except ModuleNotFoundError as exc:
        if exc.name not in {"google", "google.cloud", "google.cloud.bigquery"}:
            raise
        raise ImportError(
            "Install patent support with: uv sync --extra patents"
        ) from exc


def _record(row: Any) -> PatentRecord:
    def texts(field: str) -> tuple[LocalizedText, ...]:
        return tuple(
            LocalizedText(x.get("language"), x.get("text"))
            for x in (row.get(field + "_localized") or ())
        )

    date = row.get("publication_date")
    parsed_date = None
    if date:
        try:
            parsed_date = calendar_date.fromisoformat(str(date)).isoformat()
        except ValueError:
            pass  # The dataset uses zero/unknown dates; never invent a date.
    number = row["publication_number"]
    return PatentRecord(
        publication_number=number,
        family_id=row.get("family_id"),
        country_code=row.get("country_code"),
        publication_date=parsed_date,
        title=texts("title"),
        abstract=texts("abstract"),
        assignees=tuple(
            x["name"] for x in (row.get("assignee_harmonized") or ()) if x.get("name")
        ),
        classifications=tuple(
            x["code"] for x in (row.get("cpc") or ()) if x.get("code")
        ),
        url=f"https://patents.google.com/patent/{number.replace('-', '')}",
        claims=texts("claims"),
        description=texts("description"),
    )


class GooglePatentsClient:
    """Read patents with application-default credentials or an injected client.

    Construction does not authenticate or access the network. Every operation
    requires a positive byte budget. SDK errors propagate unchanged.
    """

    def __init__(
        self, project: str | None = None, *, client: Any = None, timeout: float = 120
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.project = project
        self._client = client
        self.timeout = timeout

    def _run(
        self,
        sql: str,
        parameters: list[Any],
        query: dict[str, Any],
        *,
        maximum_bytes_billed: int,
        dry_run: bool,
    ) -> PatentResults | QueryEstimate:
        if type(maximum_bytes_billed) is not int or maximum_bytes_billed <= 0:
            raise ValueError("maximum_bytes_billed must be a positive integer")
        bq = _bigquery()
        if self._client is None:
            if not self.project:
                raise ValueError(
                    "Supply a Google Cloud project or an existing BigQuery client"
                )
            self._client = bq.Client(project=self.project)
        config = bq.QueryJobConfig(
            query_parameters=parameters,
            maximum_bytes_billed=maximum_bytes_billed,
            dry_run=dry_run,
            use_query_cache=not dry_run,
        )
        job = self._client.query(sql, job_config=config, timeout=self.timeout)
        if dry_run:
            return QueryEstimate(job.total_bytes_processed, maximum_bytes_billed)
        rows = job.result(timeout=self.timeout)
        return PatentResults(
            tuple(_record(row) for row in rows),
            query,
            datetime.now(UTC).isoformat(),
        )

    def search(
        self,
        terms: Sequence[str],
        *,
        maximum_bytes_billed: int,
        fields: Sequence[str] = TEXT_FIELDS,
        countries: Sequence[str] = (),
        limit: int = 20,
        dry_run: bool = False,
    ) -> PatentResults | QueryEstimate:
        """Match every literal term in any selected localized field.

        Case-insensitive substring matching, not website query syntax. Search
        returns metadata; get_publication retrieves available full text. LIMIT
        bounds returned records, not scan cost. Empty countries means all.
        """
        if (
            isinstance(terms, str)
            or not terms
            or any(not isinstance(t, str) or not t.strip() for t in terms)
        ):
            raise ValueError("terms must be a nonempty sequence of nonblank strings")
        if (
            isinstance(fields, str)
            or not fields
            or any(f not in TEXT_FIELDS for f in fields)
        ):
            raise ValueError(f"fields must be a nonempty subset of {TEXT_FIELDS}")
        if type(limit) is not int or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(countries, str) or any(
            not isinstance(c, str) or len(c) != 2 or not c.isascii() or not c.isalpha()
            for c in countries
        ):
            raise ValueError("countries must contain two-letter country codes")
        bq = _bigquery()
        terms = tuple(t.strip() for t in terms)
        fields = tuple(dict.fromkeys(fields))
        countries = tuple(c.upper() for c in countries)
        matches = " OR ".join(
            f"EXISTS (SELECT 1 FROM UNNEST(p.{f}_localized) AS txt "
            "WHERE STRPOS(LOWER(txt.text), LOWER(term)) > 0)"
            for f in fields
        )
        sql = f"""SELECT p.publication_number, p.family_id, p.country_code,
    p.publication_date, p.title_localized, p.abstract_localized,
    p.assignee_harmonized, p.cpc
FROM `{TABLE}` AS p
WHERE NOT EXISTS (SELECT 1 FROM UNNEST(@terms) AS term WHERE NOT ({matches}))
    AND (ARRAY_LENGTH(@countries) = 0 OR p.country_code IN UNNEST(@countries))
ORDER BY p.publication_date DESC, p.publication_number ASC
LIMIT @limit"""
        params = [
            bq.ArrayQueryParameter("terms", "STRING", terms),
            bq.ArrayQueryParameter("countries", "STRING", countries),
            bq.ScalarQueryParameter("limit", "INT64", limit),
        ]
        return self._run(
            sql,
            params,
            {
                "operation": "search",
                "terms": terms,
                "fields": fields,
                "countries": countries,
                "limit": limit,
            },
            maximum_bytes_billed=maximum_bytes_billed,
            dry_run=dry_run,
        )

    def get_publication(
        self,
        publication_number: str,
        *,
        maximum_bytes_billed: int,
        dry_run: bool = False,
    ) -> PatentResults | QueryEstimate:
        """Fetch available text using the exact hyphenated ID returned by search.

        Unknown publications return an empty records tuple. Full text coverage
        varies by jurisdiction and publication; no text is fabricated.
        """
        if not isinstance(publication_number, str) or not publication_number.strip():
            raise ValueError("publication_number must be a nonblank string")
        number = publication_number.strip()
        bq = _bigquery()
        sql = f"""SELECT publication_number, family_id, country_code, publication_date,
    title_localized, abstract_localized, assignee_harmonized, cpc,
    claims_localized, description_localized
FROM `{TABLE}` WHERE publication_number = @publication_number
LIMIT 1"""
        return self._run(
            sql,
            [bq.ScalarQueryParameter("publication_number", "STRING", number)],
            {"operation": "get_publication", "publication_number": number},
            maximum_bytes_billed=maximum_bytes_billed,
            dry_run=dry_run,
        )
