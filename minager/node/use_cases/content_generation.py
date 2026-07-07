from abc import ABCMeta, abstractmethod
from typing import Self

from huggingface_hub import ChatCompletionOutput, InferenceClient

from minager.settings import config

from .. import exceptions, models, repositories

PROMPT = """
You are a knowledge architect/scientific trainer.

Your task is to generate content for a single node in a hierarchical knowledge tree.
The goal is to explain the topic clearly, precisely, and structurally, using a decomposition approach.

OUTPUT FORMAT
- Output MUST be valid rich-text HTML
- Allowed HTML tags only:
  p, h1-h6, ul, ol, li, a, span, pre, code
- Do NOT use any other HTML tags
- Code blocks MUST be wrapped in:
  <pre><code> ... </code></pre>
- Do NOT apply syntax highlighting or language identifiers
- Do NOT include inline code outside <code> tags
- Do NOT include introductions or conclusions
- Do NOT mention applications, platforms, editors, or the knowledge tree itself

LANGUAGE & STYLE RULES
- Be strict and concise
- No noise or filler
- Use simple, direct language
- Use headings, lists, and spacing to organize information
- Inline formatting using <span> is allowed for emphasis or definitions
- No metaphors, no marketing language, no emojis
- No references like “in this section”, “below”, or “as mentioned earlier”

CONTENT RULES
- Answer all user-defined questions fully
- You may add a small number of important questions if they improve understanding, and answer them
- Avoid unnecessary comparisons unless they clarify the concept
- Examples must be minimal and directly relevant
- Code examples are allowed but must be short and illustrative only

CONTENT STRUCTURE
Use the following blocks when relevant:

1. Description
   - Short and meaningful
   - Clearly defines what the topic is

2. Main Features
   - Core characteristics only

3. Advantages and Disadvantages
   - Balanced and factual
   - No opinionated language

4. Use Cases
   - Typical and realistic scenarios

5. Examples
   - Conceptual examples and/or short code blocks
   - No full implementations

INPUT DATA
Node name: {title}
Node address in the tree: {address}
User-defined questions: {questions}
"""


class BaseNodeContentGenerator(metaclass=ABCMeta):
    @abstractmethod
    async def generate(self, *args, **kwargs):
        pass


class HuggingFaceNodeContentGenerator(BaseNodeContentGenerator):
    def __init__(self, token: str, model: str, **client_kwargs):
        self.client = InferenceClient(token=token, model=model, **client_kwargs)

    @classmethod
    def from_config(cls) -> Self:
        return cls(token=config.huggingface_api_token, model=config.huggingface_llm_model)

    async def generate(self, node: models.Node, *args, **kwargs) -> str:
        prepared_prompt = PROMPT.format(
            title=node.title, questions=node.questions, address='not filled for now'
        )
        output = self.client.chat_completion(messages=[{'role': 'user', 'content': prepared_prompt}])
        return self._extract_generate_response_content(output)

    def _extract_generate_response_content(self, response: ChatCompletionOutput) -> str:
        output = []
        for choice in response.choices:
            if choice.message:
                output.append(choice.message['content'])
        return '\n'.join(output)


class GenerateNodeContentUseCase:
    def __init__(self, repository: repositories.NodeRepository):
        self.repository = repository

    async def execute(self, id_: str) -> str:
        node = await self.repository.get(id_)
        if not node:
            raise exceptions.NodeNotFoundError
        generator = HuggingFaceNodeContentGenerator.from_config()
        return await generator.generate(node)
