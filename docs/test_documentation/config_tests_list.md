# Config Tests - Test Listesi

## Test Dosyası
`tests/unit_tests/test_database_manager/test_config.py`

## Test Kategorileri ve Amaçları

### 1. DatabaseType Tests (2 test)

| Test Adı | Amacı | Hata Anlamı |
|----------|-------|-------------|
| `test_database_type_values` | Enum değerlerinin doğru olduğunu kontrol eder | DatabaseType enum'ında değerler yanlış |
| `test_database_type_count` | Enum'da 3 değer olduğunu kontrol eder | DatabaseType enum'ında eksik/fazla değer var |

### 2. EngineConfig Tests (6 test)

| Test Adı | Amacı | Hata Anlamı |
|----------|-------|-------------|
| `test_engine_config_default_values` | Default değerlerin doğru olduğunu kontrol eder | EngineConfig default değerleri yanlış |
| `test_engine_config_custom_values` | Custom değerlerle oluşturmayı test eder | EngineConfig custom değerler çalışmıyor |
| `test_engine_config_to_dict` | to_dict() metodunun çalıştığını test eder | to_dict() metodu hatalı |
| `test_engine_config_with_all_fields` | Tüm field'ların çalıştığını test eder | EngineConfig field'larından biri bozuk |
| `test_engine_config_edge_cases` | Edge case'leri test eder | Edge case'lerde sorun var |

### 3. DatabaseConfig Tests (11 test)

| Test Adı | Amacı | Hata Anlamı |
|----------|-------|-------------|
| `test_database_config_default_values` | Default değerlerin doğru olduğunu kontrol eder | DatabaseConfig default değerleri yanlış |
| `test_sqlite_connection_string` | SQLite connection string oluşturmayı test eder | SQLite connection string yanlış |
| `test_mysql_connection_string` | MySQL connection string oluşturmayı test eder | MySQL connection string yanlış |
| `test_postgresql_connection_string` | PostgreSQL connection string oluşturmayı test eder | PostgreSQL connection string yanlış |
| `test_to_dict_with_password_masked` | Şifre maskeleme özelliğini test eder | Password masking çalışmıyor |
| `test_to_dict_with_password_unmasked` | Şifre maskelemeden döndürme özelliğini test eder | Password unmasking çalışmıyor |
| `test_to_dict_without_password` | Şifre olmadan to_dict metodunu test eder | None password durumu çalışmıyor |
| `test_connection_string_unsupported_database_type` | Desteklenmeyen DB türü hatası | Hata fırlatma mekanizması bozuk |
| `test_connection_string_none_db_type` | None db_type hatası | None değer kontrolü bozuk |
| `test_connection_string_none_db_name` | None db_name durumu | None db_name işleme bozuk |
| `test_database_config_without_engine_config` | Engine config olmadan oluşturma | None engine_config işleme bozuk |
| `test_to_dict_with_none_values` | None değerlerle to_dict | None değerlerle to_dict bozuk |

### 4. DBEngineConfigs Tests (4 test)

| Test Adı | Amacı | Hata Anlamı |
|----------|-------|-------------|
| `test_sqlite_engine_config` | SQLite engine config değerlerini test eder | SQLite engine config yanlış |
| `test_postgresql_engine_config` | PostgreSQL engine config değerlerini test eder | PostgreSQL engine config yanlış |
| `test_mysql_engine_config` | MySQL engine config değerlerini test eder | MySQL engine config yanlış |
| `test_all_database_types_have_configs` | Tüm DB türlerinin config'e sahip olduğunu test eder | Eksik engine config var |

### 5. GetDatabaseConfig Tests (5 test)

| Test Adı | Amacı | Hata Anlamı |
|----------|-------|-------------|
| `test_get_database_config_with_predefined_engine` | Önceden tanımlanmış engine ile test | Predefined engine çalışmıyor |
| `test_get_database_config_with_custom_engine` | Custom engine config ile test | Custom engine çalışmıyor |
| `test_get_database_config_unsupported_type_error` | Desteklenmeyen tür hatası | Hata fırlatma mekanizması bozuk |
| `test_get_database_config_with_none_values` | None değerlerle config oluşturma | None değerlerle config oluşturma bozuk |
| `test_get_database_config_all_database_types` | Tüm DB türleri için config oluşturma | Bazı DB türleri için config oluşturulamıyor |

### 6. FactoryFunctions Tests (9 test)

| Test Adı | Amacı | Hata Anlamı |
|----------|-------|-------------|
| `test_get_sqlite_config_default` | Default SQLite config | get_sqlite_config() default değerleri yanlış |
| `test_get_sqlite_config_custom` | Custom SQLite config | get_sqlite_config() custom değerleri çalışmıyor |
| `test_get_postgresql_config_default` | Default PostgreSQL config | get_postgresql_config() default değerleri yanlış |
| `test_get_postgresql_config_custom` | Custom PostgreSQL config | get_postgresql_config() custom değerleri çalışmıyor |
| `test_get_mysql_config_default` | Default MySQL config | get_mysql_config() default değerleri yanlış |
| `test_get_mysql_config_custom` | Custom MySQL config | get_mysql_config() custom değerleri çalışmıyor |
| `test_get_sqlite_config_direct` | Doğrudan SQLite factory fonksiyonu | get_sqlite_config() fonksiyonu bozuk |
| `test_get_postgresql_config_direct` | Doğrudan PostgreSQL factory fonksiyonu | get_postgresql_config() fonksiyonu bozuk |
| `test_get_mysql_config_direct` | Doğrudan MySQL factory fonksiyonu | get_mysql_config() fonksiyonu bozuk |

## Test Çalıştırma

```bash
# Tüm config testleri
python -m pytest tests/unit_tests/test_database_manager/test_config.py -v

# Belirli test kategorisi
python -m pytest tests/unit_tests/test_database_manager/test_config.py::TestEngineConfig -v

# Belirli test
python -m pytest tests/unit_tests/test_database_manager/test_config.py::TestDatabaseConfig::test_sqlite_connection_string -v
```

## Test Sonuçları

- **Toplam Test:** 37
- **Geçen Test:** 37
- **Başarısız Test:** 0
- **Çalışma Süresi:** ~0.05 saniye 