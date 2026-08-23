#!/usr/bin/env python
# Collective aggregator over DAOs.

from __future__ import annotations
from typing import List

from .collective import CollectiveDAO
from .collective_contract import CollectiveContract

class CollectiveAggregator:
    def __init__(self, daos: List[CollectiveDAO]):
        self.daos = daos

    def list_all_promoted(self) -> List[CollectiveContract]:
        aggregates: List[CollectiveContract] = []
        for dao in self.daos:
            promoted_ids = dao.list_promoted()
            for pid in promoted_ids:
                lc_state = dao.get_lifecycle_state(pid)
                if lc_state is None or lc_state[1]:  # revoked
                    continue
                record = dao.get_by_id(pid)
                if not record:
                    continue
                (
                    entry_id,
                    source_profile,
                    origin_memory_id,
                    proposed_at,
                    validated_at,
                    validation_score,
                    validator_profile,
                    *_,
                ) = record
                aggregates.append(
                    CollectiveContract(
                        id=int(entry_id),
                        source_profile=source_profile,
                        origin_memory_id=origin_memory_id,
                        proposed_at=proposed_at,
                        validated_at=validated_at,
                        validator_profile=validator_profile,
                        validation_score=float(validation_score) if validation_score is not None else None,
                        lifecycle_state="promoted",
                    )
                )
        return aggregates

    def get_by_source_across_profiles(self, src: str, orig_mem: str):
        for dao in self.daos:
            rec = dao.get_by_source(src, orig_mem)
            if rec is not None:
                return rec
        raise KeyError(f"No collective entry matching {src}/{orig_mem}")
