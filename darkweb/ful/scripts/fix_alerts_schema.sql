-- Add deactivated_at column to alerts table if it doesn't exist
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMP;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_alerts_deactivated_at ON alerts(deactivated_at);
CREATE INDEX IF NOT EXISTS idx_alerts_is_active ON alerts(is_active);
