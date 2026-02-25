import asyncio
import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

from app.services.blockchain_service import blockchain_service

async def test():
    # Test BTC address (random active one)
    btc_addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" # Genesis block
    print(f"Testing BTC address: {btc_addr}")
    type_btc = blockchain_service.identify_address_type(btc_addr)
    print(f"Identified type: {type_btc}")
    
    details = await blockchain_service.get_address_details(type_btc, btc_addr)
    print(f"Details: {details}")
    
    # Test ETH address
    eth_addr = "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe" # Ethereum Foundation
    print(f"\nTesting ETH address: {eth_addr}")
    type_eth = blockchain_service.identify_address_type(eth_addr)
    print(f"Identified type: {type_eth}")
    
    details_eth = await blockchain_service.get_address_details(type_eth, eth_addr)
    print(f"Details: {details_eth}")

if __name__ == "__main__":
    asyncio.run(test())
