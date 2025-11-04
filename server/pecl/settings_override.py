# Put your custom settings in this file
# They will override the settings defined in Enthusiast's pecl/settings.py
AVAILABLE_AGENTS: dict[str, dict[str, str]] = { 
    "question_answer_agent": {
        "name": "Question Answer Agent",
        "agent_directory_path": "agent.core.agents.tool_calling_agent",
    },
   "react_agent": {
        "name": "ReAct Agent",
        "agent_directory_path": "enthusiast_agent_re_act",
    },

}
