"""Example: fetch account balance and profile."""
import asyncio
import os
from dotenv import load_dotenv
from pytradowix import Tradowix

load_dotenv()


async def main() -> None:
    client = Tradowix(
        email=os.getenv("TRADOWIX_EMAIL", ""),
        password=os.getenv("TRADOWIX_PASSWORD", ""),
        is_demo=True,
    )
    await client.connect()

    profile = client.get_profile()
    balance = client.get_balance()

    if profile is None or balance is None:
        print("Failed to fetch profile or balance info.")
        await client.close()
        return

    print(f"Name    : {profile.display_name}")
    print(f"Email   : {profile.email}")
    print(f"Country : {profile.country}")
    print(f"Demo    : {balance.demo_balance} {balance.currency}")
    print(f"Real    : {balance.real_balance} {balance.currency}")

    assets = client.get_assets()
    open_assets = [a for a in assets if a.is_open]
    print(f"\nOpen instruments: {len(open_assets)} / {len(assets)}")
    for a in open_assets[:5]:
        print(f"  {a.symbol:20s} payout={a.turbo_payout_rate:.0%}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
