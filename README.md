# 00_ready-for-database

这个目录是数据库开发的交付层。上游 `01` 到 `05` 目录保留原始分析结果，本目录只生成面向数据库导入、状态检查和后续更新的索引表与汇总表。

## 推荐使用顺序

1. 先读 `manifests/ready_manifest.json`：查看生成时间、样本总数、各分析覆盖数量。
2. 主表使用 `tables/master_sample_index.tsv`：一行一个样本，主键为 `sample_id`，自然键为 `full_name`。
3. 数据库导入时按模块读取 `tables/*.tsv`：
   - `genome_summary.tsv`
   - `general_functional_annotation_summary.tsv`
   - `pathogenicity_associated_summary.tsv`
   - `proteins.tsv`
   - `protein_general_annotation_summary.tsv`
   - `kegg_pathway_members.tsv`
   - `protein_pathogenicity_summary.tsv`
   - `protein_pathogenicity_features.tsv`
   - `busco_summary.tsv`
   - `antismash_genome_summary.tsv`
   - `signalp_summary.tsv`
4. 注释类别和解释口径使用 `tables/annotation_sources.tsv`。
5. 前端或接口需要定位原始文件时，使用 `tables/sample_file_paths.tsv`。
6. 每次更新后先检查：
   - `checks/missing_by_analysis.tsv`
   - `checks/unmatched_source_records.tsv`

## 项目管理与备份

当前阶段采用最小管理体系：代码和文档用 Git 管理，大型 TSV、SQLite 数据库和上游分析结果只在重要节点做备份快照。具体执行规范见 `docs/project_management.md`。

## 当前生成结果

当前主样本数：655。

| 指标 | 数量 |
|---|---:|
| 基础数据库字段完整样本 | 655 |
| BUSCO 有 summary JSON 样本 | 654 |
| antiSMASH 有 JSON 样本 | 630 |
| SignalP6 有预测结果样本 | 649 |
| 五类分析全部齐全样本 | 625 |
| 上游存在但未匹配到主样本的记录 | 7 |
| 蛋白级主表记录 | 6,509,352 |
| KEGG 通路成员记录 | 13,431,724 |
| 蛋白致病相关特征记录 | 2,707,105 |

## 注释分类口径

本目录采用三类注释/评估口径：

| 类别 | 说明 | 当前来源 |
|---|---|---|
| `general_functional_annotation` | 通用功能注释，描述基因/蛋白的一般功能、同源、通路或产物信息 | funannotate annotate、eggNOG/KEGG |
| `pathogenicity_associated_annotation` | 致病相关特征注释，表示与分泌、宿主互作、侵染、降解、次生代谢等过程相关的候选特征 | SignalP6、EffectorP、CAZyme/dbCAN、MEROPS、antiSMASH |
| `quality_control` | 数据质量评估，不属于功能或致病相关注释 | BUSCO |

注意：`pathogenicity_associated_annotation` 表示“致病相关特征”或“宿主互作相关候选特征”，不等同于已经实验证实的致病基因。

## 目录结构

```text
00_ready-for-database/
├── README.md
├── scripts/
│   └── build_ready_tables.py
├── tables/
│   ├── master_sample_index.tsv
│   ├── genome_summary.tsv
│   ├── general_functional_annotation_summary.tsv
│   ├── functional_annotation_summary.tsv
│   ├── pathogenicity_associated_summary.tsv
│   ├── annotation_sources.tsv
│   ├── busco_summary.tsv
│   ├── antismash_genome_summary.tsv
│   ├── signalp_summary.tsv
│   ├── proteins.tsv
│   ├── protein_general_annotation_summary.tsv
│   ├── kegg_pathway_members.tsv
│   ├── protein_pathogenicity_summary.tsv
│   ├── protein_pathogenicity_features.tsv
│   ├── analysis_status_matrix.tsv
│   └── sample_file_paths.tsv
├── checks/
│   ├── missing_by_analysis.tsv
│   └── unmatched_source_records.tsv
├── manifests/
│   ├── ready_manifest.json
│   └── source_manifest.tsv
└── docs/
    ├── table_dictionary.md
    └── update_workflow.md
```

## 主键约定

- `sample_id`：数据库推荐主键，来自现有样本缩写，例如 `Bbas_MBC_306`。
- `full_name`：原始样本/目录名，例如 `Beauveria_bassiana_MBC_306`。
- `protein_uid`：蛋白级推荐主键，格式为 `sample_id|protein_id`，例如 `A_G78|FUN_000005-T1`。
- 路径字段全部使用相对路径，基准目录为项目根目录 `/data/home/zhangchaowei/project/fungi-database`。

## 基因/蛋白级检索

如果目标是“点开某个物种/菌株，再检索某个 KEGG 通路有哪些基因”，数据库开发者应重点导入：

- `tables/proteins.tsv`：蛋白/基因主表，一行一个蛋白。
- `tables/protein_general_annotation_summary.tsv`：蛋白级通用功能注释宽表。
- `tables/kegg_pathway_members.tsv`：KEGG 通路成员表，一行表示一个蛋白属于一个 KEGG pathway。
- `tables/protein_pathogenicity_summary.tsv`：蛋白级致病相关特征宽表。
- `tables/protein_pathogenicity_features.tsv`：SignalP、EffectorP、CAZyme、MEROPS 的蛋白级特征长表。

典型查询逻辑：

```text
sample_id = A_G78
kegg_pathway_id = ko00511
```

在 `kegg_pathway_members.tsv` 中筛选这两个字段，即可得到该菌株在该 KEGG 通路下的基因/蛋白列表，再用 `protein_uid` 关联 `proteins.tsv` 和 `protein_general_annotation_summary.tsv` 展示位置、product、KO、description 等信息。

## 重建方式

从项目根目录运行：

```bash
python3 00_ready-for-database/scripts/build_ready_tables.py
python3 00_ready-for-database/scripts/build_gene_search_tables.py
```

脚本只读取上游目录，不移动、不删除、不修改 `01` 到 `05` 的原始结果。

## 当前查漏点

- `BUSCO`：`Drechmeria_coniospora_ARSEF_6962` 有 BUSCO 目录，但没有 `run_hypocreales_odb12/short_summary.json`。
- `antiSMASH`：25 个主样本未匹配到 `04_antismash-bigscape/00_data/<full_name>/<full_name>.json`。
- `SignalP6`：6 个主样本未匹配到 `05_sigalp-protein-data/<sample_id>/prediction_results.txt`。
- `03_busco` 中还有 7 个目录不属于当前 655 个主样本，见 `checks/unmatched_source_records.tsv`。
