from minager.core.db.managers import PostgresDatabaseManager

from . import models


class UserProfileManager(PostgresDatabaseManager):
    id_field_name = 'user_id'
    model_class = models.UserProfile


class UserManager:
    pass
