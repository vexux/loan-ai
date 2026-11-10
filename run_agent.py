import os
import sys
import logging
import warnings
import asyncio
from uuid import uuid4
from core_agent.cli_ui import print_banner, print_card, print_observability

os.environ["HF_HUB_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["MODELSCOPE_LOG_LEVEL"] = "40"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore")

import transformers.utils.logging as hf_logging
hf_logging.set_verbosity_error()
hf_logging.disable_progress_bar()

try:
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars()
except Exception:
    pass

logging.getLogger("modelscope").setLevel(logging.ERROR)
logging.getLogger("modelscope_hub").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

from contracts.common.request_context import RequestContext
from core_agent.bootstrap import create_llm_agent
from core_agent.models.agent_request import AgentRequest


async def main():
    print_banner()
    agent = create_llm_agent()
    session_id = str(uuid4())
    current_user = None          
    current_role = "guest"
    print("  \033[90mSession started as:\033[0m Guest \033[90m(Unauthenticated)\033[0m\n")

    while True:
        try:
            prompt_tag = f"[{current_role.upper()}{':' + current_user if current_user else ''}] ❯ "
            user_query = input(prompt_tag).strip()


            if not user_query:
                continue

            if user_query.lower() in {"exit", "quit", "q"}:
                print("\n[INFO] Exiting session. Goodbye!")
                break

            # ── RBAC CLI Commands ──
            if user_query.lower() == "/whoami":
                print(f"👤 Current User: {current_user} | Role: {current_role}\n")
                continue

            # ── RBAC & Session Management Commands ──
            if user_query.lower() in {"/clear", "/reset"}:
                if agent.memory and session_id:
                    await agent.memory.clear_session(session_id)
                session_id = str(uuid4())
                print("[INFO] Conversation history cleared.\n")
                continue

            if user_query.lower().startswith("/login "):
                # Purge old user's dialogue history before switching identity
                if agent.memory and session_id:
                    await agent.memory.clear_session(session_id)

                target = user_query.split(maxsplit=1)[1].strip()
                if target.lower() == "admin":
                    current_user = "admin_user"
                    current_role = "admin"
                else:
                    current_user = target
                    current_role = "customer"
                session_id = str(uuid4())
                print(f"[INFO] Logged in as: {current_user} (Role: {current_role}) | Memory reset.\n")
                continue

            if user_query.lower() == "/logout":
                # Purge customer's dialogue history on logout
                if agent.memory and session_id:
                    await agent.memory.clear_session(session_id)

                current_user = None
                current_role = "guest"
                session_id = str(uuid4())
                print("[INFO] Logged out. Session reset to Guest mode | Memory reset.\n")
                continue


            context = RequestContext(
                request_id=str(uuid4()),
                session_id=session_id,
                correlation_id=session_id,
                user_id=current_user or "guest",
                tenant_id="default",
                metadata={"role": current_role},
            )

            request = AgentRequest(message=user_query, context=context)
            response = await agent.run(request)

            trace_id = response.metadata.get("trace_id", "N/A") if response.metadata else "N/A"
            latency = response.metadata.get("latency_ms", "N/A") if response.metadata else "N/A"
            trace_file = response.metadata.get("trace_file", "") if response.metadata else ""

            # Format latency in seconds
            if isinstance(latency, (int, float)):
                duration_str = f"{latency / 1000.0:.2f} s"
            else:
                duration_str = f"{latency}"

            if response.success:
                print_card("🤖 AGENT RESPONSE", response.message, is_error=False)
            else:
                print_card("❌ ERROR OCCURRED", response.error or response.message, is_error=True)

            print_observability(trace_id, duration_str, 'SUCCESS' if response.success else 'FAILED', trace_file)



        except (KeyboardInterrupt, EOFError):
            print("\n\n[INFO] Session interrupted. Goodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
