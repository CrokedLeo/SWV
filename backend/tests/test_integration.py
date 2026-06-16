"""
Integration tests with real database and API routes
Tests: Database persistence, API responses, end-to-end workflow
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from backend.models.database import Base, get_db
from backend.main import app
from backend.models.orm import HistoricalReport, PollutantReading
from datetime import datetime, timedelta

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def api_headers():
    return {"X-API-Key": "test-key"}


class TestDatabaseIntegration:
    def test_create_and_retrieve_report(self):
        db = TestingSessionLocal()
        report = HistoricalReport(
            report_id="RPT_TEST0001",
            timestamp=datetime.utcnow(),
            latitude=43.7701,
            longitude=11.2556,
            aqi_value=45,
            smoke_percentage=12.5,
            primary_pollutant="PM2.5",
            risk_level="excellent",
        )
        db.add(report)
        db.commit()
        retrieved = db.query(HistoricalReport).filter(HistoricalReport.report_id == "RPT_TEST0001").first()
        assert retrieved is not None
        assert retrieved.aqi_value == 45
        assert retrieved.latitude == 43.7701
        db.close()

    def test_cascade_delete_pollutant_readings(self):
        db = TestingSessionLocal()
        report = HistoricalReport(
            report_id="RPT_TEST0002",
            timestamp=datetime.utcnow(),
            latitude=43.7701,
            longitude=11.2556,
            aqi_value=80,
            smoke_percentage=10.0,
            primary_pollutant="NO2",
            risk_level="good",
        )
        db.add(report)
        db.flush()

        reading = PollutantReading(
            report_id=report.id,
            pollutant_type="NO2",
            value=40.0,
            unit="ppb",
            aqi_index=80,
            risk_level="good",
        )
        db.add(reading)
        db.commit()

        assert db.query(PollutantReading).count() == 1
        db.delete(report)
        db.commit()
        assert db.query(PollutantReading).count() == 0
        db.close()

    def test_spatial_query_index(self):
        db = TestingSessionLocal()
        reports_data = [
            HistoricalReport(report_id=f"RPT_SPATIAL{i:04d}", timestamp=datetime.utcnow(),
                             latitude=round(43.77 + i * 0.01, 6), longitude=11.25, aqi_value=50,
                             smoke_percentage=5.0, primary_pollutant="PM2.5", risk_level="good")
            for i in range(5)
        ]
        for r in reports_data:
            db.add(r)
        db.commit()

        results = db.query(HistoricalReport).filter(
            HistoricalReport.latitude >= 43.77,
            HistoricalReport.latitude <= 43.81,
        ).all()
        assert len(results) == 5
        db.close()


class TestAPIEndpoints:
    def test_health_endpoint(self):
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_reports_history_pagination(self):
        client = TestClient(app)
        db = TestingSessionLocal()
        now = datetime.utcnow()
        for i in range(100):
            r = HistoricalReport(
                report_id=f"RPT_PAG{i:04d}",
                timestamp=now - timedelta(hours=i),
                latitude=43.7701,
                longitude=11.2556,
                aqi_value=i % 300,
                smoke_percentage=float(i % 100),
                primary_pollutant="PM2.5",
                risk_level="moderate",
            )
            db.add(r)
        db.commit()
        db.close()

        headers = {"X-API-Key": "your-secret-key-change-in-production"}
        response = client.get("/api/v1/reports/history?latitude=43.7701&longitude=11.2556&offset=0&limit=20", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 20
        assert data["total"] == 100
        assert data["offset"] == 0
        assert data["limit"] == 20
        assert data["has_more"] is True
        assert len(data["reports"]) == 20

    def test_aqi_reference_endpoint(self):
        client = TestClient(app)
        response = client.get("/api/v1/aqi-reference")
        assert response.status_code == 200
        data = response.json()
        assert "aqi_ranges" in data
        assert "excellent" in data["aqi_ranges"]


class TestPagination:
    headers = {"X-API-Key": "your-secret-key-change-in-production"}

    def test_pagination_offset_limit(self):
        client = TestClient(app)
        db = TestingSessionLocal()
        now = datetime.utcnow()
        for i in range(50):
            db.add(HistoricalReport(
                report_id=f"RPT_OFF{i:04d}",
                timestamp=now - timedelta(hours=i),
                latitude=43.7701,
                longitude=11.2556,
                aqi_value=i,
                smoke_percentage=float(i),
                primary_pollutant="PM2.5",
                risk_level="good",
            ))
        db.commit()
        db.close()

        r1 = client.get("/api/v1/reports/history?latitude=43.7701&longitude=11.2556&offset=0&limit=10", headers=self.headers)
        r2 = client.get("/api/v1/reports/history?latitude=43.7701&longitude=11.2556&offset=10&limit=10", headers=self.headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        d1, d2 = r1.json(), r2.json()
        assert d1["count"] == 10
        assert d2["count"] == 10
        ids1 = [r["report_id"] for r in d1["reports"]]
        ids2 = [r["report_id"] for r in d2["reports"]]
        assert not set(ids1) & set(ids2)

    def test_pagination_has_more(self):
        client = TestClient(app)
        db = TestingSessionLocal()
        now = datetime.utcnow()
        for i in range(25):
            db.add(HistoricalReport(
                report_id=f"RPT_MORE{i:04d}",
                timestamp=now - timedelta(hours=i),
                latitude=43.7701,
                longitude=11.2556,
                aqi_value=i,
                smoke_percentage=float(i),
                primary_pollutant="PM10",
                risk_level="good",
            ))
        db.commit()
        db.close()

        r1 = client.get("/api/v1/reports/history?latitude=43.7701&longitude=11.2556&offset=0&limit=20", headers=self.headers)
        r2 = client.get("/api/v1/reports/history?latitude=43.7701&longitude=11.2556&offset=20&limit=20", headers=self.headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["has_more"] is True
        assert r2.json()["has_more"] is False

    def test_pagination_total_count(self):
        client = TestClient(app)
        db = TestingSessionLocal()
        now = datetime.utcnow()
        for i in range(37):
            db.add(HistoricalReport(
                report_id=f"RPT_CNT{i:04d}",
                timestamp=now - timedelta(hours=i),
                latitude=43.7701,
                longitude=11.2556,
                aqi_value=i,
                smoke_percentage=float(i),
                primary_pollutant="NO2",
                risk_level="good",
            ))
        db.commit()
        db.close()

        response = client.get("/api/v1/reports/history?latitude=43.7701&longitude=11.2556&offset=0&limit=10", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 37
        assert data["count"] == 10
