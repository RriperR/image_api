CREATE TABLE IF NOT EXISTS images (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'image/jpeg',
    data BYTEA NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    quality INT NOT NULL,
    size_bytes BIGINT NOT NULL,
    source_format TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_images_created_at ON images (created_at DESC);
