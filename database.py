"""
Database module for Recruitment Tracker System
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet

class Database:
    def __init__(self, db_path="data/recruitment_data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
        
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hiring_managers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hm_projects (
                hm_id TEXT,
                project_id TEXT,
                FOREIGN KEY (hm_id) REFERENCES hiring_managers(id),
                FOREIGN KEY (project_id) REFERENCES projects(id),
                PRIMARY KEY (hm_id, project_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                country_name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                mobile TEXT,
                current_location_id TEXT,
                nationality TEXT,
                notice_period TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (current_location_id) REFERENCES locations(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def generate_id(self, prefix):
        """Generate unique ID with pattern PREFIX-YYMMDD-XXXX"""
        date_part = datetime.now().strftime("%y%m%d")
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get count for today
        query = f"""
            SELECT COUNT(*) FROM (
                SELECT id FROM hiring_managers WHERE id LIKE '{prefix}-{date_part}-%'
                UNION ALL
                SELECT id FROM projects WHERE id LIKE '{prefix}-{date_part}-%'
                UNION ALL
                SELECT id FROM positions WHERE id LIKE '{prefix}-{date_part}-%'
                UNION ALL
                SELECT id FROM locations WHERE id LIKE '{prefix}-{date_part}-%'
                UNION ALL
                SELECT id FROM candidates WHERE id LIKE '{prefix}-{date_part}-%'
            )
        """
        cursor.execute(query)
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return f"{prefix}-{date_part}-{count+1:04d}"
    
    def encrypt_value(self, value):
        """Encrypt sensitive values"""
        # Generate key if not exists
        key_file = Path("data/.encryption_key")
        if not key_file.exists():
            key = Fernet.generate_key()
            key_file.write_bytes(key)
        else:
            key = key_file.read_bytes()
        
        f = Fernet(key)
        return f.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value):
        """Decrypt sensitive values"""
        key_file = Path("data/.encryption_key")
        if not key_file.exists():
            return None
        
        key = key_file.read_bytes()
        f = Fernet(key)
        return f.decrypt(encrypted_value.encode()).decode()

    def add_hiring_manager(self, name, email):
        """Add new hiring manager"""
        conn = self.get_connection()
        cursor = conn.cursor()
        hm_id = self.generate_id("HM")
        
        try:
            cursor.execute(
                "INSERT INTO hiring_managers (id, name, email) VALUES (?, ?, ?)",
                (hm_id, name, email)
            )
            conn.commit()
            return hm_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_hiring_managers(self):
        """Get all hiring managers"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hiring_managers ORDER BY name")
        results = cursor.fetchall()
        conn.close()
        return results
    
    def add_project(self, name):
        """Add new project"""
        conn = self.get_connection()
        cursor = conn.cursor()
        project_id = self.generate_id("PROJ")
        
        try:
            cursor.execute(
                "INSERT INTO projects (id, name) VALUES (?, ?)",
                (project_id, name)
            )
            conn.commit()
            return project_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_projects(self):
        """Get all projects"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY name")
        results = cursor.fetchall()
        conn.close()
        return results
    
    def set_config(self, key, value, encrypt=False):
        """Set system configuration"""
        if encrypt:
            value = self.encrypt_value(value)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()
        conn.close()
    
    # Add these methods to your Database class in database.py

    def add_candidate(self, name, email='', mobile='', current_location='', nationality='', notice_period=''):
        """Add new candidate"""
        conn = self.get_connection()
        cursor = conn.cursor()
        candidate_id = self.generate_id("CAND")
        
        try:
            # First, check if location exists, if not create it
            location_id = None
            if current_location:
                cursor.execute("SELECT id FROM locations WHERE country_name = ?", (current_location,))
                location = cursor.fetchone()
                if location:
                    location_id = location[0]
                else:
                    location_id = self.generate_id("LOC")
                    cursor.execute(
                        "INSERT INTO locations (id, country_name) VALUES (?, ?)",
                        (location_id, current_location)
                    )
            
            # Insert candidate
            cursor.execute(
                """INSERT INTO candidates (id, name, email, mobile, current_location_id, nationality, notice_period) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (candidate_id, name, email, mobile, location_id, nationality, notice_period)
            )
            conn.commit()
            return candidate_id
        except sqlite3.IntegrityError as e:
            return None
        finally:
            conn.close()

    def get_candidates(self):
        """Get all candidates"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, c.email, c.mobile, 
                l.country_name, c.nationality, c.notice_period
            FROM candidates c
            LEFT JOIN locations l ON c.current_location_id = l.id
            ORDER BY c.name
        """)
        results = cursor.fetchall()
        conn.close()
        return results

    def search_candidates(self, criteria):
        """Search candidates based on criteria"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT c.id, c.name, c.email, c.mobile, 
                l.country_name, c.nationality, c.notice_period
            FROM candidates c
            LEFT JOIN locations l ON c.current_location_id = l.id
            WHERE 1=1
        """
        params = []
        
        if criteria.get('name'):
            query += " AND c.name LIKE ?"
            params.append(f"%{criteria['name']}%")
        
        if criteria.get('location'):
            query += " AND l.country_name LIKE ?"
            params.append(f"%{criteria['location']}%")
        
        if criteria.get('nationality'):
            query += " AND c.nationality LIKE ?"
            params.append(f"%{criteria['nationality']}%")
        
        query += " ORDER BY c.name"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    def get_locations(self):
        """Get all locations"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM locations ORDER BY country_name")
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_config(self, key, decrypt=False):
        """Get system configuration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        
        if result and decrypt:
            return self.decrypt_value(result[0])
        return result[0] if result else None
