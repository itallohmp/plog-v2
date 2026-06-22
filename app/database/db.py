from sqlalchemy import DeclarativeBase, create_engine

db = create_engine(
    "sqlite:///database/plog.db"
)  # sqlite é um banco de dados leve e fácil de usar

Base = DeclarativeBase()
