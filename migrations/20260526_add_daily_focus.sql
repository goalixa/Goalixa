-- Migration: Add daily_focus table
-- Date: 2026-05-26
-- Description: Create the daily_focus table with proper constraints, indexes, and trigger for auto-updating timestamps.

-- Create daily_focus table
CREATE TABLE IF NOT EXISTS daily_focus (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    focus_date DATE NOT NULL,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    time_block VARCHAR(20) DEFAULT 'unscheduled',
    scheduled_start TIME,
    scheduled_end TIME,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_daily_focus_user_date_task UNIQUE(user_id, focus_date, task_id),
    CONSTRAINT chk_time_block CHECK (time_block IN ('morning', 'afternoon', 'evening', 'unscheduled'))
);

-- Create indexes for query performance
CREATE INDEX IF NOT EXISTS idx_daily_focus_user_date ON daily_focus(user_id, focus_date);
CREATE INDEX IF NOT EXISTS idx_daily_focus_task ON daily_focus(task_id);

-- Create trigger function for updated_at auto-update
CREATE OR REPLACE FUNCTION update_daily_focus_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at auto-update on row update
DROP TRIGGER IF EXISTS trg_daily_focus_updated_at ON daily_focus;
CREATE TRIGGER trg_daily_focus_updated_at
    BEFORE UPDATE ON daily_focus
    FOR EACH ROW
    EXECUTE FUNCTION update_daily_focus_updated_at();

-- Commit the migration
COMMIT;
