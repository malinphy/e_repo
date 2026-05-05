from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
load_dotenv(override=True)
# memory sistemi
checkpointer = MemorySaver()

# agent oluştur
agent = create_deep_agent(
    model="openai:gpt-4o-mini",
    skills=["./skills"],  # tüm skill klasörlerini otomatik okur
    checkpointer=checkpointer,
)

# test promptları
queries = [
    "15 * 8 kaç eder?",
    "Hello'yu Türkçeye çevir",
    "LangChain is a framework for building LLM applications. It provides tools for chaining models, memory, and agents. Summarize this."
]

for q in queries:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": q}]},
        config={"configurable": {"thread_id": "test-thread"}}
    )
    print("\nSoru:", q)
    msg = result["messages"][-1]
    content = msg.content
    if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
        content = content[0]["text"]
    print("Cevap:", content)