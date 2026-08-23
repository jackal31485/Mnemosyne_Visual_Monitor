from typing import NamedTuple, Optional

class CollectiveContract(NamedTuple):
    id: int
    source_profile: str
    origin_memory_id: str
    proposed_at: Optional[str]
    validated_at: Optional[str]
    validator_profile: Optional[str]
    validation_score: Optional[float]
    lifecycle_state: str
