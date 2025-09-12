# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.agent import Agent  # noqa
from app.models.associations import agent_followers  # noqa
from app.models.chat_settings import ChatSettings  # noqa
from app.models.message import Message  # noqa
from app.models.resource import Resource  # noqa
from app.models.settings import Settings  # noqa
from app.models.user import User  # noqa
