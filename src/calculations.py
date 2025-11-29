from database import get_db
from collections import defaultdict

def calculate_settlement(room_id):
    """
    計算房間的結算結果
    
    回傳格式：
    {
        "balances": [{"email": "A", "balance": -600}, ...],
        "payments": [{"from": "A", "to": "B", "amount": 600}, ...]
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 取得所有支出
    cursor.execute(
        "SELECT id, title, amount, payer_email FROM expenses WHERE room_id=?",
        (room_id,)
    )
    expenses = cursor.fetchall()
    
    # 計算每人的 total_paid 和 total_share
    total_paid = defaultdict(int)  # 每人總共付了多少
    total_share = defaultdict(int)  # 每人應該負擔多少
    
    for expense in expenses:
        expense_id = expense[0]
        amount = expense[2]
        payer_email = expense[3]
        
        # 取得參與者
        cursor.execute(
            "SELECT email FROM expense_participants WHERE expense_id=?",
            (expense_id,)
        )
        participants = cursor.fetchall()
        
        if not participants:
            continue
        
        participant_count = len(participants)
        share_per_person = amount // participant_count
        
        # 記錄付款者
        total_paid[payer_email] += amount
        
        # 記錄每個參與者的負擔
        for participant in participants:
            total_share[participant[0]] += share_per_person
    
    conn.close()
    
    # 計算 balance = total_paid - total_share
    balances = {}
    for email in set(list(total_paid.keys()) + list(total_share.keys())):
        balances[email] = total_paid[email] - total_share[email]
    
    # 轉換為列表格式
    balance_list = [{"email": email, "balance": balance} 
                    for email, balance in balances.items()]
    
    # 分離債權人和債務人
    creditors = [(email, balance) for email, balance in balances.items() if balance > 0]
    debtors = [(email, -balance) for email, balance in balances.items() if balance < 0]
    
    # 排序：債權人從大到小，債務人從大到小
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    
    # 雙指針配對算法
    payments = []
    i = 0  # 債權人索引
    j = 0  # 債務人索引
    
    while i < len(creditors) and j < len(debtors):
        creditor_email, creditor_amount = creditors[i]
        debtor_email, debtor_amount = debtors[j]
        
        payment_amount = min(creditor_amount, debtor_amount)
        
        if payment_amount > 0:
            payments.append({
                "from": debtor_email,
                "to": creditor_email,
                "amount": payment_amount
            })
        
        creditors[i] = (creditor_email, creditor_amount - payment_amount)
        debtors[j] = (debtor_email, debtor_amount - payment_amount)
        
        if creditors[i][1] == 0:
            i += 1
        if debtors[j][1] == 0:
            j += 1
    
    return {
        "balances": balance_list,
        "payments": payments
    }

