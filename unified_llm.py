from langchain_community.chat_models import ChatLiteLLM

key = "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"
llm = ChatLiteLLM(model = "openrouter/nvidia/nemotron-nano-12b-v2-vl:free",api_key = key)

print(llm.invoke("How are you ?"))