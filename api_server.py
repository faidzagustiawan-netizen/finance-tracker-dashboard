#!/usr/bin/env python3
"""
Finance Tracker API Server
Serves JSON data untuk dashboard
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from finance_tracker import FinanceTracker
from command_handler import FinanceCommandHandler
from whatsapp_voice_handler import WhatsAppVoiceHandler
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

# Initialize tracker & handlers
tracker = FinanceTracker("finance.db")
command_handler = FinanceCommandHandler("finance.db")
voice_handler = WhatsAppVoiceHandler("finance.db")

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
                'type': a.get('account_type', 'wallet'),
                'icon': a.get('icon', '💰'),
                'color': a.get('color', '#3b82f6'),
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

@app.route('/api/debt/add', methods=['POST'])
def add_debt_endpoint():
    """Add new debt"""
    try:
        data = request.json
        friend = data.get('friend_name', '').strip()
        amount = int(data.get('amount', 0))
        dtype = data.get('type', 'owe')
        desc = data.get('description', '')
        if not friend or amount <= 0:
            return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
        conn = tracker.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO debts (friend_name, amount, type, description, date, status, created_at) VALUES (?, ?, ?, ?, date('now'), 'pending', datetime('now'))", (friend, amount, dtype, desc))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': f'Hutang ke {friend} Rp {amount:,} ditambahkan'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/debt/<int:debt_id>/pay', methods=['PUT'])
def pay_debt_endpoint(debt_id):
    """Mark debt as settled (paid)"""
    try:
        conn = tracker.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE debts SET status = 'settled', settled_date = date('now') WHERE id = ?", (debt_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Hutang ditandai lunas'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/debt/<int:debt_id>/delete', methods=['DELETE'])
def delete_debt_endpoint(debt_id):
    """Delete debt"""
    try:
        conn = tracker.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Hutang dihapus'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# ─────────────────────────────────────────────
# Voice Message Processing
# ─────────────────────────────────────────────

@app.route('/api/voice/transcribe', methods=['POST'])
def transcribe_voice():
    """
    Transcribe voice message to text (Bahasa Indonesia)
    Input: audio file (multipart/form-data)
    Output: transcribed text
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'status': 'error', 'message': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Save temp file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            audio_file.save(tmp.name)
            
            # Transcribe
            text = voice_handler.audio_processor.process_audio_file(tmp.name)
            
            # Cleanup
            import os
            os.unlink(tmp.name)
        
        if not text:
            return jsonify({'status': 'error', 'message': 'Failed to transcribe'}), 500
        
        return jsonify({
            'status': 'success',
            'text': text,
            'language': 'id'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/voice/process', methods=['POST'])
def process_voice_transaction():
    """
    Transcribe voice AND process as transaction
    Input: audio file (multipart/form-data)
    Output: transaction result
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'status': 'error', 'message': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Save temp file & transcribe
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            audio_file.save(tmp.name)
            text = voice_handler.audio_processor.process_audio_file(tmp.name)
            os.unlink(tmp.name)
        
        if not text:
            return jsonify({'status': 'error', 'message': 'Failed to transcribe'}), 500
        
        # Process as transaction
        result = command_handler.handle_message(text, force=False)
        
        return jsonify({
            'status': 'success',
            'transcribed_text': text,
            'processing_result': result
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ─────────────────────────────────────────────
# WhatsApp Webhook - Voice Messages
# ─────────────────────────────────────────────

@app.route('/api/whatsapp/voice', methods=['POST'])
def handle_whatsapp_voice():
    """
    Webhook endpoint for Hermes WhatsApp voice messages
    Auto-transcribe and process voice as finance transaction
    """
    try:
        # Verify webhook secret
        webhook_secret = request.headers.get('X-Webhook-Secret')
        if webhook_secret != 'finance-tracker-secret-2026':
            return jsonify({'status': 'error', 'message': 'Invalid secret'}), 401
        
        data = request.get_json()
        media_url = data.get('media_url')
        
        if not media_url:
            return jsonify({'status': 'error', 'message': 'No media URL'}), 400
        
        # Process voice message
        result = voice_handler.handle_voice_message(media_url, data.get('media_id'))
        
        if result.get('status') == 'error':
            reply = f"❌ Gagal: {result.get('message')}"
        else:
            transcribed = result.get('transcribed_text')
            processing = result.get('processing_result')
            reply = f"🎙️ *Transcribed:* {transcribed}\n\n"
            
            if isinstance(processing, dict) and processing.get('action') == 'confirm':
                reply += processing.get('message', 'Confirm transaksi?')
            elif isinstance(processing, str):
                reply += processing
            else:
                reply += str(processing)
        
        return jsonify({
            'status': 'success',
            'reply': reply,
            'auto_reply': True,
            'transcribed_text': result.get('transcribed_text')
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ─────────────────────────────────────────────
# Monitoring Alerts - WhatsApp Webhook
# ─────────────────────────────────────────────

@app.route('/api/alert/whatsapp', methods=['POST'])
def alert_whatsapp():
    """
    Receive Prometheus/AlertManager alerts and send via WhatsApp
    """
    try:
        data = request.get_json()
        alerts = data.get('alerts', [])
        
        if not alerts:
            return jsonify({'status': 'success', 'message': 'No alerts'}), 200
        
        # Format alert message
        messages = []
        for alert in alerts:
            status = alert.get('status', 'unknown')
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})
            
            alert_name = labels.get('alertname', 'Unknown Alert')
            summary = annotations.get('summary', 'No summary')
            description = annotations.get('description', '')
            
            emoji = '🔴' if status == 'firing' else '🟢'
            msg = f"{emoji} *{alert_name}*\n{summary}\n{description}"
            messages.append(msg)
        
        alert_msg = "\n\n".join(messages)
        
        # Send via Hermes WhatsApp
        import subprocess
        cmd = f'hermes send --to whatsapp:62895397133738 "{alert_msg}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        return jsonify({
            'status': 'success',
            'message': 'Alert sent',
            'alerts_count': len(alerts)
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

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

# ─────────────────────────────────────────────
# Prometheus Metrics
# ─────────────────────────────────────────────

@app.route('/metrics', methods=['GET'])
def prometheus_metrics():
    """Prometheus metrics endpoint"""
    try:
        conn = tracker.get_connection()
        cursor = conn.cursor()
        
        # Get metrics
        cursor.execute("SELECT COUNT(*) FROM transactions")
        tx_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
        income = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
        expense = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM debts")
        debt_count = cursor.fetchone()[0]
        
        balance = income - expense
        
        conn.close()
        
        # Format as Prometheus metrics
        metrics = f"""# HELP finance_transactions_total Total number of transactions
# TYPE finance_transactions_total gauge
finance_transactions_total {tx_count}

# HELP finance_income_total Total income
# TYPE finance_income_total gauge
finance_income_total {income}

# HELP finance_expense_total Total expenses
# TYPE finance_expense_total gauge
finance_expense_total {expense}

# HELP finance_balance Current balance
# TYPE finance_balance gauge
finance_balance {balance}

# HELP finance_debts_total Total debts
# TYPE finance_debts_total gauge
finance_debts_total {debt_count}
"""
        return metrics, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    except Exception as e:
        return f"# Error: {str(e)}", 500


# Update alert webhook dengan security
@app.route('/api/alert/whatsapp', methods=['POST'])
def alert_whatsapp_secure():
    """Receive Prometheus alerts with authentication"""
    try:
        # Verify secret header
        webhook_secret = request.headers.get('X-Alert-Secret')
        if webhook_secret != 'alert-secret-2026-finance':
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        
        data = request.get_json()
        if not data or 'alerts' not in data:
            return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
        
        alerts = data.get('alerts', [])
        if len(alerts) > 10:  # Rate limit
            return jsonify({'status': 'error', 'message': 'Too many alerts'}), 429
        
        messages = []
        for alert in alerts:
            status = alert.get('status', 'unknown')
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})
            
            alert_name = labels.get('alertname', 'Unknown')
            summary = annotations.get('summary', 'No summary')
            
            emoji = '🔴' if status == 'firing' else '🟢'
            msg = f"{emoji} *{alert_name}*\n{summary}"
            messages.append(msg)
        
        if messages:
            alert_msg = "\n\n".join(messages)
            import subprocess
            subprocess.run(
                f'hermes send --to whatsapp:62895397133738 "{alert_msg}"',
                shell=True, capture_output=True
            )
        
        return jsonify({'status': 'success', 'alerts_processed': len(alerts)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─────────────────────────────────────────────
# Response Caching
# ─────────────────────────────────────────────

from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Cache decorators for common endpoints
@app.route('/api/balance/cached', methods=['GET'])
@cache.cached(timeout=300)  # 5 minutes
def get_balance_cached():
    """Get balance (cached 5 min)"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        balances = tracker.get_account_balances(start_date, end_date)
        total_income = sum(b.get('income', 0) for b in balances)
        total_expense = sum(b.get('expense', 0) for b in balances)
        
        return jsonify({
            'status': 'success',
            'data': {
                'balance': total_income - total_expense,
                'income': total_income,
                'expense': total_expense,
                'currency': 'IDR',
                'cached': True,
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/accounts/cached', methods=['GET'])
@cache.cached(timeout=600)  # 10 minutes
def get_accounts_cached():
    """Get accounts (cached 10 min)"""
    try:
        accounts = tracker.get_accounts()
        balances = tracker.get_account_balances()
        balance_map = {b['account_id']: b for b in balances}
        
        result = []
        for a in accounts:
            bal = balance_map.get(a['id'], {})
            result.append({
                'id': a['id'],
                'name': a['name'],
                'type': a.get('account_type', 'wallet'),
                'icon': a.get('icon', '💰'),
                'color': a.get('color', '#3b82f6'),
                'income': bal.get('income', 0),
                'expense': bal.get('expense', 0),
                'balance': bal.get('income', 0) - bal.get('expense', 0)
            })
        
        return jsonify({'status': 'success', 'data': result, 'cached': True})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/categories/cached', methods=['GET'])
@cache.cached(timeout=3600)  # 1 hour
def get_categories_cached():
    """Get categories (cached 1 hour)"""
    try:
        categories = tracker.get_categories()
        return jsonify({'status': 'success', 'data': categories, 'cached': True})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─────────────────────────────────────────────
# Receipt OCR Processing
# ─────────────────────────────────────────────

from ocr_processor import ReceiptOCR
import os
from werkzeug.utils import secure_filename

UPLOAD_DIR = '/tmp/receipts'
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/receipt/ocr', methods=['POST'])
def process_receipt_ocr():
    """
    Upload receipt image and extract transaction data via OCR
    Returns: merchant, amount, date, items
    """
    try:
        # Check if file is present
        if 'receipt' not in request.files:
            return jsonify({'status': 'error', 'message': 'No receipt image provided'}), 400
        
        file = request.files['receipt']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'status': 'error', 'message': 'Invalid file type. Allowed: png, jpg, jpeg, gif, bmp'}), 400
        
        # Save uploaded file
        filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)
        
        # Process receipt with OCR
        processor = ReceiptOCR()
        result = processor.process_receipt(filepath)
        
        if result['status'] == 'success':
            return jsonify({
                'status': 'success',
                'receipt_data': result['data'],
                'confidence': result['confidence'],
                'message': f"Receipt processed with {result['confidence']}% confidence"
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 400
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/receipt/create-transaction', methods=['POST'])
def create_transaction_from_receipt():
    """
    Create transaction from OCR receipt data
    Input: {merchant, amount, category, account_id, description}
    """
    try:
        data = request.get_json()
        
        if not data or 'amount' not in data:
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        amount = int(data.get('amount', 0))
        if amount <= 0:
            return jsonify({'status': 'error', 'message': 'Amount must be positive'}), 400
        
        # Get or create account
        account_id = data.get('account_id', 6)  # Default to Cash
        
        # Get or create category
        category_name = data.get('category', 'Makanan')
        conn = tracker.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        category = cursor.fetchone()
        if not category:
            cursor.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (category_name, 'expense'))
            conn.commit()
            category_id = cursor.lastrowid
        else:
            category_id = category[0]
        
        # Create transaction
        description = data.get('description', data.get('merchant', 'Receipt transaction'))
        date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        cursor.execute("""
            INSERT INTO transactions 
            (account_id, category_id, amount, type, description, date)
            VALUES (?, ?, ?, 'expense', ?, ?)
        """, (account_id, category_id, amount, description, date_str))
        
        conn.commit()
        tx_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'status': 'success',
            'transaction_id': tx_id,
            'message': f'Transaction created: {description} - Rp {amount:,}',
            'data': {
                'id': tx_id,
                'amount': amount,
                'description': description,
                'category': category_name,
                'date': date_str
            }
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

