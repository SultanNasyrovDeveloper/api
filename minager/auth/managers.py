from minager.core.db.managers import PostgresDatabaseManager

from .models import User


class UserManager(PostgresDatabaseManager[User]):
    model_class = User
