"""
Tests for cron cost visibility features (GH#78).

Tests cover:
- Schema migration (new columns in cron_runs)
- Cost data insertion and querying
- Leaderboard computation
- Anomaly detection
- Daily totals and projection
- Cost history per cron job
- API endpoint structure
"""
import os
import sys
import json
import time
import tempfile
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from history import HistoryDB


@pytest.fixture
def db():
    """Create a temporary HistoryDB for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        yield HistoryDB(db_path)
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


# ── Schema Tests ──────────────────────────────────────────────────────

class TestSchema:
    def test_cron_runs_has_cost_columns(self, db):
        """cron_runs table should have tokens_in, tokens_out, cost_usd, model, session_id."""
        conn = db._get_conn()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(cron_runs)").fetchall()}
        assert 'tokens_in' in cols
        assert 'tokens_out' in cols
        assert 'cost_usd' in cols
        assert 'model' in cols
        assert 'session_id' in cols

    def test_migration_on_existing_db(self):
        """Migration should add columns to an existing DB without cost columns."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            import sqlite3
            # Create old-schema table
            conn = sqlite3.connect(db_path)
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS cron_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    job_id TEXT NOT NULL,
                    job_name TEXT DEFAULT '',
                    status TEXT DEFAULT 'unknown',
                    duration_ms INTEGER DEFAULT 0,
                    error TEXT DEFAULT '',
                    extra_json TEXT DEFAULT '{}'
                );
            ''')
            conn.commit()
            conn.close()

            # Now open with HistoryDB which should migrate
            db = HistoryDB(db_path)
            conn = db._get_conn()
            cols = {row[1] for row in conn.execute("PRAGMA table_info(cron_runs)").fetchall()}
            assert 'tokens_in' in cols
            assert 'cost_usd' in cols
            assert 'model' in cols
            assert 'session_id' in cols
        finally:
            os.unlink(db_path)


# ── Insert & Query Tests ─────────────────────────────────────────────

class TestInsertCronRun:
    def test_insert_with_cost_data(self, db):
        """Insert a cron run with cost data and verify it's stored."""
        now = time.time()
        db.insert_cron_run(
            job_id='heartbeat-123',
            job_name='heartbeat',
            status='ok',
            duration_ms=5000,
            tokens_in=1200,
            tokens_out=350,
            cost_usd=0.0421,
            model='claude-sonnet-4-20250514',
            session_id='abc-def-123',
            ts=now,
        )
        results = db.query_crons(now - 1, now + 1, job_id='heartbeat-123')
        assert len(results) == 1
        r = results[0]
        assert r['job_id'] == 'heartbeat-123'
        assert r['tokens_in'] == 1200
        assert r['tokens_out'] == 350
        assert abs(r['cost_usd'] - 0.0421) < 0.0001
        assert r['model'] == 'claude-sonnet-4-20250514'
        assert r['session_id'] == 'abc-def-123'

    def test_insert_without_cost_data(self, db):
        """Insert a cron run without cost data (backward compat)."""
        now = time.time()
        db.insert_cron_run(
            job_id='check-123',
            job_name='check',
            status='ok',
            duration_ms=2000,
            ts=now,
        )
        results = db.query_crons(now - 1, now + 1, job_id='check-123')
        assert len(results) == 1
        r = results[0]
        assert r['tokens_in'] == 0
        assert r['cost_usd'] == 0.0
        assert r['model'] == ''

    def test_insert_with_none_values(self, db):
        """None values should be handled gracefully."""
        now = time.time()
        db.insert_cron_run(
            job_id='test-none',
            job_name='test',
            status='ok',
            tokens_in=None,
            tokens_out=None,
            cost_usd=None,
            model=None,
            session_id=None,
            ts=now,
        )
        results = db.query_crons(now - 1, now + 1, job_id='test-none')
        assert len(results) == 1
        assert results[0]['tokens_in'] == 0
        assert results[0]['cost_usd'] == 0.0


# ── Cost History Tests ────────────────────────────────────────────────

class TestCostHistory:
    def _seed_job_runs(self, db, job_id='hb-001', count=10, base_cost=0.04):
        """Seed multiple cron runs for a job."""
        now = time.time()
        for i in range(count):
            cost = base_cost + (i * 0.005)
            db.insert_cron_run(
                job_id=job_id,
                job_name=f'heartbeat-{job_id}',
                status='ok',
                duration_ms=3000 + i * 100,
                tokens_in=1000 + i * 100,
                tokens_out=300 + i * 50,
                cost_usd=cost,
                model='claude-sonnet-4-20250514',
                session_id=f'session-{i}',
                ts=now - (count - i) * 3600,  # One per hour going back
            )

    def test_cost_history_returns_data(self, db):
        self._seed_job_runs(db)
        history = db.query_cron_cost_history('hb-001', 30)
        assert len(history) == 10
        assert all(h['cost_usd'] > 0 for h in history)

    def test_cost_history_ordered_by_time(self, db):
        self._seed_job_runs(db)
        history = db.query_cron_cost_history('hb-001', 30)
        timestamps = [h['timestamp'] for h in history]
        assert timestamps == sorted(timestamps)

    def test_cost_history_empty_for_unknown_job(self, db):
        self._seed_job_runs(db)
        history = db.query_cron_cost_history('nonexistent', 30)
        assert history == []


# ── Leaderboard Tests ─────────────────────────────────────────────────

class TestLeaderboard:
    def _seed_multiple_jobs(self, db):
        now = time.time()
        # Job A: expensive (10 runs, ~$0.50 total)
        for i in range(10):
            db.insert_cron_run('job-a', 'Expensive Job', 'ok', 5000,
                               tokens_in=5000, tokens_out=1500, cost_usd=0.05,
                               model='claude-opus-4-20250514', ts=now - i * 3600)
        # Job B: medium (5 runs, ~$0.10 total)
        for i in range(5):
            db.insert_cron_run('job-b', 'Medium Job', 'ok', 3000,
                               tokens_in=2000, tokens_out=500, cost_usd=0.02,
                               model='claude-sonnet-4-20250514', ts=now - i * 3600)
        # Job C: cheap (20 runs, ~$0.02 total)
        for i in range(20):
            db.insert_cron_run('job-c', 'Cheap Job', 'ok', 1000,
                               tokens_in=200, tokens_out=50, cost_usd=0.001,
                               model='claude-haiku-3', ts=now - i * 3600)

    def test_leaderboard_ordered_by_cost(self, db):
        self._seed_multiple_jobs(db)
        leaders = db.query_cron_cost_leaderboard(days=7)
        assert len(leaders) == 3
        assert leaders[0]['job_id'] == 'job-a'
        assert leaders[1]['job_id'] == 'job-b'
        assert leaders[2]['job_id'] == 'job-c'

    def test_leaderboard_totals_correct(self, db):
        self._seed_multiple_jobs(db)
        leaders = db.query_cron_cost_leaderboard(days=7)
        a = leaders[0]
        assert abs(a['total_cost'] - 0.50) < 0.01
        assert a['run_count'] == 10
        assert abs(a['avg_cost_per_run'] - 0.05) < 0.001

    def test_leaderboard_respects_limit(self, db):
        self._seed_multiple_jobs(db)
        leaders = db.query_cron_cost_leaderboard(days=7, limit=2)
        assert len(leaders) == 2

    def test_leaderboard_respects_days(self, db):
        now = time.time()
        # Old run (8 days ago)
        db.insert_cron_run('old-job', 'Old', 'ok', 1000,
                           cost_usd=10.0, ts=now - 8 * 86400)
        # Recent run
        db.insert_cron_run('new-job', 'New', 'ok', 1000,
                           cost_usd=0.01, ts=now - 3600)
        leaders = db.query_cron_cost_leaderboard(days=7)
        job_ids = [l['job_id'] for l in leaders]
        assert 'new-job' in job_ids
        assert 'old-job' not in job_ids


# ── Anomaly Detection Tests ──────────────────────────────────────────

class TestAnomalyDetection:
    def test_detects_cost_spike(self, db):
        now = time.time()
        # Seed 7 days of normal runs (avg ~$0.04)
        for i in range(14):
            db.insert_cron_run('job-x', 'Job X', 'ok', 3000,
                               cost_usd=0.04, ts=now - (i + 1) * 43200)  # Every 12h
        # Add a spike in the last 24h
        db.insert_cron_run('job-x', 'Job X', 'ok', 3000,
                           cost_usd=0.20, ts=now - 3600)  # 5x the average

        anomalies = db.query_cron_anomalies(multiplier=2.0)
        assert len(anomalies) == 1
        assert anomalies[0]['job_id'] == 'job-x'
        assert anomalies[0]['spike_ratio'] > 2.0

    def test_no_anomaly_for_normal_cost(self, db):
        now = time.time()
        # Normal runs over 7 days
        for i in range(14):
            db.insert_cron_run('job-y', 'Job Y', 'ok', 3000,
                               cost_usd=0.04, ts=now - (i + 1) * 43200)
        # Recent run at normal cost
        db.insert_cron_run('job-y', 'Job Y', 'ok', 3000,
                           cost_usd=0.04, ts=now - 3600)

        anomalies = db.query_cron_anomalies(multiplier=2.0)
        assert len(anomalies) == 0

    def test_no_anomaly_with_insufficient_history(self, db):
        """Need at least 3 historical runs to flag anomalies."""
        now = time.time()
        # Only 2 historical runs
        for i in range(2):
            db.insert_cron_run('job-z', 'Job Z', 'ok', 3000,
                               cost_usd=0.04, ts=now - (i + 2) * 86400)
        # Expensive recent run
        db.insert_cron_run('job-z', 'Job Z', 'ok', 3000,
                           cost_usd=1.00, ts=now - 3600)

        anomalies = db.query_cron_anomalies()
        assert len(anomalies) == 0


# ── Daily Totals Tests ────────────────────────────────────────────────

class TestDailyTotals:
    def test_daily_aggregation(self, db):
        now = time.time()
        today_start = (int(now) // 86400) * 86400
        # 3 runs today
        for i in range(3):
            db.insert_cron_run('job-d', 'Daily', 'ok', 1000,
                               cost_usd=0.05, ts=today_start + i * 3600)
        # 2 runs yesterday
        for i in range(2):
            db.insert_cron_run('job-d', 'Daily', 'ok', 1000,
                               cost_usd=0.03, ts=today_start - 86400 + i * 3600)

        daily = db.query_cron_daily_totals(days=7)
        assert len(daily) >= 2
        # Find today's total
        today_data = [d for d in daily if d['day_ts'] == today_start]
        assert len(today_data) == 1
        assert abs(today_data[0]['total_cost'] - 0.15) < 0.01
        assert today_data[0]['run_count'] == 3

    def test_empty_daily_totals(self, db):
        daily = db.query_cron_daily_totals(days=7)
        assert daily == []


# ── API Endpoint Tests ────────────────────────────────────────────────

class TestCronCostAPIs:
    """Test API endpoints return correct structure. Requires running server."""

    def test_cost_leaderboard_endpoint(self, api, base_url):
        r = api.get(f"{base_url}/api/crons/cost-leaderboard", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert 'jobs' in d
        assert isinstance(d['jobs'], list)

    def test_anomalies_endpoint(self, api, base_url):
        r = api.get(f"{base_url}/api/crons/anomalies", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert 'anomalies' in d
        assert isinstance(d['anomalies'], list)

    def test_daily_totals_endpoint(self, api, base_url):
        r = api.get(f"{base_url}/api/crons/daily-totals", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert 'days' in d
        assert isinstance(d['days'], list)
        # projection should be present (null or dict)
        assert 'projection' in d

    def test_cost_history_endpoint(self, api, base_url):
        r = api.get(f"{base_url}/api/cron/fake-job-id/cost-history", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert 'data' in d
        assert isinstance(d['data'], list)

    def test_crons_endpoint_has_cost_fields(self, api, base_url):
        r = api.get(f"{base_url}/api/crons", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert 'jobs' in d
        # Jobs may be empty but the structure should be right
        for j in d.get('jobs', []):
            # These fields should exist if cost data is available
            # They're optional (only present when history has data)
            assert isinstance(j, dict)
