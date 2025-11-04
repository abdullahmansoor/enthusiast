from enthusiast_common.config import AgentConfigWithDefaults, LLMToolConfig
from langchain_core.prompts import ChatPromptTemplate

from .tools.pdf_context_tool import ContextSearchTool
from .agent import BaseReActAgent
from .template_re_act_prompt import TEMPLATE_RE_ACT_PROMPT


def get_config(conversation_id: int, streaming: bool) -> AgentConfigWithDefaults:
    return AgentConfigWithDefaults(
        conversation_id=conversation_id,
        prompt_template=ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    TEMPLATE_RE_ACT_PROMPT,
                ),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        ),
        agent_class=BaseReActAgent,
        llm_tools=[
            LLMToolConfig(
                tool_class=ContextSearchTool,
            )
        ],
    )