"""Terminal chat with the finance agent.

Usage:
    export GROQ_API_KEY=gsk_...   # or set in .env
    python main.py
"""

import sys

from agent.agent import FinanceAgent


def main():
    agent = FinanceAgent()
    print("FinBuddy — personal finance agent. Ctrl+C or 'quit' to exit.\n")
    while True:
        try:
            user = input("you > ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if not user:
            continue
        if user.lower() in {"quit", "exit"}:
            break
        reply = agent.chat(user)
        print(f"\nfinbuddy > {reply}\n")


if __name__ == "__main__":
    main()
