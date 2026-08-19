# 更新与维护流程

## 核心原则

1. `01_genome-data` 是主样本来源。
2. `sample_id` 使用样本缩写，`full_name` 使用原始目录名。
3. `00_ready-for-database` 是可重建目录，不应手工修改 `tables/` 中的结果表。
4. 新增、删除或替换上游数据后，重跑 `scripts/build_ready_tables.py`。
5. 入库前必须检查 `checks/` 和 `manifests/ready_manifest.json`。

## 新增样本

新增一个样本时，建议按以下顺序补齐：

1. 在 `01_genome-data/<order_group>/<full_name>/` 放置核心文件：
   - `*.scaffolds.fa`
   - `*.cds.fa`
   - `*.gff3`
   - `*.gbk`
2. 更新或重建 `genome_stats_2026-05-12.csv`。
3. 更新 `strain_abbreviation_map.csv`，确保新样本有唯一缩写。
4. 在 `02_annotation-protein-data` 补齐蛋白和功能注释结果。
5. 根据需要补 BUSCO、antiSMASH、SignalP6。
6. 重跑：

```bash
python3 00_ready-for-database/scripts/build_ready_tables.py
python3 00_ready-for-database/scripts/build_gene_search_tables.py
```

7. 检查新样本是否出现在：
   - `tables/master_sample_index.tsv`
   - `tables/analysis_status_matrix.tsv`
   - `checks/missing_by_analysis.tsv`

## 删除样本

删除样本时，不建议只删除某个分析目录。应先确认主样本是否从 `01_genome-data` 和 `genome_stats_2026-05-12.csv` 中移除。

推荐步骤：

1. 从主数据源中移除样本目录或从 `genome_stats_2026-05-12.csv` 移除记录。
2. 同步处理缩写映射。
3. 上游分析结果可先保留，但重跑后会进入 `checks/unmatched_source_records.tsv`。
4. 数据库端根据新的 `master_sample_index.tsv` 进行软删除或版本化处理。

## 替换或更新某个分析

如果只更新某个模块，例如重新跑 antiSMASH：

1. 覆盖或新增 `04_antismash-bigscape/00_data/<full_name>/` 的结果。
2. 更新对应的 QC/汇总表，例如 `09_antismash_family_qc/genome_qc.tsv`。
3. 重跑构建脚本。
4. 检查 `has_antismash`、`bgc_count`、`antismash_json_path` 是否符合预期。

## 数据库导入建议

推荐关系模型：

| 数据库表 | 来源 TSV | 粒度 |
|---|---|---|
| `samples` | `master_sample_index.tsv` | 样本 |
| `genome_metrics` | `genome_summary.tsv` | 样本 |
| `annotation_sources` | `annotation_sources.tsv` | 注释来源 |
| `general_functional_annotation_summary` | `general_functional_annotation_summary.tsv` | 样本 |
| `pathogenicity_associated_summary` | `pathogenicity_associated_summary.tsv` | 样本 |
| `proteins` | `proteins.tsv` | 蛋白 |
| `protein_general_annotation_summary` | `protein_general_annotation_summary.tsv` | 蛋白 |
| `kegg_pathway_members` | `kegg_pathway_members.tsv` | 蛋白-KEGG pathway |
| `protein_pathogenicity_summary` | `protein_pathogenicity_summary.tsv` | 蛋白 |
| `protein_pathogenicity_features` | `protein_pathogenicity_features.tsv` | 蛋白-特征 |
| `busco_summary` | `busco_summary.tsv` | 样本 |
| `antismash_genome_summary` | `antismash_genome_summary.tsv` | 样本 |
| `signalp_summary` | `signalp_summary.tsv` | 样本 |
| `sample_files` | `sample_file_paths.tsv` | 样本-文件 |
| `analysis_status` | `analysis_status_matrix.tsv` | 样本 |

其中 `sample_id` 可作为主键或外键。若未来担心缩写变化，可以在数据库内部增加自增 ID 或 UUID，但仍保留 `sample_id` 和 `full_name` 两个业务键。

`functional_annotation_summary.tsv` 会继续生成，作为旧命名兼容表；新开发建议使用 `general_functional_annotation_summary.tsv`。CAZyme、MEROPS、SignalP6、EffectorP、antiSMASH 统一在 `pathogenicity_associated_summary.tsv` 中体现，解释为“致病相关/宿主互作相关候选特征”，不要在数据库字段或前端文案中直接写成“已验证致病基因”。

## 基因/蛋白级检索索引建议

为了支持“进入某个菌株后查某个 KEGG 通路有哪些基因”，数据库建议建立这些索引：

| 表 | 推荐索引 |
|---|---|
| `proteins` | `protein_uid`、`sample_id`、`sample_id + protein_id` |
| `protein_general_annotation_summary` | `protein_uid`、`sample_id`、`kegg_ko` |
| `kegg_pathway_members` | `sample_id + kegg_pathway_id`、`protein_uid`、`kegg_ko` |
| `protein_pathogenicity_summary` | `protein_uid`、`sample_id`、`is_secreted`、`is_effector_candidate` |
| `protein_pathogenicity_features` | `sample_id + feature_type`、`protein_uid`、`source_key`、`feature_id` |

典型查询流程：

1. 用户进入样本 `A_G78`。
2. 用户选择 KEGG pathway `ko00511`。
3. 后端查询 `kegg_pathway_members`：

```sql
SELECT *
FROM kegg_pathway_members
WHERE sample_id = 'A_G78'
  AND kegg_pathway_id = 'ko00511';
```

4. 用返回的 `protein_uid` 关联 `proteins`、`protein_general_annotation_summary` 和 `protein_pathogenicity_summary`，展示基因位置、KO、描述、是否分泌、是否候选 effector、是否 CAZyme/MEROPS。

## 推荐的版本控制方式

当前阶段的项目管理和备份执行规范见 `docs/project_management.md`。原则是代码和文档进入 Git，大型数据和数据库文件在重要节点做快照备份。

每次正式入库前保存以下信息：

- `manifests/ready_manifest.json`
- `manifests/source_manifest.tsv`
- `checks/missing_by_analysis.tsv`
- `checks/unmatched_source_records.tsv`

如果数据库需要支持历史版本，可以新增一个 `dataset_release` 字段或发布号，例如：

```text
fungi_db_20260703
```

入库时把发布号写入每张业务表，后续新增样本或重跑分析时生成新的 release。

## 当前脚本已处理的命名差异

构建脚本对以下情况做了兼容：

- 部分样本 `scaffolds.fa`/`gff3` 使用 `<full_name>_Default` 前缀，而 `cds.fa`/`gbk` 使用 `<full_name>` 前缀。
- 功能注释文件可能使用 `<full_name>` 或 `<file_prefix>`。
- BUSCO 中部分目录名含 `,_`，例如 `Costa_Rica,_ECA_0`，会规范化匹配到 `Costa_Rica_ECA_0`。

这些兼容只发生在索引层，不会重命名上游原始目录。

## 每次重建后的最小检查

```bash
cat 00_ready-for-database/manifests/ready_manifest.json
awk -F'\t' 'NR>1{c[$1]++} END{for(k in c) print k,c[k]}' \
  00_ready-for-database/checks/missing_by_analysis.tsv
cat 00_ready-for-database/checks/unmatched_source_records.tsv
```

当前期望结果大致为：

- 主样本：655
- `ready_basic_db`：655
- `ready_full_analysis`：625
- 缺失分析记录：32
- 未匹配上游记录：7
