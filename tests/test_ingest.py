import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.datastore.models import Project
from migration_utility.ingest.service import IngestService
from migration_utility.ingest.staging import count_staged_rows, staging_table_name
from migration_utility.schema.registry import build_default_schema_registry
from migration_utility.schema.validation import validate_records


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.type.__class__.__name__ == "JSONB":
                from sqlalchemy import JSON

                column.type = JSON()
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    project = Project(
        name="Test",
        slug="test-proj",
        source_connector_key="staging",
        target_adapter_key="mock",
    )
    session.add(project)
    session.commit()
    yield session, project, engine
    session.close()


def test_validate_records_required_field():
    registry = build_default_schema_registry()
    entity = registry.get("account")
    valid, errors = validate_records(entity, [{"id": "1", "name": "X"}])
    assert len(valid) == 0
    assert len(errors) == 1
    assert "status" in errors[0][2]


def test_ingest_csv_stages_valid_rows(db_session):
    session, project, engine = db_session
    csv_content = "id,name,status\nACC-001,Alice,active\nACC-002,,active\nACC-003,Carol,active\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    registry = build_default_schema_registry()
    service = IngestService(session, registry, engine=engine)

    ingest_file = service.register_upload(
        project,
        entity="account",
        original_filename="accounts.csv",
        temp_path=tmp_path,
    )
    result = service.process_file(ingest_file, project)

    assert result.status == "processed"
    assert result.total_rows == 3
    assert result.staged_count == 2
    assert result.error_count == 1

    table_name = staging_table_name(project.slug, "account")
    assert count_staged_rows(engine, table_name, project.id) == 2

    tmp_path.unlink(missing_ok=True)
