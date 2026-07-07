# AI Repetition Assistant — Design

Design decisions for `repetition_assistant`, an AI-driven chat that reviews a user's understanding of a node. Finalized 2026-07-07, revised 2026-07-07 (standalone scope, lazy persistence, no verdict tracking).

## What it is

A new top-level module, `repetition_assistant/`, sitting as a peer to `node/`, `learning_session/`, and `user/`. It provides a conversational, AI-driven review of a node as an alternative to just reading the node and self-rating.

**It is advisory only, and fully standalone.** The module has zero coupling to `learning_session` — not even a session existence check:

- It never writes to `LearningSession` documents.
- It never touches the SM2 algorithm, the review queue, or `bad_repetition_queue`.
- It is not scoped to a session at all — a chat is keyed on `node_id` only. Any node the user can view, they can chat about, whether or not it's the current/queued node in any repetition session.
- The user still manually submits their own 0-5 rating through the existing, unchanged `POST /learning-sessions/{id}/repeat` endpoint. Nothing in this module notifies that flow or gates it.

Anything the AI says — including a suggested rating and topic feedback, if and when it gets there — is only ever *shown* to the user (e.g. alongside the node detail page) as a recommendation. The user decides what to actually submit, and decides when they're done with the conversation. There is no "finish"/"skip" action in this module — the user simply stops sending messages whenever they want.

## Why this shape

- `learning_session`'s SM2/filter/traversal design was only just finalized and is unrelated to this feature — this avoids re-opening or complicating that mechanism, and avoids needing any Port/Adapter into it at all.
- Keeping the AI's output advisory-only avoids trusting unreliable LLM output for automatic mutations to the knowledge tree or session state.
- No explicit "conversation finished" contract means no extra endpoint, no extra state field, and no coordination problem between "user closed the tab" and "backend thinks the review is still open." A message list is either short or long; nothing depends on it being "complete."

## Conversation flow

1. **Opener is frontend-only.** When the user opens the chat for a node, the frontend renders a greeting/prompt locally (from node data it already has: title, questions, tree address). **No backend call happens at this point** — no review row is created.
2. **First real backend call = user's first message.** `POST /repetition-assistant/reviews { node_id, content }` creates the review document, fetches the node via the existing `KnowledgeTreeClient` Port (source of truth for content sent to the LLM — not trusted from the client), builds the system prompt, appends the user's message, and calls the LLM for the first real turn.
3. **Every LLM response is structured** as one of:
   ```
   { "role": "assistant", "type": "question", "content": "<follow-up question or task>" }
   { "role": "assistant", "type": "verdict", "rating": 0-5, "topics_to_add": ["..."], "topics_to_repeat": ["..."] }
   ```
   The model self-reports which one it's producing each turn. There is no separate `Verdict` model — a "verdict" is just an assistant message whose `type` happens to be `verdict`. The frontend renders it distinctly (e.g. a recommendation card) purely based on that field.
4. **Question cap.** The LLM gets at most **3 questions** across the conversation. If it hasn't produced a `type: verdict` message by the 3rd question, the next call forces one (`force_verdict=True` passed to the client, independent of any user action).
5. **Subsequent turns:** `POST /repetition-assistant/reviews/{id}/messages { content }` appends the user's message and returns the next assistant turn.
6. **Ending.** There is no dedicated action. The user stops sending messages whenever they're satisfied (having reached a `verdict` turn or not) and goes to the node detail page / repeats the node manually. A conversation that never reaches a `verdict` message is not an error state — it's just a shorter conversation.

## Message & data model

One MongoDB document per conversation, created lazily on the first real message (see above — never created for an opener the user never responds to):

```jsonc
{
  "_id": ObjectId,
  "node_id": "...",
  "user_id": "...",
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "type": "question", "content": "..." },
    { "role": "user", "content": "..." },
    { "role": "assistant", "type": "verdict", "rating": 4, "topics_to_add": [...], "topics_to_repeat": [...] }
  ],
  "created": "...",
  "updated": "..."
}
```

User messages are **plain text** (`content: str`) — no rich-text/Lexical editor for chat input. Node content itself can stay rich HTML (unrelated, unchanged); only the chat message format is plain text, sent to the LLM verbatim.

## Cross-module dependencies

