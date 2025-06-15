from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps
from ..exceptions import Result


# Helper function for validation
def _validate_workflow_exists(db_path, workflow_id):
    """
    Amaç: Belirtilen workflow ID'nin veritabanında mevcut olup olmadığını kontrol eder.
    Döner: Workflow mevcutsa True, yoksa False döner.
    """
    query = "SELECT id FROM workflows WHERE id = ?"
    result = fetch_one(db_path, query, (workflow_id,))
    return result.success and result.data is not None


# Temel CRUD operasyonaları
@handle_db_errors("create node")
def create_node(db_path, workflow_id, name, type, script, params):
    """
    Amaç: Belirtilen iş akışına yeni bir düğüm ekler ve workflow doğrulaması yapar.
    Döner: Başarılı ise node_id içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Validate required parameters
    if not name or not type:
        return Result.error("Node name and type are required")
    
    # Validate workflow exists
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
    node_id = generate_uuid()
    query = """
        INSERT INTO nodes (id, workflow_id, name, type, script, params)
        VALUES (?, ?, ?, ?, ?, ?)
        """
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(node_id, workflow_id, name, type, script, safe_json_dumps(params)))
    
    if not result.success:
        return Result.error(f"Failed to create node: {result.error}")
    return Result.success({"node_id": node_id})

@handle_db_errors("get node")
def get_node(db_path, node_id):
    """
    Amaç: Belirtilen ID'ye sahip düğümün tüm bilgilerini getirir.
    Döner: Başarılı ise node verilerini içeren Result objesi, bulunamazsa None, hata durumunda hata mesajı.
    """
    query = "SELECT * FROM nodes WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(node_id,))

    if not result.success:
        return Result.error(f"Failed to get node: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete node")
def delete_node(db_path, node_id):
    """
    Amaç: Belirtilen düğümü veritabanından siler, önce varlığını kontrol eder.
    Döner: Başarılı ise silme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Check if node exists first
    check_result = get_node(db_path, node_id)
    if not check_result.success:
        return check_result
    
    if not check_result.data:
        return Result.error(f"Node not found: {node_id}")
    
    query = "DELETE FROM nodes WHERE id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(node_id,))
    
    if not result.success:
        return Result.error(f"Failed to delete node: {result.error}")
    return Result.success({"deleted": True, "node_id": node_id})

@handle_db_errors("list nodes")
def list_nodes(db_path):
    """
    Amaç: Veritabanındaki tüm düğümleri listeler.
    Döner: Başarılı ise node listesi içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    query = "SELECT * FROM nodes"
    result = fetch_all(db_path=db_path, query=query, params=None)

    if not result.success:
        return Result.error(f"Failed to list nodes: {result.error}")
    return Result.success(result.data)

# Workflow tablosu ile bağlantılı işlemler
@handle_db_errors("list workflow nodes")
def list_workflow_nodes(db_path, workflow_id):
    """
    Amaç: Belirtilen iş akışına ait tüm düğümleri listeler, workflow varlığını doğrular.
    Döner: Başarılı ise workflow'a ait node listesi içeren Result objesi, hata durumunda hata mesajı.
    """
    # Validate workflow exists
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
    query = "SELECT * FROM nodes WHERE workflow_id = ?"
    result = fetch_all(db_path=db_path, query=query, params=(workflow_id,))

    if not result.success:
        return Result.error(f"Failed to list workflow nodes: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete workflow nodes")
def delete_workflow_nodes(db_path, workflow_id):
    """
    Amaç: Belirtilen iş akışına ait tüm düğümleri siler, workflow varlığını doğrular.
    Döner: Başarılı ise silme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Validate workflow exists
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
    query = "DELETE FROM nodes WHERE workflow_id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(workflow_id,))

    if not result.success:
        return Result.error(f"Failed to delete workflow nodes: {result.error}")
    return Result.success({"deleted": True, "workflow_id": workflow_id})

# Düğüm işlemleri 
@handle_db_errors("get node dependents")
def get_node_dependents(db_path, node_id):
    """
    Amaç: Bu düğüme bağımlı olan düğümlerin listesini getirir (bu düğümün işaret ettiği düğümler).
    Döner: Başarılı ise bağımlı node ID'lerinin listesi içeren Result objesi, hata durumunda hata mesajı.
    """
    # Validate node exists
    if not get_node(db_path, node_id).data:
        return Result.error(f"Node not found: {node_id}")
    
    query = """
        SELECT n.id 
        FROM nodes n
        JOIN edges e ON n.id = e.to_node_id
        WHERE e.from_node_id = ?
        """
    result = fetch_all(db_path=db_path, query=query, params=(node_id,))
    
    if not result.success:
            return Result.error(f"Failed to get node dependents: {result.error}")
    
    node_ids = [row["id"] for row in result.data]
    return Result.success(node_ids)

@handle_db_errors("get node dependencies")
def get_node_dependencies(db_path, node_id):
    """
    Amaç: Bu düğümün bağımlı olduğu düğümlerin listesini getirir (bu düğüme işaret eden düğümler).
    Döner: Başarılı ise bağımlılık node ID'lerinin listesi içeren Result objesi, hata durumunda hata mesajı.
    """
    # Validate node exists
    if not get_node(db_path, node_id).data:
        return Result.error(f"Node not found: {node_id}")
    
    query = """
        SELECT n.id 
        FROM nodes n
        JOIN edges e ON n.id = e.from_node_id
        WHERE e.to_node_id = ?
        """
    result = fetch_all(db_path=db_path, query=query, params=(node_id,))
       
    if not result.success:
        return Result.error(f"Failed to get node dependencies: {result.error}")
        
    node_ids = [row["id"] for row in result.data]
    return Result.success(node_ids)


@handle_db_errors("update node params")
def update_node_params(db_path, node_id, params):
    """
    Amaç: Belirtilen düğümün parametrelerini günceller
    Döner: Başarılı ise güncelleme onayı içeren Result objesi, hata durumunda hata mesajı
    
    Bu fonksiyon workflow loading sırasında node parameter mapping için kullanılır
    """
    # Check if node exists first
    check_result = get_node(db_path, node_id)
    if not check_result.success:
        return check_result
    
    if not check_result.data:
        return Result.error(f"Node not found: {node_id}")
    
    query = "UPDATE nodes SET params = ? WHERE id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(safe_json_dumps(params), node_id))
    
    if not result.success:
        return Result.error(f"Failed to update node params: {result.error}")
    
    return Result.success({"updated": True, "node_id": node_id})