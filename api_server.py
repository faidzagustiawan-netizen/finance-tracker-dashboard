#!/usr/bin/env python3
"""
Finance Tracker API Server
Serves JSON data untuk dashboard
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from finance_tracker import FinanceTracker
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

# Initialize tracker
tracker = FinanceTracker("finance.db")

# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    })

# ─────────────────────────────────────────────
# Balance Endpoints
# ─────────────────────────────────────────────

@app.route('/api/balance', methods=['GET'])
def get_balance():
    """Get current balance (income - expense)"""
    try:
        balance_data = tracker.get_balance()
        return jsonify({
            'status': 'success',
            'data': {
                'income': balance_data['income'],
                'expense': balance_data['expense'],
                'balance': balance_data['balance'],
                'currency': 'IDR',
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ─────────────────────────────────────────────
# Expense Endpoints
# ─────────────────────────────────────────────

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """Get expenses breakdown by category (current month)"""
    try:
        month = request.args.get('month')  # Format: YYYY-MM
        expenses = tracker.get_expense_by_category(month)
        
        # Format untuk chart
        categories = [e['category'] for e in expenses]
        amounts = [e['total'] for e in expenses]
        percentages = [e['percentage'] for e in expenses]
        
        return jsonify({
            'status': 'success',
            'data': {
                'expenses': expenses,
                'categories': categories,
                'amounts': amounts,
                'percentages': percentages,
                'total': sum(amounts),
                'count': len(expenses),
                'month': month or datetime.now().strftime('%Y-%m')
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """Get recent transactions"""
    try:
        limit = request.args.get('limit', 50, type=int)
        trans_type = request.args.get('type')  # 'income', 'expense', or None (all)
        
        conn = tracker.get_connection()
        cursor = conn.cursor()
        
        # Query with category name JOIN
        base_query = """
        SELECT t.id, t.amount, COALESCE(t.description, ''), c.name, t.date, t.type
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        """
        
        if trans_type:
            base_query += f" WHERE t.type = ?"
            cursor.execute(base_query + " ORDER BY t.date DESC LIMIT ?", (trans_type, limit))
        else:
            cursor.execute(base_query + " ORDER BY t.date DESC LIMIT ?", (limit,))
        
        rows = cursor.fetchall()
        
        transactions = []
        for row in rows:
            transactions.append({
                'id': row[0],
                'amount': row[1],
                'description': row[2],
                'category': row[3] or 'N/A',
                'date': row[4],
                'type': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'transactions': transactions,
                'count': len(transactions)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ─────────────────────────────────────────────
# Debt Endpoints
# ─────────────────────────────────────────────

@app.route('/api/debts', methods=['GET'])
def get_debts():
    """Get all pending debts"""
    try:
        debts_raw = tracker.get_all_pending_debts()
        
        # Map schema type ('owe'/'owed') to response type
        debts = []
        for d in debts_raw:
            debts.append({
                'id': d['id'],
                'friend': d['friend_name'],
                'amount': d['amount'],
                'type': 'owe' if d['type'] == 'owe' else 'receivable',
                'date': d['date'],
                'description': d.get('description', '')
            })
        
        # Separate owe vs receivable
        owe = [d for d in debts if d['type'] == 'owe']
        receivable = [d for d in debts if d['type'] == 'receivable']
        
        total_owe = sum(d['amount'] for d in owe)
        total_receivable = sum(d['amount'] for d in receivable)
        
        return jsonify({
            'status': 'success',
            'data': {
                'all_debts': debts,
                'owe': owe,
                'receivable': receivable,
                'total_owe': total_owe,
                'total_receivable': total_receivable,
                'net_balance': total_receivable - total_owe,
                'count': len(debts)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/debts/<friend_name>', methods=['GET'])
def get_friend_debt(friend_name):
    """Get debt detail dengan specific friend"""
    try:
        debt_info = tracker.get_friend_debts(friend_name)
        return jsonify({
            'status': 'success',
            'data': {
                'friend': friend_name,
                'debts': debt_info
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ─────────────────────────────────────────────
# Summary Endpoints
# ─────────────────────────────────────────────

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Get complete financial summary"""
    try:
        balance = tracker.get_balance()
        expenses = tracker.get_expense_by_category()
        debts = tracker.get_all_pending_debts()
        
        owe = [d for d in debts if d['type'] == 'owe']
        receivable = [d for d in debts if d['type'] == 'receivable']
        
        return jsonify({
            'status': 'success',
            'data': {
                'balance': {
                    'income': balance['income'],
                    'expense': balance['expense'],
                    'net': balance['balance']
                },
                'expenses_by_category': expenses,
                'debts': {
                    'owe_total': sum(d['amount'] for d in owe),
                    'receivable_total': sum(d['amount'] for d in receivable),
                    'count': len(debts)
                },
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ─────────────────────────────────────────────
# Statistics Endpoints
# ─────────────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get financial statistics"""
    try:
        balance = tracker.get_balance()
        expenses = tracker.get_expense_by_category()
        
        if expenses:
            top_category = max(expenses, key=lambda x: x['total'])
            avg_expense = balance['expense'] / len(expenses) if expenses else 0
        else:
            top_category = None
            avg_expense = 0
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_income': balance['income'],
                'total_expense': balance['expense'],
                'remaining': balance['balance'],
                'expense_ratio': (balance['expense'] / balance['income'] * 100) if balance['income'] > 0 else 0,
                'top_category': top_category,
                'avg_per_category': avg_expense,
                'categories_count': len(expenses)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ─────────────────────────────────────────────
# Error Handlers
# ─────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print("🚀 Finance Tracker API Server")
    print("📊 Running on http://127.0.0.1:5000")
    print("📍 Endpoints:")
    print("   GET  /health")
    print("   GET  /api/balance")
    print("   GET  /api/expenses")
    print("   GET  /api/transactions")
    print("   GET  /api/debts")
    print("   GET  /api/debts/<friend_name>")
    print("   GET  /api/summary")
    print("   GET  /api/stats")
    print("")
    
    # Run on all interfaces, port 5000
    app.run(host='127.0.0.1', port=5000, debug=False)
