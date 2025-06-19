from minager.core.db.managers import PostgresDatabaseManager

from .models import UserProfile


class UserProfileManager(PostgresDatabaseManager):
    id_field_name = 'user_id'
    model_class = UserProfile
