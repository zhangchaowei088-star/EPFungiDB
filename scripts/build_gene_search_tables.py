#!/usr/bin/env python3
"""Build gene/protein-level search tables for database use.

This complements build_ready_tables.py. The existing ready tables are
sample-level summaries; this script creates protein-level and annotation-level
tables needed for searching within a selected species/strain, such as finding
all genes in a KEGG pathway.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
READY = ROOT / "00_ready-for-database"
TABLES = READY / "tables"
CHECKS = READY / "checks"
MANIFESTS = READY / "manifests"

MASTER_INDEX = TABLES / "master_sample_index.tsv"

MISSING_VALUES = {"", "-", "NA", "N/A", "none", "None", "null"}
BUILD_GENERAL_LONG = False


class NullList:
    def append(self, _item: Any) -> None:
        return None

    def __iter__(self) -> Iterator[Any]:
        return iter(())

    def __len__(self) -> int:
        return 0


def rel(path: Optional[Path]) -> str:
    if not path:
        return ""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def open_tsv(path: Path) -> Iterator[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        yield from csv.DictReader(handle, delimiter="\t")


def write_tsv(path: Path, rows: Iterable[Dict[str, Any]], fields: List[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
            count += 1
    return count


def split_values(value: str) -> List[str]:
    if value in MISSING_VALUES:
        return []
    out: List[str] = []
    for item in re.split(r"[,;]", value):
        item = item.strip()
        if item and item not in MISSING_VALUES:
            out.append(item)
    return out


def normalize_kegg_id(value: str) -> str:
    return value.strip().replace("ko:", "")


def first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def fasta_ids_and_lengths(path: Path) -> Tuple[List[str], Dict[str, int]]:
    ids: List[str] = []
    lengths: Dict[str, int] = {}
    if not path.exists():
        return ids, lengths
    current_id = ""
    current_len = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_id:
                    lengths[current_id] = current_len
                current_id = line[1:].split()[0]
                ids.append(current_id)
                current_len = 0
            else:
                current_len += len(line)
        if current_id:
            lengths[current_id] = current_len
    return ids, lengths


def parse_signalp(path: Path, protein_order: List[str]) -> Dict[str, Dict[str, str]]:
    data: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return data
    idx = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            raw_protein_id = parts[0]
            protein_id = protein_order[idx] if idx < len(protein_order) else raw_protein_id
            idx += 1
            cs_position = parts[4]
            signalp_end = ""
            match = re.search(r"CS pos:\s*(\d+)-(\d+)", cs_position)
            if match:
                signalp_end = match.group(1)
            data[protein_id] = {
                "raw_protein_id": raw_protein_id,
                "prediction": parts[1],
                "other_score": parts[2],
                "sp_score": parts[3],
                "cs_position": cs_position,
                "signal_peptide_start": "1" if parts[1] == "SP" else "",
                "signal_peptide_end": signalp_end,
            }
    return data


def parse_effectorp(path: Path) -> Dict[str, Dict[str, str]]:
    data: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return data
    score_pattern = re.compile(r"\(([^)]+)\)")
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            scores = []
            for field in parts[1:4]:
                match = score_pattern.search(field)
                if match:
                    scores.append(match.group(1))
            data[parts[0]] = {
                "prediction": parts[4],
                "score": ";".join(scores),
            }
    return data


def parse_cazyme(path: Path) -> Dict[str, List[Dict[str, str]]]:
    data: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    if not path.exists():
        return data
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 10:
                continue
            data[parts[2]].append(
                {
                    "feature_id": parts[0],
                    "feature_label": parts[0],
                    "evalue": parts[4],
                    "score": "",
                    "start": parts[7],
                    "end": parts[8],
                    "coverage": parts[9],
                }
            )
    return data


def parse_merops(path: Path) -> Dict[str, List[Dict[str, str]]]:
    data: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    if not path.exists():
        return data
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 12:
                continue
            family = parts[12].split()[-1] if len(parts) > 12 and parts[12] else ""
            data[parts[0]].append(
                {
                    "feature_id": parts[1],
                    "feature_label": family,
                    "evalue": parts[10],
                    "score": parts[11],
                    "start": parts[6],
                    "end": parts[7],
                    "coverage": "",
                }
            )
    return data


def protein_uid(sample_id: str, protein_id: str) -> str:
    return f"{sample_id}|{protein_id}"


def sample_rows() -> List[Dict[str, str]]:
    rows = list(open_tsv(MASTER_INDEX))
    return sorted(rows, key=lambda row: row["sample_id"])


def annotation_row(
    sample: Dict[str, str],
    protein_id: str,
    source_key: str,
    annotation_type: str,
    annotation_id: str,
    annotation_label: str = "",
    description: str = "",
    evalue: str = "",
    score: str = "",
    evidence_strength: str = "general",
) -> Dict[str, str]:
    return {
        "protein_uid": protein_uid(sample["sample_id"], protein_id),
        "sample_id": sample["sample_id"],
        "full_name": sample["full_name"],
        "protein_id": protein_id,
        "source_key": source_key,
        "annotation_category": "general_functional_annotation",
        "annotation_type": annotation_type,
        "annotation_id": annotation_id,
        "annotation_label": annotation_label,
        "description": description,
        "evalue": evalue,
        "score": score,
        "evidence_strength": evidence_strength,
    }


def iter_sample_tables(
    sample: Dict[str, str],
    counters: Counter,
    missing_rows: List[Dict[str, str]],
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    sample_id = sample["sample_id"]
    full_name = sample["full_name"]
    file_prefix = sample["file_prefix"]
    general_path = ROOT / sample["genome_dir"] / "annotate" / "merged_functional_annotation.tsv"
    protein_fasta = ROOT / sample["protein_fasta_path"] if sample["protein_fasta_path"] else Path("")

    if not general_path.exists():
        missing_rows.append(
            {
                "sample_id": sample_id,
                "full_name": full_name,
                "missing_table": "merged_functional_annotation.tsv",
                "expected_path": rel(general_path),
                "note": "Required for protein-level general annotation tables",
            }
        )
        return [], [], [], [], [], []

    protein_order, lengths = (
        fasta_ids_and_lengths(protein_fasta) if protein_fasta.exists() else ([], {})
    )
    signalp = (
        parse_signalp(ROOT / sample["signalp_prediction_path"], protein_order)
        if sample["signalp_prediction_path"]
        else {}
    )
    effectorp_path = first_existing(
        [
            ROOT / "02_annotation-protein-data" / "03_Effector" / f"{full_name}.effectorp.tsv",
            ROOT / "02_annotation-protein-data" / "03_Effector" / f"{file_prefix}.effectorp.tsv",
        ]
    )
    cazyme_path = first_existing(
        [
            ROOT / "02_annotation-protein-data" / "04_CAZ" / f"{full_name}.dbcan.tsv",
            ROOT / "02_annotation-protein-data" / "04_CAZ" / f"{file_prefix}.dbcan.tsv",
        ]
    )
    merops_path = first_existing(
        [
            ROOT / "02_annotation-protein-data" / "05_MEROP" / f"{full_name}.merops.tsv",
            ROOT / "02_annotation-protein-data" / "05_MEROP" / f"{file_prefix}.merops.tsv",
        ]
    )
    effectorp = parse_effectorp(effectorp_path) if effectorp_path else {}
    cazyme = parse_cazyme(cazyme_path) if cazyme_path else {}
    merops = parse_merops(merops_path) if merops_path else {}

    proteins: List[Dict[str, Any]] = []
    general_summaries: List[Dict[str, Any]] = []
    general_long: Any = [] if BUILD_GENERAL_LONG else NullList()
    kegg_members: List[Dict[str, Any]] = []
    patho_summaries: List[Dict[str, Any]] = []
    patho_features: List[Dict[str, Any]] = []

    for row in open_tsv(general_path):
        protein_id = row.get("protein_id") or row.get("transcript_id")
        if not protein_id:
            continue
        gene_id = row.get("gene_id", "")
        uid = protein_uid(sample_id, protein_id)
        ko_ids = [normalize_kegg_id(v) for v in split_values(row.get("eggnog_KEGG_ko", ""))]
        pathway_ids = [normalize_kegg_id(v) for v in split_values(row.get("eggnog_KEGG_Pathway", ""))]
        go_terms = split_values(row.get("eggnog_GOs", ""))
        ec_numbers = split_values(row.get("eggnog_EC", ""))
        modules = [normalize_kegg_id(v) for v in split_values(row.get("eggnog_KEGG_Module", ""))]
        reactions = [normalize_kegg_id(v) for v in split_values(row.get("eggnog_KEGG_Reaction", ""))]
        brite_terms = [normalize_kegg_id(v) for v in split_values(row.get("eggnog_BRITE", ""))]
        pfams = split_values(row.get("eggnog_PFAMs", ""))
        fun_pfams = split_values(row.get("funannotate_pfam", ""))
        cazy_families = sorted({hit["feature_id"] for hit in cazyme.get(protein_id, [])})
        merops_families = sorted(
            {hit["feature_label"] or hit["feature_id"] for hit in merops.get(protein_id, [])}
        )
        signalp_info = signalp.get(protein_id, {})
        effectorp_info = effectorp.get(protein_id, {})

        proteins.append(
            {
                "protein_uid": uid,
                "sample_id": sample_id,
                "full_name": full_name,
                "gene_id": gene_id,
                "transcript_id": row.get("transcript_id", ""),
                "protein_id": protein_id,
                "seqid": row.get("seqid", ""),
                "start": row.get("start", ""),
                "end": row.get("end", ""),
                "strand": row.get("strand", ""),
                "protein_length": lengths.get(protein_id, ""),
                "product": row.get("funannotate_product", ""),
                "has_general_functional_annotation": row.get(
                    "has_any_functional_annotation", ""
                ),
                "has_pathogenicity_associated_feature": 1
                if signalp_info.get("prediction") == "SP"
                or effectorp_info.get("prediction", "") not in ("", "Non-effector")
                or protein_id in cazyme
                or protein_id in merops
                else 0,
            }
        )

        general_summaries.append(
            {
                "protein_uid": uid,
                "sample_id": sample_id,
                "full_name": full_name,
                "gene_id": gene_id,
                "protein_id": protein_id,
                "funannotate_product": row.get("funannotate_product", ""),
                "funannotate_dbxref": row.get("funannotate_dbxref", ""),
                "funannotate_note": row.get("funannotate_note", ""),
                "eggnog_seed_ortholog": row.get("eggnog_seed_ortholog", ""),
                "eggnog_evalue": row.get("eggnog_evalue", ""),
                "eggnog_score": row.get("eggnog_score", ""),
                "eggnog_cog_category": row.get("eggnog_COG_category", ""),
                "eggnog_description": row.get("eggnog_Description", ""),
                "eggnog_preferred_name": row.get("eggnog_Preferred_name", ""),
                "go_terms": ",".join(go_terms),
                "ec_numbers": ",".join(ec_numbers),
                "kegg_ko": ",".join(ko_ids),
                "kegg_pathways": ",".join(pathway_ids),
                "kegg_modules": ",".join(modules),
                "kegg_reactions": ",".join(reactions),
                "brite_terms": ",".join(brite_terms),
                "pfam_domains": ",".join(sorted(set(pfams + fun_pfams))),
            }
        )

        if row.get("funannotate_product", "") not in MISSING_VALUES:
            general_long.append(
                annotation_row(
                    sample,
                    protein_id,
                    "funannotate_annotate",
                    "product",
                    row.get("funannotate_product", ""),
                    description=row.get("funannotate_product", ""),
                )
            )
        for go_term in go_terms:
            general_long.append(
                annotation_row(sample, protein_id, "eggnog_kegg", "GO", go_term)
            )
        for ec in ec_numbers:
            general_long.append(
                annotation_row(sample, protein_id, "eggnog_kegg", "EC", ec)
            )
        for ko in ko_ids:
            general_long.append(
                annotation_row(
                    sample,
                    protein_id,
                    "eggnog_kegg",
                    "KEGG_KO",
                    ko,
                    annotation_label=row.get("eggnog_Preferred_name", ""),
                    description=row.get("eggnog_Description", ""),
                    evalue=row.get("eggnog_evalue", ""),
                    score=row.get("eggnog_score", ""),
                )
            )
        for pathway in pathway_ids:
            general_long.append(
                annotation_row(
                    sample,
                    protein_id,
                    "eggnog_kegg",
                    "KEGG_Pathway",
                    pathway,
                    annotation_label=row.get("eggnog_Preferred_name", ""),
                    description=row.get("eggnog_Description", ""),
                    evalue=row.get("eggnog_evalue", ""),
                    score=row.get("eggnog_score", ""),
                )
            )
            kegg_members.append(
                {
                    "sample_id": sample_id,
                    "full_name": full_name,
                    "kegg_pathway_id": pathway,
                    "protein_uid": uid,
                    "protein_id": protein_id,
                    "gene_id": gene_id,
                    "seqid": row.get("seqid", ""),
                    "start": row.get("start", ""),
                    "end": row.get("end", ""),
                    "strand": row.get("strand", ""),
                    "kegg_ko": ",".join(ko_ids),
                    "preferred_name": row.get("eggnog_Preferred_name", ""),
                    "description": row.get("eggnog_Description", ""),
                    "evalue": row.get("eggnog_evalue", ""),
                    "score": row.get("eggnog_score", ""),
                }
            )
        for module in modules:
            general_long.append(
                annotation_row(sample, protein_id, "eggnog_kegg", "KEGG_Module", module)
            )
        for reaction in reactions:
            general_long.append(
                annotation_row(sample, protein_id, "eggnog_kegg", "KEGG_Reaction", reaction)
            )
        for brite in brite_terms:
            general_long.append(
                annotation_row(sample, protein_id, "eggnog_kegg", "KEGG_BRITE", brite)
            )
        for pfam in sorted(set(pfams + fun_pfams)):
            general_long.append(
                annotation_row(sample, protein_id, "funannotate_annotate", "PFAM", pfam)
            )

        is_secreted = 1 if signalp_info.get("prediction") == "SP" else 0
        is_effector = 1 if effectorp_info.get("prediction", "") not in ("", "Non-effector") else 0
        patho_summaries.append(
            {
                "protein_uid": uid,
                "sample_id": sample_id,
                "full_name": full_name,
                "gene_id": gene_id,
                "protein_id": protein_id,
                "is_secreted": is_secreted,
                "signalp_prediction": signalp_info.get("prediction", ""),
                "signalp_sp_score": signalp_info.get("sp_score", ""),
                "signalp_cs_position": signalp_info.get("cs_position", ""),
                "is_effector_candidate": is_effector,
                "effectorp_prediction": effectorp_info.get("prediction", ""),
                "effectorp_score": effectorp_info.get("score", ""),
                "has_cazyme": 1 if cazy_families else 0,
                "cazyme_families": ",".join(cazy_families),
                "has_merops": 1 if merops_families else 0,
                "merops_families": ",".join(merops_families),
                "pathogenicity_feature_count": is_secreted
                + is_effector
                + len(cazy_families)
                + len(merops_families),
            }
        )

        if is_secreted:
            patho_features.append(
                {
                    "protein_uid": uid,
                    "sample_id": sample_id,
                    "full_name": full_name,
                    "protein_id": protein_id,
                    "feature_type": "secreted_signal_peptide",
                    "source_key": "signalp6",
                    "feature_id": "SP",
                    "feature_label": "signal peptide",
                    "prediction": signalp_info.get("prediction", ""),
                    "score": signalp_info.get("sp_score", ""),
                    "start": signalp_info.get("signal_peptide_start", ""),
                    "end": signalp_info.get("signal_peptide_end", ""),
                    "evalue": "",
                    "coverage": "",
                    "evidence_strength": "associated",
                    "notes": signalp_info.get("cs_position", ""),
                }
            )
        if is_effector:
            patho_features.append(
                {
                    "protein_uid": uid,
                    "sample_id": sample_id,
                    "full_name": full_name,
                    "protein_id": protein_id,
                    "feature_type": "effector_candidate",
                    "source_key": "effectorp",
                    "feature_id": effectorp_info.get("prediction", ""),
                    "feature_label": effectorp_info.get("prediction", ""),
                    "prediction": effectorp_info.get("prediction", ""),
                    "score": effectorp_info.get("score", ""),
                    "start": "",
                    "end": "",
                    "evalue": "",
                    "coverage": "",
                    "evidence_strength": "candidate",
                    "notes": "",
                }
            )
        for hit in cazyme.get(protein_id, []):
            patho_features.append(
                {
                    "protein_uid": uid,
                    "sample_id": sample_id,
                    "full_name": full_name,
                    "protein_id": protein_id,
                    "feature_type": "carbohydrate_active_enzyme",
                    "source_key": "dbcan_cazyme",
                    "prediction": "",
                    "evidence_strength": "associated",
                    "notes": "",
                    **hit,
                }
            )
        for hit in merops.get(protein_id, []):
            patho_features.append(
                {
                    "protein_uid": uid,
                    "sample_id": sample_id,
                    "full_name": full_name,
                    "protein_id": protein_id,
                    "feature_type": "protease",
                    "source_key": "merops",
                    "prediction": "",
                    "evidence_strength": "associated",
                    "notes": "",
                    **hit,
                }
            )

    counters["samples_processed"] += 1
    counters["proteins"] += len(proteins)
    counters["protein_general_annotation_summary"] += len(general_summaries)
    counters["protein_general_annotations"] += len(general_long)
    counters["kegg_pathway_members"] += len(kegg_members)
    counters["protein_pathogenicity_summary"] += len(patho_summaries)
    counters["protein_pathogenicity_features"] += len(patho_features)
    return proteins, general_summaries, general_long, kegg_members, patho_summaries, patho_features


def main() -> None:
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    counters: Counter = Counter()
    missing_rows: List[Dict[str, str]] = []

    protein_fields = [
        "protein_uid",
        "sample_id",
        "full_name",
        "gene_id",
        "transcript_id",
        "protein_id",
        "seqid",
        "start",
        "end",
        "strand",
        "protein_length",
        "product",
        "has_general_functional_annotation",
        "has_pathogenicity_associated_feature",
    ]
    general_summary_fields = [
        "protein_uid",
        "sample_id",
        "full_name",
        "gene_id",
        "protein_id",
        "funannotate_product",
        "funannotate_dbxref",
        "funannotate_note",
        "eggnog_seed_ortholog",
        "eggnog_evalue",
        "eggnog_score",
        "eggnog_cog_category",
        "eggnog_description",
        "eggnog_preferred_name",
        "go_terms",
        "ec_numbers",
        "kegg_ko",
        "kegg_pathways",
        "kegg_modules",
        "kegg_reactions",
        "brite_terms",
        "pfam_domains",
    ]
    general_long_fields = [
        "protein_uid",
        "sample_id",
        "full_name",
        "protein_id",
        "source_key",
        "annotation_category",
        "annotation_type",
        "annotation_id",
        "annotation_label",
        "description",
        "evalue",
        "score",
        "evidence_strength",
    ]
    kegg_fields = [
        "sample_id",
        "full_name",
        "kegg_pathway_id",
        "protein_uid",
        "protein_id",
        "gene_id",
        "seqid",
        "start",
        "end",
        "strand",
        "kegg_ko",
        "preferred_name",
        "description",
        "evalue",
        "score",
    ]
    patho_summary_fields = [
        "protein_uid",
        "sample_id",
        "full_name",
        "gene_id",
        "protein_id",
        "is_secreted",
        "signalp_prediction",
        "signalp_sp_score",
        "signalp_cs_position",
        "is_effector_candidate",
        "effectorp_prediction",
        "effectorp_score",
        "has_cazyme",
        "cazyme_families",
        "has_merops",
        "merops_families",
        "pathogenicity_feature_count",
    ]
    patho_feature_fields = [
        "protein_uid",
        "sample_id",
        "full_name",
        "protein_id",
        "feature_type",
        "source_key",
        "feature_id",
        "feature_label",
        "prediction",
        "score",
        "start",
        "end",
        "evalue",
        "coverage",
        "evidence_strength",
        "notes",
    ]

    outputs = {
        "proteins": (TABLES / "proteins.tsv", protein_fields),
        "protein_general_annotation_summary": (
            TABLES / "protein_general_annotation_summary.tsv",
            general_summary_fields,
        ),
        "kegg_pathway_members": (TABLES / "kegg_pathway_members.tsv", kegg_fields),
        "protein_pathogenicity_summary": (
            TABLES / "protein_pathogenicity_summary.tsv",
            patho_summary_fields,
        ),
        "protein_pathogenicity_features": (
            TABLES / "protein_pathogenicity_features.tsv",
            patho_feature_fields,
        ),
    }
    if BUILD_GENERAL_LONG:
        outputs["protein_general_annotations"] = (
            TABLES / "protein_general_annotations.tsv",
            general_long_fields,
        )

    handles = {}
    writers = {}
    try:
        for key, (path, fields) in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("w", newline="", encoding="utf-8")
            handles[key] = handle
            writer = csv.DictWriter(
                handle, fieldnames=fields, delimiter="\t", extrasaction="ignore"
            )
            writer.writeheader()
            writers[key] = writer

        for sample in sample_rows():
            (
                proteins,
                general_summaries,
                general_long,
                kegg_members,
                patho_summaries,
                patho_features,
            ) = iter_sample_tables(sample, counters, missing_rows)
            for row in proteins:
                writers["proteins"].writerow(row)
            for row in general_summaries:
                writers["protein_general_annotation_summary"].writerow(row)
            if BUILD_GENERAL_LONG:
                for row in general_long:
                    writers["protein_general_annotations"].writerow(row)
            for row in kegg_members:
                writers["kegg_pathway_members"].writerow(row)
            for row in patho_summaries:
                writers["protein_pathogenicity_summary"].writerow(row)
            for row in patho_features:
                writers["protein_pathogenicity_features"].writerow(row)
    finally:
        for handle in handles.values():
            handle.close()

    write_tsv(
        CHECKS / "missing_gene_search_sources.tsv",
        missing_rows,
        ["sample_id", "full_name", "missing_table", "expected_path", "note"],
    )

    manifest_path = MANIFESTS / "gene_search_manifest.json"
    payload = {
        "generated_at": generated_at,
        "project_root": str(ROOT),
        "primary_keys": {
            "protein": "protein_uid",
            "sample": "sample_id",
        },
        "status_counts": dict(counters),
        "tables": {key: rel(path) for key, (path, _fields) in outputs.items()},
        "checks": {
            "missing_gene_search_sources": rel(
                CHECKS / "missing_gene_search_sources.tsv"
            )
        },
        "query_examples": {
            "species_kegg_pathway": "filter kegg_pathway_members.tsv by sample_id and kegg_pathway_id",
            "secreted_effectors": "filter protein_pathogenicity_summary.tsv by sample_id, is_secreted=1, is_effector_candidate=1",
        },
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    print(json.dumps(payload["status_counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