- **Node content:** read via the existing `KnowledgeTreeClient` Port (`core/clients/knowledge_tree`). No changes needed there. This is the *only* cross-module dependency this module has.
- No Port into `learning_session` — not designed, not needed. (`learning_session`'s own business logic around AI-assisted review, if any, is still being worked out separately and is out of scope here.)
- No other module may import `repetition_assistant` internals directly, and `repetition_assistant` may not import `learning_session` or `node` directly — same Ports & Adapters rules as the rest of the codebase apply; the one exception is the `KnowledgeTreeClient` Port above.

## LLM client

- A **single concrete class**, not a Protocol/ABC or a multi-provider abstraction at our layer — same reasoning as before: there's no real second provider to swap in today, so a Port here would have no second consumer.
- Implementation library: **`langchain-openai`**'s `ChatOpenAI`, used *inside* that one concrete class — chosen for familiarity with the LangChain ecosystem, not for its multi-provider abstraction (we don't use that part). Its `.with_structured_output()` is a wrapper around OpenAI's native structured-output support, so functionally this is equivalent to calling the `openai` SDK directly — the tradeoff is a heavier, faster-moving dependency in exchange for hands-on LangChain experience. Worth being explicit that's the reason, since it's not a capability gain.
- Structured output enforced via a discriminated Pydantic union (`type: Literal['question'] | Literal['verdict']`) matching the message shape above.

## Architecture / file layout

```
minager/repetition_assistant/
├── api.py            # POST /repetition-assistant/reviews, /reviews/{id}/messages
├── schemas.py         # request schemas, response aliased to models.RepetitionAssistantReview
├── models.py          # Mongo document model (messages only, no separate verdict field)
├── enums.py            # MessageRole, TurnType
├── services.py        # simple reads (get)
├── use_cases.py        # SendMessageUseCase (handles both "create on first message" and "append")
├── client.py           # concrete ChatReviewClient (langchain-openai backed)
├── repositories.py    # Mongo persistence, built on the new shared base (see below)
├── dependencies.py    # DI wiring
└── exceptions.py       # ReviewNotFoundError
```

## Implementation Plan

This section says *how* to build the above, tying each piece to an existing file in this repo it should mirror or reuse.

### Shared Mongo repository base (new, extracted)

`core/db/mongo.py` currently only defines `MongoDBId` — no base repository class exists yet. `LearningSessionRepository` (`minager/learning_session/repositories.py`) and the new `RepetitionAssistantRepository` are near-identical (`COLLECTION` class attr, `get`/`create`/`update` via `find_one`/`insert_one`/`find_one_and_update(..., return_document=ReturnDocument.AFTER)`). With two real concrete consumers, extract:

```python
# core/db/mongo.py
class MongoRepository[ModelT: BaseModel]:
    COLLECTION: ClassVar[str]
    model: ClassVar[type[ModelT]]  # Python generics don't expose ModelT at runtime — declare explicitly

    def __init__(self, connection: motor.AsyncIOMotorCollection):
        self.connection = connection

    async def get(self, id_: str | ObjectId) -> ModelT | None:
        id_ = id_ if isinstance(id_, ObjectId) else ObjectId(id_)
        doc = await self.connection.find_one({'_id': id_})
        return self.model.model_validate(doc) if doc else None

    async def create(self, data: dict | ModelT) -> ModelT:
        document = data.model_dump(mode='json') if isinstance(data, BaseModel) else data
        insert_result = await self.connection.insert_one(document)
        return await self.get(insert_result.inserted_id)

    async def update(self, id_: str | ObjectId, data: dict) -> ModelT:
        id_ = id_ if isinstance(id_, ObjectId) else ObjectId(id_)
        updated = await self.connection.find_one_and_update(
            {'_id': id_}, {'$set': data}, return_document=ReturnDocument.AFTER
        )
        if updated is None:
            raise ValueError(f'{self.model.__name__}({id_}) not found')
        return self.model.model_validate(updated)
```

`LearningSessionRepository` is refactored to subclass this, collapsing to just its bespoke method:

```python
class LearningSessionRepository(MongoRepository[LearningSession]):
    COLLECTION = 'session'
    model = LearningSession

    async def find_active_for_user(self, user_id: str) -> LearningSession | None:
        doc = await self.connection.find_one({'user_id': user_id, 'is_active': True})
        return self.model.model_validate(doc) if doc else None
```

