-- Migration: Create audit_events table
-- Created: 2024-01-15
-- Description: Creates the audit_events table with indexes for audit trail storage

-- Create audit_events table
CREATE TABLE audit_events (
    id BIGSERIAL PRIMARY KEY,
    trace_id UUID,
    request_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_audit_events_trace_id ON audit_events(trace_id);
CREATE INDEX idx_audit_events_request_id ON audit_events(request_id);
CREATE INDEX idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp);
CREATE INDEX idx_audit_events_trace_timestamp ON audit_events(trace_id, timestamp);

-- GIN index for JSONB queries (e.g., filtering by user_id in event_data)
CREATE INDEX idx_audit_events_event_data_gin ON audit_events USING GIN(event_data);

