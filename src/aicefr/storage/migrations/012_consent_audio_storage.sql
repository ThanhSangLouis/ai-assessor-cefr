-- SCRUM-87: retain independent choices for audio storage and research reuse.
-- Historical consents did not capture the audio-storage choice and default to denied.
ALTER TABLE consents ADD COLUMN audio_storage_allowed INTEGER NOT NULL DEFAULT 0
    CHECK(audio_storage_allowed IN (0,1));
ALTER TABLE consent_events ADD COLUMN audio_storage_allowed INTEGER NOT NULL DEFAULT 0
    CHECK(audio_storage_allowed IN (0,1));
