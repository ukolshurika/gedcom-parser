"""
GEDCOM Parser - A library for parsing and querying GEDCOM genealogy files.

This subpackage provides core GEDCOM parsing functionality that can be used
independently of the FastAPI server.

Main components:
- GedcomContext: Context manager for GEDCOM data and caches
- PersonDetails: Model for person information
- Data access functions: load_gedcom_file, get_person_record, etc.
- Analysis functions: get_statistics_report, find_shortest_relationship_path, etc.
- Utility functions: date parsing, name parsing, place normalization
"""

from __future__ import annotations

# Core context and models
from .gedcom_context import (
    GedcomContext,
    get_gedcom_context,
    CACHE_SIZES,
)

from .gedcom_models import (
    PersonDetails,
    PersonRelationships,
    NodePriority,
    LoadGedcomParams,
    GetPersonParams,
    FindPersonParams,
    GetRelationshipsParams,
    GetEventsParams,
    GetPlacesParams,
    GetTimelineParams,
    SearchParams,
    GetNotesParams,
    GetSourcesParams,
    GetStatisticsParams,
    GetCommonAncestorsParams,
)

# Constants
from .gedcom_constants import (
    EVENT_TYPES,
    ATTRIBUTE_TYPES,
)

# Data access functions
from .gedcom_data_access import (
    load_gedcom_file,
    save_gedcom_file,
    get_person_record,
    find_person_by_name,
    search_gedcom,
    fuzzy_search_records,
    decode_event_details,
)

# Data management functions
from .gedcom_data_management import (
    batch_update_person_attributes,
)

# Search functions
from .gedcom_search import (
    find_shortest_relationship_path,
)

# Analysis functions
from .gedcom_analysis import (
    get_statistics_report,
    get_living_status,
    get_common_ancestors,
)

# Utility functions
from .gedcom_utils import (
    normalize_string,
    extract_birth_year,
)

# Date utilities
from .gedcom_date_utils import (
    GenealogyDate,
    DateCertainty,
    parse_genealogy_date,
    validate_date_consistency,
    get_date_certainty_level,
)

# Name utilities
from .gedcom_name_utils import (
    GenealogyName,
    parse_genealogy_name,
    normalize_name,
    find_name_variants,
    format_gedcom_name,
    format_gedcom_name_from_string,
)

# Place utilities
from .gedcom_place_utils import (
    NormalizedPlace,
    normalize_place_name,
    extract_geographic_hierarchy,
)

__all__ = [
    # Context
    "GedcomContext",
    "get_gedcom_context",
    "CACHE_SIZES",
    # Models
    "PersonDetails",
    "PersonRelationships",
    "NodePriority",
    "LoadGedcomParams",
    "GetPersonParams",
    "FindPersonParams",
    "GetRelationshipsParams",
    "GetEventsParams",
    "GetPlacesParams",
    "GetTimelineParams",
    "SearchParams",
    "GetNotesParams",
    "GetSourcesParams",
    "GetStatisticsParams",
    "GetCommonAncestorsParams",
    # Constants
    "EVENT_TYPES",
    "ATTRIBUTE_TYPES",
    # Data access
    "load_gedcom_file",
    "save_gedcom_file",
    "get_person_record",
    "find_person_by_name",
    "search_gedcom",
    "fuzzy_search_records",
    "decode_event_details",
    # Data management
    "batch_update_person_attributes",
    # Search
    "find_shortest_relationship_path",
    # Analysis
    "get_statistics_report",
    "get_living_status",
    "get_common_ancestors",
    # Utilities
    "normalize_string",
    "extract_birth_year",
    # Date utilities
    "GenealogyDate",
    "DateCertainty",
    "parse_genealogy_date",
    "validate_date_consistency",
    "get_date_certainty_level",
    # Name utilities
    "GenealogyName",
    "parse_genealogy_name",
    "normalize_name",
    "find_name_variants",
    "format_gedcom_name",
    "format_gedcom_name_from_string",
    # Place utilities
    "NormalizedPlace",
    "normalize_place_name",
    "extract_geographic_hierarchy",
]
