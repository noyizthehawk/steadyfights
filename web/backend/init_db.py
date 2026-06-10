
from .database import Base, engine
from . import models 

Base.metadata.create_all(bind=engine)

print("Database ready. Tables:", list(Base.metadata.tables.keys()))
