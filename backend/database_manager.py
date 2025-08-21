# database_manager.py
import sqlite3
import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")

def get_oracle_credentials():
    """Get Oracle credentials from environment variables"""
    return {
        "host": os.getenv("ORACLE23AI_HOST"),
        "port": int(os.getenv("ORACLE23AI_PORT", "1521")),
        "service_name": os.getenv("ORACLE23AI_SERVICENAME"),
        "user": os.getenv("ORACLE23AI_USER"),
        "password": os.getenv("ORACLE23AI_PASSWORD")
    }

class DatabaseManager:
    """Unified database manager for SQLite and Oracle with Flask integration"""
    
    def __init__(self, db_type: str = "sqlite", **kwargs):
        self.db_type = db_type.lower()
        self.connection = None
        self.cursor = None
        
        if self.db_type == "sqlite":
            self.db_path = kwargs.get("db_path", "project_database.db")
        elif self.db_type == "oracle":
            self.config = kwargs
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def connect(self):
        """Connect to database"""
        try:
            if self.db_type == "sqlite":
                self.connection = sqlite3.connect(self.db_path)
                self.connection.row_factory = sqlite3.Row
                self.cursor = self.connection.cursor()
                logging.info(f"Connected to SQLite: {self.db_path}")
            else:  # Oracle
                import oracledb
                self.connection = oracledb.connect(**self.config)
                self.cursor = self.connection.cursor()
                logging.info(f"Connected to Oracle: {self.config['host']}:{self.config['port']}")
        except Exception as e:
            logging.error(f"Connection error: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logging.info("Database disconnected")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        self.cursor.execute(query, params)
        if self.db_type == "sqlite":
            return [dict(row) for row in self.cursor.fetchall()]
        else:  # Oracle
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query"""
        self.cursor.execute(query, params)
        self.connection.commit()
        return self.cursor.rowcount if self.db_type == "oracle" else self.cursor.lastrowid
    
    def create_table(self, table_name: str, columns: Dict[str, str]):
        """Create table with specified columns"""
        column_defs = ", ".join([f"{col} {dtype}" for col, dtype in columns.items()])
        
        if self.db_type == "sqlite":
            query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs})"
        else:  # Oracle
            # Check if table exists first for Oracle
            check_query = """
            SELECT COUNT(*) as count FROM user_tables WHERE table_name = UPPER(:1)
            """
            self.cursor.execute(check_query, (table_name,))
            exists = self.cursor.fetchone()[0] > 0
            
            if not exists:
                query = f"CREATE TABLE {table_name} ({column_defs})"
            else:
                logging.info(f"Table '{table_name}' already exists")
                return
        
        self.cursor.execute(query)
        self.connection.commit()
        logging.info(f"Table '{table_name}' created")
    
    def upload_data(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Upload data to specified table"""
        if not data:
            return 0
        
        columns = list(data[0].keys())
        
        if self.db_type == "sqlite":
            placeholders = ", ".join(["?" for _ in columns])
        else:  # Oracle
            placeholders = ", ".join([f":{i+1}" for i in range(len(columns))])
        
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        for record in data:
            values = tuple(record[col] for col in columns)
            self.execute_update(query, values)
        
        logging.info(f"Uploaded {len(data)} records to {table_name}")
        return len(data)
    
    def retrieve_data(self, table_name: str, conditions: str = "", params: tuple = ()) -> List[Dict[str, Any]]:
        """Retrieve data from specified table"""
        query = f"SELECT * FROM {table_name}"
        if conditions:
            query += f" WHERE {conditions}"
        return self.execute_query(query, params)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        param_style = ":1" if self.db_type == "oracle" else "?"
        users = self.retrieve_data("users", f"id = {param_style}", (user_id,))
        return users[0] if users else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        param_style = ":1" if self.db_type == "oracle" else "?"
        users = self.retrieve_data("users", f"email = {param_style}", (email,))
        return users[0] if users else None
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user and return user ID"""
        import uuid
        from datetime import datetime
        
        user_id = str(uuid.uuid4())
        user_record = {
            'id': user_id,
            'name': user_data['name'],
            'email': user_data['email'],
            'password_hash': user_data['password_hash'],
            'role': user_data.get('role', 'user'),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        self.upload_data("users", [user_record])
        return user_id
    
    def create_project(self, project_data: Dict[str, Any]) -> str:
        """Create a new project and return project ID"""
        import uuid
        from datetime import datetime
        import json
        
        project_id = str(uuid.uuid4())
        project_record = {
            'id': project_id,
            'title': project_data['title'],
            'description': project_data.get('description', ''),
            'status': 'processing',
            'progress': 0,
            'status_message': None,
            'files_json': json.dumps(project_data.get('files', [])),
            'documentation': None,
            'generation_metadata': None,
            'diagrams_json': json.dumps({}),
            'diagrams_generated_at': None,
            'created_by': project_data['created_by'],
            'tags': json.dumps([]),
            'is_public': False,
            'version': '1.0.0',
            'error_message': None,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        self.upload_data("projects", [project_record])
        return project_id
    
    def update_project(self, project_id: str, updates: Dict[str, Any]) -> bool:
        """Update project with given data"""
        from datetime import datetime
        
        print(f"🗃️ Updating project {project_id} with: {list(updates.keys())}")
        
        # Build update query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if self.db_type == "sqlite":
                set_clauses.append(f"{key} = ?")
                params.append(value)
            else:  # Oracle
                set_clauses.append(f"{key} = :{len(params)+1}")
                params.append(value)
        
        # Add updated_at
        if self.db_type == "sqlite":
            set_clauses.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
        else:
            set_clauses.append(f"updated_at = :{len(params)+1}")
            params.append(datetime.utcnow().isoformat())
        
        # Add project_id for WHERE clause
        if self.db_type == "sqlite":
            where_clause = "id = ?"
            params.append(project_id)
        else:
            where_clause = f"id = :{len(params)+1}"
            params.append(project_id)
        
        query = f"UPDATE projects SET {', '.join(set_clauses)} WHERE {where_clause}"
        print(f"🗃️ SQL Query: {query}")
        print(f"🗃️ Parameters: {params}")
        
        rows_affected = self.execute_update(query, tuple(params))
        print(f"🗃️ Rows affected: {rows_affected}")
        
        # Verify the update by reading back
        if rows_affected > 0:
            verify_query = f"SELECT generation_metadata FROM projects WHERE id = {'?' if self.db_type == 'sqlite' else ':1'}"
            result = self.execute_query(verify_query, (project_id,))
            if result:
                print(f"🗃️ Verified metadata after update: {result[0].get('generation_metadata', 'None')[:100]}...")
        
        return rows_affected > 0
    
    def get_project_by_id(self, project_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get project by ID, optionally filtered by user"""
        if user_id:
            if self.db_type == "sqlite":
                conditions = "id = ? AND created_by = ?"
                params = (project_id, user_id)
            else:
                conditions = "id = :1 AND created_by = :2"
                params = (project_id, user_id)
        else:
            if self.db_type == "sqlite":
                conditions = "id = ?"
                params = (project_id,)
            else:
                conditions = "id = :1"
                params = (project_id,)
        
        projects = self.retrieve_data("projects", conditions, params)
        if projects:
            project = projects[0]
            metadata = project.get('generation_metadata', 'None')
            print(f"🗃️ Retrieved project {project_id} with metadata: {metadata[:100] if metadata else 'None'}...")
            return project
        else:
            print(f"🗃️ No project found with ID: {project_id}")
            return None
    
    def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects for a user"""
        param_style = ":1" if self.db_type == "oracle" else "?"
        return self.retrieve_data("projects", f"created_by = {param_style} ORDER BY updated_at DESC", (user_id,))
    
    def delete_project(self, project_id: str, user_id: str) -> bool:
        """Delete a project"""
        if self.db_type == "sqlite":
            query = "DELETE FROM projects WHERE id = ? AND created_by = ?"
            params = (project_id, user_id)
        else:
            query = "DELETE FROM projects WHERE id = :1 AND created_by = :2"
            params = (project_id, user_id)
        
        rows_affected = self.execute_update(query, params)
        return rows_affected > 0
    
    def initialize_tables(self):
        """Initialize all required tables"""
        # Users table
        if self.db_type == "sqlite":
            user_columns = {
                "id": "TEXT PRIMARY KEY",
                "name": "TEXT NOT NULL",
                "email": "TEXT UNIQUE NOT NULL",
                "password_hash": "TEXT NOT NULL",
                "role": "TEXT DEFAULT 'user'",
                "created_at": "TEXT",
                "updated_at": "TEXT"
            }
        else:  # Oracle
            user_columns = {
                "id": "VARCHAR2(36) PRIMARY KEY",
                "name": "VARCHAR2(200) NOT NULL",
                "email": "VARCHAR2(255) UNIQUE NOT NULL",
                "password_hash": "VARCHAR2(255) NOT NULL",
                "role": "VARCHAR2(20) DEFAULT 'user'",
                "created_at": "VARCHAR2(50)",
                "updated_at": "VARCHAR2(50)"
            }
        
        self.create_table("users", user_columns)
        
        # Projects table
        if self.db_type == "sqlite":
            project_columns = {
                "id": "TEXT PRIMARY KEY",
                "title": "TEXT NOT NULL",
                "description": "TEXT",
                "status": "TEXT DEFAULT 'processing'",
                "progress": "INTEGER DEFAULT 0",
                "status_message": "TEXT",
                "files_json": "TEXT DEFAULT '[]'",
                "documentation": "TEXT",
                "generation_metadata": "TEXT",
                "diagrams_json": "TEXT DEFAULT '{}'",
                "diagrams_generated_at": "TEXT",
                "created_by": "TEXT NOT NULL",
                "tags": "TEXT DEFAULT '[]'",
                "is_public": "INTEGER DEFAULT 0",
                "version": "TEXT DEFAULT '1.0.0'",
                "error_message": "TEXT",
                "created_at": "TEXT",
                "updated_at": "TEXT",
                "FOREIGN KEY (created_by)": "REFERENCES users(id)"
            }
        else:  # Oracle
            project_columns = {
                "id": "VARCHAR2(36) PRIMARY KEY",
                "title": "VARCHAR2(200) NOT NULL",
                "description": "CLOB",
                "status": "VARCHAR2(20) DEFAULT 'processing'",
                "progress": "NUMBER DEFAULT 0",
                "status_message": "VARCHAR2(255)",
                "files_json": "CLOB DEFAULT '[]'",
                "documentation": "CLOB",
                "generation_metadata": "CLOB",
                "diagrams_json": "CLOB DEFAULT '{}'",
                "diagrams_generated_at": "VARCHAR2(50)",
                "created_by": "VARCHAR2(36) NOT NULL",
                "tags": "CLOB DEFAULT '[]'",
                "is_public": "NUMBER(1) DEFAULT 0",
                "version": "VARCHAR2(10) DEFAULT '1.0.0'",
                "error_message": "CLOB",
                "created_at": "VARCHAR2(50)",
                "updated_at": "VARCHAR2(50)"
            }
        
        self.create_table("projects", project_columns)

# Global database configuration - CHANGE THIS LINE TO SWITCH DATABASES
DATABASE_TYPE = "sqlite"  # Change to "oracle" to use Oracle database
# DATABASE_TYPE = "oracle"  # Uncomment this line and comment the above to use Oracle

def get_database_manager():
    """Get configured database manager instance"""
    if DATABASE_TYPE == "oracle":
        config = get_oracle_credentials()
        return DatabaseManager(db_type="oracle", **config)
    else:
        return DatabaseManager(db_type="sqlite", db_path="project_database.db")

@contextmanager
def get_db():
    """Context manager for database operations"""
    db = get_database_manager()
    try:
        db.connect()
        yield db
    finally:
        db.disconnect()

# Initialize database tables on import
def initialize_database():
    """Initialize database tables"""
    with get_db() as db:
        db.initialize_tables()

if __name__ == "__main__":
    # Test the database manager
    initialize_database()
    print(f"Database initialized with {DATABASE_TYPE}")