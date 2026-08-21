from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List

class ProposalState(Enum):
    PROPOSED = "PROPOSED"
    PRIVACY_FILTERING = "PRIVACY_FILTERING"
    VALIDATING = "VALIDATING"
    REJECTED = "REJECTED"
    READY_FOR_PROMOTION = "READY_FOR_PROMOTION"
    MANUAL_REVIEW = "MANUAL_REVIEW"

@dataclass
class SourceReference:
    profile: str
    memory_id: str

@dataclass
class PrivacyResult:
    masked_fields: List[str]
    sanitized_content: Optional[str] = None

@dataclass
class ValidationOutcome:
    source_profile: str
    source_record_reference: SourceReference
    validation_score: float
    is_validated: bool
    reason_for_rejection: Optional[str] = None

# Proposal data class; only contains fields needed for tests and documentation
@dataclass
class Proposal:
    source_profile: str
    source_memory_id: str
    proposed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: ProposalState = ProposalState.PROPOSED
    provenance: Optional[dict] = None
    validation_history: List[str] = field(default_factory=list)
    # reference to the original memory for gateway lookup
    source_reference: SourceReference = field(init=False)
    # transient fields
    validation_representation: Optional[dict] = None
    privacy_filter_result: Optional[PrivacyResult] = None

    def __post_init__(self):
        self.source_reference = SourceReference(self.source_profile, self.source_memory_id)