`RepetitionAssistantRepository` subclasses it too, adding only an `append_message` helper (a `$push` update, the one operation the generic base doesn't cover):

```python
class RepetitionAssistantRepository(MongoRepository[RepetitionAssistantReview]):
    COLLECTION = 'repetition_assistant_review'
    model = RepetitionAssistantReview

    async def append_message(self, id_: str | ObjectId, message: Message) -> RepetitionAssistantReview:
        id_ = id_ if isinstance(id_, ObjectId) else ObjectId(id_)
        updated = await self.connection.find_one_and_update(
            {'_id': id_},
            {'$push': {'messages': message.model_dump(mode='json')}, '$set': {'updated': datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise ValueError(f'RepetitionAssistantReview({id_}) not found')
        return self.model.model_validate(updated)
```

### File-by-file breakdown of `minager/repetition_assistant/`

- **`models.py`** — `RepetitionAssistantReview(MongoDBModel)`: `id`, `node_id`, `user_id`, `messages: list[Message]`, `created`, `updated`. `Message` is a discriminated union:
  - `UserMessage { role: 'user', content: str }`
  - `AssistantQuestionMessage { role: 'assistant', type: 'question', content: str }`
  - `AssistantVerdictMessage { role: 'assistant', type: 'verdict', rating: int, topics_to_add: list[str], topics_to_repeat: list[str] }`
- **`enums.py`** — `MessageRole` (`user`/`assistant`), `TurnType` (`question`/`verdict`).
- **`schemas.py`** — `SendMessageSchema { node_id?, content }` (node_id required only on the creating call). Response aliased directly to `models.RepetitionAssistantReview` — no separate DTO, per the "repositories return DB/ORM models directly" rule, mirroring `learning_session/schemas.py`'s `LearningSessionSchema = LearningSession`.
- **`repositories.py`** — `RepetitionAssistantRepository(MongoRepository[RepetitionAssistantReview])`, `COLLECTION = 'repetition_assistant_review'`, plus `append_message`.
- **`client.py`** — concrete `ChatReviewClient`:
  - `__init__(self, api_key: str, model: str)`, backed by `langchain_openai.ChatOpenAI`.
  - `from_config(cls) -> Self` classmethod reading `config.openai_api_key` / `config.openai_model` — mirrors `HuggingFaceNodeContentGenerator.from_config()` in `minager/node/use_cases/content_generation.py`.
  - `async def next_turn(self, node, messages: list[Message], *, force_verdict: bool = False) -> AssistantQuestionMessage | AssistantVerdictMessage`.
- **`use_cases.py`** — `SendMessageUseCase(repository, knowledge_tree_client, chat_client)`:
  - If no `review_id` given (first call): fetch node via `KnowledgeTreeClient`, create a new `RepetitionAssistantReview` with the user's message, call `chat_client.next_turn`, append the response, persist, return.
  - If `review_id` given: load the review, append the user's message, count prior `type: question` assistant messages, call `chat_client.next_turn(..., force_verdict=count >= 3)`, append, persist, return.
  - One use case covers both cases (they're the same operation at different starting points) rather than a separate `StartReviewUseCase`.
- **`services.py`** — thin `RepetitionAssistantService(repository)` with `get(id_)`.
- **`api.py`**:
  - `POST /repetition-assistant/reviews` — body `{node_id, content}`, no `review_id` yet → creates.
  - `POST /repetition-assistant/reviews/{id_}/messages` — body `{content}` → appends.
  - Both behind `CurrentUserID` (from `minager.core.auth.dependencies`); `ReviewNotFoundError` → 404, mirroring `learning_session/api.py`'s error-translation pattern.
- **`dependencies.py`** — DI chain mirroring `learning_session/dependencies.py`: `RepositoryDependency` → `ServiceDependency` / `SendMessageUseCaseDependency`, plus `ChatReviewClientDependency` and reuse of the existing `KnowledgeTreeClientDependency` pattern (built from `SurrealSession`, same as in `learning_session/dependencies.py`).
- **`exceptions.py`** — `ReviewNotFoundError` only. (No `NodeNotUnderReviewError` — there's no validation to fail.)

### Config

Add to `ApplicationConfig` in `minager/settings.py`, beside the existing `huggingface_*` fields:
```python
openai_api_key: str | None = Field(default=None)
openai_model: str = 'gpt-4o-mini'
```
Add `langchain-openai` to `pyproject.toml` dependencies.

### Mongo collection

New collection (`repetition_assistant_review`) on the same `app.state.mongo` connection already wired in `lifespan.py` — no lifespan changes needed.

### Testing

Mirror `tests/learning_session/`: `tests/repetition_assistant/test_api.py`, `test_use_cases.py`, `test_repositories.py`. `ChatReviewClient` is the one dependency that must be faked/stubbed in tests (unlike Repositories, which hit real DBs per this repo's testing philosophy) — inject a stub via `app.dependency_overrides`, the same override mechanism already used for DB dependencies.

## Open questions (deferred, not yet decided)

- **Config key names** — e.g. `OPENAI_API_KEY`, `OPENAI_MODEL` (exact naming TBD at implementation time).
- **Content format sent to the LLM** — raw HTML `node.content` vs. a stripped plain-text version (affects prompt size/cost and how cleanly the model reads it). Note this is about *node* content read via `KnowledgeTreeClient`, unrelated to chat message format (which is settled: plain text).

Do not assume answers to these — they need a decision before or during implementation.
