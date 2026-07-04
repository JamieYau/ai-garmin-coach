import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import target_metadata


class ExampleParent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "example_parents"

    email: Mapped[str] = mapped_column(String(320), nullable=False)

    __table_args__ = (
        UniqueConstraint("email"),
        Index(None, "email"),
    )


class ExampleChild(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "example_children"

    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("example_parents.id"))


def test_model_metadata_uses_shared_naming_convention() -> None:
    assert Base.metadata is target_metadata
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"

    assert ExampleParent.__table__.primary_key.name == "pk_example_parents"
    assert next(iter(ExampleParent.__table__.indexes)).name == "ix_example_parents_email"

    unique_constraint = next(
        constraint
        for constraint in ExampleParent.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    )
    assert unique_constraint.name == "uq_example_parents_email"

    foreign_key_constraint = next(iter(ExampleChild.__table__.foreign_key_constraints))
    assert foreign_key_constraint.name == "fk_example_children_parent_id_example_parents"


def test_common_model_columns_are_declared() -> None:
    columns = ExampleParent.__table__.columns

    assert columns["id"].primary_key is True
    assert columns["id"].type.python_type is uuid.UUID
    assert columns["created_at"].nullable is False
    assert columns["updated_at"].nullable is False
    assert columns["created_at"].server_default is not None
    assert columns["updated_at"].server_default is not None
