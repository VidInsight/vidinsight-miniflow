
# Tablo tanımları
WORKFLOWS_TABLE = """
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    version NUMBER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

NODES_TABLE = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    script TEXT,
    params TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows (id) ON DELETE CASCADE
)
"""

EDGES_TABLE = """
CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    condition_type TEXT DEFAULT 'success',
    FOREIGN KEY (workflow_id) REFERENCES workflows (id) ON DELETE CASCADE,
    FOREIGN KEY (from_node_id) REFERENCES nodes (id) ON DELETE CASCADE,
    FOREIGN KEY (to_node_id) REFERENCES nodes (id) ON DELETE CASCADE
)
"""

EXECUTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    results TEXT DEFAULT '{}',
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows (id) ON DELETE CASCADE
)
"""

EXECUTION_QUEUE_TABLE = """
CREATE TABLE IF NOT EXISTS execution_queue (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    dependency_count NUMBER,
    FOREIGN KEY (execution_id) REFERENCES executions (id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE
)
"""

EXECUTIONS_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_results (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    status TEXT NOT NULL,
    result_data TEXT,
    error_message TEXT,
    started_at TEXT,
    ended_at TEXT,
    FOREIGN KEY (execution_id) REFERENCES executions (id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE
)
"""

TRIGGERS_TABLE = """
CREATE TABLE IF NOT EXISTS triggers (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    config TEXT DEFAULT '{}',
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (workflow_id) REFERENCES workflows (id) ON DELETE CASCADE
)
"""

# Tüm tablolar listesi
ALL_TABLES = [
    ("workflows", WORKFLOWS_TABLE),
    ("nodes", NODES_TABLE), 
    ("edges", EDGES_TABLE),
    ("executions", EXECUTIONS_TABLE),
    ("execution_queue", EXECUTION_QUEUE_TABLE),
    ("execution_results", EXECUTIONS_RESULTS_TABLE),
    ("triggers", TRIGGERS_TABLE)
]

# İndeksler
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)",
    "CREATE INDEX IF NOT EXISTS idx_nodes_workflow_id ON nodes(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_edges_workflow_id ON edges(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_edges_from_node ON edges(from_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_edges_to_node ON edges(to_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_executions_workflow_id ON executions(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status)",
    "CREATE INDEX IF NOT EXISTS idx_queue_execution_id ON execution_queue(execution_id)",
    "CREATE INDEX IF NOT EXISTS idx_queue_status_priority ON execution_queue(status, priority)",
    "CREATE INDEX IF NOT EXISTS idx_execution_results_execution_id ON execution_results(execution_id)",
    "CREATE INDEX IF NOT EXISTS idx_execution_results_node_id ON execution_results(node_id)",
    "CREATE INDEX IF NOT EXISTS idx_triggers_workflow_id ON triggers(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_triggers_active ON triggers(is_active) WHERE is_active=1"
]
