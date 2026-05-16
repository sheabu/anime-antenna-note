#!/usr/bin/env bash
# launchd ジョブのインストール / アンインストール。
#   ./install_launchd.sh install     # 登録（既存があれば置き換え）
#   ./install_launchd.sh uninstall   # 解除
#   ./install_launchd.sh status      # 状態確認
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
LABELS=(
  "com.abesho.anime-automation.daily-briefing"
  "com.abesho.anime-automation.auto-pilot"
)

cmd="${1:-install}"

case "$cmd" in
  install)
    mkdir -p "$AGENTS"
    for label in "${LABELS[@]}"; do
      src="$DIR/$label.plist"
      dst="$AGENTS/$label.plist"
      # __AUTOMATION_DIR__ を実パスに置換して配置
      sed "s|__AUTOMATION_DIR__|$DIR|g" "$src" > "$dst"
      launchctl unload "$dst" 2>/dev/null || true
      launchctl load "$dst"
      echo "登録: $label"
    done
    chmod +x "$DIR/run.sh"
    echo "完了。'$0 status' で確認できます。"
    ;;
  uninstall)
    for label in "${LABELS[@]}"; do
      dst="$AGENTS/$label.plist"
      launchctl unload "$dst" 2>/dev/null || true
      rm -f "$dst"
      echo "解除: $label"
    done
    ;;
  status)
    for label in "${LABELS[@]}"; do
      if launchctl list | grep -q "$label"; then
        echo "稼働中: $label"
        launchctl list "$label" | grep -E '"(PID|LastExitStatus)"' || true
      else
        echo "未登録: $label"
      fi
    done
    ;;
  *)
    echo "usage: $0 {install|uninstall|status}" >&2
    exit 1
    ;;
esac
