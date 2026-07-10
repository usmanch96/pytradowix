import asyncio
import os
import logging
from pytradowix import Tradowix, Quote

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("smoke_test")

def load_dotenv():
    """Load simple key=value pairs from .env file into environment."""
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

async def on_quote_callback(quote: Quote):
    logger.info(f"[Price Feed Update] {quote.symbol}: {quote.price} (timestamp: {quote.timestamp})")

async def main():
    load_dotenv()
    email = os.getenv("TRADOWIX_EMAIL")
    password = os.getenv("TRADOWIX_PASSWORD")

    if not email or not password:
        logger.error("Missing credentials in .env file (email and password required)")
        return

    logger.info("Initializing Tradowix Client...")
    client = Tradowix(email=email, password=password, is_demo=True)
    client.on_quote = on_quote_callback

    try:
        logger.info("Connecting to Tradowix...")
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect!")
            return
        
        logger.info("Connection established!")
        
        # Verify Profile
        profile = client.get_profile()
        if profile is None:
            logger.error("Failed to retrieve profile info.")
            return
        logger.info(f"Verified Profile: Name={profile.full_name}, Email={profile.email}, Country={profile.country}")
        
        # Verify Balance
        balance = client.get_balance()
        if balance is None:
            logger.error("Failed to retrieve balance info.")
            return
        logger.info(f"Verified Balance: Current={balance.current_balance} {balance.currency}, Demo={balance.demo_balance}")
        
        # Verify Instrument Cache
        logger.info(f"Verified Instruments Cache: Loaded {len(client.instruments)} assets.")
        
        # Verify Historical Candles Retrieval
        symbol = "USDJPY-OTC"
        logger.info(f"Fetching 1 hour of 1-minute historical candles for {symbol}...")
        # 3600 seconds = 60 minutes = 1 hour
        candles = await client.get_historical_candles(symbol=symbol, amount_of_seconds=3600, period=60)
        logger.info(f"Successfully retrieved {len(candles)} historical candles!")
        if candles:
            logger.info(f"Oldest Candle: {candles[0]}")
            logger.info(f"Newest Candle: {candles[-1]}")
        
        # Verify Tick Subscription
        symbol = "USDJPY-OTC"
        logger.info(f"Subscribing to {symbol} tick feed...")
        await client.subscribe_ticks(symbol)
        
        # Let it stream for 5 seconds
        logger.info("Streaming prices for 5 seconds...")
        await asyncio.sleep(5.0)
        
        # Place a $1 call trade on USDJPY-OTC
        logger.info(f"Placing a $1 call option order on {symbol}...")
        trade = await client.buy(amount=1.0, symbol=symbol, direction="call", duration=1)
        trade_id = trade.get('id')
        if not isinstance(trade_id, str):
            logger.error(f"Invalid or missing trade ID in order response: {trade_id}")
            return
        logger.info(f"Order executed successfully! Trade ID: {trade_id}, Open Price: {trade.get('openPrice')}")
        
        # Wait for resolution
        logger.info(f"Waiting for trade {trade_id} to resolve...")
        result = await client.check_win(trade_id, timeout=80.0)
        
        logger.info(f"Trade {trade_id} resolved! Result: {result.result.upper()}, Profit Payout: ${result.profit}, New Balance: ${result.new_balance}")
        
        # Unsubscribe
        logger.info(f"Unsubscribing from {symbol}...")
        await client.unsubscribe_ticks(symbol)
        
    except Exception as e:
        logger.error(f"Smoke test encountered error: {e}", exc_info=True)
    finally:
        logger.info("Closing client connection...")
        await client.close()
        logger.info("Smoke test completed!")

if __name__ == "__main__":
    asyncio.run(main())
