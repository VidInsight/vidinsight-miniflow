# Miniflow Database Modülü Dökümantasyonu

## Amaç ve Kapsam
Miniflow'un tüm veritabanı işlemleri bu modülde toplanır. SQLite tabanlıdır ve kolayca başka DBMS'lere uyarlanabilir. CRUD işlemleri, bağlantı yönetimi, tablo şemaları ve yardımcı fonksiyonlar içerir.

## Ana Dosyalar ve Sınıflar

- **core.py**: Temel SQL işlemleri, tablo oluşturma/silme, bağlantı yönetimi.
- **config.py**: Veritabanı bağlantı ayarları ve context manager (`DatabaseConfig`, `DatabaseConnection`).
- **schema.py**: Tüm tablo ve index şemaları.
- **exceptions.py**: Hata yönetimi ve Result objesi (`Result`).
- **utils.py**: UUID, JSON işlemleri, yardımcı fonksiyonlar.
- **functions/**: Tablolara özel CRUD ve iş mantığı fonksiyonları (ör: `nodes_table.py`, `edges_table.py`, `workflow_orchestration.py`).

## Temel Fonksiyonlar ve Kullanım

### Veritabanı Başlatma
```python
from miniflow.database.core import init_database
result = init_database("mydb.sqlite")
if result.success:
    print("Veritabanı hazır!")
```

### Veri Ekleme/Okuma
```python
from miniflow.database.core import execute_sql_query, fetch_all
execute_sql_query("mydb.sqlite", "INSERT INTO nodes (id, name) VALUES (?, ?)", (id, name))
rows = fetch_all("mydb.sqlite", "SELECT * FROM nodes")
```

### Result Kullanımı
```python
from miniflow.database.exceptions import Result
res = Result.success(data={"foo": 1})
if res:
    print(res.data)
```

### İpuçları
- Tüm fonksiyonlar `Result` objesi döner, hata kontrolü kolaydır.
- JSON alanlar için `safe_json_dumps` ve `safe_json_loads` kullanın.
- Tabloları elle silmek için `drop_all_tables` fonksiyonunu kullanabilirsiniz.

---

Daha fazla detay için ilgili dosyaların başındaki docstring açıklamalarına bakabilirsiniz. 