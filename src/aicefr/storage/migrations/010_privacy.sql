CREATE TABLE privacy_erasure_links (
 intent_id TEXT NOT NULL REFERENCES cleanup_intents(intent_id) ON DELETE CASCADE,
 resource_kind TEXT NOT NULL,
 resource_id TEXT NOT NULL,
 PRIMARY KEY(intent_id,resource_kind,resource_id)
);

DROP TRIGGER audit_no_update;
CREATE TRIGGER audit_no_update
BEFORE UPDATE ON audit
WHEN NOT EXISTS (
 SELECT 1 FROM cleanup_intents i
 WHERE i.resource_kind='privacy_erasure' AND i.state='running'
 AND (OLD.actor_id=i.owner_id OR OLD.object_id=i.owner_id OR EXISTS (
  SELECT 1 FROM privacy_erasure_links l
  WHERE l.intent_id=i.intent_id AND l.resource_id=OLD.object_id
 ))
 AND NEW.event_id=OLD.event_id AND NEW.action=OLD.action
 AND NEW.recorded_at=OLD.recorded_at AND NEW.reason IS NULL
 AND NEW.actor_id=CASE WHEN OLD.actor_id=i.owner_id THEN 'privacy:'||i.intent_id ELSE OLD.actor_id END
 AND NEW.object_id=CASE
  WHEN OLD.object_id=i.owner_id OR EXISTS (
   SELECT 1 FROM privacy_erasure_links l
   WHERE l.intent_id=i.intent_id AND l.resource_id=OLD.object_id
  ) THEN 'privacy:'||i.intent_id ELSE OLD.object_id END
)
BEGIN SELECT RAISE(ABORT,'audit update requires exact privacy redaction'); END;

DROP TRIGGER consent_events_no_delete;
CREATE TRIGGER consent_events_no_delete
BEFORE DELETE ON consent_events
WHEN NOT EXISTS (
 SELECT 1 FROM cleanup_intents i
 WHERE i.resource_kind='privacy_erasure' AND i.owner_id=OLD.account_id AND i.state='running'
)
BEGIN SELECT RAISE(ABORT,'consent events require authorized privacy erasure'); END;

DROP TRIGGER research_ratings_immutable_delete;
CREATE TRIGGER research_ratings_immutable_delete
BEFORE DELETE ON research_ratings
WHEN NOT EXISTS (
 SELECT 1 FROM rating_assignments a
 JOIN responses r ON r.response_id=a.response_id
 JOIN cleanup_intents i ON i.resource_kind='privacy_erasure'
  AND i.owner_id=r.owner_id AND i.state='running'
 WHERE a.assignment_id=OLD.assignment_id
)
BEGIN SELECT RAISE(ABORT,'research ratings require authorized privacy erasure'); END;
