"""
TA-DSS Agent Team Runner
Usage: python -m agents.run "Your prompt here"
"""
import asyncio
import sys
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.team import AGENTS


async def run(prompt: str, verbose: bool = False):
    """Run a prompt against the full TA-DSS agent team."""
    print(f"\n[team] Running prompt...\n{'─' * 60}")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[
                "Read", "Edit", "Write", "Bash",
                "Grep", "Glob",
                "Agent",  # required to spawn sub-agents
            ],
            agents=AGENTS,
        ),
    ):
        if verbose:
            print(f"[debug] {type(message).__name__}: {message}")

        if hasattr(message, "result"):
            print(f"\n{'─' * 60}\n[result]\n\n{message.result}")

        elif hasattr(message, "text") and message.text:
            print(message.text, end="", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    verbose = "--verbose" in args or "-v" in args
    args = [a for a in args if a not in ("--verbose", "-v")]

    if not args:
        print("Usage: python -m agents.run [-v] \"Your prompt here\"")
        sys.exit(1)

    prompt = " ".join(args)
    asyncio.run(run(prompt, verbose=verbose))
