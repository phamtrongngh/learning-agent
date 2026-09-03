SCHEMA_VERSION = 1
MASTERY_LEVELS = {"unobserved": 0, "assisted": 1, "independent": 2, "transfer": 3}
EVIDENCE_TYPES = {"explanation", "practical", "test", "debugging", "transfer"}
EVENT_TYPES = EVIDENCE_TYPES | {"disposition", "environment"}
EVENT_OUTCOMES = {"accepted", "inconclusive", "rejected"}
AUTHORS = {"learner", "agent", "collaborative"}
LESSON_STATES = {"locked", "available", "active", "remediation", "passed", "skipped", "waived"}
COURSE_FILES = {
    "course": "course.json",
    "curriculum": "curriculum.json",
    "progress": "progress.json",
    "evidence": "evidence.jsonl",
    "sources": "sources.json",
}
