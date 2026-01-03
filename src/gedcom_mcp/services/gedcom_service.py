"""
GEDCOM service for managing genealogy data.

Provides high-level operations for loading and querying GEDCOM files
with caching support.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import HTTPException, status

from ..parser.gedcom_context import GedcomContext
from ..parser.gedcom_data_access import get_person_record, load_gedcom_file
from ..parser.gedcom_analysis import _get_timeline_internal
from ..parser.gedcom_models import PersonDetails
from .file_cache import FileCache, get_file_cache

logger = logging.getLogger(__name__)


class GedcomService:
    """
    Service for GEDCOM file operations.

    Manages loading, caching, and querying GEDCOM files.
    Each loaded file is cached in memory to avoid repeated parsing.
    """

    def __init__(self, file_cache: FileCache) -> None:
        """
        Initialize the GEDCOM service.

        Args:
            file_cache: FileCache instance for file retrieval
        """
        self.file_cache = file_cache
        self._contexts: Dict[str, GedcomContext] = {}

    def get_or_load_context(self, file_path: str) -> GedcomContext:
        """
        Get or load a GEDCOM file context.

        If the file has been loaded before, returns the cached context.
        Otherwise, loads the file and caches the context.

        Args:
            file_path: Path to GEDCOM file (local or S3)

        Returns:
            GedcomContext instance

        Raises:
            HTTPException: If file cannot be loaded (404 or 500)
        """
        # Get the file from cache or download
        local_path = self.file_cache.get_file(file_path)
        if not local_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GEDCOM file not found: {file_path}"
            )

        local_path_str = str(local_path)

        # Check if we already have this context loaded
        if local_path_str in self._contexts:
            return self._contexts[local_path_str]

        # Load the GEDCOM file
        try:
            gedcom_ctx = GedcomContext()
            gedcom_ctx.file_path = local_path_str
            load_gedcom_file(local_path_str, gedcom_ctx)

            # Cache the context
            self._contexts[local_path_str] = gedcom_ctx
            logger.info(f"Loaded GEDCOM file: {local_path_str}")

            return gedcom_ctx
        except Exception as e:
            logger.error(f"Failed to load GEDCOM file {local_path_str}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load GEDCOM file: {str(e)}"
            )

    def get_all_person_ids(self, file_path: str) -> List[str]:
        """
        Get all person IDs from a GEDCOM file.

        Args:
            file_path: Path to GEDCOM file

        Returns:
            List of person IDs
        """
        context = self.get_or_load_context(file_path)
        person_ids = list(context.individual_lookup.keys())
        logger.info(f"Found {len(person_ids)} persons in GEDCOM file")
        return person_ids

    def get_person_details(self, person_id: str, file_path: str) -> PersonDetails:
        """
        Get detailed information about a specific person.

        Args:
            person_id: Person ID (e.g., @I1@)
            file_path: Path to GEDCOM file

        Returns:
            PersonDetails object

        Raises:
            HTTPException: If person not found (404)
        """
        context = self.get_or_load_context(file_path)
        person = get_person_record(person_id, context)

        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Person not found: {person_id}"
            )

        return person

    def get_person_timeline(
        self,
        person_id: str,
        file_path: str
    ) -> List[Dict]:
        """
        Generate a chronological timeline of events for a person.

        Args:
            person_id: Person ID (e.g., @I1@)
            file_path: Path to GEDCOM file

        Returns:
            List of timeline events
        """
        context = self.get_or_load_context(file_path)
        timeline = _get_timeline_internal(person_id, context)
        return timeline or []

    def clear_context(self, file_path: str) -> bool:
        """
        Clear a cached GEDCOM context.

        Args:
            file_path: Path to the GEDCOM file

        Returns:
            True if context was cleared, False if not found
        """
        local_path = self.file_cache.get_file(file_path)
        if local_path and str(local_path) in self._contexts:
            del self._contexts[str(local_path)]
            return True
        return False

    def clear_all_contexts(self) -> int:
        """
        Clear all cached GEDCOM contexts.

        Returns:
            Number of contexts cleared
        """
        count = len(self._contexts)
        self._contexts.clear()
        return count


def get_gedcom_service() -> GedcomService:
    """
    Get GedcomService instance with dependencies.

    Returns:
        GedcomService instance
    """
    return GedcomService(file_cache=get_file_cache())
