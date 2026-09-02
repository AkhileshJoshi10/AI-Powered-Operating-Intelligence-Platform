from __future__ import annotations

from dataclasses import dataclass
import json
import re
import socket
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)




class _NoRedirectHandler(HTTPRedirectHandler):
    """Prevent redirects from forwarding automation credentials."""

    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        del req
        del fp
        del code
        del msg
        del headers
        del newurl
        return None


class N8NClientConfigurationError(RuntimeError):
    """Raised when the n8n client is not safely configured."""


class N8NClientError(RuntimeError):
    """Safe outbound n8n delivery failure."""

    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        attempts: int,
        http_status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.attempts = attempts
        self.http_status_code = http_status_code


@dataclass(frozen=True)
class N8NWebhookResult:
    """Minimal safe metadata returned from one n8n webhook request."""

    http_status_code: int
    attempt_count: int
    n8n_execution_id: str | None = None


class N8NClient:
    """Small HTTP boundary for fixed, authenticated n8n webhooks."""

    def __init__(
        self,
        *,
        base_url: str,
        auth_token: str,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
    ) -> None:
        self.base_url = base_url.strip()
        self.auth_token = auth_token.strip()
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = int(max_retries)
        self.retry_backoff_seconds = float(
            retry_backoff_seconds
        )
        self._opener = build_opener(
            _NoRedirectHandler()
        )

        self._validate_configuration()

    def _validate_configuration(self) -> None:
        parsed = urlparse(self.base_url)

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise N8NClientConfigurationError(
                "N8N_WEBHOOK_BASE_URL must be a valid http(s) URL "
                "without embedded credentials."
            )

        if not self.auth_token:
            raise N8NClientConfigurationError(
                "N8N_OUTBOUND_AUTH_TOKEN must be configured."
            )

        if self.timeout_seconds <= 0:
            raise N8NClientConfigurationError(
                "N8N_TIMEOUT_SECONDS must be greater than zero."
            )

        if self.max_retries < 0:
            raise N8NClientConfigurationError(
                "N8N_MAX_RETRIES cannot be negative."
            )

        if self.retry_backoff_seconds < 0:
            raise N8NClientConfigurationError(
                "N8N_RETRY_BACKOFF_SECONDS cannot be negative."
            )

    def _build_url(
        self,
        webhook_path: str,
    ) -> str:
        normalized = webhook_path.strip().lstrip("/")
        parsed_path = urlparse(normalized)

        if (
            not normalized
            or parsed_path.scheme
            or parsed_path.netloc
            or parsed_path.query
            or parsed_path.fragment
            or ".." in normalized.split("/")
            or "//" in normalized
            or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9/_-]{0,199}",
                normalized,
            )
            is None
        ):
            raise N8NClientConfigurationError(
                "n8n webhook paths must be fixed relative paths."
            )

        base = self.base_url.rstrip("/") + "/"
        return urljoin(base, normalized)

    @staticmethod
    def _extract_execution_id(
        response_body: bytes,
    ) -> str | None:
        if not response_body:
            return None

        try:
            decoded = json.loads(
                response_body.decode(
                    "utf-8"
                )
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return None

        if not isinstance(
            decoded,
            dict,
        ):
            return None

        for key in (
            "executionId",
            "execution_id",
            "id",
        ):
            value = decoded.get(
                key
            )

            if value is not None:
                normalized = str(
                    value
                ).strip()

                if normalized:
                    return normalized[
                        :200
                    ]

        return None

    def post_webhook(
        self,
        *,
        webhook_path: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> N8NWebhookResult:
        """POST one bounded JSON payload to a configured n8n webhook."""

        url = self._build_url(
            webhook_path
        )

        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        maximum_attempts = (
            self.max_retries + 1
        )

        for attempt in range(
            1,
            maximum_attempts + 1,
        ):
            request = Request(
                url=url,
                data=body,
                method="POST",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": (
                        f"Bearer {self.auth_token}"
                    ),
                    "X-Idempotency-Key": (
                        idempotency_key
                    ),
                    "User-Agent": (
                        "AI-Operating-Intelligence/automation"
                    ),
                },
            )

            try:
                with self._opener.open(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    status_code = int(
                        response.status
                    )
                    response_body = response.read(
                        65536
                    )

                return N8NWebhookResult(
                    http_status_code=status_code,
                    attempt_count=attempt,
                    n8n_execution_id=(
                        self._extract_execution_id(
                            response_body
                        )
                    ),
                )

            except HTTPError as error:
                status_code = int(
                    error.code
                )
                retryable = (
                    status_code == 429
                    or status_code >= 500
                )

                if (
                    retryable
                    and attempt < maximum_attempts
                ):
                    self._sleep_before_retry(
                        attempt
                    )
                    continue

                raise N8NClientError(
                    "The n8n webhook returned an unsuccessful HTTP "
                    "status.",
                    error_type="N8NHTTPError",
                    attempts=attempt,
                    http_status_code=status_code,
                ) from error

            except (
                URLError,
                TimeoutError,
                socket.timeout,
            ) as error:
                if attempt < maximum_attempts:
                    self._sleep_before_retry(
                        attempt
                    )
                    continue

                raise N8NClientError(
                    "The n8n webhook could not be reached.",
                    error_type="N8NConnectionError",
                    attempts=attempt,
                ) from error

        raise N8NClientError(
            "The n8n webhook request failed.",
            error_type="N8NClientError",
            attempts=maximum_attempts,
        )

    def _sleep_before_retry(
        self,
        attempt: int,
    ) -> None:
        delay = (
            self.retry_backoff_seconds
            * attempt
        )

        if delay > 0:
            time.sleep(
                delay
            )
