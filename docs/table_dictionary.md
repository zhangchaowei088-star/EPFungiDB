# 表结构说明

## 总体设计

本目录采用一个主样本表加多个模块表的结构：

- 所有样本级表均以 `sample_id` 作为推荐主键/外键。
- `full_name` 保留原始目录名，适合回溯上游文件。
- 所有路径为项目根目录下的相对路径。
- 状态字段使用 `1/0` 或 `True/False`，其中 `has_*` 表示文件或分析是否可用。
- 注释类别用 `annotation_sources.tsv` 统一定义，避免把“致病相关候选特征”误写成“已验证致病基因”。

## tables/master_sample_index.tsv

用途：数据库开发最常用的总索引表。一行一个主样本，合并基础分类、基因组统计、主要分析摘要、状态和关键路径。

关键字段：

| 字段 | 说明 |
|---|---|
| `sample_id` | 推荐数据库主键，样本缩写 |
| `full_name` | 原始样本名/目录名 |
| `order_group` | 原始分组：`Cordy`、`Metarhizium`、`Ophiocordy` |
| `family` / `genus` / `species` | 优先来自 antiSMASH QC 的分类字段，缺失时用名称推断 |
| `genome_size`、`gc_content`、`n50` | 基因组基础统计 |
| `functional_any_annotation_ratio` | 有任一功能注释的基因比例 |
| `busco_complete_pct` | BUSCO 完整度 |
| `bgc_count` | antiSMASH BGC 数 |
| `signalp_sp_count` | SignalP6 预测为信号肽蛋白数 |
| `has_genome_core` | scaffold/CDS/GFF3/GBK 是否齐全 |
| `effector_candidate_count` | EffectorP 候选效应蛋白数 |
| `cazyme_protein_count` | 至少命中一个 CAZyme/dbCAN 家族的蛋白数 |
| `merops_protein_count` | 至少命中一个 MEROPS 条目的蛋白数 |
| `has_functional_core` | 当前基础交付层所需的蛋白、eggNOG、EffectorP、CAZyme、MEROPS 是否齐全 |
| `ready_basic_db` | 是否适合进入基础数据库表 |
| `ready_full_analysis` | 基础、BUSCO、antiSMASH、SignalP6 是否全部齐全 |

## tables/genome_summary.tsv

用途：基因组统计表。适合导入 `genome_metrics` 或样本详情页。

主要字段来自 `genome_stats_2026-05-12.csv`，包括 genome size、GC、N50/L50、scaffold 数、基因数、蛋白数、tRNA/rRNA/ncRNA 数等。

## tables/annotation_sources.tsv

用途：定义每种注释来源属于哪一类，以及结果应该如何解释。数据库和前端应优先使用该表驱动模块分组。

当前分类：

| category | 含义 | 当前来源 |
|---|---|---|
| `general_functional_annotation` | 通用功能注释 | funannotate annotate、eggNOG/KEGG |
| `pathogenicity_associated_annotation` | 致病相关/宿主互作相关候选特征 | CAZyme、MEROPS、SignalP6、EffectorP、antiSMASH |
| `quality_control` | 质量控制 | BUSCO |

关键字段：

- `source_key`
- `display_name`
- `category`
- `sub_category`
- `evidence_type`
- `evidence_strength`
- `result_level`
- `primary_output_table`
- `interpretation_note`

## tables/general_functional_annotation_summary.tsv

用途：样本级通用功能注释覆盖统计。适合导入 `general_functional_annotation_summary`。

主要字段：

- `total_genes`
- `funannotate_annotated_genes`
- `eggnog_matched_genes`
- `eggnog_annotated_genes`
- `any_functionally_annotated_genes`
- `unannotated_genes`
- 各类 ratio 字段
- `complete_02_annotation`

蛋白/基因级注释明细仍在上游目录中，当前表是样本级汇总。

## tables/functional_annotation_summary.tsv

用途：兼容旧命名的通用功能注释汇总表。内容与 `general_functional_annotation_summary.tsv` 相同。新开发建议使用 `general_functional_annotation_summary.tsv`，使表名与注释类别一致。

