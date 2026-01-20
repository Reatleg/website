import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

class TradingDatabase:
    """Manages all database operations for FuryTrader Pro"""
    
    def __init__(self, db_name: str = "furytrader.db"):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        """Create a database connection"""
        return sqlite3.connect(self.db_name)
    
    def init_database(self):
        """Initialize all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Journal Table - Stores manual trade entries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                pair TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                position_size REAL,
                balance_before REAL,
                balance_after REAL,
                pnl REAL,
                pnl_percent REAL,
                r_multiple REAL,
                outcome TEXT,
                confluences TEXT,
                narrative TEXT,
                mistake_tag TEXT,
                setup_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # AI Analysis Table - Stores AI predictions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                pair TEXT NOT NULL,
                timeframes TEXT,
                scenario_a TEXT,
                scenario_b TEXT,
                scenario_c TEXT,
                verdict TEXT,
                confidence_score INTEGER,
                key_levels TEXT,
                analysis_summary TEXT,
                chart_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES journal (id)
            )
        ''')
        
        # Settings Table - Stores user preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_trade(self, trade_data: Dict) -> int:
        """Add a new trade to the journal"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Calculate R multiple if possible
        r_multiple = None
        if trade_data.get('pnl') and trade_data.get('entry_price') and trade_data.get('stop_loss'):
            risk = abs(trade_data['entry_price'] - trade_data['stop_loss'])
            if risk > 0:
                r_multiple = trade_data['pnl'] / risk
        
        cursor.execute('''
            INSERT INTO journal (
                date, pair, direction, entry_price, stop_loss, take_profit,
                position_size, balance_before, balance_after, pnl, pnl_percent,
                r_multiple, outcome, confluences, narrative, mistake_tag, setup_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            trade_data['pair'],
            trade_data['direction'],
            trade_data['entry_price'],
            trade_data['stop_loss'],
            trade_data['take_profit'],
            trade_data.get('position_size'),
            trade_data.get('balance_before'),
            trade_data.get('balance_after'),
            trade_data.get('pnl'),
            trade_data.get('pnl_percent'),
            r_multiple,
            trade_data.get('outcome'),
            trade_data.get('confluences'),
            trade_data.get('narrative'),
            trade_data.get('mistake_tag'),
            trade_data.get('setup_type')
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def add_analysis(self, analysis_data: Dict) -> int:
        """Store AI analysis results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_analysis (
                trade_id, pair, timeframes, scenario_a, scenario_b, scenario_c,
                verdict, confidence_score, key_levels, analysis_summary, chart_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis_data.get('trade_id'),
            analysis_data['pair'],
            json.dumps(analysis_data.get('timeframes', [])),
            analysis_data.get('scenario_a'),
            analysis_data.get('scenario_b'),
            analysis_data.get('scenario_c'),
            analysis_data.get('verdict'),
            analysis_data.get('confidence_score'),
            json.dumps(analysis_data.get('key_levels', {})),
            analysis_data.get('analysis_summary'),
            analysis_data.get('chart_data')
        ))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return analysis_id
    
    def get_all_trades(self) -> pd.DataFrame:
        """Retrieve all trades as a DataFrame"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM journal ORDER BY date DESC", conn)
        conn.close()
        return df
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Dict]:
        """Get a specific trade by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM journal WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_analysis_by_trade_id(self, trade_id: int) -> Optional[Dict]:
        """Get AI analysis for a specific trade"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM ai_analysis WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_statistics(self) -> Dict:
        """Calculate trading statistics"""
        df = self.get_all_trades()
        
        if df.empty:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_rr': 0,
                'total_pnl': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        wins = df[df['outcome'] == 'Win']
        losses = df[df['outcome'] == 'Loss']
        
        return {
            'total_trades': len(df),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': (len(wins) / len(df) * 100) if len(df) > 0 else 0,
            'avg_rr': df['r_multiple'].mean() if 'r_multiple' in df else 0,
            'total_pnl': df['pnl'].sum() if 'pnl' in df else 0,
            'best_trade': df['pnl'].max() if 'pnl' in df else 0,
            'worst_trade': df['pnl'].min() if 'pnl' in df else 0,
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0
        }
    
    def update_trade(self, trade_id: int, updates: Dict):
        """Update an existing trade"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [trade_id]
        
        cursor.execute(f"UPDATE journal SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()
    
    def delete_trade(self, trade_id: int):
        """Delete a trade and its analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM ai_analysis WHERE trade_id = ?", (trade_id,))
        cursor.execute("DELETE FROM journal WHERE id = ?", (trade_id,))
        
        conn.commit()
        conn.close()