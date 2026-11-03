"""Run the exact conversation engine locally without a Telegram token."""

import argparse

from assistant import answer
from store import connect, load_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Try the Telegram bot's answer engine locally")
    parser.add_argument("message", nargs="*", help="Message to send; omit for interactive mode")
    args = parser.parse_args()
    policy = load_policy()
    connection = connect(":memory:")
    if args.message:
        print(answer(" ".join(args.message), policy, connection))
        return
    print("Enter a message, or Ctrl+D to exit.")
    try:
        while True:
            print(answer(input("> "), policy, connection))
    except EOFError:
        print()


if __name__ == "__main__":
    main()
