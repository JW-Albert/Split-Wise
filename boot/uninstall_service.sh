#!/bin/bash

# Split-Wise 開機自動啟動卸載腳本

echo "正在卸載 Split-Wise 開機自動啟動服務..."

# 停止服務
sudo systemctl stop splitwise.service

# 禁用開機自動啟動
sudo systemctl disable splitwise.service

# 刪除 service 文件
sudo rm /etc/systemd/system/splitwise.service

# 重新載入 systemd
sudo systemctl daemon-reload

echo "卸載完成！"

