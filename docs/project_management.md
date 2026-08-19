# EPFungiDB 最小项目管理

当前阶段只做最小管理：**代码进 Git，数据做节点备份**。先保持简单、可执行、可回溯。

## 1. Git 管理

纳入 Git：

```text
config/ database/ scripts/ docs/
README.md README_BACKEND.md requirements.txt manage.py .gitignore
```

不纳入 Git：

```text
db.sqlite3
tables/*.tsv
checks/*.tsv
manifests/*.json
manifests/*.tsv
*.log
截图、临时设计文件、上游大数据
```

日常提交：

```bash
git status
git diff
git add .gitignore README.md README_BACKEND.md docs config database scripts manage.py requirements.txt
git commit -m "简短说明本次修改"
```

查看历史：

```bash
git log --oneline --graph --decorate --all
```

推送到 GitHub：

```bash
env -u LD_LIBRARY_PATH GIT_SSH_COMMAND="/usr/bin/ssh -i /data/home/zhangchaowei/.github-keys/epfungidb_ed25519 -o UserKnownHostsFile=/data/home/zhangchaowei/.github-keys/known_hosts" git push
```

说明：服务器的 conda 环境会影响系统 SSH 的 OpenSSL 库，因此推送时需要临时清空 `LD_LIBRARY_PATH`，并指定当前项目使用的 GitHub key。

重要阶段可打 tag：

```bash
git tag -a v0.2.0 -m "EPFungiDB v0.2.0"
```

## 2. 重要更新节点

以下情况需要 Git 提交，并考虑备份数据：

- 新增/删除样本
- 重新生成 `tables/`
- 重新导入数据库
- 新增主要页面或 API
- 修改数据库模型或导入脚本
- 阶段性汇报、展示、发布

## 3. 数据备份

备份位置：

```text
/data/home/zhangchaowei/project/fungi-database/backups/
```

最小备份内容：

```text
db.sqlite3
tables/
checks/
manifests/
README_BACKUP.md
checksums.sha256
```

备份命令：

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

find "$DEST" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$DEST/checksums.sha256"

cat > "$DEST/README_BACKUP.md" <<EOF
# EPFungiDB backup ${STAMP}

- Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo "not recorded")
- Created at: $(date -Iseconds)
- Contents: db.sqlite3, tables, checks, manifests
EOF
```

完整上游数据只在正式发布、论文节点或大规模更新后归档；平时不重复复制。

## 4. 当前原则

- 不引入 DVC、git-annex、CI。
- 不把大数据塞进 Git。
- 每次重要功能修改后提交 Git。
- 每次重要数据更新后做备份快照。
