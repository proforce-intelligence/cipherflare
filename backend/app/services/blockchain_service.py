import aiohttp
import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class BlockchainService:
    """
    Service for interacting with multiple blockchains via public APIs
    """
    def __init__(self):
        # We use multiple fallbacks to avoid 430/rate limits
        self.blockchair_base = "https://api.blockchair.com"
        self.blockchain_info_base = "https://blockchain.info"
        
    def identify_address_type(self, address: str) -> Optional[str]:
        """Identify the likely blockchain based on address format"""
        if re.match(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[ac-hj-np-z02-9]{11,71}$", address):
            return "bitcoin"
        if re.match(r"^0x[a-fA-F0-9]{40}$", address):
            return "ethereum"
        if re.match(r"^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$", address):
            return "monero"
        if re.match(r"^T[A-Za-z1-9]{33}$", address):
            return "tron"
        return None

    async def get_address_details(self, chain: str, address: str) -> Dict[str, Any]:
        """Fetch balance and basic stats for an address with fallbacks"""
        if chain == "bitcoin":
            return await self._get_btc_details(address)
        elif chain == "ethereum":
            return await self._get_eth_details(address)
        
        return {"error": f"Chain {chain} not supported for live lookup"}

    async def _get_btc_details(self, address: str) -> Dict[str, Any]:
        """Specific logic for BTC with fallbacks"""
        # Try Blockchain.info first (very reliable for BTC)
        url = f"{self.blockchain_info_base}/rawaddr/{address}?limit=0"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "balance": data.get("final_balance", 0) / 100000000, # satoshis to BTC
                            "transaction_count": data.get("n_tx", 0),
                            "received_total": data.get("total_received", 0) / 100000000,
                            "sent_total": data.get("total_sent", 0) / 100000000,
                            "balance_usd": "0.00", # requires price feed
                        }
        except Exception as e:
            logger.warning(f"Blockchain.info failed for {address}: {e}")

        # Fallback to Blockchair
        return await self._get_blockchair_details("bitcoin", address)

    async def _get_eth_details(self, address: str) -> Dict[str, Any]:
        """Specific logic for ETH with fallback to Blockscout"""
        url = f"https://eth.blockscout.com/api/v2/addresses/{address}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Blockscout returns balance in Wei
                        balance_wei = int(data.get("coin_balance", 0))
                        return {
                            "balance": balance_wei / 10**18,
                            "transaction_count": "N/A", # Not always in summary
                            "received_total": "N/A",
                            "sent_total": "N/A",
                            "balance_usd": "0.00", 
                        }
        except Exception as e:
            logger.warning(f"Blockscout failed for {address}: {e}")

        # Fallback to Blockchair
        return await self._get_blockchair_details("ethereum", address)

    async def _get_blockchair_details(self, chain: str, address: str) -> Dict[str, Any]:
        url = f"{self.blockchair_base}/{chain}/dashboards/address/{address}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        addr_data = data.get("data", {}).get(address, {})
                        info = addr_data.get("address", {})
                        return {
                            "balance": info.get("balance", 0),
                            "balance_usd": info.get("balance_usd", 0),
                            "transaction_count": info.get("transaction_count", 0),
                            "first_seen": info.get("first_seen_receiving"),
                            "received_total": info.get("received_total", 0),
                            "sent_total": info.get("spent_total", 0),
                        }
                    return {"error": f"API returned status {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_transaction_details(self, chain: str, tx_hash: str) -> Dict[str, Any]:
        """Fetch details for a specific transaction hash"""
        # Blockchair is best for general TX info
        return await self._get_blockchair_tx(chain, tx_hash)

    async def _get_blockchair_tx(self, chain: str, tx_hash: str) -> Dict[str, Any]:
        url = f"{self.blockchair_base}/{chain}/dashboards/transaction/{tx_hash}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        tx_data = data.get("data", {}).get(tx_hash, {})
                        return {
                            "hash": tx_hash,
                            "block_id": tx_data.get("transaction", {}).get("block_id"),
                            "time": tx_data.get("transaction", {}).get("time"),
                            "output_total": tx_data.get("transaction", {}).get("output_total"),
                            "output_total_usd": tx_data.get("transaction", {}).get("output_total_usd"),
                        }
                    return {"error": f"API status {response.status}"}
        except Exception as e:
            return {"error": str(e)}

blockchain_service = BlockchainService()
