"""Interactive Terminal Chat for testing the E-Commerce Agent."""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from langchain_core.messages import HumanMessage
from backend.app.agent.graph import get_compiled_shop_graph


async def main():
    print("=" * 65)
    print("🛒 SMART E-COMMERCE ASSISTANT — INTERACTIVE CLI")
    print("=" * 65)
    print("💡 Examples:")
    print("   - 'hello' or 'hi' (Chitchat)")
    print("   - 'find bluetooth headphones under 100 dollars' (Search Subgraph)")
    print("   - 'search logitech mx master 3s' (Walmart, eBay, Amazon, Google Shopping)")
    print("   - 'what is in my cart' or 'add the 2nd one to cart' (Cart actions)")
    print("   - To quit: 'exit' or 'q'")
    print("-" * 65)

    app = await get_compiled_shop_graph()
    thread_id = f"test_thread_{uuid.uuid4().hex[:6]}"
    user_id = "test_user_alex"
    config = {"configurable": {"thread_id": thread_id}}

    print(f"[*] Active Session: thread_id='{thread_id}', user_id='{user_id}'\n")

    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "q", "quit"):
            print("Goodbye!")
            break

        input_payload = {
            "messages": [HumanMessage(content=user_input)],
            "user_id": user_id,
            "thread_id": thread_id,
        }

        print("\n⏳ Assistant is thinking and querying marketplaces...")
        try:
            result = await app.ainvoke(input_payload, config=config)

            # Debug metadata
            intent = result.get("intent", "unknown")
            last_results = result.get("last_results") or []
            print(f"\n[🔍 Router Intent: {intent.upper()} | 📦 Found Products: {len(last_results)}]")

            # Print Assistant Response
            messages = result.get("messages") or []
            if messages:
                latest_reply = messages[-1].content
                print(f"\nAssistant >\n{latest_reply}\n")
            print("-" * 65)

        except Exception as exc:
            print(f"\n[!] Error occurred: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
