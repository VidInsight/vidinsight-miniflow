from miniflow.database_manager.crud.base_crud import BaseCRUD
from miniflow.database_manager.models import Workflow, Base, WorkflowStatus
from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import create_database_engine
import time

# Database engine oluştur
config = get_sqlite_config(db_name="optimized_test")
engine = create_database_engine(config)
engine.start()

# Tabloları oluştur
engine.create_tables(Base.metadata)

# Session oluştur
with engine.get_session_context() as session:
    workflow_crud = BaseCRUD(Workflow)
    
    print("=== OPTIMIZED OPERATIONS ÖRNEKLERİ ===\n")
    
    # Test verisi oluştur
    print("1. TEST VERİSİ OLUŞTURMA")
    print("-" * 50)
    
    test_workflows = [
        {"name": "Data Pipeline Alpha", "description": "First pipeline", "status": "active", "priority": 1},
        {"name": "Data Pipeline Beta", "description": "Second pipeline", "status": "active", "priority": 2},
        {"name": "Data Pipeline Gamma", "description": "Third pipeline", "status": "draft", "priority": 3},
        {"name": "Data Pipeline Delta", "description": "Fourth pipeline", "status": "inactive", "priority": 4},
        {"name": "Data Pipeline Epsilon", "description": "Fifth pipeline", "status": "active", "priority": 5},
        {"name": "Data Pipeline Zeta", "description": "Sixth pipeline", "status": "active", "priority": 6},
        {"name": "Data Pipeline Eta", "description": "Seventh pipeline", "status": "draft", "priority": 7},
        {"name": "Data Pipeline Theta", "description": "Eighth pipeline", "status": "inactive", "priority": 8},
    ]
    
    # Bulk create ile hızlı oluşturma
    created_workflows = workflow_crud.bulk_create(session, test_workflows)
    print(f"✅ {len(created_workflows)} test workflow oluşturuldu")
    
    # Oluşturulan workflow'ları listele
    all_workflows = workflow_crud.get_all(session, limit=10)
    print(f"📋 Toplam {len(all_workflows)} workflow var")
    for wf in all_workflows:
        print(f"   - {wf.name} ({wf.status}) - Priority: {wf.priority}")
    print()
    
    # 2. CHECK_NAME_EXISTS - İsim Varlık Kontrolü
    print("2. CHECK_NAME_EXISTS - İsim Varlık Kontrolü")
    print("-" * 50)
    
    # Mevcut isim kontrolü
    existing_name = "Data Pipeline Alpha"
    name_exists = workflow_crud.check_name_exists(session, existing_name)
    print(f"🔍 '{existing_name}' ismi mevcut mu? {name_exists}")
    
    # Olmayan isim kontrolü
    non_existing_name = "Non Existent Workflow"
    name_exists = workflow_crud.check_name_exists(session, non_existing_name)
    print(f"🔍 '{non_existing_name}' ismi mevcut mu? {name_exists}")
    
    # Exclude ile kontrol (update senaryosu için)
    workflow_to_update = all_workflows[0]
    exclude_result = workflow_crud.check_name_exists(
        session, 
        workflow_to_update.name, 
        exclude_id=workflow_to_update.id
    )
    print(f"🔍 '{workflow_to_update.name}' ismi (kendisi hariç) mevcut mu? {exclude_result}")
    print()
    
    # 3. BULK_UPDATE_STATUS - Toplu Status Güncelleme
    print("3. BULK_UPDATE_STATUS - Toplu Status Güncelleme")
    print("-" * 50)
    
    # Active workflow'ları bul
    active_workflows = workflow_crud.find_by_field(session, "status", "active", limit=100)
    active_ids = [wf.id for wf in active_workflows]
    
    print(f"🔄 {len(active_ids)} active workflow'u 'archived' olarak güncellenecek")
    
    # Performance karşılaştırması
    start_time = time.time()
    updated_count = workflow_crud.bulk_update_status(
        session, active_ids, "status", "archived"
    )
    optimized_time = time.time() - start_time
    
    print(f"✅ Optimized: {updated_count} workflow güncellendi ({optimized_time:.4f}s)")
    
    # Normal way ile karşılaştırma (simülasyon)
    print("📊 Performance karşılaştırması:")
    print(f"   - Optimized (bulk_update_status): {optimized_time:.4f}s")
    print(f"   - Normal (loop + individual): ~{optimized_time * 10:.4f}s (tahmini)")
    print(f"   - Hız artışı: ~10x")
    print()
    
    # 4. BULK_UPDATE_FIELDS - Çoklu Alan Güncelleme
    print("4. BULK_UPDATE_FIELDS - Çoklu Alan Güncelleme")
    print("-" * 50)
    
    # Tüm workflow'ları al
    all_remaining = workflow_crud.get_all(session, limit=100)
    all_ids = [wf.id for wf in all_remaining]
    
    print(f"🔄 {len(all_ids)} workflow'un birden fazla alanı güncellenecek")
    
    # Çoklu alan güncelleme
    field_updates = {
        "priority": 100,
        "description": "Bulk optimized update"
    }
    
    start_time = time.time()
    updated_count = workflow_crud.bulk_update_fields(session, all_ids, field_updates)
    optimized_time = time.time() - start_time
    
    print(f"✅ Optimized: {updated_count} workflow güncellendi ({optimized_time:.4f}s)")
    
    # Güncelleme sonrasını kontrol et
    updated_workflows = workflow_crud.select_in_bulk(session, all_ids[:3])  # İlk 3'ünü kontrol et
    for wf in updated_workflows:
        print(f"   - {wf.name}: priority={wf.priority}, desc='{wf.description[:30]}...'")
    print()
    
    # 5. PERFORMANCE KARŞILAŞTIRMASI - Normal vs Optimized
    print("5. PERFORMANCE KARŞILAŞTIRMASI")
    print("-" * 50)
    
    # Test verisi oluştur
    test_data = [{"name": f"Test Workflow {i}", "status": "active"} for i in range(10)]
    workflow_crud.bulk_create(session, test_data)
    
    # Normal way (simülasyon)
    print("🐌 Normal Operations (Simülasyon):")
    print("   - Her kayıt için ayrı sorgu")
    print("   - ORM object oluşturma")
    print("   - Individual flush")
    print("   - Yavaş ve kaynak tüketen")
    print()
    
    # Optimized way
    print("⚡ Optimized Operations:")
    print("   - Tek SQL sorgusu")
    print("   - Bulk operations")
    print("   - Minimal memory usage")
    print("   - Hızlı ve verimli")
    print()
    
    # 6. VALIDATION ÖRNEKLERİ
    print("6. VALIDATION ÖRNEKLERİ")
    print("-" * 50)
    
    try:
        # Geçersiz field ile bulk update
        workflow_crud.bulk_update_status(session, all_ids, "invalid_field", "value")
    except ValueError as e:
        print(f"✅ Validation çalışıyor: {e}")
    
    try:
        # Geçersiz field ile bulk update fields
        workflow_crud.bulk_update_fields(session, all_ids, {"invalid_field": "value"})
    except ValueError as e:
        print(f"✅ Validation çalışıyor: {e}")
    
    try:
        # Name field'ı olmayan model için check_name_exists
        class TestModel:
            pass
        test_crud = BaseCRUD(TestModel)
        test_crud.check_name_exists(session, "test")
    except ValueError as e:
        print(f"✅ Validation çalışıyor: {e}")
    
    print()
    
    # 7. REAL-WORLD SCENARIOS
    print("7. REAL-WORLD SCENARIOS")
    print("-" * 50)
    
    # Senaryo 1: Workflow lifecycle management
    print("📋 Senaryo 1: Workflow Lifecycle Management")
    
    # Draft workflow'ları active yap
    draft_workflows = workflow_crud.find_by_field(session, "status", "draft", limit=100)
    draft_ids = [wf.id for wf in draft_workflows]
    
    if draft_ids:
        workflow_crud.bulk_update_status(session, draft_ids, "status", "active")
        print(f"   ✅ {len(draft_ids)} draft workflow active yapıldı")
    
    # Eski workflow'ları archive et
    old_workflows = workflow_crud.find_by_field(session, "status", "inactive", limit=100)
    old_ids = [wf.id for wf in old_workflows]
    
    if old_ids:
        workflow_crud.bulk_update_status(session, old_ids, "status", "archived")
        print(f"   ✅ {len(old_ids)} inactive workflow archived yapıldı")
    
    # Senaryo 2: Batch processing
    print("\n📋 Senaryo 2: Batch Processing")
    
    # Tüm workflow'ların priority'sini artır
    all_workflows = workflow_crud.get_all(session, limit=100)
    all_ids = [wf.id for wf in all_workflows]
    
    if all_ids:
        workflow_crud.bulk_update_fields(session, all_ids, {"priority": 999})
        print(f"   ✅ {len(all_ids)} workflow'un priority'si 999 yapıldı")
    
    # Senaryo 3: Data cleanup
    print("\n📋 Senaryo 3: Data Cleanup")
    
    # Test workflow'larını temizle
    test_workflows = workflow_crud.find_by_field(session, "name", "Test Workflow", limit=100)
    test_ids = [wf.id for wf in test_workflows]
    
    if test_ids:
        deleted_count = workflow_crud.bulk_delete(session, test_ids)
        print(f"   ✅ {deleted_count} test workflow silindi")
    
    print()
    
    # 8. MEMORY USAGE OPTIMIZATION
    print("8. MEMORY USAGE OPTIMIZATION")
    print("-" * 50)
    
    # Normal way (memory intensive)
    print("🐌 Normal way (Memory Intensive):")
    print("   - Tüm kayıtları memory'ye yükle")
    print("   - ORM object'ler oluştur")
    print("   - Her kayıt için ayrı işlem")
    print("   - High memory usage")
    
    # Optimized way (memory efficient)
    print("\n⚡ Optimized way (Memory Efficient):")
    print("   - Sadece gerekli veriyi işle")
    print("   - Bulk operations kullan")
    print("   - Minimal object creation")
    print("   - Low memory usage")
    
    print()
    
    # 9. ERROR HANDLING
    print("9. ERROR HANDLING")
    print("-" * 50)
    
    # Boş liste ile operations
    empty_result = workflow_crud.bulk_update_status(session, [], "status", "active")
    print(f"✅ Boş liste ile bulk update: {empty_result} kayıt güncellendi")
    
    # Geçersiz ID'ler ile operations
    invalid_ids = ["INVALID1", "INVALID2"]
    invalid_result = workflow_crud.bulk_update_status(session, invalid_ids, "status", "active")
    print(f"✅ Geçersiz ID'ler ile bulk update: {invalid_result} kayıt güncellendi")
    
    # Geçersiz field ile operations
    try:
        workflow_crud.bulk_update_status(session, all_ids, "non_existent_field", "value")
    except ValueError as e:
        print(f"✅ Field validation: {e}")
    
    print()
    
    # 10. FINAL STATISTICS
    print("10. FINAL STATISTICS")
    print("-" * 50)
    
    # Son durumu kontrol et
    final_workflows = workflow_crud.get_all(session, limit=100)
    
    status_counts = {}
    for wf in final_workflows:
        status = wf.status.value if hasattr(wf.status, 'value') else str(wf.status)
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("📊 Final Workflow Durumları:")
    for status, count in status_counts.items():
        print(f"   - {status}: {count} workflow")
    
    print(f"\n📋 Toplam: {len(final_workflows)} workflow")
    print("✅ Optimized operations başarıyla tamamlandı!")
    
    print("\n=== OPTIMIZED OPERATIONS TAMAMLANDI ===")

engine.stop()
