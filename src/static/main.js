// 主要 JavaScript 功能（如果需要額外的功能）

// 格式化金額顯示
function formatCurrency(amount) {
    return new Intl.NumberFormat('zh-TW', {
        style: 'currency',
        currency: 'TWD',
        minimumFractionDigits: 0
    }).format(amount);
}

