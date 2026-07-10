"""Example: place a call trade and wait for its settlement result."""
import asyncio
import os
from dotenv import load_dotenv
from pytradowix import Tradowix

load_dotenv()

SYMBOL = "USDJPY-OTC"
AMOUNT = 1.0
DURATION = 1  # turbo minutes


async def main() -> None:
    client = Tradowix(
        email=os.getenv("TRADOWIX_EMAIL", ""),
        password=os.getenv("TRADOWIX_PASSWORD", ""),
        is_demo=True,  # always use demo for testing
    )
    await client.connect()

    balance = client.get_balance()
    if balance is None:
        print("Failed to fetch initial balance.")
        await client.close()
        return
    print(f"Starting balance: {balance.current_balance} {balance.currency}")

    # Subscribe to get the current price before trading
    await client.subscribe_ticks(SYMBOL)
    await asyncio.sleep(2)  # wait for first tick
    quote = client.quotes.get(SYMBOL)
    if quote:
        print(f"Current price: {quote.price}")

    # Place a call (Higher) trade
    print(f"\nPlacing ${AMOUNT} CALL on {SYMBOL} for {DURATION} minute(s)...")
    trade = await client.buy(amount=AMOUNT, symbol=SYMBOL, direction="call", duration=DURATION)
    trade_id = trade.get("id")
    if not isinstance(trade_id, str):
        print(f"Failed to place trade: {trade}")
        await client.unsubscribe_ticks(SYMBOL)
        await client.close()
        return
    open_price = trade.get("openPrice")
    print(f"Trade opened! ID={trade_id}, Open Price={open_price}")

    # Wait for settlement
    print("Waiting for settlement...")
    result = await client.check_win(trade_id, timeout=120.0)

    print(f"\n{'WIN' if result.result == 'win' else 'LOSS'} — "
          f"Close Price={result.close_price}, P&L=${result.profit:+.2f}")

    balance = client.get_balance()
    if balance is not None:
        print(f"New balance: {balance.current_balance} {balance.currency}")

    await client.unsubscribe_ticks(SYMBOL)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
