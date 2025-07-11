-- PostgreSQL Database Schema for Zamaz Debate System
-- This schema supports hybrid operation with JSON files during transition

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema
CREATE SCHEMA IF NOT EXISTS zamaz_debate;
SET search_path TO zamaz_debate, public;

-- =====================================
-- Core Debate Tables
-- =====================================

-- Debates table
CREATE TABLE debates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL, -- Maps to file-based IDs
    question TEXT NOT NULL,
    context TEXT,
    complexity VARCHAR(50) NOT NULL CHECK (complexity IN ('simple', 'moderate', 'complex')),
    method VARCHAR(50) NOT NULL DEFAULT 'debate',
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    final_decision TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_debates_external_id ON debates(external_id);
CREATE INDEX idx_debates_complexity ON debates(complexity);
CREATE INDEX idx_debates_created_at ON debates(created_at DESC);

-- Debate rounds table
CREATE TABLE debate_rounds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    debate_id UUID NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    claude_response TEXT,
    gemini_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(debate_id, round_number)
);

CREATE INDEX idx_debate_rounds_debate_id ON debate_rounds(debate_id);

-- Consensus analysis table
CREATE TABLE consensus_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    debate_id UUID NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
    has_consensus BOOLEAN NOT NULL,
    consensus_level DECIMAL(3,2) CHECK (consensus_level >= 0 AND consensus_level <= 1),
    consensus_type VARCHAR(50),
    areas_of_agreement TEXT[],
    areas_of_disagreement TEXT[],
    combined_recommendation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_consensus_analyses_debate_id ON consensus_analyses(debate_id);

-- =====================================
-- Decision Management Tables
-- =====================================

-- Decisions table
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    question TEXT NOT NULL,
    context TEXT,
    decision_text TEXT NOT NULL,
    decision_type VARCHAR(50) NOT NULL CHECK (decision_type IN ('SIMPLE', 'MODERATE', 'COMPLEX', 'EVOLUTION')),
    method VARCHAR(50) NOT NULL,
    rounds INTEGER DEFAULT 0,
    implementation_assignee VARCHAR(100),
    debate_id UUID REFERENCES debates(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_decisions_external_id ON decisions(external_id);
CREATE INDEX idx_decisions_type ON decisions(decision_type);
CREATE INDEX idx_decisions_assignee ON decisions(implementation_assignee);

-- =====================================
-- Implementation Tracking Tables
-- =====================================

-- Pull requests table
CREATE TABLE pull_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    decision_id UUID REFERENCES decisions(id),
    pr_number INTEGER,
    title TEXT NOT NULL,
    body TEXT,
    branch_name VARCHAR(255),
    base_branch VARCHAR(255) DEFAULT 'main',
    assignee VARCHAR(100),
    reviewer VARCHAR(100),
    labels TEXT[],
    state VARCHAR(50) DEFAULT 'open',
    merged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    merged_at TIMESTAMP WITH TIME ZONE,
    url TEXT
);

CREATE INDEX idx_pull_requests_external_id ON pull_requests(external_id);
CREATE INDEX idx_pull_requests_state ON pull_requests(state);
CREATE INDEX idx_pull_requests_assignee ON pull_requests(assignee);

-- GitHub issues table
CREATE TABLE github_issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    issue_number INTEGER UNIQUE NOT NULL,
    decision_id UUID REFERENCES decisions(id),
    pr_id UUID REFERENCES pull_requests(id),
    title TEXT NOT NULL,
    body TEXT,
    assignee VARCHAR(100),
    labels TEXT[],
    state VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE,
    url TEXT NOT NULL
);

CREATE INDEX idx_github_issues_number ON github_issues(issue_number);
CREATE INDEX idx_github_issues_state ON github_issues(state);
CREATE INDEX idx_github_issues_assignee ON github_issues(assignee);

-- Commits table
CREATE TABLE commits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sha VARCHAR(40) UNIQUE NOT NULL,
    pr_id UUID REFERENCES pull_requests(id),
    message TEXT NOT NULL,
    author VARCHAR(255),
    committed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_commits_sha ON commits(sha);
CREATE INDEX idx_commits_pr_id ON commits(pr_id);

