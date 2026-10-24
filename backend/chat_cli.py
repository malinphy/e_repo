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
from backend.app.agent.graph import build_shop_graph


async def main():
    print("=" * 65)
    print("🛒 AKILLI E-TİCARET ASİSTANI — İNTERAKTİF TEST CHAT")
    print("=" * 65)
    print("💡 İpuçları:")
    print("   - 'selam' veya 'merhaba' (Chitchat testi)")
    print("   - '100 dolar altı bluetooth kulaklık ara' (Search Subgraph)")
    print("   - 'logitech mx master 3s bul' (Walmart, eBay, Amazon, Google Shopping)")
    print("   - 'sepetimde ne var' veya '2. ürünü sepete ekle' (Intent yönlendirme)")
    print("   - Çıkmak için: 'exit' veya 'q'")
    print("-" * 65)

    app = build_shop_graph()
    thread_id = f"test_thread_{uuid.uuid4().hex[:6]}"
    user_id = "test_user_ahmet"
    config = {"configurable": {"thread_id": thread_id}}

    print(f"[*] Aktif Oturum: thread_id='{thread_id}', user_id='{user_id}'\n")

    while True:
        try:
            user_input = input("Siz > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nÇıkış yapılıyor...")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "q", "quit"):
            print("Görüşmek üzere!")
            break

        input_payload = {
            "messages": [HumanMessage(content=user_input)],
            "user_id": user_id,
            "thread_id": thread_id,
        }

        print("\n⏳ Asistan düşünüyor ve pazaryerlerini tarıyor...")
        try:
            result = await app.ainvoke(input_payload, config=config)

            # Debug metadata
            intent = result.get("intent", "unknown")
            last_results = result.get("last_results") or []
            print(f"\n[🔍 Router Intent: {intent.upper()} | 📦 Bulunan Ürün: {len(last_results)}]")

            # Print Assistant Response
            messages = result.get("messages") or []
            if messages:
                latest_reply = messages[-1].content
                print(f"\nAsistan >\n{latest_reply}\n")
            print("-" * 65)

        except Exception as exc:
            print(f"\n[!] Hata oluştu: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
