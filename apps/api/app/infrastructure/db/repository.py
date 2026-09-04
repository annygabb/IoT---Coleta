import sqlite3
import json
from typing import Dict, Any, List, Optional

class SimulationRepository:
    """
    Repositório persistente para telemetria, eventos, decisões e auditoria (Cap. 10).
    Opera com SQLite local sem custo de licença ou infraestrutura gerenciada.
    """
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                bin_id TEXT,
                sim_time TEXT,
                fill_pct REAL,
                temperature_c REAL,
                battery_pct REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operational_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE,
                bin_id TEXT,
                severity TEXT,
                message TEXT,
                sim_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actuator_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_id TEXT UNIQUE,
                truck_id TEXT,
                action TEXT,
                target_node TEXT,
                sim_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT UNIQUE,
                truck_id TEXT,
                target_bin_id TEXT,
                strategy TEXT,
                reason TEXT,
                sim_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def save_telemetry(self, data: Dict[str, Any]):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO telemetry (event_id, bin_id, sim_time, fill_pct, temperature_c, battery_pct)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get('event_id'),
                data.get('bin_id'),
                data.get('sim_time'),
                data.get('fill_pct'),
                data.get('temperature_c'),
                data.get('battery_pct')
            ))
            self.conn.commit()
        except Exception:
            pass

    def save_decision(self, data: Dict[str, Any]):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO decisions (decision_id, truck_id, target_bin_id, strategy, reason, sim_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get('decision_id'),
                data.get('truck_id'),
                data.get('target_bin_id'),
                str(data.get('strategy')),
                data.get('reason'),
                data.get('sim_time')
            ))
            self.conn.commit()
        except Exception:
            pass
