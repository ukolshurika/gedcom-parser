#!/usr/bin/env python3

"""
Tests for the FastAPI GEDCOM server.

These tests cover:
- Timeline endpoint
- Persons list endpoint
- Person details endpoint
- File caching functionality
- S3 integration (mocked)
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from src.gedcom_mcp.fastapi_server import app, FileCache, config, _gedcom_contexts


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def sample_gedcom_file(tmp_path):
    """Create a sample GEDCOM file for testing"""
    gedcom_content = """0 HEAD
1 SOUR Test
1 GEDC
2 VERS 5.5.1
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Doe/
2 GIVN John
2 SURN Doe
1 SEX M
1 BIRT
2 DATE 1 JAN 1950
2 PLAC New York, USA
1 DEAT
2 DATE 1 JAN 2020
2 PLAC Los Angeles, USA
1 OCCU Engineer
1 FAMS @F1@
0 @I2@ INDI
1 NAME Jane /Smith/
2 GIVN Jane
2 SURN Smith
1 SEX F
1 BIRT
2 DATE 15 MAR 1955
2 PLAC Boston, USA
1 FAMS @F1@
0 @I3@ INDI
1 NAME Bob /Doe/
2 GIVN Bob
2 SURN Doe
1 SEX M
1 BIRT
2 DATE 10 JUL 1980
2 PLAC Chicago, USA
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 MARR
2 DATE 1 JUN 1975
2 PLAC Las Vegas, USA
0 TRLR
"""
    gedcom_file = tmp_path / "test.ged"
    gedcom_file.write_text(gedcom_content)
    return str(gedcom_file)


@pytest.fixture(autouse=True)
def clear_gedcom_contexts():
    """Clear GEDCOM contexts before each test"""
    _gedcom_contexts.clear()
    yield
    _gedcom_contexts.clear()


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data
        assert "/timeline" in data["endpoints"]
        assert "/persons" in data["endpoints"]
        assert "/person" in data["endpoints"]


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "cache_dir" in data
        assert "s3_configured" in data


class TestTimelineEndpoint:
    """Tests for timeline endpoint"""

    def test_timeline_success(self, client, sample_gedcom_file):
        """Test successful timeline retrieval"""
        response = client.get(
            "/timeline",
            params={
                "gedcom_id": "@I1@",
                "gedcom_file_path": sample_gedcom_file
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "person_id" in data
        assert "timeline" in data
        assert data["person_id"] == "@I1@"

    def test_timeline_missing_params(self, client):
        """Test timeline endpoint with missing parameters"""
        response = client.get("/timeline")
        assert response.status_code == 422  # Validation error

    def test_timeline_file_not_found(self, client):
        """Test timeline with non-existent file"""
        response = client.get(
            "/timeline",
            params={
                "gedcom_id": "@I1@",
                "gedcom_file_path": "/nonexistent/file.ged"
            }
        )
        assert response.status_code == 404

    def test_timeline_invalid_person_id(self, client, sample_gedcom_file):
        """Test timeline with invalid person ID"""
        response = client.get(
            "/timeline",
            params={
                "gedcom_id": "@I999@",
                "gedcom_file_path": sample_gedcom_file
            }
        )
        # Should return 200 with "No timeline found" message
        assert response.status_code == 200
        data = response.json()
        assert "No timeline found" in data["timeline"]


class TestPersonsEndpoint:
    """Tests for persons list endpoint"""

    def test_persons_list_success(self, client, sample_gedcom_file):
        """Test successful persons list retrieval"""
        response = client.get(
            "/persons",
            params={"gedcom_file_path": sample_gedcom_file}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "persons" in data
        assert data["total"] == 3
        assert "@I1@" in data["persons"]
        assert "@I2@" in data["persons"]
        assert "@I3@" in data["persons"]

    def test_persons_missing_params(self, client):
        """Test persons endpoint with missing parameters"""
        response = client.get("/persons")
        assert response.status_code == 422  # Validation error

    def test_persons_file_not_found(self, client):
        """Test persons list with non-existent file"""
        response = client.get(
            "/persons",
            params={"gedcom_file_path": "/nonexistent/file.ged"}
        )
        assert response.status_code == 404


class TestPersonEndpoint:
    """Tests for person details endpoint"""

    def test_person_details_success(self, client, sample_gedcom_file):
        """Test successful person details retrieval"""
        response = client.get(
            "/person",
            params={
                "id": "@I1@",
                "gedcom_file_path": sample_gedcom_file
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "@I1@"
        assert "John" in data["name"]
        assert "Doe" in data["name"]
        assert data["gender"] == "M"
        assert data["birth_date"] is not None
        assert data["death_date"] is not None
        assert data["occupation"] == "Engineer"

    def test_person_with_relationships(self, client, sample_gedcom_file):
        """Test person details includes relationships"""
        response = client.get(
            "/person",
            params={
                "id": "@I3@",
                "gedcom_file_path": sample_gedcom_file
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "@I3@"
        assert len(data["parents"]) == 2
        assert "@I1@" in data["parents"]
        assert "@I2@" in data["parents"]

    def test_person_missing_params(self, client):
        """Test person endpoint with missing parameters"""
        response = client.get("/person")
        assert response.status_code == 422  # Validation error

    def test_person_not_found(self, client, sample_gedcom_file):
        """Test person details with invalid person ID"""
        response = client.get(
            "/person",
            params={
                "id": "@I999@",
                "gedcom_file_path": sample_gedcom_file
            }
        )
        assert response.status_code == 404


class TestFileCache:
    """Tests for file caching functionality"""

    def test_cache_initialization(self, tmp_path):
        """Test cache directory is created on initialization"""
        cache_dir = tmp_path / "test_cache"
        with patch.object(config, 'CACHE_DIR', str(cache_dir)):
            cache = FileCache()
            assert cache.cache_dir.exists()

    def test_cache_key_generation(self):
        """Test cache key generation is consistent"""
        cache = FileCache()
        key1 = cache._get_cache_key("/path/to/file.ged")
        key2 = cache._get_cache_key("/path/to/file.ged")
        key3 = cache._get_cache_key("/path/to/other.ged")

        assert key1 == key2
        assert key1 != key3

    def test_get_local_file(self, sample_gedcom_file):
        """Test getting a file that exists locally"""
        cache = FileCache()
        result = cache.get_file(sample_gedcom_file)

        assert result is not None
        assert result.exists()
        assert str(result) == sample_gedcom_file

    def test_get_nonexistent_file(self):
        """Test getting a file that doesn't exist"""
        cache = FileCache()
        result = cache.get_file("/nonexistent/file.ged")

        assert result is None

    def test_cache_validity_check(self, tmp_path):
        """Test cache validity based on TTL"""
        cache = FileCache()

        # Create a test file
        test_file = tmp_path / "test.ged"
        test_file.write_text("test content")

        # File should be valid when just created
        assert cache._is_cache_valid(test_file)

        # Modify the file's timestamp to be old
        old_time = datetime.now() - timedelta(hours=config.CACHE_TTL_HOURS + 1)
        os.utime(test_file, (old_time.timestamp(), old_time.timestamp()))

        # File should now be invalid
        assert not cache._is_cache_valid(test_file)

    def test_clean_old_files(self, tmp_path):
        """Test cleaning old cached files"""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        with patch.object(config, 'CACHE_DIR', str(cache_dir)):
            cache = FileCache()

            # Create some test files
            old_file = cache_dir / "old.ged"
            new_file = cache_dir / "new.ged"
            old_file.write_text("old")
            new_file.write_text("new")

            # Make old file actually old
            old_time = datetime.now() - timedelta(hours=config.CACHE_TTL_HOURS + 1)
            os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))

            # Clean cache
            cache.clean_old_files()

            # Old file should be deleted, new file should remain
            assert not old_file.exists()
            assert new_file.exists()

    @patch('boto3.client')
    def test_s3_download_success(self, mock_boto_client, tmp_path):
        """Test successful S3 download"""
        # Setup mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        with patch.object(config, 'S3_BUCKET', 'test-bucket'):
            cache = FileCache()
            cache.s3_client = mock_s3

            local_path = tmp_path / "downloaded.ged"
            result = cache._download_from_s3("s3://test-bucket/file.ged", local_path)

            # Should call download_file
            mock_s3.download_file.assert_called_once()

    @patch('boto3.client')
    def test_s3_download_failure(self, mock_boto_client, tmp_path):
        """Test S3 download failure"""
        from botocore.exceptions import ClientError

        # Setup mock S3 client that raises an error
        mock_s3 = MagicMock()
        mock_s3.download_file.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "download_file"
        )
        mock_boto_client.return_value = mock_s3

        with patch.object(config, 'S3_BUCKET', 'test-bucket'):
            cache = FileCache()
            cache.s3_client = mock_s3

            local_path = tmp_path / "downloaded.ged"
            result = cache._download_from_s3("s3://test-bucket/file.ged", local_path)

            assert result is False


