from miniflow.database_manager.crud.base_crud import BaseCRUD
from miniflow.database_manager.models import Workflow, Base, WorkflowStatus
from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import create_database_engine

# Database engine oluştur
config = get_sqlite_config(db_name="test")
engine = create_database_engine(config)
engine.start()

# Tabloları oluştur
engine.create_tables(Base.metadata)

# Session oluştur
with engine.get_session_context() as session:
    workflow_crud = BaseCRUD(Workflow)
    
    print("=== BULK OPERATIONS ÖRNEKLERİ ===\n")
    
    # 1. BULK CREATE - Toplu oluşturma (ID'ler otomatik oluşacak)
    print("1. BULK CREATE - Toplu Workflow Oluşturma (Otomatik ID)")
    print("-" * 50)
    
    import time
    timestamp = int(time.time())
    bulk_workflows = [
        {"name": f"Data Pipeline 1-{timestamp}", "description": "First data pipeline", "status": "active"},
        {"name": f"Data Pipeline 2-{timestamp}", "description": "Second data pipeline", "status": "draft"},
        {"name": f"Data Pipeline 3-{timestamp}", "description": "Third data pipeline", "status": "active"},
        {"name": f"Data Pipeline 4-{timestamp}", "description": "Fourth data pipeline", "status": "inactive"},
        {"name": f"Data Pipeline 5-{timestamp}", "description": "Fifth data pipeline", "status": "active"}
    ]
    
    objects_data = workflow_crud.bulk_create(session, bulk_workflows)
    print(f"✅ {len(objects_data)} workflow toplu olarak oluşturuldu (ID'ler otomatik)")
    print(objects_data)

    
    # 2. BULK UPDATE - Toplu güncelleme
    print("\n2. BULK UPDATE - Toplu Status Güncelleme")
    print("-" * 50)
    
    # Önce active olan workflow'ları bul
    active_workflows = workflow_crud.find_by_field(session, "status", "active", limit=100)
    active_ids = [wf.id for wf in active_workflows]
    
    print(f"🔄 {len(active_ids)} active workflow'u 'archived' olarak güncellenecek")
    
    # Bulk update için data hazırla
    bulk_updates = []
    for wf_id in active_ids:
        bulk_updates.append({
            "id": wf_id,
            "status": "archived",
            "description": f"Updated: {wf_id}"
        })
    
    updated = workflow_crud.bulk_update(session, bulk_updates)
    print(f"✅ {len(updated)} workflow toplu olarak güncellendi")
    print(updated)
    
    # Güncelleme sonrasını kontrol et
    archived_workflows = workflow_crud.find_by_field(session, "status", "archived", limit=100)
    print(f"📋 {len(archived_workflows)} workflow artık 'archived' durumunda")
    print()
    
    # 3. BULK DELETE - Toplu silme
    print("3. BULK DELETE - Toplu Silme")
    print("-" * 50)
    
    # Draft olan workflow'ları bul ve sil
    draft_workflows = workflow_crud.find_by_field(session, "status", "draft", limit=100)
    draft_ids = [wf.id for wf in draft_workflows]
    
    print(f"🗑️ {len(draft_ids)} draft workflow silinecek")
    
    deleted_count = workflow_crud.bulk_delete(session, draft_ids)
    print(f"✅ {deleted_count} workflow toplu olarak silindi")
    
    # Silme sonrasını kontrol et
    remaining_workflows = workflow_crud.get_all(session, limit=10)
    print(f"📋 Silme sonrası {len(remaining_workflows)} workflow kaldı")
    print()
    
    # 4. SELECT IN BULK - Toplu seçim
    print("4. SELECT IN BULK - Toplu Seçim")
    print("-" * 50)
    
    # Belirli ID'lere sahip workflow'ları seç
    specific_ids = [remaining_workflows[0].id, remaining_workflows[1].id] if len(remaining_workflows) >= 2 else []
    
    if specific_ids:
        selected_workflows = workflow_crud.select_in_bulk(session, specific_ids)
        print(f"📋 {len(selected_workflows)} workflow seçildi:")
        for wf in selected_workflows:
            print(f"   - {wf.name} (ID: {wf.id})")
    else:
        print("❌ Seçim için yeterli workflow yok")
    print()
    
    # 7. PERFORMANCE KARŞILAŞTIRMASI
    print("7. PERFORMANCE KARŞILAŞTIRMASI")
    print("-" * 50)
    
    # Tek tek oluşturma vs Bulk oluşturma
    import time
    
    # Tek tek oluşturma
    timestamp2 = int(time.time() * 1000)  # Mikrosaniye hassasiyeti
    start_time = time.time()
    for i in range(5):  # Daha az sayıda test için
        workflow_crud.create(session, name=f"Single {i}-{timestamp2}", status="active")
    single_time = time.time() - start_time
    
    # Bulk oluşturma (artık ID'ler otomatik)
    bulk_data = [{"name": f"Bulk {i}-{timestamp2}", "status": "active"} for i in range(5)]
    start_time = time.time()
    workflow_crud.bulk_create(session, bulk_data)
    bulk_time = time.time() - start_time
    
    print(f"⏱️ Tek tek oluşturma: {single_time:.4f} saniye")
    print(f"⏱️ Bulk oluşturma: {bulk_time:.4f} saniye")
    if bulk_time > 0:
        print(f"🚀 Bulk işlem {single_time/bulk_time:.1f}x daha hızlı!")
    else:
        print("🚀 Bulk işlem çok hızlı!")
    print()
    
    # 8. HATA YÖNETİMİ
    print("8. HATA YÖNETİMİ")
    print("-" * 50)
    
    try:
        # Geçersiz ID ile bulk delete
        invalid_ids = ["INVALID1", "INVALID2"]
        deleted_count = workflow_crud.bulk_delete(session, invalid_ids)
        print(f"✅ Geçersiz ID'lerle silme: {deleted_count} kayıt silindi (0 olmalı)")
        
        # Boş liste ile bulk operations
        empty_result = workflow_crud.bulk_create(session, [])
        print(f"✅ Boş liste ile bulk create: {empty_result} kayıt oluşturuldu (0 olmalı)")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    print("\n=== BULK OPERATIONS TAMAMLANDI ===")

engine.stop()
