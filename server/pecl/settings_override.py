# Put your custom settings in this file
# They will override the settings defined in Enthusiast's pecl/settings.py
AVAILABLE_AGENTS: dict[str, dict[str, str]] = {
    "question_answer_agent": {
        "name": "Question Answer Agent",
        "agent_directory_path": "agent.core.agents.tool_calling_agent",
    },
    # Uncomment after installing enthusiast-agent-re-act plugin:
    # "react_agent": {
    #     "name": "ReAct Agent",
    #     "agent_directory_path": "enthusiast_agent_re_act",
    # },
}

# server/pecl/settings.py
CATALOG_PRODUCT_SOURCE_PLUGINS = {
    "Sample Product Source": "enthusiast_source_sample.SampleProductSource",
    "Dermlex Product Source": "enthusiast_source_dermlax.DermlaxProductSource",
    "Custom Product Source": "enthusiast_source_custom.CustomProductSource",
}

CATALOG_DOCUMENT_SOURCE_PLUGINS = {
    "Sample Document Source": "enthusiast_source_sample.SampleDocumentSource",
    "Dermlax Document Source": "enthusiast_source_dermlax.DermlaxDocumentSource",
}
