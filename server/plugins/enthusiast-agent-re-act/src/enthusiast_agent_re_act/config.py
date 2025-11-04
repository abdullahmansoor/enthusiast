from enthusiast_common.config import AgentConfigWithDefaults, LLMToolConfig
#from langchain_core.prompts import ChatPromptTemplate
from enthusiast_common.config.base import ChatPromptTemplateConfig


from .agent import BaseReActAgent
from .template_re_act_prompt import TEMPLATE_RE_ACT_PROMPT
from agent.core.agents import ToolCallingAgent


def get_config() -> AgentConfigWithDefaults:
    return AgentConfigWithDefaults(
        chat_prompt_template=ChatPromptTemplateConfig(
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
        tools=ToolCallingAgent.TOOLS,
    )