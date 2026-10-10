import os
import pytest
from services.file_parser import ParticipantFileParser, FileParserError


@pytest.fixture
def csv_file(tmp_path):
    def _create(content):
        path = tmp_path / "test.csv"
        path.write_text(content, encoding="utf-8")
        return path
    return _create


def test_parser_valid_csv(csv_file):
    content = "name,email,course_name,completion_date\nArun,arun@example.com,Python,2026-10-01"
    path = csv_file(content)
    
    parser = ParticipantFileParser(path)
    valid_rows, errors, total = parser.parse()
    
    assert total == 1
    assert len(errors) == 0
    assert len(valid_rows) == 1
    assert valid_rows[0]["name"] == "Arun"
    assert valid_rows[0]["email"] == "arun@example.com"


def test_parser_missing_required_column(csv_file):
    content = "email,course_name\narun@example.com,Python"
    path = csv_file(content)
    
    parser = ParticipantFileParser(path)
    with pytest.raises(FileParserError, match="Missing required column: 'name'"):
        parser.parse()


def test_parser_invalid_email(csv_file):
    content = "name,email\nArun,not-an-email"
    path = csv_file(content)
    
    parser = ParticipantFileParser(path)
    valid_rows, errors, total = parser.parse()
    
    assert total == 1
    assert len(errors) == 1
    assert "Invalid email address" in errors[0]["error"]
    assert len(valid_rows) == 0


def test_parser_detects_duplicates(csv_file):
    content = "name,email\nArun,arun@example.com\nArun,arun@example.com\nPriya,priya@example.com"
    path = csv_file(content)
    
    parser = ParticipantFileParser(path)
    valid_rows, errors, total = parser.parse()
    
    assert total == 3
    assert len(errors) == 1
    assert "Duplicate record found" in errors[0]["error"]
    assert len(valid_rows) == 2
    assert valid_rows[0]["name"] == "Arun"
    assert valid_rows[1]["name"] == "Priya"
