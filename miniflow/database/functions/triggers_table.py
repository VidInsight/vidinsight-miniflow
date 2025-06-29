from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps, safe_json_loads, generate_timestamp
from ..exceptions import Result

# Supported trigger types
VALID_TRIGGER_TYPES = ['schedule', 'webhook', 'file', 'event']

# Helper functions
def _validate_workflow_exists(db_path, workflow_id):
    """
    Amaç: Belirtilen workflow ID'nin veritabanında mevcut olup olmadığını kontrol eder.
    Döner: Workflow mevcutsa True, yoksa False döner.
    """
    query = "SELECT id FROM workflows WHERE id = ?"
    result = fetch_one(db_path, query, (workflow_id,))
    return result.success and result.data is not None

def _validate_trigger_type(trigger_type):
    """
    Amaç: Trigger türünün desteklenen türlerden biri olup olmadığını doğrular.
    Döner: Geçerli trigger türüyse True, değilse False döner.
    """
    return trigger_type in VALID_TRIGGER_TYPES

def _parse_trigger_config(config_json):
    """
    Amaç: Trigger konfigürasyonu JSON string'ini güvenli şekilde parse eder.
    Döner: Parse edilmiş dictionary objesi veya boş dictionary döner.
    """
    if not config_json:
        return {}
    return safe_json_loads(config_json)

# Temel CRUD operasyonaları
@handle_db_errors("create trigger")
def create_trigger(db_path, workflow_id, trigger_type, config=None):
    """
    Amaç: Bir workflow için yeni trigger oluşturur, workflow varlığını ve trigger türünü doğrular.
    Döner: Başarılı ise trigger_id içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Step 1: Generate trigger ID
    trigger_id = generate_uuid()
    
    # Step 2: Validate workflow exists
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
    # Step 3: Validate trigger_type
    if not _validate_trigger_type(trigger_type):
        return Result.error(f"Invalid trigger type: {trigger_type}. Valid types: {VALID_TRIGGER_TYPES}")
    
    # Step 4: Process config
    config_json = safe_json_dumps(config) if config else '{}'
    
    # Step 5: Insert trigger
    query = """
    INSERT INTO triggers (id, workflow_id, trigger_type, config, is_active)
    VALUES (?, ?, ?, ?, 1)
    """
    params = (trigger_id, workflow_id, trigger_type, config_json)
    
    result = execute_sql_query(db_path, query, params)
    if not result.success:
        return Result.error(f"Failed to create trigger: {result.error}")
    
    # Step 6: Return Result with trigger_id
    return Result.success({"trigger_id": trigger_id})

@handle_db_errors("get trigger")
def get_trigger(db_path, trigger_id):
    """
    Amaç: Belirtilen ID'ye sahip trigger'ı workflow bilgileri ile birlikte getirir, config'i parse eder.
    Döner: Başarılı ise trigger verilerini içeren Result objesi, bulunamazsa None, hata durumunda hata mesajı.
    """
    # Step 1: Query trigger with workflow info
    query = """
    SELECT t.*, w.name as workflow_name
    FROM triggers t
    JOIN workflows w ON t.workflow_id = w.id
    WHERE t.id = ?
    """
    
    # Step 2: Fetch single record
    result = fetch_one(db_path, query, (trigger_id,))
    if not result.success:
        return Result.error(f"Failed to get trigger: {result.error}")
    
    if not result.data:
        return Result.success(None)
    
    # Step 3: Parse config JSON back to object
    trigger_data = dict(result.data)
    trigger_data['config'] = _parse_trigger_config(trigger_data.get('config'))
    trigger_data['is_active'] = bool(trigger_data.get('is_active', 0))
    
    # Step 4: Return complete trigger information
    return Result.success(trigger_data)

@handle_db_errors("delete trigger")
def delete_trigger(db_path, trigger_id):
    """
    Amaç: Belirtilen trigger'ı siler, önce varlığını kontrol eder ve etkilenen satır sayısını doğrular.
    Döner: Başarılı ise silme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Step 1: Check if trigger exists
    check_result = fetch_one(db_path, "SELECT id FROM triggers WHERE id = ?", (trigger_id,))
    if not check_result.success:
        return Result.error(f"Failed to check trigger existence: {check_result.error}")
    
    if not check_result.data:
        return Result.error(f"Trigger not found: {trigger_id}")
    
    # Step 2: Delete trigger
    query = "DELETE FROM triggers WHERE id = ?"
    result = execute_sql_query(db_path, query, (trigger_id,))
    
    if not result.success:
        return Result.error(f"Failed to delete trigger: {result.error}")
    
    # Step 3: Check affected rows
    affected_rows = result.data.get("affected_rows", 0)
    if affected_rows == 0:
        return Result.error(f"No trigger was deleted: {trigger_id}")
    
    # Step 4: Return deletion confirmation
    return Result.success({"deleted": True, "trigger_id": trigger_id})

# Workflow ile bağlantılı işlemler
@handle_db_errors("list workflow triggers")
def list_workflow_triggers(db_path, workflow_id):
    """
    Amaç: Belirtilen workflow'a ait tüm trigger'ları listeler, config'leri parse eder ve workflow bilgisi ekler.
    Döner: Başarılı ise workflow'a ait trigger listesi içeren Result objesi, hata durumunda hata mesajı.
    """
    # Step 1: Query all triggers for workflow
    query = """
    SELECT t.*, w.name as workflow_name
    FROM triggers t
    JOIN workflows w ON t.workflow_id = w.id
    WHERE t.workflow_id = ?
    ORDER BY t.trigger_type, t.is_active DESC
    """
    
    result = fetch_all(db_path, query, (workflow_id,))
    if not result.success:
        return Result.error(f"Failed to list workflow triggers: {result.error}")
    
    # Step 2: Parse config JSON for each trigger
    triggers = []
    for row in result.data:
        trigger_data = dict(row)
        trigger_data['config'] = _parse_trigger_config(trigger_data.get('config'))
        trigger_data['is_active'] = bool(trigger_data.get('is_active', 0))
        triggers.append(trigger_data)
    
    # Step 3: Return list of triggers with metadata
    return Result.success(triggers)

