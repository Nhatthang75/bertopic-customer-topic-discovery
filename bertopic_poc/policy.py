from __future__ import annotations
from dataclasses import dataclass, field
from .io import canonical_hash

FEATURE_FIELDS = frozenset({"conversation_id", "source_split", "segment_id", "evidence_unit_id",
    "customer_turn_index", "span_start", "span_end", "masked_customer_text", "context_turn_indices",
    "context_text", "language", "preprocessing_version"})


class LeakageError(ValueError):
    pass


def model_text(feature: dict) -> str:
    if set(feature) - FEATURE_FIELDS or not isinstance(feature.get("masked_customer_text"), str):
        raise LeakageError("feature_contract_violation")
    if feature.get("context_text") not in (None, ""):
        raise LeakageError("advanced_context_not_registered")
    return feature["masked_customer_text"]


@dataclass
class AccessPolicy:
    gate: int = 0
    valid: bool = True
    events: list = field(default_factory=list)
    snapshots: dict = field(default_factory=dict)

    def deny(self, reason):
        self.valid = False
        self.events.append({"decision": "denied", "reason": reason})
        raise LeakageError(reason)

    def authorize(self, role, resource, purpose, *, blinded=True):
        if not self.valid:
            raise LeakageError("run_invalid")
        if role == "inference" and resource not in {"features", "taxonomy_k", "registry_public"}:
            self.deny("inference_resource_denied")
        if role == "custodian" and resource == "sealed_labels" and purpose != "membership_only":
            self.deny("custodian_purpose_denied")
        if resource == "sealed_labels" and not (role == "custodian" and purpose == "membership_only"):
            if not (role == "evaluator" and self.gate >= 3 and purpose == "scoring"):
                self.deny("early_label_release")
        if resource == "taxonomy_full" and self.gate < 2 and role != "custodian":
            self.deny("early_hidden_taxonomy")
        if role == "reviewer" and not blinded:
            self.deny("reviewer_not_blinded")
        permitted = {"inference", "custodian", "evaluator", "reviewer", "operator"}
        if role not in permitted or resource not in {"features", "taxonomy_k", "registry_public", "sealed_labels", "taxonomy_full"}:
            self.deny("unknown_access_request")
        self.events.append({"decision": "allowed", "role": role, "resource": resource, "purpose": purpose})

    def lock(self, name, value):
        digest = canonical_hash(value)
        if name in self.snapshots:
            self.deny("snapshot_already_locked")
        self.snapshots[name] = digest
        return digest

    def check(self, name, value):
        if self.snapshots.get(name) != canonical_hash(value):
            self.deny("locked_snapshot_mutation")

    def advance(self, gate, *, evidence_complete=False):
        if gate != self.gate + 1 or not evidence_complete:
            self.deny("gate_prerequisites_missing")
        self.gate = gate