-- =====================================
-- Evolution Tracking Tables
-- =====================================

-- Evolutions table
CREATE TABLE evolutions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evolution_number INTEGER UNIQUE NOT NULL,
    evolution_type VARCHAR(50) NOT NULL,
    feature VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    debate_id UUID REFERENCES debates(id),
    decision_id UUID REFERENCES decisions(id),
    implemented BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evolutions_type ON evolutions(evolution_type);
CREATE INDEX idx_evolutions_feature ON evolutions(feature);
CREATE INDEX idx_evolutions_implemented ON evolutions(implemented);

-- =====================================
-- Workflow Management Tables
-- =====================================

-- Workflow definitions table
CREATE TABLE workflow_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL,
    participants TEXT[],
    max_rounds INTEGER DEFAULT 5,
    min_rounds INTEGER DEFAULT 2,
    consensus_threshold DECIMAL(3,2) DEFAULT 0.8,
    config JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflow_definitions_name ON workflow_definitions(name);
CREATE INDEX idx_workflow_definitions_active ON workflow_definitions(active);

-- Workflow executions table
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_definition_id UUID REFERENCES workflow_definitions(id),
    debate_id UUID REFERENCES debates(id),
    state VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflow_executions_state ON workflow_executions(state);
CREATE INDEX idx_workflow_executions_debate_id ON workflow_executions(debate_id);

-- =====================================
-- Event Sourcing Tables
-- =====================================

-- Domain events table
CREATE TABLE domain_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(255) NOT NULL,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(255) NOT NULL,
    event_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_domain_events_type ON domain_events(event_type);
CREATE INDEX idx_domain_events_aggregate ON domain_events(aggregate_id, aggregate_type);
CREATE INDEX idx_domain_events_occurred_at ON domain_events(occurred_at DESC);

-- =====================================
-- Analytics Tables
-- =====================================

-- Metrics table for performance tracking
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255) NOT NULL,
    metric_value DECIMAL,
    tags JSONB DEFAULT '{}',
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_name ON metrics(metric_name);
CREATE INDEX idx_metrics_recorded_at ON metrics(recorded_at DESC);

-- =====================================
-- Utility Functions
-- =====================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_debates_updated_at BEFORE UPDATE ON debates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================
-- Views for Compatibility
-- =====================================

-- View for recent debates with consensus
CREATE VIEW v_recent_debates_with_consensus AS
SELECT 
    d.id,
    d.external_id,
    d.question,
    d.complexity,
    d.start_time,
    d.end_time,
    ca.has_consensus,
    ca.consensus_level,
    ca.consensus_type,
    ca.combined_recommendation
FROM debates d
LEFT JOIN consensus_analyses ca ON ca.debate_id = d.id
ORDER BY d.created_at DESC;

-- View for implementation status
CREATE VIEW v_implementation_status AS
SELECT 
    d.id AS decision_id,
    d.external_id AS decision_external_id,
    d.question,
    d.decision_type,
    d.implementation_assignee,
    pr.pr_number,
    pr.state AS pr_state,
    pr.merged AS pr_merged,
    gi.issue_number,
    gi.state AS issue_state,
    COUNT(c.id) AS commit_count
FROM decisions d
LEFT JOIN pull_requests pr ON pr.decision_id = d.id
LEFT JOIN github_issues gi ON gi.decision_id = d.id
LEFT JOIN commits c ON c.pr_id = pr.id
WHERE d.decision_type IN ('COMPLEX', 'EVOLUTION')
GROUP BY d.id, pr.id, gi.id;

-- =====================================
-- Data Migration Support
-- =====================================

-- Table to track migrated files
CREATE TABLE migration_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path VARCHAR(500) UNIQUE NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    migrated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- =====================================
-- Permissions
-- =====================================

-- Create application user and grant permissions
-- Note: Replace 'zamaz_app' with your actual application user
-- CREATE USER zamaz_app WITH PASSWORD 'your_secure_password';
-- GRANT USAGE ON SCHEMA zamaz_debate TO zamaz_app;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA zamaz_debate TO zamaz_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA zamaz_debate TO zamaz_app;