@handle_db_errors("delete workflow triggers")
def delete_workflow_triggers(db_path, workflow_id):
    """
    Amaç: Belirtilen workflow'a ait tüm trigger'ları siler, önce sayısını belirler.
    Döner: Başarılı ise silme onayı ve silinen trigger sayısı içeren Result objesi, hata durumunda hata mesajı.
    """
    # Step 1: Count existing triggers first
    count_query = "SELECT COUNT(*) as count FROM triggers WHERE workflow_id = ?"
    count_result = fetch_one(db_path, count_query, (workflow_id,))
    
    if not count_result.success:
        return Result.error(f"Failed to count workflow triggers: {count_result.error}")
    
    trigger_count = count_result.data.get('count', 0) if count_result.data else 0
    
    # Step 2: Delete all triggers for workflow
    delete_query = "DELETE FROM triggers WHERE workflow_id = ?"
    delete_result = execute_sql_query(db_path, delete_query, (workflow_id,))
    
    if not delete_result.success:
        return Result.error(f"Failed to delete workflow triggers: {delete_result.error}")
    
    # Step 3: Return deletion summary
    return Result.success({
        "deleted": True, 
        "workflow_id": workflow_id, 
        "count": trigger_count
    })

@handle_db_errors("get trigger type")
def get_trigger_type(db_path, trigger_id):
    """
    Amaç: Belirtilen trigger'ın türü ve aktif durumu bilgilerini getirir.
    Döner: Başarılı ise trigger_type ve is_active bilgileri içeren Result objesi, hata durumunda hata mesajı.
    """
    # Step 1: Query only trigger_type field
    query = "SELECT trigger_type, is_active FROM triggers WHERE id = ?"
    result = fetch_one(db_path, query, (trigger_id,))
    
    if not result.success:
        return Result.error(f"Failed to get trigger type: {result.error}")
    
    if not result.data:
        return Result.error(f"Trigger not found: {trigger_id}")
    
    # Step 2: Return trigger type info
    return Result.success({
        "trigger_type": result.data["trigger_type"],
        "is_active": bool(result.data.get("is_active", 0))
    })

# Additional helper functions
@handle_db_errors("list triggers")
def list_triggers(db_path, active_only=False):
    """
    Amaç: Sistemdeki tüm trigger'ları listeler, aktif duruma göre filtreleme yapabilir.
    Döner: Başarılı ise trigger listesi içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    query = """
    SELECT t.*, w.name as workflow_name
    FROM triggers t
    JOIN workflows w ON t.workflow_id = w.id
    """
    params = []
    
    if active_only:
        query += " WHERE t.is_active = 1"
    
    query += " ORDER BY t.workflow_id, t.trigger_type"
    
    result = fetch_all(db_path, query, params)
    if not result.success:
        return Result.error(f"Failed to list triggers: {result.error}")
    
    # Parse config for each trigger
    triggers = []
    for row in result.data:
        trigger_data = dict(row)
        trigger_data['config'] = _parse_trigger_config(trigger_data.get('config'))
        trigger_data['is_active'] = bool(trigger_data.get('is_active', 0))
        triggers.append(trigger_data)
    
    return Result.success(triggers)

@handle_db_errors("update trigger")
def update_trigger(db_path, trigger_id, updates):
    """
    Amaç: Trigger'ın belirtilen alanlarını günceller, alan geçerliliğini ve trigger türü doğrulaması yapar.
    Döner: Başarılı ise güncelleme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Validate trigger exists
    check_result = fetch_one(db_path, "SELECT id FROM triggers WHERE id = ?", (trigger_id,))
    if not check_result.success:
        return Result.error(f"Failed to check trigger existence: {check_result.error}")
    
    if not check_result.data:
        return Result.error(f"Trigger not found: {trigger_id}")
    
    # Build update query dynamically
    valid_fields = ['trigger_type', 'config', 'is_active']
    update_fields = []
    params = []
    
    for field, value in updates.items():
        if field not in valid_fields:
            return Result.error(f"Invalid field for update: {field}")
        
        if field == 'trigger_type' and not _validate_trigger_type(value):
            return Result.error(f"Invalid trigger type: {value}")
        
        if field == 'config':
            value = safe_json_dumps(value)
        elif field == 'is_active':
            value = 1 if value else 0
        
        update_fields.append(f"{field} = ?")
        params.append(value)
    
    if not update_fields:
        return Result.error("No valid fields to update")
    
    # Add trigger_id to params
    params.append(trigger_id)
    
    # Execute update
    query = f"UPDATE triggers SET {', '.join(update_fields)} WHERE id = ?"
    result = execute_sql_query(db_path, query, params)
    
    if not result.success:
        return Result.error(f"Failed to update trigger: {result.error}")
    
    return Result.success({"updated": True, "trigger_id": trigger_id})

@handle_db_errors("activate trigger")
def activate_trigger(db_path, trigger_id):
    """
    Amaç: Belirtilen trigger'ı aktif duruma getirir.
    Döner: Başarılı ise güncelleme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    return update_trigger(db_path, trigger_id, {"is_active": True})

@handle_db_errors("deactivate trigger")
def deactivate_trigger(db_path, trigger_id):
    """
    Amaç: Belirtilen trigger'ı pasif duruma getirir.
    Döner: Başarılı ise güncelleme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    return update_trigger(db_path, trigger_id, {"is_active": False})