import sys
import os
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

# Unicode çıktı desteği
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from tools.product_search import compare_prices
load_dotenv(override=True)
# memory sistemi
checkpointer = MemorySaver()

from deepagents.backends import FilesystemBackend
from pathlib import Path

# script dizini
SCRIPT_DIR = Path(__file__).parent

# agent oluştur
agent = create_deep_agent(
    model="openai:gpt-4o-mini",
    memory=["./INSTRUCTIONS.md"],
    tools=[compare_prices],
    skills=["./skills"],  # backend root_dir'ine göre rölatif
    checkpointer=checkpointer,
    backend=FilesystemBackend(root_dir=SCRIPT_DIR),
)

# test promptları
queries = [
    # "15 * 8 kaç eder?",
    # "Hello'yu Türkçeye çevir",
    # "LangChain is a framework for building LLM applications. It provides tools for chaining models, memory, and agents. Summarize this.",
    # "Amazon, eBay ve Walmart üzerinde 'nike snickers' fiyatlarını karşılaştır.",
    "eBay üzerinde 'nike snickers' bul."
]

for q in queries:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": q}]},
        config={"configurable": {"thread_id": "test-thread-final-perfect"}}
    )
    print("\nSoru:", q)
    msg = result["messages"][-1]
    content = msg.content
    if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
        content = content[0]["text"]
    print("Cevap:", content)