## tables/pathogenicity_associated_summary.tsv

用途：样本级致病相关特征注释汇总。适合导入 `pathogenicity_associated_summary` 或按子模块拆分为 secretome、effector、CAZyme、protease、secondary metabolism 等表。

重要解释：该表中的 CAZyme、MEROPS、SignalP6、EffectorP、antiSMASH 结果表示“致病相关/宿主互作相关候选特征”，不等同于实验证实的致病基因。

主要字段：

| 字段 | 说明 |
|---|---|
| `annotation_category` | 固定为 `pathogenicity_associated_annotation` |
| `complete_pathogenicity_associated_features` | SignalP6、EffectorP、CAZyme、MEROPS、antiSMASH 是否全部可用 |
| `signalp_sp_count` | SignalP6 预测含信号肽蛋白数 |
| `signalp_high_confidence_sp_count` | `SP(Sec/SPI) >= 0.9` 的信号肽蛋白数 |
| `effector_candidate_count` | EffectorP 候选效应蛋白总数 |
| `cytoplasmic_effector_count` | 预测为胞质效应蛋白数 |
| `apoplastic_effector_count` | 预测为质外体/胞外效应蛋白数 |
| `dual_localization_effector_count` | EffectorP 双定位类别计数 |
| `cazyme_hit_count` | CAZyme 命中行数 |
| `cazyme_protein_count` | 至少命中一个 CAZyme 家族的蛋白数 |
| `merops_hit_count` | MEROPS 命中行数 |
| `merops_protein_count` | 至少命中一个 MEROPS 条目的蛋白数 |
| `bgc_count` | antiSMASH BGC 数 |
| `antismash_top_products` | antiSMASH 主要产物类别统计 |

## tables/proteins.tsv

用途：蛋白/基因主表。支持“进入某个菌株后查看所有基因/蛋白”和后续所有蛋白级注释表的关联。

主键：

- `protein_uid`：格式为 `sample_id|protein_id`。

关键字段：

| 字段 | 说明 |
|---|---|
| `sample_id` | 样本主键 |
| `full_name` | 原始样本名 |
| `gene_id` | 基因 ID |
| `transcript_id` | 转录本 ID |
| `protein_id` | 蛋白 ID |
| `seqid`、`start`、`end`、`strand` | 基因组位置 |
| `protein_length` | 蛋白长度 |
| `product` | funannotate product |
| `has_general_functional_annotation` | 是否有通用功能注释 |
| `has_pathogenicity_associated_feature` | 是否有任一致病相关候选特征 |

## tables/protein_general_annotation_summary.tsv

用途：蛋白级通用功能注释宽表。适合蛋白详情页和物种内蛋白检索。

一行一个蛋白，包含：

- funannotate product/dbxref/note
- eggNOG seed ortholog、evalue、score
- COG category
- eggNOG description/preferred name
- GO terms
- EC numbers
- KEGG KO
- KEGG pathways
- KEGG modules/reactions/BRITE
- PFAM domains

## tables/kegg_pathway_members.tsv

用途：直接支持“某个菌株的某个 KEGG 通路有哪些基因/蛋白”的查询。

推荐索引：

- `(sample_id, kegg_pathway_id)`
- `protein_uid`
- `kegg_ko`

关键字段：

| 字段 | 说明 |
|---|---|
| `sample_id` | 样本主键 |
| `kegg_pathway_id` | KEGG pathway，例如 `ko00511`、`map00511` |
| `protein_uid` | 蛋白主键 |
| `protein_id` / `gene_id` | 蛋白和基因 ID |
| `seqid`、`start`、`end`、`strand` | 基因组位置 |
| `kegg_ko` | 该蛋白对应 KO |
| `preferred_name` | eggNOG preferred name |
| `description` | eggNOG description |

典型查询：筛选 `sample_id='A_G78'` 且 `kegg_pathway_id='ko00511'`。

## tables/protein_pathogenicity_summary.tsv

