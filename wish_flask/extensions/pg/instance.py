from wish_flask.lib.instance_manager import InstanceManager
try:
    from flask_sqlalchemy import SQLAlchemy
except:
    SQLAlchemy = None


_instance_type = 'pg'
_instance_manager = InstanceManager.get_manager(_instance_type)

if SQLAlchemy:
    # Create metrics instance globally as it may be used in decorator
    _instance_manager.set_default_obj(SQLAlchemy())

# annotations
pg: SQLAlchemy = _instance_manager.get_obj_proxy()
