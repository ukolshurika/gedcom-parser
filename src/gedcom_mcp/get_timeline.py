#!/usr/bin/env python3

import argparse
import logging
import sys
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime
import json
import json
import traceback
import os

from pydantic import BaseModel, Field
from functools import total_ordering
from dataclasses import dataclass, field
import time
import re
from typing import Optional, Tuple, Dict, Any

try:
    from .gedcom_date_utils import parse_genealogy_date, validate_date_consistency, get_date_certainty_level, GenealogyDate
    DATE_UTILS_AVAILABLE = True
except ImportError:
    DATE_UTILS_AVAILABLE = False
    print("Warning: gedcom_date_utils not found. Date parsing enhancements will not be available.")

# Import our new genealogy name utilities
try:
    from .gedcom_name_utils import parse_genealogy_name, normalize_name, find_name_variants, GenealogyName
    NAME_UTILS_AVAILABLE = True
except ImportError:
    NAME_UTILS_AVAILABLE = False
    print("Warning: gedcom_name_utils not found. Name parsing enhancements will not be available.")

# Import our new genealogy place utilities
try:
    from .gedcom_place_utils import normalize_place_name, extract_geographic_hierarchy, NormalizedPlace
    PLACE_UTILS_AVAILABLE = True
except ImportError:
    PLACE_UTILS_AVAILABLE = False
    print("Warning: gedcom_place_utils not found. Place normalization enhancements will not be available.")

# Try to import GEDCOM parser
try:
    from gedcom.parser import Parser
    from gedcom.element.individual import IndividualElement
    from gedcom.element.family import FamilyElement
    from gedcom.element.object import ObjectElement
except ImportError:
    print("Error: python-gedcom library not found. Please install it with: pip install python-gedcom")
    sys.exit(1)
# Import our modularized components
from .gedcom_context import GedcomContext, get_gedcom_context, _rebuild_lookups
from .gedcom_models import PersonDetails, PersonRelationships, NodePriority
from .gedcom_data_access import (
    get_person_record, find_person_by_name, _get_relationships_internal,
    _get_events_internal, decode_event_details, _get_places_internal, _get_notes_internal, _get_sources_internal,
    search_gedcom, _extract_person_details, _get_person_relationships_internal, load_gedcom_file, save_gedcom_file, _get_person_attributes_internal,
    fuzzy_search_records
)
from .gedcom_data_management import (
    _add_person_internal, _create_marriage_internal, _add_child_to_family_internal,
    _remove_child_from_family_internal, _remove_parent_from_family_internal,
    _remove_parents_internal, _update_event_details_internal,
    _remove_event_internal, _add_note_to_entity_internal,
    _create_source_internal, _delete_note_entity_internal, _new_empty_gedcom_internal,
    _update_person_attribute_internal, _update_person_details_internal,
    batch_update_person_attributes
)
from .gedcom_search import (
    _dijkstra_bidirectional_search, _get_person_neighbors_lazy, _get_person_neighbors_lazy_reverse,
    _generate_relationship_chain_lazy, _correct_relationship_direction, _generate_relationship_description,
    _format_relationship_with_gender, _format_relationship_description,
    find_shortest_relationship_path as compute_shortest_relationship_path, _find_all_relationship_paths_internal, _find_all_paths_to_ancestor_internal
)
from .gedcom_utils import (
    normalize_string, _get_gedcom_tag_from_event_type, _get_gedcom_tag_from_attribute_type,
    extract_birth_year, _extract_year_from_genealogy_date, _normalize_genealogy_name,
    _normalize_genealogy_date, _normalize_genealogy_place, _extract_year_from_date,
    _matches_criteria
)
from .gedcom_analysis import (
    _get_attribute_statistics_internal, get_statistics_report, _get_timeline_internal, _get_ancestors_internal, _get_descendants_internal,
    _get_family_tree_summary_internal, _get_surname_statistics_internal, _get_date_range_analysis_internal,
    _find_potential_duplicates_internal, get_common_ancestors
)


def get_timeline(person_id: str, gedcom_ctx: GedcomContext) -> str:
    """Generate a chronological timeline of events for a person"""
    if not gedcom_ctx.gedcom_parser:
        return "No GEDCOM file loaded. Please load a GEDCOM file first."

    timeline = _get_timeline_internal(person_id, gedcom_ctx)
    if timeline:
        return str(timeline)
    else:
        return f"No timeline found for person: {person_id}"


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Generate timeline for a person from a GEDCOM file')
    parser.add_argument('gedcom_file', help='Path to the GEDCOM file')
    parser.add_argument('--person-id', '-p', help='Person ID to generate timeline for')
    parser.add_argument('--search-name', '-n', help='Search for person by name')

    args = parser.parse_args()

    # Load the GEDCOM file
    gedcom_ctx = GedcomContext()
    gedcom_ctx.file_path = args.gedcom_file

    try:
        load_gedcom_file(args.gedcom_file, gedcom_ctx)
        print(f"Loaded GEDCOM file: {args.gedcom_file}")

        # Find person
        person_id = args.person_id
        if not person_id and args.search_name:
            results = find_person_by_name(args.search_name, gedcom_ctx)
            if results:
                print(f"\nFound {len(results)} matching people:")
                for i, person in enumerate(results[:10], 1):
                    print(f"{i}. {person}")
                if len(results) == 1:
                    # Extract ID from the first result (PersonDetails object)
                    person_id = results[0].id
                else:
                    print("\nMultiple matches found. Please specify --person-id")
                    return
            else:
                print(f"No person found with name: {args.search_name}")
                return

        if not person_id:
            print("Error: Please specify either --person-id or --search-name")
            return

        # Generate and print timeline
        timeline_result = get_timeline(person_id, gedcom_ctx)
        print(f"\n{timeline_result}")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    main()