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
        name="Test Workflow",
        description="This is a test workflow",
        status="active"
    )
    print(workflow)
    print(workflow.id)
    print(workflow.name)
    print(workflow.created_at)
    print(workflow.updated_at)
    print(workflow.status)

    result = workflow_crud.find_by_id(session, workflow.id)
    print(result)

    result = workflow_crud.find_by_name(session, "Test Workflow")
    print(result)

    result = workflow_crud.update(session, workflow.id, 
                                  name="Test Workflow 2")

    print(result)

    result = workflow_crud.delete(session, workflow.id)
    print(result)
engine.stop()
