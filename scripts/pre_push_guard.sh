#!/bin/sh
# ============================================================
# EVOLUTION AI — pre-push 专利保护守卫 (patent pre-push guard)
#
# 为什么需要: 中国《专利法》第24条的宽限期不涵盖"自行公开"。
#   发明一(G2 连续 NURBS 构造方法)与发明二(NURBS 进化优化系统)
#   的核心实现在获得申请日之前, 一旦推送到公开仓库即构成现有技术,
#   直接破坏新颖性且不可补救(美国 AIA 有12个月发明人宽限, 中国/欧洲没有)。
#
# 行为: 对本次 push 中「尚未存在于任何远程分支」的提交, 扫描三类内容:
#   1) 新增代码行 (diff 添加行, 不含上下文行/删除行/已公开内容)
#   2) 新增/重命名文件的路径
#   3) 提交说明 (commit message)
# 命中任一专利敏感特征 → 阻断推送 (exit 1)。
# 已在远程分支上的内容不会重复扫描(避免 echarts 等历史文件的误报)。
#
# 用法:
#   安装到本仓库钩子:    sh scripts/pre_push_guard.sh --install
#   编码/规则自检:       sh scripts/pre_push_guard.sh --selftest
#   手动模拟(测试用):    echo "<local-ref> <sha> <remote-ref> <sha>" | sh .git/hooks/pre-push
#   临时放行(专利已获申请日或经权利人书面确认):
#                        EVOAI_ALLOW_PUSH=1 git push ...
#
# 维护: 新增敏感特征直接编辑下方两个特征表, 然后在各工作克隆重新 --install。
#       注意: 本守卫只保护装有钩子的克隆, 其他 AI 工具的克隆需各自安装。
# ============================================================

LC_ALL=C
export LC_ALL

ZEROS=0000000000000000000000000000000000000000

# 守卫脚本自身必然包含特征表字符串, 扫描 diff 时按文件豁免, 否则自阻断
# (字面路径, 配合 awk index() 使用; 重命名脚本时同步改这里)
GUARD_SELF='scripts/pre_push_guard.sh'

PAT_FILE=$(mktemp)   || { echo "守卫: 无法创建临时文件" >&2; exit 2; }
PATHS_FILE=$(mktemp) || { echo "守卫: 无法创建临时文件" >&2; exit 2; }
DIFF_OUT=$(mktemp)   || { echo "守卫: 无法创建临时文件" >&2; exit 2; }
trap 'rm -f "$PAT_FILE" "$PATHS_FILE" "$DIFF_OUT"' EXIT

# ---- 内容特征表 (逐行一条, grep -E 语法, 大小写不敏感) ----
# ASCII 标识符 = 代码指纹; 中文词 = 注释/文档指纹
cat >"$PAT_FILE" <<'EOP'
kv_target
g2_k
use_g2
nsga
mvfsa
continuitychecker
圆顶
法曲率
0\.35[^0-9]{0,60}0\.25[^0-9]{0,60}0\.20
EOP

# ---- 路径黑名单: 发明二的工程实现文件 (ba3a4434 确认仅存本地历史) ----
cat >"$PATHS_FILE" <<'EOP'
services/optimization/
nurbs_generator\.py
saga\.py
mvfsa\.py
control_point_optimizer\.py
optimization_routes\.py
EOP

