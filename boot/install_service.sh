#!/bin/bash

# Split-Wise 開機自動啟動安裝腳本

echo "正在安裝 Split-Wise 開機自動啟動服務..."

# 獲取當前腳本所在目錄的父目錄（專案根目錄）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 複製 service 文件到 systemd 目錄
sudo cp "$SCRIPT_DIR/splitwise.service" /etc/systemd/system/splitwise.service

# 替換 service 文件中的路徑
sudo sed -i "s|/root/Split-Wise|$PROJECT_DIR|g" /etc/systemd/system/splitwise.service

# 重新載入 systemd
sudo systemctl daemon-reload

# 啟用服務（開機自動啟動）
sudo systemctl enable splitwise.service

# 啟動服務
sudo systemctl start splitwise.service

echo "安裝完成！"
echo ""
echo "服務管理命令："
echo "  啟動服務: sudo systemctl start splitwise"
echo "  停止服務: sudo systemctl stop splitwise"
echo "  重啟服務: sudo systemctl restart splitwise"
echo "  查看狀態: sudo systemctl status splitwise"
echo "  查看日誌: sudo journalctl -u splitwise -f"
echo "  禁用開機啟動: sudo systemctl disable splitwise"

