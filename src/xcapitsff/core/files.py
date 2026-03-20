"""File/document management system — in-memory storage.

Provides upload, download, listing, search, and entity attachment for files
associated with tenants.  Storage is entirely in-memory (dict-backed).
"""

import hashlib
import mimetypes
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class EntityType(str, Enum):
    LEAD = "lead"
    TICKET = "ticket"
    CUSTOMER = "customer"
    NONE = "none"


class TenantPlan(str, Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


# Max file size per plan (bytes)
MAX_FILE_SIZE: dict[TenantPlan, int] = {
    TenantPlan.FREE: 5 * 1024 * 1024,         # 5 MB
    TenantPlan.PRO: 25 * 1024 * 1024,          # 25 MB
    TenantPlan.ENTERPRISE: 100 * 1024 * 1024,  # 100 MB
}

ALLOWED_EXTENSIONS: set[str] = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".csv", ".txt", ".png", ".jpg", ".jpeg",
    ".gif", ".zip",
}


@dataclass
class FileMetadata:
    id: str
    tenant_id: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    uploaded_at: datetime
    entity_type: EntityType
    entity_id: str | None
    tags: list[str]
    description: str | None
    checksum: str  # sha256
    storage_path: str


class FileManager:
    """In-memory file manager with per-tenant isolation."""

    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    MAX_FILE_SIZE = MAX_FILE_SIZE

    def __init__(self) -> None:
        self._metadata: dict[str, FileMetadata] = {}
        self._content: dict[str, bytes] = {}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_upload(
        filename: str,
        size: int,
        tenant_plan: TenantPlan | str = TenantPlan.FREE,
    ) -> tuple[bool, str | None]:
        """Validate a file before upload.  Returns (valid, error_message)."""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Extension '{ext}' is not allowed"

        if isinstance(tenant_plan, str):
            try:
                tenant_plan = TenantPlan(tenant_plan)
            except ValueError:
                tenant_plan = TenantPlan.FREE

        max_size = MAX_FILE_SIZE[tenant_plan]
        if size > max_size:
            max_mb = max_size / (1024 * 1024)
            return False, f"File size {size} bytes exceeds {max_mb:.0f} MB limit for {tenant_plan.value} plan"

        return True, None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def upload(
        self,
        tenant_id: str,
        filename: str,
        content: bytes,
        uploaded_by: str,
        content_type: str | None = None,
        entity_type: EntityType | str | None = None,
        entity_id: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> FileMetadata:
        """Upload a file and return its metadata."""
        # Auto-detect content type from extension if not provided
        if content_type is None:
            guessed, _ = mimetypes.guess_type(filename)
            content_type = guessed or "application/octet-stream"

        # Resolve entity_type
        if entity_type is None:
            resolved_entity_type = EntityType.NONE
        elif isinstance(entity_type, str):
            try:
                resolved_entity_type = EntityType(entity_type)
            except ValueError:
                resolved_entity_type = EntityType.NONE
        else:
            resolved_entity_type = entity_type

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Generate unique ID and storage path
        file_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        storage_path = f"{tenant_id}/{now.year}/{now.month:02d}/{file_id}_{filename}"

        meta = FileMetadata(
            id=file_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            uploaded_by=uploaded_by,
            uploaded_at=now,
            entity_type=resolved_entity_type,
            entity_id=entity_id,
            tags=list(tags) if tags else [],
            description=description,
            checksum=checksum,
            storage_path=storage_path,
        )

        self._metadata[file_id] = meta
        self._content[file_id] = content
        return meta

    def download(self, file_id: str) -> tuple[FileMetadata, bytes] | None:
        """Download a file.  Returns (metadata, content) or None."""
        meta = self._metadata.get(file_id)
        if meta is None:
            return None
        return meta, self._content[file_id]

    def delete(self, file_id: str) -> bool:
        """Delete a file.  Returns True if it existed."""
        if file_id not in self._metadata:
            return False
        del self._metadata[file_id]
        del self._content[file_id]
        return True

    def get_metadata(self, file_id: str) -> FileMetadata | None:
        """Get file metadata without content."""
        return self._metadata.get(file_id)

    # ------------------------------------------------------------------
    # Listing & search
    # ------------------------------------------------------------------

    def list_files(
        self,
        tenant_id: str,
        entity_type: EntityType | str | None = None,
        entity_id: str | None = None,
    ) -> list[FileMetadata]:
        """List files for a tenant, optionally filtered by entity."""
        results: list[FileMetadata] = []
        for meta in self._metadata.values():
            if meta.tenant_id != tenant_id:
                continue
            if entity_type is not None:
                et = entity_type if isinstance(entity_type, EntityType) else EntityType(entity_type)
                if meta.entity_type != et:
                    continue
            if entity_id is not None and meta.entity_id != entity_id:
                continue
            results.append(meta)
        return results

    def search_files(self, tenant_id: str, query: str) -> list[FileMetadata]:
        """Search files by filename, description, and tags."""
        if not query or not query.strip():
            return []
        q = query.lower().strip()
        results: list[FileMetadata] = []
        for meta in self._metadata.values():
            if meta.tenant_id != tenant_id:
                continue
            # Match against filename
            if q in meta.filename.lower():
                results.append(meta)
                continue
            # Match against description
            if meta.description and q in meta.description.lower():
                results.append(meta)
                continue
            # Match against tags
            if any(q in tag.lower() for tag in meta.tags):
                results.append(meta)
                continue
        return results

    # ------------------------------------------------------------------
    # Entity attachment
    # ------------------------------------------------------------------

    def attach_to_entity(
        self, file_id: str, entity_type: EntityType | str, entity_id: str,
    ) -> FileMetadata | None:
        """Attach a file to an entity.  Returns updated metadata or None."""
        meta = self._metadata.get(file_id)
        if meta is None:
            return None
        et = entity_type if isinstance(entity_type, EntityType) else EntityType(entity_type)
        meta.entity_type = et
        meta.entity_id = entity_id
        return meta

    def detach_from_entity(self, file_id: str) -> FileMetadata | None:
        """Detach a file from its entity.  Returns updated metadata or None."""
        meta = self._metadata.get(file_id)
        if meta is None:
            return None
        meta.entity_type = EntityType.NONE
        meta.entity_id = None
        return meta

    # ------------------------------------------------------------------
    # Usage stats
    # ------------------------------------------------------------------

    def get_storage_usage(self, tenant_id: str) -> dict:
        """Return storage usage stats for a tenant."""
        total_files = 0
        total_bytes = 0
        by_type: dict[str, int] = {}
        for meta in self._metadata.values():
            if meta.tenant_id != tenant_id:
                continue
            total_files += 1
            total_bytes += meta.size_bytes
            by_type[meta.content_type] = by_type.get(meta.content_type, 0) + 1
        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "by_type": by_type,
        }


# Module-level default instance
file_manager = FileManager()
