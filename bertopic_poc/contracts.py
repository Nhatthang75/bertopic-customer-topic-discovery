from __future__ import annotations
import csv
import io
import math

BASE = {"schema_version": "str", "experiment_id": "str", "run_id": "str"}
FIELDS = {
 "segments": {"segment_id":"str", "conversation_id":"str", "source_split":"str", "evidence_unit_id":"str", "customer_turn_index":"int", "span_start":"int", "span_end":"int", "masked_customer_text":"str", "content_status":"str", "preprocessing_version":"str"},
 "run_manifest": {"config_hash":"str", "source_hashes":"dict", "model_revisions":"dict", "split_manifest_hash":"str", "taxonomy_version":"str", "mapping_version":"str", "preprocessing_version":"str", "seed":"int", "fit_scopes":"list", "search_registry_hash":"str", "gate_events":"list", "artifact_hashes":"dict", "benchmark_validity":"str", "resource_usage":"dict"},
 "data_quality": {"counts":"dict", "reason_counts":"dict", "unresolved_counts":"dict", "metadata_availability":"dict", "alignment_ablation_failures":"int"},
 "assignments": {"evidence_unit_id":"str", "topic_id":"str", "source":"str", "conversation_id":"str", "segment_ids":"list", "score":"number?", "score_type":"str", "assignment_status":"str", "evidence_spans":"list", "evidence_status":"str", "cluster_key":"str?"},
 "conversation_topics": {"conversation_id":"str", "topic_id":"str", "source":"str", "evidence_basis":"str", "primary_topic":"bool", "max_score":"number?", "evidence_count":"int?", "taxonomy_version":"str"},
 "topic_statistics": {"scope_id":"str", "topic_id":"str", "source":"str", "evidence_basis":"str", "customer_message_count":"int", "source_messages_with_assignment":"int", "segment_count":"int", "mention_count":"int?", "conversation_count":"int", "eligible_conversations":"int", "conversation_share":"number?", "evidence_coverage":"number", "unique_customers":"int?", "time_bucket":"str?", "channel":"str?", "null_reason":"str?"},
 "candidates": {"cluster_key":"str", "seed":"int", "local_cluster_id":"int", "keywords":"list", "representative_unit_ids":"list", "random_unit_ids":"list", "conversation_support":"int", "label":"str?", "description":"str?", "status":"str", "review_version":"int"},
 "reviews": {"cluster_key":"str", "review_version":"int", "reviewer_ids":"list", "rubric_scores":"dict", "sample_ids":"list", "per_sample_judgements":"list", "adjudication":"dict?", "target_id":"str?", "reason":"str", "reviewed_at":"str"},
 "metrics": {"metric_name":"str", "cohort_id":"str", "level":"str", "seed":"int", "evaluation_stage":"str", "value":"number?", "support":"int", "denominator":"int?", "grain":"str", "CI":"list?", "null_reason":"str?", "experiment_mode":"str", "ground_truth_type":"str"}
}
KEYS = {"segments":["segment_id"], "run_manifest":[], "data_quality":[],
 "assignments":["evidence_unit_id","topic_id","source"],
 "conversation_topics":["conversation_id","topic_id","source","evidence_basis"],
 "topic_statistics":["scope_id","topic_id","source","evidence_basis"], "candidates":["cluster_key"],
 "reviews":["cluster_key","review_version"], "metrics":["metric_name","cohort_id","level","seed","evaluation_stage"]}
ENUMS = {"source_split":{"train","dev","test"}, "content_status":{"non_need","insufficient_evidence","analyzable"}, "evidence_status":{"model_supported","human_verified","cluster_only"}, "source":{"fixed","discovery"}, "evidence_basis":{"predicted","verified","cluster_membership"}, "experiment_mode":{"inductive","batch_transductive"}, "ground_truth_type":{"scenario_proxy","manual_gold","review_sample"}}


class SchemaError(ValueError):
    pass


def validate(kind, row):
    fields = BASE | FIELDS[kind]
    if set(fields) - set(row) or row.get("schema_version") != "1.0.0":
        raise SchemaError("schema_error:missing_fields_or_version")
    for key, expected in fields.items():
        value = row[key]
        if value is None and expected.endswith("?"):
            continue
        expected = expected.rstrip("?")
        ok = {"str":lambda: isinstance(value,str) and bool(value), "int":lambda:type(value) is int and value>=0,
              "number":lambda:type(value) in (int,float) and math.isfinite(value), "bool":lambda:type(value) is bool,
              "dict":lambda:isinstance(value,dict), "list":lambda:isinstance(value,list)}[expected]()
        if not ok or (key in ENUMS and value not in ENUMS[key]):
            raise SchemaError("schema_error:type_or_enum:"+key)
        if key in {"conversation_share","evidence_coverage"} and not 0<=value<=1:
            raise SchemaError("schema_error:ratio")
    if kind == "segments" and row["span_end"] <= row["span_start"]:
        raise SchemaError("schema_error:offsets")
    if kind == "metrics" and row["value"] is None and not row["null_reason"]:
        raise SchemaError("schema_error:null_reason")
    if kind == "data_quality":
        c=row["counts"]
        if set(c)<={"read","quarantine","excluded","eligible"} and len(c)<4:
            raise SchemaError("schema_error:quality_counts")
        if any(type(c.get(k)) is not int or c[k]<0 for k in ("read","quarantine","excluded","eligible")):
            raise SchemaError("schema_error:quality_counts")
        if c["read"] != c["quarantine"]+c["excluded"]+c["eligible"]:
            raise SchemaError("schema_error:quality_conservation")


def validate_rows(kind, rows, *, references=None):
    seen=set()
    for row in rows:
        validate(kind,row)
        key=tuple(row[k] for k in ["experiment_id","run_id"]+KEYS[kind])
        if key in seen:
            raise SchemaError("schema_error:duplicate_key")
        seen.add(key)
        for field, allowed in (references or {}).items():
            vals=row[field] if isinstance(row[field],list) else [row[field]]
            if any(v is not None and v not in allowed for v in vals):
                raise SchemaError("schema_error:foreign_key")


def csv_dump(rows, fields):
    stream=io.StringIO(newline="")
    writer=csv.DictWriter(stream,fieldnames=fields,lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        if any(v=="\\N" for v in row.values()):
            raise SchemaError("reserved_value")
        writer.writerow({k:"\\N" if row[k] is None else row[k] for k in fields})
    return stream.getvalue()


def csv_load(text):
    return [{k:None if v=="\\N" else v for k,v in row.items()} for row in csv.DictReader(io.StringIO(text,newline=""))]