用途：蛋白级致病相关候选特征宽表。适合蛋白详情页和组合筛选。

典型筛选：

- `is_secreted = 1`：分泌蛋白候选。
- `is_effector_candidate = 1`：候选效应蛋白。
- `is_secreted = 1 AND is_effector_candidate = 1`：分泌型候选效应蛋白。
- `has_cazyme = 1`：CAZyme 蛋白。
- `has_merops = 1`：蛋白酶候选。

## tables/protein_pathogenicity_features.tsv

用途：蛋白级致病相关特征长表。一行表示一个蛋白的一条特征。

当前 `feature_type` 包括：

- `secreted_signal_peptide`
- `effector_candidate`
- `carbohydrate_active_enzyme`
- `protease`

该表适合做高级筛选和统计，例如 secreted CAZymes、secreted proteases、某个 CAZyme family 在不同菌株中的分布。

## tables/busco_summary.tsv

用途：BUSCO 样本级完整性结果。

主要字段：

- `lineage`：当前为 `hypocreales_odb12`
- `busco_version`
- `complete_pct`
- `single_copy_pct`
- `duplicated_pct`
- `fragmented_pct`
- `missing_pct`
- 对应 BUSCO 数量字段
- `summary_json_path`
- `has_summary_json`

注意：该表包含已匹配主样本的 BUSCO 目录；其中有一个样本目录存在但 summary JSON 缺失。

## tables/antismash_genome_summary.tsv

用途：antiSMASH 样本级 BGC/QC 汇总。

主要字段：

- `BGC_count`
- `antiSMASH_version`
- `Top_products`
- `Contig_edge_BGCs`
- `Contig_edge_fraction`
- `Median_BGC_size_kb`
- `JSON_present`
- `HTML_present`
- `ZIP_present`
- `Full_GBK_present`

BGC/GCF 详细表仍保留在 `04_antismash-bigscape/08_BGC_analysis`、`09_antismash_family_qc`、`10_bigscape_gcf_analysis` 中。

## tables/signalp_summary.tsv

用途：SignalP6 样本级汇总。

主要字段：

- `signalp_total_proteins`
- `signalp_sp_count`
- `signalp_other_count`
- `signalp_sp_fraction`
- `signalp_high_confidence_sp_count`：`SP(Sec/SPI) >= 0.9` 的 SP 数量
- `prediction_results_path`
- `output_gff3_path`

## tables/analysis_status_matrix.tsv

用途：快速过滤可导入样本和待补分析样本。

常用筛选：

- `ready_basic_db == 1`：基础数据库可导入。
- `ready_full_analysis == 1`：五类分析全部齐全。
- `has_antismash == 0`：待补 antiSMASH。
- `has_signalp == 0`：待补 SignalP6。

## tables/sample_file_paths.tsv

用途：文件级路径索引。适合数据库开发人员定位原始文件，或后续构建文件下载/浏览接口。

字段：

| 字段 | 说明 |
|---|---|
| `sample_id` | 样本主键 |
| `full_name` | 原始样本名 |
| `data_type` | 文件类型，例如 `genome_fasta`、`eggnog_annotations`、`signalp_prediction_results` |
| `object_type` | 当前均为 `file` |
| `path` | 相对路径 |
| `exists` | 文件是否存在 |
| `size_bytes` | 文件大小 |
| `mtime` | 文件修改时间 |

## checks/missing_by_analysis.tsv

用途：主样本缺失分析清单。一行表示一个样本缺一个分析模块。

字段：

- `analysis`
- `sample_id`
- `full_name`
- `expected_path_hint`

## checks/unmatched_source_records.tsv

用途：上游分析目录存在，但没有匹配到当前 655 个主样本的记录。通常用于判断是否是旧样本、额外样本或名称不一致。

## manifests/source_manifest.tsv

用途：记录脚本读取了哪些上游源文件/目录，以及源记录数。

## manifests/ready_manifest.json

用途：机器可读的生成摘要。数据库流水线可以先读取该文件判断样本数、覆盖数和输出表路径。
