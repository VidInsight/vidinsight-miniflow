# Models Tests - Test Listesi

## Test Dosyası
`tests/unit_tests/test_database_manager/test_models.py`

## Test Kategorileri ve Amaçları

### 1. Enum Tests (16 test)

| Test Adı | Amacı | Hata Anlamı |
|----------|-------|-------------|
| `test_workflow_status_values` | WorkflowStatus enum değerlerinin doğru olduğunu kontrol eder | Enum değerleri yanlış tanımlanmış |
| `test_workflow_status_count` | WorkflowStatus enum'da 4 değer olduğunu kontrol eder | Enum'da eksik/fazla değer var |
| `test_execution_status_values` | ExecutionStatus enum değerlerinin doğru olduğunu kontrol eder | Enum değerleri yanlış tanımlanmış |
| `test_execution_status_count` | ExecutionStatus enum'da 5 değer olduğunu kontrol eder | Enum'da eksik/fazla değer var |
| `test_execution_output_status_values` | ExecutionOutputStatus enum değerlerinin doğru olduğunu kontrol eder | Enum değerleri yanlış tanımlanmış |
| `test_execution_output_status_count` | ExecutionOutputStatus enum'da 4 değer olduğunu kontrol eder | Enum'da eksik/fazla değer var |
| `test_condition_type_values` | ConditionType enum değerlerinin doğru olduğunu kontrol eder | Enum değerleri yanlış tanımlanmış |
| `test_condition_type_count` | ConditionType enum'da 4 değer olduğunu kontrol eder | Enum'da eksik/fazla değer var |
| `test_script_type_values` | ScriptType enum değerlerinin doğru olduğunu kontrol eder | Enum değerleri yanlış tanımlanmış |
| `test_script_type_count` | ScriptType enum'da 1 değer olduğunu kontrol eder | Enum'da eksik/fazla değer var |
| `test_test_status_values` | TestStatus enum değerlerinin doğru olduğunu kontrol eder | Enum değerleri yanlış tanımlanmış |
| `test_test_status_count` | TestStatus enum'da 4 değer olduğunu kontrol eder | Enum'da eksik/fazla değer var |
| `test_audit_action_values` | AuditAction enum değerlerinin doğru olduğunu kontrol eder | Enum değerleri yanlış tanımlanmış |
| `test_audit_action_count` | AuditAction enum'da 5 değer olduğunu kontrol eder | Enum'da eksik/fazla değer var |
| `test_archive_reason_values` | ArchiveReason enum değerlerinin doğru olduğunu kontrol eder | Enum değerleri yanlış tanımlanmış |
| `test_archive_reason_count` | ArchiveReason enum'da 4 değer olduğunu kontrol eder | Enum'da eksik/fazla değer var |

### 2. BaseModel Tests (8 test)

| Test Adı | Amacı | Hata Anlamı |
|----------|-------|-------------|
| `test_id_generation` | ID generation fonksiyonunun çalışması ve unique ID üretmesi | ID generation algoritması bozuk |
| `test_id_generation_with_different_prefixes` | Farklı modeller için farklı prefix'lerle ID üretilmesi | Model prefix'leri yanlış çalışıyor |
| `test_timestamps_creation` | created_at ve updated_at timestamp'lerinin otomatik oluşturulması | Timestamp otomatik ayarlanması çalışmıyor |
| `test_timestamps_update` | Update işleminde updated_at'ın güncellenmesi | Update timestamp'i güncellenmiyor |
| `test_repr_method` | __repr__ metodunun doğru string döndürmesi | String representation yanlış |
| `test_to_dict_basic_fields` | to_dict() metodunun basic field'ları doğru dönüştürmesi | Field dönüşümü çalışmıyor |
| `test_to_dict_datetime_conversion` | to_dict() metodunun datetime'ları ISO formatına çevirmesi | Datetime dönüşümü başarısız |
| `test_to_dict_enum_conversion` | to_dict() metodunun enum'ları value'ya çevirmesi | Enum dönüşümü çalışmıyor |

### 3. Model Specific Tests (Henüz tamamlanmadı)

Bu bölümde her model için spesifik testler yer alacak:
- Workflow Model Tests
- Node Model Tests  
- Edge Model Tests
- Script Model Tests
- Execution Model Tests
- AuditLog Model Tests
- Relationship Tests

## Test İstatistikleri

### ✅ Başarılı Testler: 24/24
- **Enum Tests**: 16/16 ✅
- **BaseModel Tests**: 8/8 ✅

### 🔧 Fixture'lar (conftest.py)
- `test_database_session`: In-memory SQLite database session
- `sample_workflow_data`: Test için workflow verileri
- `sample_node_data`: Test için node verileri  
- `sample_script_data`: Test için script verileri
- `sample_execution_data`: Test için execution verileri
- `sample_edge_data`: Test için edge verileri
- `sample_audit_log_data`: Test için audit log verileri
- `workflow_with_nodes`: Relationship testleri için hazır workflow+node setup
- `enum_test_data`: Tüm enum'lar için test verileri

## Çalıştırma Komutları

```bash
# Tüm models testleri
python -m pytest tests/unit_tests/test_database_manager/test_models.py -v

# Sadece enum testleri
python -m pytest tests/unit_tests/test_database_manager/test_models.py::TestEnums -v

# Sadece BaseModel testleri  
python -m pytest tests/unit_tests/test_database_manager/test_models.py::TestBaseModel -v

# Belirli bir test
python -m pytest tests/unit_tests/test_database_manager/test_models.py::TestEnums::test_workflow_status_values -v
```

## Notlar

1. **Database Setup**: Her test için in-memory SQLite kullanılıyor
2. **Isolation**: Her test bağımsız çalışıyor, ortak state yok
3. **Unique Constraints**: Test isimleri unique constraint'lerden kaçınmak için farklı
4. **Fixtures**: Conftest.py'de tanımlı fixture'lar tüm testler tarafından kullanılabiliyor
5. **Coverage**: Enum'lar ve BaseModel için %100 coverage sağlandı