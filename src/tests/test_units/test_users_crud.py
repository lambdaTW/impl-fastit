import pathlib
import typing
from unittest import mock

import pytest
from fastapi import encoders
from sqlalchemy import future as sqlalchemy_future
from sqlalchemy import orm
from sqlalchemy.ext import asyncio as sqlalchemy_asyncio
from sqlalchemy_utils import functions

from app.models import auth as auth_models
from core import config


@pytest.fixture
def settings() -> typing.Iterator[config.Settings]:
    settings = config.Settings()
    settings.MODE = "test"
    settings.DATABASE_URL = settings.DATABASE_URL + "_test"
    with mock.patch("core.config.Settings") as Settings:
        Settings.return_value = settings
        yield settings


@pytest.fixture
async def gen_db(
    settings: config.Settings,
) -> None:
    engine = sqlalchemy_asyncio.create_async_engine(
        settings.DATABASE_URL,
        echo=True,
    )
    sessionmaker = orm.sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=sqlalchemy_asyncio.AsyncSession,
    )
    async with sessionmaker() as session:
        async with session as db:
            await db.run_sync(
                lambda _: (functions.create_database(settings.DATABASE_URL))
            )
            yield
        async with session as db:
            await db.close()
            await db.run_sync(
                lambda _: (functions.drop_database(settings.DATABASE_URL))
            )


@pytest.fixture
async def db(
    settings: config.Settings,
    gen_db: None,
) -> typing.AsyncIterator[sqlalchemy_asyncio.AsyncSession]:
    engine = sqlalchemy_asyncio.create_async_engine(
        settings.DATABASE_URL,
        echo=True,
    )
    sessionmaker = orm.sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=sqlalchemy_asyncio.AsyncSession,
    )
    async with sessionmaker() as session:
        async with session as db:
            yield db
    await session.close()


@pytest.fixture
async def migrate(
    settings: config.Settings,
    gen_db: None,
) -> typing.AsyncIterator[None]:
    from alembic import config as alembic_config
    from alembic.runtime.environment import EnvironmentContext
    from alembic.script import ScriptDirectory

    # 強制指定 alembic.ini
    alembic_cfg = alembic_config.Config(file_=str(pathlib.Path("src/app/alembic.ini")))
    # 強制指定 migrations 的資料夾
    alembic_cfg.set_main_option(
        "script_location", str(pathlib.Path("src/app/migrations"))
    )
    script = ScriptDirectory.from_config(alembic_cfg)

    def upgrade(rev, context):
        return script._upgrade_revs("heads", rev)

    context_kwargs = dict(
        config=alembic_cfg,
        script=script,
    )
    upgrade_kwargs = dict(fn=upgrade, starting_rev=None, destination_rev="heads")
    with EnvironmentContext(**upgrade_kwargs, **context_kwargs):
        from app.migrations import env

        # 跑起來！
        await env.run_async_migrations()
        yield


@pytest.mark.asyncio
async def test_create_and_read_user(
    db: sqlalchemy_asyncio.AsyncSession,
    migrate: None,
):
    username = "username"
    password = "password"
    obj_in = {
        "username": username,
        "password": password,
    }
    obj_in_data = encoders.jsonable_encoder(obj_in)
    user = auth_models.User(**obj_in_data)
    db.add(user)
    await db.commit()
    user = (
        (
            await db.execute(
                sqlalchemy_future.select(auth_models.User).where(
                    auth_models.User.id == user.id
                )
            )
        )
        .scalars()
        .first()
    )
    assert user.username == "username"
    assert user.password == "password"
