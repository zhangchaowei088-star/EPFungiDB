# EPFungiDB 最小项目管理与备份规范

本文档记录当前阶段采用的最小管理体系。原则是先保证可执行、可坚持、可回溯，不提前引入复杂的数据版本系统。

## 管理边界

本项目分为两类内容管理：

| 类型 | 管理方式 | 说明 |
|---|---|---|
| 代码与文档 | Git | Django 后端、模板、静态文件、导入脚本、说明文档 |
| 数据与数据库快照 | 重要节点备份 | 大型 TSV、SQLite 数据库、上游分析结果、日志 |

不要把百万行 TSV、`db.sqlite3`、大图、日志或完整分析结果提交到 Git。当前 `tables/` 中有多个 GB 级文件，适合做快照备份，不适合做 Git 历史。

## Git 管理范围

建议纳入 Git 的内容：

```text
config/
database/
scripts/
docs/
README.md
README_BACKEND.md
requirements.txt
.gitignore
manage.py
```

不纳入 Git 的内容：

```text
db.sqlite3
tables/*.tsv
checks/*.tsv
manifests/*.json
manifests/*.tsv
*.log
截图和临时设计文件
```

这些忽略规则已经写入项目根目录的 `.gitignore`。

## 最小日常流程

每完成一组相关修改，先检查状态：

```bash
git status
```

查看具体变更：

```bash
git diff
```

确认没问题后提交代码：

```bash
git add .gitignore README.md README_BACKEND.md docs config database scripts manage.py requirements.txt
git commit -m "Describe the completed change"
```

提交信息建议直接说明做了什么，例如：

```text
Add bioassay and literature evidence pages
Update genome detail host metadata display
Fix search form control alignment
```

## 重要节点

以下情况视为重要更新节点，需要同时做 Git 提交和数据/数据库备份：

- 新增或删除样本
- 重新生成 `tables/`
- 重新导入数据库
- 新增一个前端页面或主要 API
- 大幅修改数据库模型或导入脚本
- 准备给他人查看、汇报或阶段性发布

重要节点建议使用 tag 标记：

```bash
git tag -a v0.2.0 -m "EPFungiDB v0.2.0"
```

查看历史：

```bash
git log --oneline --graph --decorate --all
git show v0.2.0
```

## 数据和数据库备份

重要节点备份目录建议放在项目上一级或专门备份目录，不放入 Git：

```text
/data/home/zhangchaowei/project/fungi-database/backups/
```

最小备份内容：

```text
backups/
  2026-08-19_v0.2.0/
    db.sqlite3
    tables/
    checks/
    manifests/
    README_BACKUP.md
```

推荐备份命令：

```bash
BACKUP_ROOT=/data/home/zhangchaowei/project/fungi-database/backups
VERSION=v0.2.0
STAMP=$(date +%Y-%m-%d)_${VERSION}
DEST=${BACKUP_ROOT}/${STAMP}

mkdir -p "$DEST"
cp db.sqlite3 "$DEST/db.sqlite3"
rsync -a tables/ "$DEST/tables/"
rsync -a checks/ "$DEST/checks/"
rsync -a manifests/ "$DEST/manifests/"
```

生成校验文件：

```bash
find "$DEST" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$DEST/checksums.sha256"
```

写一个最小备份说明：

```bash
cat > "$DEST/README_BACKUP.md" <<EOF
# EPFungiDB backup ${STAMP}

- Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo "not recorded")
- Created at: $(date -Iseconds)
- Contents: db.sqlite3, tables, checks, manifests
- Note:
EOF
```

如果要备份完整上游分析结果，例如 `01_genome-data`、`02_annotation-protein-data`、`04_antismash-bigscape`，不要默认每次都复制。只有在正式发布、论文节点或大规模数据更新后再做完整归档。

## 当前阶段建议

当前阶段只执行四件事：

1. 用 Git 管理代码、页面、脚本和文档。
2. 不把大型数据文件提交到 Git。
3. 重要节点复制 `db.sqlite3`、`tables/`、`checks/`、`manifests/` 到备份目录。
4. 每个阶段性版本用 Git tag 标记。

暂时不引入 DVC、git-annex、自动 CI 或正式数据发布平台。等数据库结构稳定、需要公开发布或多人协作时，再升级管理体系。
