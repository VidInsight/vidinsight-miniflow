from miniflow.database_manager.crud.base_crud import BaseCRUD
from miniflow.database_manager.models import Workflow, Base
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

    workflow = workflow_crud.create(
        session=session,
        name="Test Workflow 1",
        description="This is a test workflow 1",
        status="active"
    )

    workflow = workflow_crud.create(
        session=session,
        name="Test Workflow 2",
        description="This is a test workflow 2",
        status="active"
    )

    workflow = workflow_crud.create(
        session=session,
        name="Test Workflow 3",
        description="This is a test workflow 3",
        status="active"
    )

    result = workflow_crud.get_all(session)
    print("=========== GET ALL ==")
    print(result)

    result = workflow_crud.count(session)
    print("=========== COUNT ==")
    print(result)

    result = workflow_crud.exists(session, workflow.id)
    print("=========== EXISTS ==")
    print(result)

    result = workflow_crud.filter(session, {"name": "Test Workflow 1"})
    print("=========== FILTER - NAME ==")
    print(result)

    result = workflow_crud.filter(session, {"status": "active"})
    print("=========== FILTER - STATUS==")
    print(result)

    result = workflow_crud.count_filtered(session, {"status": "active"})
    print("=========== COUNT FILTERED ==")
    print(result)

    result = workflow_crud.find_by_field(session, "name", "Test Workflow 1")
    print("=========== FIND BY FIELD ==")
    print(result)