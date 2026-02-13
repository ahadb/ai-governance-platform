-- Migration: Create hitl_reviews table with PostgreSQL queue support
-- Created: 2024-01-15
-- Description: Creates the hitl_reviews table for human-in-the-loop review queue

-- Create review status enum
CREATE TYPE review_status AS ENUM (
    'pending',      -- Waiting in queue for assignment
    'assigned',     -- Assigned to a reviewer
    'processing',   -- Currently being reviewed
    'approved',     -- Approved by reviewer
    'rejected',     -- Rejected by reviewer
    'expired'       -- Review expired (timeout)
);

-- Create hitl_reviews table
CREATE TABLE hitl_reviews (
    id BIGSERIAL PRIMARY KEY,
    
    -- Request correlation
    request_id UUID NOT NULL,
    trace_id UUID,
    
    -- Review metadata
    checkpoint VARCHAR(20) NOT NULL,  -- 'input' or 'output'
    reason TEXT NOT NULL,              -- Policy reason for escalation
    
    -- Review content (stored as JSONB for flexibility)
    context_data JSONB NOT NULL,       -- Full PolicyContext snapshot
    prompt TEXT,                       -- User prompt (for quick access)
    response TEXT,                     -- LLM response (if output checkpoint)
    
    -- Queue management
    status review_status NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 0,        -- Higher = more urgent (for future use)
    
    -- Worker assignment (for queue processing)
    assigned_to VARCHAR(255),          -- Reviewer user_id
    locked_until TIMESTAMPTZ,          -- Lock expiration (prevents stuck reviews)
    
    -- Review decision
    reviewed_by VARCHAR(255),          -- User who made the decision
    review_notes TEXT,                 -- Reviewer's notes
    decision_timestamp TIMESTAMPTZ,    -- When decision was made
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,             -- Review expiration (optional timeout)
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for queue operations
CREATE INDEX idx_hitl_reviews_status ON hitl_reviews(status) WHERE status = 'pending';
CREATE INDEX idx_hitl_reviews_status_created ON hitl_reviews(status, created_at) WHERE status = 'pending';
CREATE INDEX idx_hitl_reviews_request_id ON hitl_reviews(request_id);
CREATE INDEX idx_hitl_reviews_trace_id ON hitl_reviews(trace_id);
CREATE INDEX idx_hitl_reviews_assigned_to ON hitl_reviews(assigned_to) WHERE status IN ('assigned', 'processing');
CREATE INDEX idx_hitl_reviews_expires_at ON hitl_reviews(expires_at) WHERE status = 'pending';

-- GIN index for JSONB queries on context_data and metadata
CREATE INDEX idx_hitl_reviews_context_data_gin ON hitl_reviews USING GIN(context_data);
CREATE INDEX idx_hitl_reviews_metadata_gin ON hitl_reviews USING GIN(metadata);

-- Comments for documentation
COMMENT ON TABLE hitl_reviews IS 'Human-in-the-loop review queue for escalated policy decisions';
COMMENT ON COLUMN hitl_reviews.status IS 'Queue status: pending (in queue), assigned, processing, approved, rejected, expired';
COMMENT ON COLUMN hitl_reviews.locked_until IS 'Lock expiration time for worker assignment (prevents stuck reviews)';
COMMENT ON COLUMN hitl_reviews.context_data IS 'Full PolicyContext snapshot stored as JSONB';
COMMENT ON COLUMN hitl_reviews.checkpoint IS 'Which checkpoint triggered escalation: input or output';

