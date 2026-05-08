-- anomaly_events
--
-- Per-reading output of the scoring pipeline. One row per
-- (temperature_reading_id, model_run_id, model_config_name) identity tuple.
--
-- Persists ANOMALIES ONLY (rows the model flagged). The full scored audit
-- trail (every reading in the window, anomaly or not) lives in the hourly
-- scoring CSVs on the shared PVC; this table is the operator/dashboard view.
--
-- Idempotency: the unique constraint on the identity tuple lets the scorer
-- UPSERT safely. Re-running a window writes the same rows; rolling back a
-- bad model is `DELETE FROM anomaly_events WHERE model_run_id = '...'`.
--
-- Timestamps: TIMESTAMPTZ (UTC instants on disk). To render EST in queries:
--   ALTER DATABASE zigbee_db SET timezone TO 'America/New_York';

BEGIN;

CREATE TABLE IF NOT EXISTS anomaly_events (
    id                      BIGSERIAL        PRIMARY KEY,

    temperature_reading_id  BIGINT           NOT NULL
                                             REFERENCES temperature_readings(id) ON DELETE CASCADE,
    device_id               UUID             NOT NULL
                                             REFERENCES devices(id) ON DELETE CASCADE,

    model_run_id            TEXT             NOT NULL,
    model_config_name       TEXT             NOT NULL,
    model_trained_at        TIMESTAMPTZ      NULL,

    scored_at               TIMESTAMPTZ      NOT NULL,
    prediction              SMALLINT         NOT NULL,
    anomaly_score           DOUBLE PRECISION NOT NULL,
    anomaly_reason          TEXT             NULL,

    event_status            TEXT             NOT NULL DEFAULT 'open',
    event_severity          TEXT             NULL,

    created_at              TIMESTAMPTZ      NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ      NOT NULL DEFAULT now(),

    CONSTRAINT anomaly_events_identity_uq
        UNIQUE (temperature_reading_id, model_run_id, model_config_name),

    CONSTRAINT anomaly_events_prediction_chk
        CHECK (prediction IN (-1, 1)),

    CONSTRAINT anomaly_events_event_status_chk
        CHECK (event_status IN ('open', 'acknowledged', 'resolved')),

    CONSTRAINT anomaly_events_event_severity_chk
        CHECK (event_severity IS NULL OR event_severity IN ('low', 'medium', 'high'))
);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_device_scored_at
    ON anomaly_events (device_id, scored_at DESC);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_open_scored_at
    ON anomaly_events (scored_at DESC)
    WHERE event_status = 'open';

CREATE INDEX IF NOT EXISTS idx_anomaly_events_model_run
    ON anomaly_events (model_run_id);

CREATE OR REPLACE FUNCTION anomaly_events_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_anomaly_events_updated_at ON anomaly_events;
CREATE TRIGGER trg_anomaly_events_updated_at
    BEFORE UPDATE ON anomaly_events
    FOR EACH ROW EXECUTE FUNCTION anomaly_events_set_updated_at();

COMMENT ON TABLE  anomaly_events                  IS 'Per-reading anomaly output. One row per (temperature_reading, model_run, model_config). Anomalies only.';
COMMENT ON COLUMN anomaly_events.prediction       IS 'sklearn IsolationForest convention: -1 anomaly, 1 normal. Anomalies-only persistence => -1.';
COMMENT ON COLUMN anomaly_events.anomaly_score    IS 'sklearn IsolationForest score_samples output. Lower = more anomalous.';
COMMENT ON COLUMN anomaly_events.event_status     IS 'Lifecycle: open | acknowledged | resolved. Default open on insert.';
COMMENT ON COLUMN anomaly_events.event_severity   IS 'Optional severity bucket (low | medium | high). Set once thresholds are tuned.';

COMMIT;