case "$1" in
  --install)
    hook_dir=$(git rev-parse --git-path hooks 2>/dev/null) || {
      echo "守卫: 未找到 git 仓库, 请在仓库内执行安装" >&2; exit 2; }
    [ -d "$hook_dir" ] || mkdir -p "$hook_dir"
    hook="$hook_dir/pre-push"
    if [ -f "$hook" ]; then
      if diff -q "$hook" "$0" >/dev/null 2>&1; then
        echo "✓ 守卫已是最新, 无需重装: $hook"
        exit 0
      fi
      backup="$hook.bak-$(date +%Y%m%d%H%M%S)"
      cp "$hook" "$backup"
      echo "  已备份原有钩子 → $backup"
    fi
    cp "$0" "$hook" && chmod +x "$hook" 2>/dev/null
    echo "✓ pre-push 专利守卫已安装: $hook"
    echo "  建议: sh scripts/pre_push_guard.sh --selftest 验证特征编码"
    exit 0
    ;;
  --selftest)
    ok=1
    s1=$(printf '+ kv_target = 0.8' | grep -i -E -f "$PAT_FILE")
    [ -n "$s1" ] || ok=0
    s2=$(printf '+ # 圆顶封口与法曲率匹配测试' | grep -i -E -f "$PAT_FILE")
    [ -n "$s2" ] || ok=0
    s3=$(printf 'A\tbackend/app/services/optimization/saga.py' | grep -E -f "$PATHS_FILE")
    [ -n "$s3" ] || ok=0
    s4=$(printf '+ fitness = 0.35*q + 0.25*c + 0.20*s' | grep -i -E -f "$PAT_FILE")
    [ -n "$s4" ] || ok=0
    s5=$(printf '+ 普通业务代码, 无敏感特征的一行' | grep -i -E -f "$PAT_FILE")
    [ -z "$s5" ] || ok=0
    # 守卫脚本自身含特征表字符串, diff 中必须按文件豁免
    s6=$(printf 'diff --git a/scripts/pre_push_guard.sh b/scripts/pre_push_guard.sh\n+kv_target\n' \
      | GUARD_SELF="$GUARD_SELF" awk '/^diff --git / { skip = (index($0, "b/" ENVIRON["GUARD_SELF"]) > 0) }
             /^\+/ && !/^\+\+\+/ && !skip { print }' \
      | grep -i -E -f "$PAT_FILE")
    [ -z "$s6" ] || ok=0
    s7=$(printf 'diff --git a/backend/app/x.py b/backend/app/x.py\n+kv_target = 0.8\n' \
      | GUARD_SELF="$GUARD_SELF" awk '/^diff --git / { skip = (index($0, "b/" ENVIRON["GUARD_SELF"]) > 0) }
             /^\+/ && !/^\+\+\+/ && !skip { print }' \
      | grep -i -E -f "$PAT_FILE")
    [ -n "$s7" ] || ok=0
    if [ "$ok" = "1" ]; then
      echo "✓ selftest PASS: ASCII/中文/权重公式命中, 负样本不误报, 自豁免有效"
      exit 0
    fi
    echo "✗ selftest FAIL: s1=[$s1] s2=[$s2] s3=[$s3] s4=[$s4] s5=[$s5] s6=[$s6] s7=[$s7]" >&2
    echo "  常见原因: 文件被转成 CRLF/BOM 编码 — 用 UTF-8(无BOM)+LF 重新保存" >&2
    exit 1
    ;;
esac

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "pre-push 守卫: 当前目录不在 git 仓库内" >&2; exit 2; }

if [ "${EVOAI_ALLOW_PUSH:-0}" = "1" ]; then
  echo "⚠  EVOAI_ALLOW_PUSH=1: 专利守卫本次放行 (请确认专利申请已获申请日)" >&2
  exit 0
fi

blocked=0
while read -r local_ref local_sha remote_ref remote_sha; do
  [ -n "$local_sha" ] || continue
  [ "$local_sha" = "$ZEROS" ] && continue   # 分支删除, 无公开内容

  # 本次推送中"尚未存在于任何远程分支"的提交 = 将被新公开的内容
  new_commits=$(git rev-list "$local_sha" --not --remotes 2>/dev/null)
  [ -n "$new_commits" ] || continue

  # 1) 提交说明
  msg_hits=$(printf '%s\n' "$new_commits" \
    | git log --format=%B --stdin --no-walk 2>/dev/null \
    | grep -i -E -f "$PAT_FILE")

  # 2) 新增/重命名文件路径
  path_hits=$(printf '%s\n' "$new_commits" \
    | git diff-tree --stdin --root -r -m --name-status 2>/dev/null \
    | grep -E -f "$PATHS_FILE")

  # 3) 新增代码行 (排除 +++ 文件头; 按文件豁免守卫脚本自身)
  printf '%s\n' "$new_commits" \
    | git diff-tree --stdin -p --root -r -m > "$DIFF_OUT" 2>/dev/null
  content_hits=$(GUARD_SELF="$GUARD_SELF" awk '
      /^diff --git / { skip = (index($0, "b/" ENVIRON["GUARD_SELF"]) > 0) }
      /^\+/ && !/^\+\+\+/ && !skip { print }
    ' "$DIFF_OUT" | grep -i -E -f "$PAT_FILE")

  if [ -n "$msg_hits" ] || [ -n "$path_hits" ] || [ -n "$content_hits" ]; then
    blocked=1
    {
      echo ""
      echo "============================================================"
      echo "⛔ EVOLUTION AI 专利守卫: 本次推送包含专利敏感内容, 已阻断"
      echo "   分支: $local_ref → $remote_ref"
      if [ -n "$path_hits" ]; then
        echo "---- 敏感文件路径 ----"
        printf '%s\n' "$path_hits" | head -30
      fi
      if [ -n "$content_hits" ]; then
        echo "---- 敏感代码行 ----"
        printf '%s\n' "$content_hits" | head -40
      fi
      if [ -n "$msg_hits" ]; then
        echo "---- 敏感提交说明 ----"
        printf '%s\n' "$msg_hits" | head -20
      fi
      echo "------------------------------------------------------------"
      echo "中国《专利法》第24条无自行公开宽限期: 申请日前公开将不可逆地"
      echo "破坏 EVOL-PAT-2026-001 两项发明的新颖性。"
      echo "处理: 移除/改写上述内容后再推送;"
      echo "      或经权利人确认后 EVOAI_ALLOW_PUSH=1 git push ... 临时放行。"
      echo "============================================================"
    } >&2
  fi
done

if [ "$blocked" = "1" ]; then
  exit 1
fi
echo "✓ pre-push 守卫通过: 本次推送不含专利敏感内容" >&2
exit 0