class TestCacheCleanEndpoint:
    """Tests for cache cleaning endpoint"""

    def test_clean_cache_success(self, client):
        """Test cache cleaning endpoint"""
        response = client.post("/cache/clean")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestIntegration:
    """Integration tests"""

    def test_multiple_requests_use_cache(self, client, sample_gedcom_file):
        """Test that multiple requests to same file use cached context"""
        # First request
        response1 = client.get(
            "/persons",
            params={"gedcom_file_path": sample_gedcom_file}
        )
        assert response1.status_code == 200

        # Second request should use cached context
        response2 = client.get(
            "/persons",
            params={"gedcom_file_path": sample_gedcom_file}
        )
        assert response2.status_code == 200

        # Both should return same data
        assert response1.json() == response2.json()

    def test_workflow_get_persons_then_details(self, client, sample_gedcom_file):
        """Test typical workflow: list persons, then get details"""
        # Get list of persons
        persons_response = client.get(
            "/persons",
            params={"gedcom_file_path": sample_gedcom_file}
        )
        assert persons_response.status_code == 200
        persons_data = persons_response.json()
        assert persons_data["total"] > 0

        # Get details for first person
        first_person_id = persons_data["persons"][0]
        person_response = client.get(
            "/person",
            params={
                "id": first_person_id,
                "gedcom_file_path": sample_gedcom_file
            }
        )
        assert person_response.status_code == 200
        person_data = person_response.json()
        assert person_data["id"] == first_person_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
