"""Example: fetch historical candle data with backward pagination."""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from pytradowix import Tradowix, Candle

load_dotenv()

SYMBOL = "USDJPY-OTC"
PERIOD = 60        # 1-minute bars
HOURS = 24         # how many hours of history to fetch


async def main() -> None:
    client = Tradowix(
        email=os.getenv("TRADOWIX_EMAIL", ""),
        password=os.getenv("TRADOWIX_PASSWORD", ""),
        is_demo=True,
    )
    await client.connect()

    amount_of_seconds = HOURS * 3600
    print(f"Fetching {HOURS}h of {PERIOD}s candles for {SYMBOL}...")

    candles: list[Candle] = await client.get_historical_candles(
        symbol=SYMBOL,
        amount_of_seconds=amount_of_seconds,
        period=PERIOD,
    )

    print(f"\nRetrieved {len(candles)} candles\n")
    if candles:
        oldest = candles[0]
        newest = candles[-1]
        print(f"  Oldest : {datetime.fromtimestamp(oldest.time).isoformat()}  "
              f"O={oldest.open} H={oldest.high} L={oldest.low} C={oldest.close}  [{oldest.color}]")
        print(f"  Newest : {datetime.fromtimestamp(newest.time).isoformat()}  "
              f"O={newest.open} H={newest.high} L={newest.low} C={newest.close}  [{newest.color}]")

        # Simple stats
        greens = sum(1 for c in candles if c.color == "green")
        reds = sum(1 for c in candles if c.color == "red")
        print(f"\n  Green: {greens}  Red: {reds}  Doji: {len(candles) - greens - reds}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
