from fastapi import status
from fastapi.exceptions import HTTPException

from minager.core.clients.knowledge_tree.client import KnowledgeTreeClient
from minager.settings import config

from . import managers, models, schemas


class UserSignupService:
    async def signup(self, user_data: schemas.UserCreateDataSchema) -> models.User:
        try:
            async with managers.UserManager() as user_manager:
                user = await user_manager.create_user(user_data)
            try:
                async with (
                    KnowledgeTreeClient(config.palace_node_db) as knowledge_tree_client,
                    managers.UserProfileManager() as profile_manager,
                ):
                    knowledge_tree_root_data = {
                        'owner_id': str(user.id),
                        'title': f"{user.username.title()}'s knowledge tree",
                        'order': 'aaaaaa',
                        'questions': 'What do I know?',
                    }
                    root = await knowledge_tree_client.create(knowledge_tree_root_data)
                    if not root:
                        raise ValueError('Unable to create knowledge tree root.')
                    profile_data = schemas.UserProfileCreateSchema(
                        user_id=user.id,
                        knowledge_tree_root_id=root.id.id,
                    )
                    await profile_manager.create_profile(profile_data)
            except Exception:
                async with managers.UserManager() as user_manager:
                    await user_manager.delete(str(user.id))
                raise

            return user
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
