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
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        balance_data = tracker.get_balance(start_date, end_date)
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
    """Get expenses breakdown by category"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        expenses = tracker.get_expense_by_category(start_date, end_date)
        
        # Format untuk chart
        categories = [e.get('name', '') for e in expenses]
        amounts = [e.get('total', 0) for e in expenses]
        
        total_amount = sum(amounts)
        percentages = [round((a / total_amount * 100), 2) for a in amounts] if total_amount > 0 else []
        
        return jsonify({
            'status': 'success',
            'data': {
                'expenses': expenses,
                'categories': categories,
                'amounts': amounts,
                'percentages': percentages,
                'total': total_amount,
                'count': len(expenses),
                'start_date': start_date,
                'end_date': end_date
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
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = tracker.get_connection()
        cursor = conn.cursor()
        
        # Query with category name and account JOIN
        base_query = """
        SELECT t.id, t.amount, COALESCE(t.description, ''), c.name, t.date, t.type,
               t.account_id, COALESCE(a.name, 'Cash') as account_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN accounts a ON t.account_id = a.id
        WHERE 1=1
        """
        
        params = []
        if trans_type:
            base_query += " AND t.type = ?"
            params.append(trans_type)
            
        if start_date and end_date:
            base_query += " AND t.date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
            
        base_query += " ORDER BY t.date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(base_query, params)
        
        rows = cursor.fetchall()
        
        transactions = []
        for row in rows:
            transactions.append({
                'id': row[0],
                'amount': row[1],
                'description': row[2],
                'category': row[3] or 'N/A',
                'date': row[4],
                'type': row[5],
                'account_id': row[6],
                'account_name': row[7]
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
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        balance = tracker.get_balance(start_date, end_date)
        expenses = tracker.get_expense_by_category(start_date, end_date)
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
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        balance = tracker.get_balance(start_date, end_date)
        expenses = tracker.get_expense_by_category(start_date, end_date)
        
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
# Account Endpoints
# ─────────────────────────────────────────────

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Get all accounts with balances"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        accounts = tracker.get_accounts()
        balances = tracker.get_account_balances(start_date, end_date)
        # Merge balance into account data
        balance_map = {b['account_id']: b for b in balances}
        result = []
        for a in accounts:
            bal = balance_map.get(a['id'], {})
            result.append({
                'id': a['id'],
                'name': a['name'],
                'type': a['type'],
                'icon': a['icon'],
                'color': a['color'],
                'income': bal.get('income', 0),
                'expense': bal.get('expense', 0),
                'balance': bal.get('income', 0) - bal.get('expense', 0)
            })
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        trans_type = request.args.get('type')
        cats = tracker.get_categories(trans_type)
        return jsonify({'status': 'success', 'data': cats})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ─────────────────────────────────────────────
# CRUD & Chat Endpoints
# ─────────────────────────────────────────────

from command_handler import FinanceCommandHandler
cmd_handler = FinanceCommandHandler("finance.db")

@app.route('/api/chat', methods=['POST'])
def chat_input():
    """Handle natural language input via dashboard"""
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({'status': 'error', 'message': 'Text required'}), 400
        
        force = data.get('force', False)
        response = cmd_handler.handle_message(data['text'], force)
        
        if isinstance(response, dict) and response.get('action') == 'confirm':
            return jsonify({
                'status': 'confirm',
                'data': response
            })
            
        return jsonify({
            'status': 'success',
            'data': {
                'response': response
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    """Delete a transaction"""
    try:
        conn = tracker.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/transactions/<int:tx_id>', methods=['PUT'])
def update_transaction(tx_id):
    """Update a transaction"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data'}), 400
        success = tracker.update_transaction(
            tx_id,
            amount=data.get('amount'),
            description=data.get('description'),
            category_name=data.get('category'),
            account_id=data.get('account_id'),
            date=data.get('date')
        )
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Transaction not found'}), 404
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
