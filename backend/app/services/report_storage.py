"""Local and private S3 storage for medical reports."""

from __future__ import annotations

from functools import lru_cache
import logging
from pathlib import Path

from app.core.config import get_settings
from app.services.exceptions import ResourceNotFoundError, StorageUnavailableError, ValidationError

logger = logging.getLogger(__name__)
STAGING_PREFIX = "pending-reports/"
REPORT_PREFIX = "reports/"
POST_TTL_SECONDS = 600


class LocalReportStorage:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path(self, name: str) -> Path:
        if Path(name).name != name or "/" in name or "\\" in name or name in {"", ".", ".."}:
            raise StorageUnavailableError("Invalid stored report name.")
        return self.directory / name

    def put(self, name: str, content: bytes, content_type: str) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self.path(name).write_bytes(content)
        except OSError as exc:
            raise StorageUnavailableError("Could not store the report.") from exc

    def delete(self, name: str) -> None:
        try:
            self.path(name).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageUnavailableError("Could not remove the stored report.") from exc

    def download(self, name: str, extension: str) -> Path:
        path = self.path(name)
        if not path.is_file():
            raise ResourceNotFoundError("Stored report not found.")
        return path


class S3ReportStorage:
    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        settings = get_settings()
        self.bucket = settings.storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint or None,
            region_name=settings.storage_region,
            aws_access_key_id=settings.storage_access_key_id,
            aws_secret_access_key=settings.storage_secret_access_key,
            config=Config(signature_version="s3v4", connect_timeout=5, read_timeout=20,
                          retries={"mode": "standard", "total_max_attempts": 2}),
        )

    def _call(self, operation: str, **kwargs):
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            return getattr(self.client, operation)(**kwargs)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if operation == "get_object" and code in {"404", "NoSuchKey", "NotFound"}:
                raise ResourceNotFoundError("Uploaded file not found.") from exc
            logger.warning("Report storage operation %s failed (%s)", operation, type(exc).__name__)
            raise StorageUnavailableError("Report storage temporarily unavailable.") from exc
        except BotoCoreError as exc:
            logger.warning("Report storage operation %s failed (%s)", operation, type(exc).__name__)
            raise StorageUnavailableError("Report storage temporarily unavailable.") from exc

    def authorize_upload(self, name: str, content_type: str, size: int) -> dict:
        return self._call(
            "generate_presigned_post",
            Bucket=self.bucket,
            Key=STAGING_PREFIX + name,
            Fields={"Content-Type": content_type},
            Conditions=[{"Content-Type": content_type}, ["content-length-range", size, size]],
            ExpiresIn=POST_TTL_SECONDS,
        )

    def read_upload(self, name: str, content_type: str, size: int) -> bytes:
        from botocore.exceptions import BotoCoreError

        result = self._call("get_object", Bucket=self.bucket, Key=STAGING_PREFIX + name)
        body = result["Body"]
        try:
            if result["ContentLength"] != size or result.get("ContentType") != content_type:
                raise ValidationError("The uploaded file did not match the upload request.")
            content = body.read(size + 1)
            if len(content) != size:
                raise ValidationError("The uploaded file did not match the upload request.")
            return content
        except BotoCoreError as exc:
            raise StorageUnavailableError("Could not read the uploaded report.") from exc
        finally:
            body.close()

    def put(self, name: str, content: bytes, content_type: str) -> None:
        self._call("put_object", Bucket=self.bucket, Key=REPORT_PREFIX + name,
                   Body=content, ContentType=content_type)

    def delete(self, name: str) -> None:
        self._call("delete_object", Bucket=self.bucket, Key=REPORT_PREFIX + name)

    def delete_upload(self, name: str) -> None:
        self._call("delete_object", Bucket=self.bucket, Key=STAGING_PREFIX + name)

    def download(self, name: str, extension: str) -> str:
        return self._call(
            "generate_presigned_url",
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket,
                "Key": REPORT_PREFIX + name,
                "ResponseContentDisposition": f'attachment; filename="report.{extension.lower()}"',
                "ResponseContentType": "application/octet-stream",
                "ResponseCacheControl": "private, no-store",
            },
            ExpiresIn=60,
        )


@lru_cache
def get_s3_report_storage() -> S3ReportStorage:
    return S3ReportStorage()
