from minager.core.clients.knowledge_tree import KnowledgeTreeClient

from . import exceptions, models, schemas
from .services import UserProfileService, UserService


class SignUpUseCase:
    """Registers a user, provisions their knowledge-tree root, and creates their profile.

    Rolls back the created user if the knowledge-tree root cannot be created.
    """

    def __init__(
        self,
        user_service: UserService,
        user_profile_service: UserProfileService,
        knowledge_tree: KnowledgeTreeClient,
    ):
        self.user_service = user_service
        self.user_profile_service = user_profile_service
        self.knowledge_tree = knowledge_tree

    async def execute(
        self, user_data: schemas.UserCreateDataSchema
    ) -> tuple[models.User, models.UserProfile]:
        user = await self.user_service.register(user_data)
        root = await self.knowledge_tree.create(
            {
                'owner_id': str(user.id),
                'title': f"{user.username.title()}'s knowledge tree",
                'order': 'aaaaaa',
                'questions': 'What do I know?',
            }
        )
        if not root:
            await self.user_service.delete(user.id)
            raise exceptions.KnowledgeTreeProvisioningError
        profile = await self.user_profile_service.create_profile(
            schemas.UserProfileCreateSchema(
                user_id=user.id,
                knowledge_tree_root_id=root.id.id_,
            )
        )
        return user, profile
