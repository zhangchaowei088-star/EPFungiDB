#!/usr/bin/env python3
"""Build database-ready inventory tables for the fungi database project.

The script is intentionally read-only for upstream analysis directories. It
rebuilds files under 00_ready-for-database from the current project state.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
READY = ROOT / "00_ready-for-database"
TABLES = READY / "tables"
CHECKS = READY / "checks"
MANIFESTS = READY / "manifests"


GENOME_STATS = ROOT / "genome_stats_2026-05-12.csv"
ABBR_MAP = ROOT / "strain_abbreviation_map.csv"
FUNCTIONAL_SUMMARY = (
    ROOT
    / "02_annotation-protein-data"
    / "merged_functional_annotation_summary_20260703.tsv"
)
FUNCTIONAL_COVERAGE = (
    ROOT
    / "02_annotation-protein-data"
    / "annotation_coverage_normalized_summary_20260703.tsv"
)
ANTISMASH_QC = (
    ROOT / "04_antismash-bigscape" / "09_antismash_family_qc" / "genome_qc.tsv"
)


def rel(path: Optional[Path]) -> str:
    if not path:
        return ""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def rel_if_exists(path: Path) -> str:
    return rel(path) if path.exists() else ""


def exists_i(path: Path) -> int:
    return 1 if path.exists() else 0


def first_existing(candidates: Iterable[Path]) -> Path:
    candidates = list(candidates)
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def canonical_sample_name(name: str) -> str:
    """Normalize known punctuation-only source naming differences."""
    return name.replace(",_", "_").replace(",", "")


def read_delimited(path: Path, delimiter: str) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_tsv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def normalize_float(value: str) -> str:
    if value in ("", None):
        return ""
    try:
        return str(float(value))
    except (TypeError, ValueError):
        return str(value)


def split_taxonomy(full_name: str) -> Dict[str, str]:
    parts = full_name.split("_")
    genus = parts[0] if parts else ""
    species_epithet = parts[1] if len(parts) > 1 else ""
    species_binomial = "_".join(parts[:2]) if len(parts) >= 2 else full_name
    strain = "_".join(parts[2:]) if len(parts) > 2 else ""
    return {
        "genus_from_name": genus,
        "species_epithet_from_name": species_epithet,
        "species_binomial_from_name": species_binomial,
        "strain_from_name": strain,
    }


def safe_int(value: Any) -> str:
    if value in ("", None):
        return ""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value)


def get_file_info(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {"exists": "0", "size_bytes": "", "mtime": ""}
    stat = path.stat()
    return {
        "exists": "1",
        "size_bytes": str(stat.st_size),
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def scan_busco_dirs() -> Tuple[Dict[str, List[Path]], List[Dict[str, Any]]]:
    busco_by_name: Dict[str, List[Path]] = defaultdict(list)
    rows: List[Dict[str, Any]] = []
    root = ROOT / "03_busco"
    if not root.exists():
        return busco_by_name, rows

    for group_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for sample_dir in sorted(p for p in group_dir.iterdir() if p.is_dir()):
            full_name = sample_dir.name
            busco_by_name[canonical_sample_name(full_name)].append(sample_dir)
            summary_json = sample_dir / "run_hypocreales_odb12" / "short_summary.json"
            top_summaries = sorted(sample_dir.glob("short_summary.specific.*.txt"))
            top_summary = top_summaries[0] if top_summaries else None
            row: Dict[str, Any] = {
                "source_group": group_dir.name,
                "full_name": full_name,
                "busco_dir": rel(sample_dir),
                "summary_json_path": rel_if_exists(summary_json),
                "summary_txt_path": rel_if_exists(top_summary) if top_summary else "",
                "has_summary_json": exists_i(summary_json),
                "has_summary_txt": 1 if top_summary else 0,
            }
            if summary_json.exists():
                try:
                    payload = json.loads(summary_json.read_text(encoding="utf-8"))
                    results = payload.get("results", {})
                    lineage = payload.get("lineage_dataset", {})
                    versions = payload.get("versions", {})
                    row.update(
                        {
                            "lineage": lineage.get("name", ""),
                            "busco_version": versions.get("busco", ""),
                            "complete_pct": results.get("Complete percentage", ""),
                            "complete_buscos": results.get("Complete BUSCOs", ""),
                            "single_copy_pct": results.get(
                                "Single copy percentage", ""
                            ),
                            "single_copy_buscos": results.get(
                                "Single copy BUSCOs", ""
                            ),
                            "duplicated_pct": results.get("Multi copy percentage", ""),
                            "duplicated_buscos": results.get("Multi copy BUSCOs", ""),
                            "fragmented_pct": results.get(
                                "Fragmented percentage", ""
                            ),
                            "fragmented_buscos": results.get("Fragmented BUSCOs", ""),
                            "missing_pct": results.get("Missing percentage", ""),
                            "missing_buscos": results.get("Missing BUSCOs", ""),
                            "n_markers": results.get("n_markers", ""),
                            "avg_identity": results.get("avg_identity", ""),
                            "internal_stop_codon_pct": results.get(
                                "internal_stop_codon_percent", ""
                            ),
                            "one_line_summary": results.get("one_line_summary", ""),
                        }
                    )
                except json.JSONDecodeError:
                    row["parse_error"] = "invalid_json"
            rows.append(row)
    return busco_by_name, rows


def parse_signalp_result(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "signalp_total_proteins": "",
        "signalp_sp_count": "",
        "signalp_other_count": "",
        "signalp_sp_fraction": "",
        "signalp_high_confidence_sp_count": "",
    }
    if not path.exists():
        return out
    total = 0
    sp_count = 0
    other_count = 0
    high_confidence = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            total += 1
            prediction = parts[1]
            if prediction == "SP":
                sp_count += 1
                try:
                    if float(parts[3]) >= 0.9:
                        high_confidence += 1
                except ValueError:
                    pass
            elif prediction == "OTHER":
                other_count += 1
    out.update(
        {
            "signalp_total_proteins": total,
            "signalp_sp_count": sp_count,
            "signalp_other_count": other_count,
            "signalp_sp_fraction": round(sp_count / total, 6) if total else "",
            "signalp_high_confidence_sp_count": high_confidence,
        }
    )
    return out


def count_fasta_records(path: Path) -> Any:
    if not path.exists():
        return ""
    count = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                count += 1
    return count


def count_non_comment_rows(path: Path) -> Any:
    if not path.exists():
        return ""
    count = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip() and not line.startswith("#"):
                count += 1
    return count


def count_unique_column(path: Path, column_index: int) -> Any:
    if not path.exists():
        return ""
    values = set()
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) > column_index and parts[column_index]:
                values.add(parts[column_index])
    return len(values)


def parse_effectorp_result(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "effectorp_total_proteins": "",
        "effector_candidate_count": "",
        "cytoplasmic_effector_count": "",
        "apoplastic_effector_count": "",
        "dual_localization_effector_count": "",
        "non_effector_count": "",
        "effector_candidate_fraction": "",
    }
    if not path.exists():
        return out
    total = 0
    cytoplasmic = 0
    apoplastic = 0
    dual_localization = 0
    non_effector = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            total += 1
            prediction = parts[4]
            if prediction == "Cytoplasmic effector":
                cytoplasmic += 1
            elif prediction == "Apoplastic effector":
                apoplastic += 1
            elif prediction in (
                "Apoplastic/cytoplasmic effector",
                "Cytoplasmic/apoplastic effector",
            ):
                dual_localization += 1
            elif prediction == "Non-effector":
                non_effector += 1
    effector_count = cytoplasmic + apoplastic + dual_localization
    out.update(
        {
            "effectorp_total_proteins": total,
            "effector_candidate_count": effector_count,
            "cytoplasmic_effector_count": cytoplasmic,
            "apoplastic_effector_count": apoplastic,
            "dual_localization_effector_count": dual_localization,
            "non_effector_count": non_effector,
            "effector_candidate_fraction": round(effector_count / total, 6)
            if total
            else "",
        }
    )
    return out


def build_annotation_sources() -> List[Dict[str, str]]:
    return [
        {
            "source_key": "funannotate_annotate",
            "display_name": "funannotate annotate",
            "category": "general_functional_annotation",
            "sub_category": "gene_product_annotation",
            "evidence_type": "homology_annotation",
            "evidence_strength": "general",
            "result_level": "gene_or_protein",
            "primary_output_table": "general_functional_annotation_summary.tsv",
            "interpretation_note": "通用基因产物和功能描述，不直接表示致病性。",
        },
        {
            "source_key": "eggnog_kegg",
            "display_name": "eggNOG-mapper / KEGG",
            "category": "general_functional_annotation",
            "sub_category": "orthology_pathway_annotation",
            "evidence_type": "orthology_annotation",
            "evidence_strength": "general",
            "result_level": "gene_or_protein",
            "primary_output_table": "general_functional_annotation_summary.tsv",
            "interpretation_note": "同源、通路和功能类别注释，作为基础功能注释使用。",
        },
        {
            "source_key": "dbcan_cazyme",
            "display_name": "dbCAN / CAZyme",
            "category": "pathogenicity_associated_annotation",
            "sub_category": "carbohydrate_active_enzyme",
            "evidence_type": "domain_hmm_annotation",
            "evidence_strength": "associated",
            "result_level": "protein",
            "primary_output_table": "pathogenicity_associated_summary.tsv",
            "interpretation_note": "糖类活性酶可能与表皮/细胞壁降解和营养利用相关，但不是致病性的直接证据。",
        },
        {
            "source_key": "merops",
            "display_name": "MEROPS",
            "category": "pathogenicity_associated_annotation",
            "sub_category": "protease",
            "evidence_type": "homology_annotation",
            "evidence_strength": "associated",
            "result_level": "protein",
            "primary_output_table": "pathogenicity_associated_summary.tsv",
            "interpretation_note": "蛋白酶可能参与侵染、组织降解或宿主互作，但需要进一步证据支持。",
        },
        {
            "source_key": "signalp6",
            "display_name": "SignalP6",
            "category": "pathogenicity_associated_annotation",
            "sub_category": "secretome",
            "evidence_type": "computational_prediction",
            "evidence_strength": "associated",
            "result_level": "protein",
            "primary_output_table": "pathogenicity_associated_summary.tsv",
            "interpretation_note": "预测分泌信号肽，是候选效应蛋白和分泌组分析的前置特征。",
        },
        {
            "source_key": "effectorp",
            "display_name": "EffectorP",
            "category": "pathogenicity_associated_annotation",
            "sub_category": "effector_candidate",
            "evidence_type": "computational_prediction",
            "evidence_strength": "candidate",
            "result_level": "protein",
            "primary_output_table": "pathogenicity_associated_summary.tsv",
            "interpretation_note": "候选效应蛋白预测，仍需实验或文献证据确认。",
        },
        {
            "source_key": "antismash",
            "display_name": "antiSMASH",
            "category": "pathogenicity_associated_annotation",
            "sub_category": "secondary_metabolite_bgc",
            "evidence_type": "biosynthetic_gene_cluster_prediction",
            "evidence_strength": "associated",
            "result_level": "genome_or_cluster",
            "primary_output_table": "pathogenicity_associated_summary.tsv",
            "interpretation_note": "次生代谢基因簇可能与毒素、竞争或适应性相关，不等同于已验证毒力因子。",
        },
        {
            "source_key": "busco",
            "display_name": "BUSCO",
            "category": "quality_control",
            "sub_category": "genome_completeness",
            "evidence_type": "ortholog_completeness_metric",
            "evidence_strength": "quality_metric",
            "result_level": "genome",
            "primary_output_table": "busco_summary.tsv",
            "interpretation_note": "基因组完整性质量评估，不属于功能注释或致病相关注释。",
        },
    ]


def build_source_manifest(source_rows: Dict[str, int]) -> List[Dict[str, Any]]:
    sources = [
        ("genome_stats", GENOME_STATS, "Primary 655-sample genome metadata table"),
        ("strain_abbreviation_map", ABBR_MAP, "Full-name to short sample ID map"),
        (
            "functional_summary",
            FUNCTIONAL_SUMMARY,
            "Merged funannotate/eggNOG annotation coverage and counts",
        ),
        (
            "functional_coverage",
            FUNCTIONAL_COVERAGE,
            "Normalized per-sample functional annotation status flags",
        ),
        (
            "antismash_genome_qc",
            ANTISMASH_QC,
            "antiSMASH per-genome QC and BGC count summary",
        ),
        (
            "busco_dirs",
            ROOT / "03_busco",
            "BUSCO hypocreales_odb12 output directories",
        ),
        (
            "signalp_dirs",
            ROOT / "05_sigalp-protein-data",
            "SignalP6 per-sample output directories",
        ),
    ]
    rows: List[Dict[str, Any]] = []
    for name, path, note in sources:
        rows.append(
            {
                "source_name": name,
                "source_path": rel(path),
                "exists": exists_i(path),
                "row_or_dir_count": source_rows.get(name, ""),
                "notes": note,
            }
        )
    return rows


def main() -> None:
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    genome_rows = read_delimited(GENOME_STATS, ",")
    abbr_rows = read_delimited(ABBR_MAP, ",")
    functional_rows = read_delimited(FUNCTIONAL_SUMMARY, "\t")
    coverage_rows = read_delimited(FUNCTIONAL_COVERAGE, "\t")
    antismash_rows = read_delimited(ANTISMASH_QC, "\t")

    abbr_by_full = {row["full_name"]: row["abbreviation"] for row in abbr_rows}
    full_by_abbr = {row["abbreviation"]: row["full_name"] for row in abbr_rows}
    functional_by_full = {row.get("species", ""): row for row in functional_rows}
    coverage_by_full = {row.get("species_normalized", ""): row for row in coverage_rows}
    antismash_by_full = {row.get("Genome", ""): row for row in antismash_rows}
    busco_by_full, busco_rows_all = scan_busco_dirs()

    sample_ids = Counter(row.get("abbreviation", "") for row in genome_rows)
    duplicate_sample_ids = {k for k, v in sample_ids.items() if k and v > 1}

    master_rows: List[Dict[str, Any]] = []
    genome_summary_rows: List[Dict[str, Any]] = []
    functional_summary_rows: List[Dict[str, Any]] = []
    pathogenicity_summary_rows: List[Dict[str, Any]] = []
    busco_summary_rows: List[Dict[str, Any]] = []
    antismash_summary_rows: List[Dict[str, Any]] = []
    signalp_summary_rows: List[Dict[str, Any]] = []
    status_rows: List[Dict[str, Any]] = []
    file_path_rows: List[Dict[str, Any]] = []
    missing_rows: List[Dict[str, Any]] = []

    for row in sorted(genome_rows, key=lambda r: r.get("abbreviation") or r["dir_name"]):
        full_name = row["dir_name"]
        sample_id = row.get("abbreviation") or abbr_by_full.get(full_name) or full_name
        sample_id_source = (
            "genome_stats.abbreviation"
            if row.get("abbreviation")
            else "strain_abbreviation_map"
            if full_name in abbr_by_full
            else "full_name_fallback"
        )
        order_group = row.get("order_group", "")
        genome_dir = ROOT / "01_genome-data" / order_group / full_name
        file_prefix = row.get("file_prefix") or full_name

        genome_fasta = first_existing(
            [
                genome_dir / f"{file_prefix}.scaffolds.fa",
                genome_dir / f"{full_name}.scaffolds.fa",
            ]
        )
        cds_fasta = first_existing(
            [
                genome_dir / f"{file_prefix}.cds.fa",
                genome_dir / f"{full_name}.cds.fa",
            ]
        )
        gff3 = first_existing(
            [
                genome_dir / f"{file_prefix}.gff3",
                genome_dir / f"{full_name}.gff3",
            ]
        )
        genbank = first_existing(
            [
                genome_dir / f"{file_prefix}.gbk",
                genome_dir / f"{full_name}.gbk",
            ]
        )
        protein_fasta = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "01.1-fullname-pep"
                / f"{full_name}.pep.fa",
                ROOT
                / "02_annotation-protein-data"
                / "01.1-fullname-pep"
                / f"{file_prefix}.pep.fa",
            ]
        )

        eggnog_annotations = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "02_kegg"
                / f"{full_name}.emapper.annotations",
                ROOT
                / "02_annotation-protein-data"
                / "02_kegg"
                / f"{file_prefix}.emapper.annotations",
            ]
        )
        eggnog_hits = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "02_kegg"
                / f"{full_name}.emapper.hits",
                ROOT
                / "02_annotation-protein-data"
                / "02_kegg"
                / f"{file_prefix}.emapper.hits",
            ]
        )
        eggnog_seed = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "02_kegg"
                / f"{full_name}.emapper.seed_orthologs",
                ROOT
                / "02_annotation-protein-data"
                / "02_kegg"
                / f"{file_prefix}.emapper.seed_orthologs",
            ]
        )
        effectorp = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "03_Effector"
                / f"{full_name}.effectorp.tsv",
                ROOT
                / "02_annotation-protein-data"
                / "03_Effector"
                / f"{file_prefix}.effectorp.tsv",
            ]
        )
        effectors_fa = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "03_Effector"
                / f"{full_name}.effectors.fa",
                ROOT
                / "02_annotation-protein-data"
                / "03_Effector"
                / f"{file_prefix}.effectors.fa",
            ]
        )
        noneffectors_fa = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "03_Effector"
                / f"{full_name}.noneffectors.fa",
                ROOT
                / "02_annotation-protein-data"
                / "03_Effector"
                / f"{file_prefix}.noneffectors.fa",
            ]
        )
        cazy_tsv = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "04_CAZ"
                / f"{full_name}.dbcan.tsv",
                ROOT
                / "02_annotation-protein-data"
                / "04_CAZ"
                / f"{file_prefix}.dbcan.tsv",
            ]
        )
        cazy_domtblout = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "04_CAZ"
                / f"{full_name}.dbcan.domtblout",
                ROOT
                / "02_annotation-protein-data"
                / "04_CAZ"
                / f"{file_prefix}.dbcan.domtblout",
            ]
        )
        merops_tsv = first_existing(
            [
                ROOT
                / "02_annotation-protein-data"
                / "05_MEROP"
                / f"{full_name}.merops.tsv",
                ROOT
                / "02_annotation-protein-data"
                / "05_MEROP"
                / f"{file_prefix}.merops.tsv",
            ]
        )

        busco_dirs = sorted(busco_by_full.get(canonical_sample_name(full_name), []))
        busco_dir = busco_dirs[0] if busco_dirs else None
        busco_json = (
            busco_dir / "run_hypocreales_odb12" / "short_summary.json"
            if busco_dir
            else None
        )

        antismash_dir = ROOT / "04_antismash-bigscape" / "00_data" / full_name
        antismash_json = antismash_dir / f"{full_name}.json"
        signalp_dir = ROOT / "05_sigalp-protein-data" / sample_id
        if not signalp_dir.exists():
            fallback = ROOT / "05_sigalp-protein-data" / full_name
            if fallback.exists():
                signalp_dir = fallback
        signalp_results = signalp_dir / "prediction_results.txt"
        signalp_gff = signalp_dir / "output.gff3"

        function_summary = functional_by_full.get(full_name, {})
        coverage = coverage_by_full.get(full_name, {})
        antismash = antismash_by_full.get(full_name, {})
        signalp_counts = parse_signalp_result(signalp_results)
        effectorp_counts = parse_effectorp_result(effectorp)
        cazyme_hit_count = count_non_comment_rows(cazy_tsv)
        cazyme_protein_count = count_unique_column(cazy_tsv, 2)
        merops_hit_count = count_non_comment_rows(merops_tsv)
        merops_protein_count = count_unique_column(merops_tsv, 0)
        effectors_fasta_count = count_fasta_records(effectors_fa)
        noneffectors_fasta_count = count_fasta_records(noneffectors_fa)

        has_genome = all(exists_i(p) for p in (genome_fasta, cds_fasta, gff3, genbank))
        has_function = all(
            exists_i(p)
            for p in (
                protein_fasta,
                eggnog_annotations,
                eggnog_hits,
                eggnog_seed,
                effectorp,
                effectors_fa,
                noneffectors_fa,
                cazy_tsv,
                cazy_domtblout,
                merops_tsv,
            )
        )
        has_busco = 1 if busco_json and busco_json.exists() else 0
        has_antismash = exists_i(antismash_json)
        has_signalp = exists_i(signalp_results)

        tax = split_taxonomy(full_name)
        busco_pick = (
            next(
                (b for b in busco_rows_all if b["busco_dir"] == rel(busco_dir)),
                {},
            )
            if busco_dir
            else {}
        )

        master = {
            "sample_id": sample_id,
            "sample_id_source": sample_id_source,
            "full_name": full_name,
            "file_prefix": file_prefix,
            "order_group": order_group,
            "abbreviation_source": row.get("abbreviation_source", ""),
            "family": antismash.get("Family", ""),
            "genus": antismash.get("Genus", tax["genus_from_name"]),
            "species": antismash.get("Species", tax["species_binomial_from_name"]),
            "species_status": antismash.get("Species_status", ""),
            **tax,
            "genome_size": safe_int(row.get("genome_size", "")),
            "gc_content": normalize_float(row.get("gc_content", "")),
            "scaffold_count": safe_int(row.get("scaffold_count", "")),
            "n50": safe_int(row.get("n50", "")),
            "gene_count": safe_int(row.get("gene_count", "")),
            "protein_count": safe_int(row.get("protein_count", "")),
            "functional_any_annotation_ratio": function_summary.get(
                "any_annotation_ratio", ""
            ),
            "functional_unannotated_ratio": function_summary.get(
                "unannotated_ratio", ""
            ),
            "busco_complete_pct": busco_pick.get("complete_pct", ""),
            "busco_missing_pct": busco_pick.get("missing_pct", ""),
            "bgc_count": antismash.get("BGC_count", ""),
            "effector_candidate_count": effectorp_counts.get(
                "effector_candidate_count", ""
            ),
            "cazyme_protein_count": cazyme_protein_count,
            "merops_protein_count": merops_protein_count,
            **signalp_counts,
            "has_genome_core": has_genome,
            "has_functional_core": has_function,
            "has_busco": has_busco,
            "has_antismash": has_antismash,
            "has_signalp": has_signalp,
            "ready_basic_db": 1 if has_genome and has_function else 0,
            "ready_full_analysis": 1
            if has_genome and has_function and has_busco and has_antismash and has_signalp
            else 0,
            "genome_dir": rel(genome_dir),
            "genome_fasta_path": rel_if_exists(genome_fasta),
            "cds_fasta_path": rel_if_exists(cds_fasta),
            "gff3_path": rel_if_exists(gff3),
            "genbank_path": rel_if_exists(genbank),
            "protein_fasta_path": rel_if_exists(protein_fasta),
            "busco_dir": rel(busco_dir) if busco_dir else "",
            "busco_summary_json_path": rel_if_exists(busco_json) if busco_json else "",
            "antismash_dir": rel(antismash_dir) if antismash_dir.exists() else "",
            "antismash_json_path": rel_if_exists(antismash_json),
            "signalp_dir": rel(signalp_dir) if signalp_dir.exists() else "",
            "signalp_prediction_path": rel_if_exists(signalp_results),
        }
        master_rows.append(master)

        genome_summary_rows.append(
            {
                "sample_id": sample_id,
                "full_name": full_name,
                "order_group": order_group,
                "genome_size": master["genome_size"],
                "gc_content": master["gc_content"],
                "n_content": row.get("n_content", ""),
                "scaffold_count": master["scaffold_count"],
                "n50": master["n50"],
                "l50": row.get("l50", ""),
                "max_scaffold_length": row.get("max_scaffold_length", ""),
                "mean_scaffold_length": row.get("mean_scaffold_length", ""),
                "gene_count": master["gene_count"],
                "protein_coding_count": row.get("protein_coding_count", ""),
                "trna_count": row.get("trna_count", ""),
                "rrna_count": row.get("rrna_count", ""),
                "ncrna_count": row.get("ncrna_count", ""),
                "protein_count": master["protein_count"],
                "mean_protein_length": row.get("mean_protein_length", ""),
                "parse_errors": row.get("parse_errors", ""),
            }
        )

        functional_summary_rows.append(
            {
                "sample_id": sample_id,
                "full_name": full_name,
                "annotation_category": "general_functional_annotation",
                **function_summary,
                "complete_02_annotation": coverage.get("complete_02_annotation", ""),
                "complete_funannotate_and_02": coverage.get(
                    "complete_funannotate_and_02", ""
                ),
            }
        )

        pathogenicity_summary_rows.append(
            {
                "sample_id": sample_id,
                "full_name": full_name,
                "annotation_category": "pathogenicity_associated_annotation",
                "has_signalp": has_signalp,
                "has_effectorp": exists_i(effectorp),
                "has_cazyme": exists_i(cazy_tsv),
                "has_merops": exists_i(merops_tsv),
                "has_antismash": has_antismash,
                "complete_pathogenicity_associated_features": 1
                if has_signalp
                and exists_i(effectorp)
                and exists_i(cazy_tsv)
                and exists_i(merops_tsv)
                and has_antismash
                else 0,
                **signalp_counts,
                **effectorp_counts,
                "effectors_fasta_count": effectors_fasta_count,
                "noneffectors_fasta_count": noneffectors_fasta_count,
                "cazyme_hit_count": cazyme_hit_count,
                "cazyme_protein_count": cazyme_protein_count,
                "merops_hit_count": merops_hit_count,
                "merops_protein_count": merops_protein_count,
                "bgc_count": antismash.get("BGC_count", ""),
                "antismash_top_products": antismash.get("Top_products", ""),
                "signalp_prediction_path": rel_if_exists(signalp_results),
                "effectorp_path": rel_if_exists(effectorp),
                "cazyme_tsv_path": rel_if_exists(cazy_tsv),
                "merops_tsv_path": rel_if_exists(merops_tsv),
                "antismash_json_path": rel_if_exists(antismash_json),
            }
        )

        if busco_pick:
            busco_summary_rows.append(
                {
                    "sample_id": sample_id,
                    **busco_pick,
                }
            )

        antismash_summary_rows.append(
            {
                "sample_id": sample_id,
                "full_name": full_name,
                **antismash,
                "antismash_dir": rel(antismash_dir) if antismash_dir.exists() else "",
            }
        )

        signalp_summary_rows.append(
            {
                "sample_id": sample_id,
                "full_name": full_name,
                **signalp_counts,
                "signalp_dir": rel(signalp_dir) if signalp_dir.exists() else "",
                "prediction_results_path": rel_if_exists(signalp_results),
                "output_gff3_path": rel_if_exists(signalp_gff),
            }
        )

        status = {
            "sample_id": sample_id,
            "full_name": full_name,
            "has_genome_core": has_genome,
            "has_protein_fasta": exists_i(protein_fasta),
            "has_eggnog": exists_i(eggnog_annotations),
            "has_effectorp": exists_i(effectorp),
            "has_cazy": exists_i(cazy_tsv),
            "has_merops": exists_i(merops_tsv),
            "has_functional_core": has_function,
            "has_busco": has_busco,
            "has_antismash": has_antismash,
            "has_signalp": has_signalp,
            "ready_basic_db": master["ready_basic_db"],
            "ready_full_analysis": master["ready_full_analysis"],
        }
        status_rows.append(status)

        path_specs = [
            ("genome_fasta", genome_fasta, "file"),
            ("cds_fasta", cds_fasta, "file"),
            ("gff3", gff3, "file"),
            ("genbank", genbank, "file"),
            ("protein_fasta", protein_fasta, "file"),
            ("eggnog_annotations", eggnog_annotations, "file"),
            ("eggnog_hits", eggnog_hits, "file"),
            ("eggnog_seed_orthologs", eggnog_seed, "file"),
            ("effectorp", effectorp, "file"),
            ("effectors_fa", effectors_fa, "file"),
            ("noneffectors_fa", noneffectors_fa, "file"),
            ("cazy_tsv", cazy_tsv, "file"),
            ("cazy_domtblout", cazy_domtblout, "file"),
            ("merops_tsv", merops_tsv, "file"),
            ("busco_summary_json", busco_json, "file"),
            ("antismash_json", antismash_json, "file"),
            ("signalp_prediction_results", signalp_results, "file"),
            ("signalp_output_gff3", signalp_gff, "file"),
        ]
        for data_type, path, object_type in path_specs:
            if path is None:
                file_info = {"exists": "0", "size_bytes": "", "mtime": ""}
                path_text = ""
            else:
                file_info = get_file_info(path)
                path_text = rel(path)
            file_path_rows.append(
                {
                    "sample_id": sample_id,
                    "full_name": full_name,
                    "data_type": data_type,
                    "object_type": object_type,
                    "path": path_text,
                    **file_info,
                }
            )

        expected = {
            "genome_core": (has_genome, rel(genome_dir)),
            "functional_core": (
                has_function,
                "02_annotation-protein-data/{02_kegg,03_Effector,04_CAZ,05_MEROP}",
            ),
            "busco": (has_busco, "03_busco/*/" + full_name),
            "antismash": (has_antismash, rel(antismash_dir)),
            "signalp": (has_signalp, f"05_sigalp-protein-data/{sample_id}"),
        }
        for analysis, (present, expected_path) in expected.items():
            if not present:
                missing_rows.append(
                    {
                        "analysis": analysis,
                        "sample_id": sample_id,
                        "full_name": full_name,
                        "expected_path_hint": expected_path,
                    }
                )

    sample_full_names = {row["full_name"] for row in master_rows}
    canonical_full_names = {canonical_sample_name(row["full_name"]) for row in master_rows}
    sample_abbrs = {row["sample_id"] for row in master_rows}
    unmatched_rows: List[Dict[str, Any]] = []

    for canonical_name in sorted(busco_by_full):
        if canonical_name not in canonical_full_names:
            for path in busco_by_full[canonical_name]:
                unmatched_rows.append(
                    {
                        "source": "03_busco",
                        "source_sample_name": path.name,
                        "source_path": rel(path),
                        "note": "BUSCO directory has no matching 01_genome-data sample",
                    }
                )

    antismash_root = ROOT / "04_antismash-bigscape" / "00_data"
    if antismash_root.exists():
        for sample_dir in sorted(p for p in antismash_root.iterdir() if p.is_dir()):
            if sample_dir.name not in sample_full_names:
                unmatched_rows.append(
                    {
                        "source": "04_antismash-bigscape/00_data",
                        "source_sample_name": sample_dir.name,
                        "source_path": rel(sample_dir),
                        "note": "antiSMASH directory has no matching 01_genome-data sample",
                    }
                )

    signalp_root = ROOT / "05_sigalp-protein-data"
    if signalp_root.exists():
        for sample_dir in sorted(p for p in signalp_root.iterdir() if p.is_dir()):
            full_name = full_by_abbr.get(sample_dir.name, sample_dir.name)
            if sample_dir.name not in sample_abbrs and full_name not in sample_full_names:
                unmatched_rows.append(
                    {
                        "source": "05_sigalp-protein-data",
                        "source_sample_name": sample_dir.name,
                        "source_path": rel(sample_dir),
                        "note": "SignalP directory has no matching sample ID or full name",
                    }
                )

    for sample_id in sorted(duplicate_sample_ids):
        unmatched_rows.append(
            {
                "source": "genome_stats_2026-05-12.csv",
                "source_sample_name": sample_id,
                "source_path": rel(GENOME_STATS),
                "note": "Duplicate sample_id in primary genome stats",
            }
        )

    master_fields = [
        "sample_id",
        "sample_id_source",
        "full_name",
        "file_prefix",
        "order_group",
        "abbreviation_source",
        "family",
        "genus",
        "species",
        "species_status",
        "genus_from_name",
        "species_epithet_from_name",
        "species_binomial_from_name",
        "strain_from_name",
        "genome_size",
        "gc_content",
        "scaffold_count",
        "n50",
        "gene_count",
        "protein_count",
        "functional_any_annotation_ratio",
        "functional_unannotated_ratio",
        "busco_complete_pct",
        "busco_missing_pct",
        "bgc_count",
        "effector_candidate_count",
        "cazyme_protein_count",
        "merops_protein_count",
        "signalp_total_proteins",
        "signalp_sp_count",
        "signalp_other_count",
        "signalp_sp_fraction",
        "signalp_high_confidence_sp_count",
        "has_genome_core",
        "has_functional_core",
        "has_busco",
        "has_antismash",
        "has_signalp",
        "ready_basic_db",
        "ready_full_analysis",
        "genome_dir",
        "genome_fasta_path",
        "cds_fasta_path",
        "gff3_path",
        "genbank_path",
        "protein_fasta_path",
        "busco_dir",
        "busco_summary_json_path",
        "antismash_dir",
        "antismash_json_path",
        "signalp_dir",
        "signalp_prediction_path",
    ]
    genome_fields = [
        "sample_id",
        "full_name",
        "order_group",
        "genome_size",
        "gc_content",
        "n_content",
        "scaffold_count",
        "n50",
        "l50",
        "max_scaffold_length",
        "mean_scaffold_length",
        "gene_count",
        "protein_coding_count",
        "trna_count",
        "rrna_count",
        "ncrna_count",
        "protein_count",
        "mean_protein_length",
        "parse_errors",
    ]
    status_fields = [
        "sample_id",
        "full_name",
        "has_genome_core",
        "has_protein_fasta",
        "has_eggnog",
        "has_effectorp",
        "has_cazy",
        "has_merops",
        "has_functional_core",
        "has_busco",
        "has_antismash",
        "has_signalp",
        "ready_basic_db",
        "ready_full_analysis",
    ]
    file_path_fields = [
        "sample_id",
        "full_name",
        "data_type",
        "object_type",
        "path",
        "exists",
        "size_bytes",
        "mtime",
    ]
    busco_fields = [
        "sample_id",
        "source_group",
        "full_name",
        "lineage",
        "busco_version",
        "complete_pct",
        "complete_buscos",
        "single_copy_pct",
        "single_copy_buscos",
        "duplicated_pct",
        "duplicated_buscos",
        "fragmented_pct",
        "fragmented_buscos",
        "missing_pct",
        "missing_buscos",
        "n_markers",
        "avg_identity",
        "internal_stop_codon_pct",
        "one_line_summary",
        "busco_dir",
        "summary_json_path",
        "summary_txt_path",
        "has_summary_json",
        "has_summary_txt",
        "parse_error",
    ]
    antismash_fields = [
        "sample_id",
        "full_name",
        "Genome",
        "Family",
        "Genus",
        "Species",
        "Species_status",
        "BGC_count",
        "JSON_records",
        "JSON_present",
        "HTML_present",
        "ZIP_present",
        "Full_GBK_present",
        "antiSMASH_version",
        "Taxonomy_empty_in_JSON",
        "Contig_edge_BGCs",
        "Contig_edge_fraction",
        "No_biosynthetic_CDS_BGCs",
        "CDS_zero_BGCs",
        "Median_BGC_size_kb",
        "Top_products",
        "antismash_dir",
    ]
    signalp_fields = [
        "sample_id",
        "full_name",
        "signalp_total_proteins",
        "signalp_sp_count",
        "signalp_other_count",
        "signalp_sp_fraction",
        "signalp_high_confidence_sp_count",
        "signalp_dir",
        "prediction_results_path",
        "output_gff3_path",
    ]
    functional_fields = [
        "sample_id",
        "full_name",
        "annotation_category",
        "species",
        "funannotate_species_name",
        "total_genes",
        "funannotate_annotated_genes",
        "eggnog_matched_genes",
        "eggnog_annotated_genes",
        "any_functionally_annotated_genes",
        "unannotated_genes",
        "funannotate_annotation_ratio",
        "eggnog_match_ratio",
        "eggnog_annotation_ratio",
        "any_annotation_ratio",
        "unannotated_ratio",
        "eggnog_only_records",
        "complete_02_annotation",
        "complete_funannotate_and_02",
        "output",
    ]
    pathogenicity_fields = [
        "sample_id",
        "full_name",
        "annotation_category",
        "has_signalp",
        "has_effectorp",
        "has_cazyme",
        "has_merops",
        "has_antismash",
        "complete_pathogenicity_associated_features",
        "signalp_total_proteins",
        "signalp_sp_count",
        "signalp_other_count",
        "signalp_sp_fraction",
        "signalp_high_confidence_sp_count",
        "effectorp_total_proteins",
        "effector_candidate_count",
        "cytoplasmic_effector_count",
        "apoplastic_effector_count",
        "dual_localization_effector_count",
        "non_effector_count",
        "effector_candidate_fraction",
        "effectors_fasta_count",
        "noneffectors_fasta_count",
        "cazyme_hit_count",
        "cazyme_protein_count",
        "merops_hit_count",
        "merops_protein_count",
        "bgc_count",
        "antismash_top_products",
        "signalp_prediction_path",
        "effectorp_path",
        "cazyme_tsv_path",
        "merops_tsv_path",
        "antismash_json_path",
    ]
    annotation_source_fields = [
        "source_key",
        "display_name",
        "category",
        "sub_category",
        "evidence_type",
        "evidence_strength",
        "result_level",
        "primary_output_table",
        "interpretation_note",
    ]

    write_tsv(TABLES / "master_sample_index.tsv", master_rows, master_fields)
    write_tsv(TABLES / "genome_summary.tsv", genome_summary_rows, genome_fields)
    write_tsv(
        TABLES / "general_functional_annotation_summary.tsv",
        functional_summary_rows,
        functional_fields,
    )
    write_tsv(
        TABLES / "functional_annotation_summary.tsv",
        functional_summary_rows,
        functional_fields,
    )
    write_tsv(
        TABLES / "pathogenicity_associated_summary.tsv",
        pathogenicity_summary_rows,
        pathogenicity_fields,
    )
    write_tsv(
        TABLES / "annotation_sources.tsv",
        build_annotation_sources(),
        annotation_source_fields,
    )
    write_tsv(TABLES / "busco_summary.tsv", busco_summary_rows, busco_fields)
    write_tsv(
        TABLES / "antismash_genome_summary.tsv",
        antismash_summary_rows,
        antismash_fields,
    )
    write_tsv(TABLES / "signalp_summary.tsv", signalp_summary_rows, signalp_fields)
    write_tsv(TABLES / "analysis_status_matrix.tsv", status_rows, status_fields)
    write_tsv(TABLES / "sample_file_paths.tsv", file_path_rows, file_path_fields)

    write_tsv(
        CHECKS / "missing_by_analysis.tsv",
        missing_rows,
        ["analysis", "sample_id", "full_name", "expected_path_hint"],
    )
    write_tsv(
        CHECKS / "unmatched_source_records.tsv",
        unmatched_rows,
        ["source", "source_sample_name", "source_path", "note"],
    )

    source_rows = {
        "genome_stats": len(genome_rows),
        "strain_abbreviation_map": len(abbr_rows),
        "functional_summary": len(functional_rows),
        "functional_coverage": len(coverage_rows),
        "antismash_genome_qc": len(antismash_rows),
        "busco_dirs": len(busco_rows_all),
        "signalp_dirs": len([p for p in (ROOT / "05_sigalp-protein-data").iterdir() if p.is_dir()])
        if (ROOT / "05_sigalp-protein-data").exists()
        else 0,
    }
    source_manifest = build_source_manifest(source_rows)
    write_tsv(
        MANIFESTS / "source_manifest.tsv",
        source_manifest,
        ["source_name", "source_path", "exists", "row_or_dir_count", "notes"],
    )

    status_counts = {
        "sample_count": len(master_rows),
        "ready_basic_db": sum(int(row["ready_basic_db"]) for row in master_rows),
        "ready_full_analysis": sum(int(row["ready_full_analysis"]) for row in master_rows),
        "has_busco": sum(int(row["has_busco"]) for row in master_rows),
        "has_antismash": sum(int(row["has_antismash"]) for row in master_rows),
        "has_signalp": sum(int(row["has_signalp"]) for row in master_rows),
        "missing_records": len(missing_rows),
        "unmatched_source_records": len(unmatched_rows),
    }
    by_group = Counter(row["order_group"] for row in master_rows)
    manifest = {
        "generated_at": generated_at,
        "project_root": str(ROOT),
        "ready_dir": rel(READY),
        "primary_key": "sample_id",
        "natural_key": "full_name",
        "status_counts": status_counts,
        "samples_by_order_group": dict(sorted(by_group.items())),
        "source_rows": source_rows,
        "tables": {
            "master_sample_index": rel(TABLES / "master_sample_index.tsv"),
            "genome_summary": rel(TABLES / "genome_summary.tsv"),
            "general_functional_annotation_summary": rel(
                TABLES / "general_functional_annotation_summary.tsv"
            ),
            "functional_annotation_summary": rel(
                TABLES / "functional_annotation_summary.tsv"
            ),
            "pathogenicity_associated_summary": rel(
                TABLES / "pathogenicity_associated_summary.tsv"
            ),
            "annotation_sources": rel(TABLES / "annotation_sources.tsv"),
            "busco_summary": rel(TABLES / "busco_summary.tsv"),
            "antismash_genome_summary": rel(
                TABLES / "antismash_genome_summary.tsv"
            ),
            "signalp_summary": rel(TABLES / "signalp_summary.tsv"),
            "analysis_status_matrix": rel(TABLES / "analysis_status_matrix.tsv"),
            "sample_file_paths": rel(TABLES / "sample_file_paths.tsv"),
        },
        "checks": {
            "missing_by_analysis": rel(CHECKS / "missing_by_analysis.tsv"),
            "unmatched_source_records": rel(CHECKS / "unmatched_source_records.tsv"),
        },
    }
    write_json(MANIFESTS / "ready_manifest.json", manifest)

    print(json.dumps(status_counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
