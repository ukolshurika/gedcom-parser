#!/usr/bin/env python3

"""
Celery configuration and background tasks for GEDCOM file processing.
"""

import os
import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from celery import Celery
import httpx
import boto3
from botocore.exceptions import ClientError

from .gedcom_context import GedcomContext
from .gedcom_data_access import load_gedcom_file
from .signature_utils import generate_signature


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery(
    "gedcom_processor",
    broker=redis_url,
    backend=redis_url
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# S3 Configuration
S3_BUCKET = os.getenv("GEDCOM_S3_BUCKET", "")
S3_REGION = os.getenv("GEDCOM_S3_REGION", "us-east-1")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")


def download_file_from_s3(s3_path: str, local_path: Path) -> bool:
    """
    Download a file from S3 to local filesystem.

    Args:
        s3_path: S3 path (can be s3://bucket/key or just key)
        local_path: Local path to save the file

    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client = boto3.client('s3', region_name=S3_REGION)

        # Remove s3:// prefix if present and extract key
        s3_key = s3_path.replace("s3://", "").replace(f"{S3_BUCKET}/", "")

        logger.info(f"Downloading from S3: s3://{S3_BUCKET}/{s3_key} to {local_path}")
        s3_client.download_file(S3_BUCKET, s3_key, str(local_path))
        logger.info(f"Successfully downloaded file")
        return True
    except ClientError as e:
        logger.error(f"Failed to download from S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading from S3: {e}")
        return False


def parse_gedcom_file(file_path: str) -> Dict[str, Any]:
    """
    Parse GEDCOM file and extract persons and events.

    Args:
        file_path: Path to GEDCOM file

    Returns:
        Dictionary with persons and events data
    """
    try:
        gedcom_ctx = GedcomContext()
        gedcom_ctx.file_path = file_path
        load_gedcom_file(file_path, gedcom_ctx)

        # Extract persons
        persons = []
        for person_id, individual in gedcom_ctx.individual_lookup.items():
            person_data = {
                "id": person_id,
                "name": "",
                "birth_date": None,
                "birth_place": None,
                "death_date": None,
                "death_place": None,
                "gender": None,
            }

            # Get name
            names = individual.get_name()
            if names:
                person_data["name"] = " ".join(names)

            # Get gender
            gender = individual.get_gender()
            if gender:
                person_data["gender"] = gender

            # Get birth info
            birth = individual.get_birth_data()
            if birth:
                person_data["birth_date"] = birth.get("date")
                person_data["birth_place"] = birth.get("place")

            # Get death info
            death = individual.get_death_data()
            if death:
                person_data["death_date"] = death.get("date")
                person_data["death_place"] = death.get("place")

            persons.append(person_data)

        # Extract events
        events = []
        for person_id, individual in gedcom_ctx.individual_lookup.items():
            # Get all individual events
            for element in individual.get_child_elements():
                tag = element.get_tag()
                if tag in ['BIRT', 'DEAT', 'MARR', 'DIV', 'BAPM', 'BURI', 'CHR', 'CONF', 'CREM', 'NATU', 'EMIG', 'IMMI', 'CENS', 'PROB', 'WILL', 'GRAD', 'RETI', 'EVEN']:
                    event_data = {
                        "person_id": person_id,
                        "type": tag,
                        "date": None,
                        "place": None,
                        "description": None,
                    }

                    # Extract event details
                    for child in element.get_child_elements():
                        child_tag = child.get_tag()
                        if child_tag == "DATE":
                            event_data["date"] = child.get_value()
                        elif child_tag == "PLAC":
                            event_data["place"] = child.get_value()
                        elif child_tag == "TYPE":
                            event_data["description"] = child.get_value()

                    events.append(event_data)

        return {
            "persons": persons,
            "events": events
        }
    except Exception as e:
        logger.error(f"Failed to parse GEDCOM file {file_path}: {e}")
        raise


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def process_gedcom_file(self, s3_file_path: str, user_id: str):
    """
    Background task to process GEDCOM file and send webhook.

    Args:
        s3_file_path: Path to file in S3
        user_id: User ID to include in the webhook payload

    Returns:
        Status message
    """
    temp_file = None

    try:
        # Step 1: Download file from S3
        logger.info(f"Processing GEDCOM file: {s3_file_path} for user {user_id}")

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.ged', delete=False) as tf:
            temp_file = Path(tf.name)

        # Download from S3
        if not download_file_from_s3(s3_file_path, temp_file):
            raise Exception(f"Failed to download file from S3: {s3_file_path}")

        # Step 2: Parse GEDCOM file
        logger.info(f"Parsing GEDCOM file: {temp_file}")
        data = parse_gedcom_file(str(temp_file))

        # Step 3: Add user_id to data
        data["user_id"] = user_id

        # Step 4: Generate signature
        signature = generate_signature(data)
        logger.info(f"Generated signature for webhook payload")

        # Step 5: Send webhook request
        webhook_url = WEBHOOK_URL
        if not webhook_url:
            raise Exception("WEBHOOK_URL environment variable is not set")

        logger.info(f"Sending webhook to {webhook_url}")

        headers = {
            "X-Signature": signature,
            "Content-Type": "application/json"
        }

        # Send request with httpx
        with httpx.Client(timeout=30.0) as client:
            response = client.post(webhook_url, json=data, headers=headers)

            # Check status code
            if response.status_code not in [200, 201]:
                logger.error(
                    f"Webhook returned status {response.status_code}: {response.text}"
                )
                # Retry the task
                raise self.retry(
                    exc=Exception(f"Webhook returned status {response.status_code}"),
                    countdown=60 * (self.request.retries + 1)  # Exponential backoff
                )

        logger.info(f"Successfully sent webhook for {s3_file_path}")
        return {
            "status": "success",
            "message": "File processed and webhook sent",
            "persons_count": len(data["persons"]),
            "events_count": len(data["events"])
        }

    except Exception as e:
        logger.error(f"Error processing file {s3_file_path}: {e}")

        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        else:
            logger.error(f"Max retries exceeded for {s3_file_path}")
            raise

    finally:
        # Step 6: Clean up temporary file
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
                logger.info(f"Deleted temporary file: {temp_file}")
            except Exception as e:
                logger.error(f"Failed to delete temporary file {temp_file}: {e}")
