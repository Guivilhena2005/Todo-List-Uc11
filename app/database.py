
"""Infraestrutura de banco: engine, fábrica de sessões e a classe Base do ORM.

Este módulo é o único lugar que sabe qual banco está em uso.
O restante da aplicação trabalha com a sessão do SQLAlchemy.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Configuracao, obter_configuracao


def _opcoes_do_engine(configuracao: Configuracao) -> dict[str, Any]:
    """Opções de conexão adequadas ao banco em uso."""

    if configuracao.dialeto == "sqlite":
        opcoes: dict[str, Any] = {
            "connect_args": {"check_same_thread": False}
        }

        if configuracao.banco_em_memoria:
            opcoes["poolclass"] = StaticPool

        return opcoes

    return {
        "pool_pre_ping": True,
        "pool_recycle": 1800
    }


@event.listens_for(Engine, "connect")
def _ativar_chaves_estrangeiras(
    conexao_dbapi: Any,
    _registro: Any
) -> None:
    """Ativa a verificação de chaves estrangeiras em cada conexão SQLite."""

    if isinstance(conexao_dbapi, sqlite3.Connection):
        cursor = conexao_dbapi.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


_configuracao = obter_configuracao()

engine = create_engine(
    _configuracao.url_banco,
    echo=_configuracao.echo_sql,
    **_opcoes_do_engine(_configuracao),
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


def criar_tabelas() -> None:
    """Cria as tabelas que ainda não existem no banco."""

    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def obter_sessao() -> Generator[Session, None, None]:
    """Fornece uma sessão de banco por requisição e a encerra ao final."""

    sessao = SessionLocal()

    try:
        yield sessao
    finally:
        sessao.close()
