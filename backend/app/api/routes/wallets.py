from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database.database import get_db
from app.models.wallet import TrackedWallet
from app.services.blockchain_service import blockchain_service
import logging
import uuid
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/wallets", tags=["wallets"])

@router.get("/analyze/{address}")
async def analyze_wallet_address(address: str):
    """Deep analysis of a wallet address using public blockchain data"""
    chain = blockchain_service.identify_address_type(address)
    if not chain:
        raise HTTPException(400, "Unsupported or invalid wallet address format")
    
    details = await blockchain_service.get_address_details(chain, address)
    return {
        "success": True,
        "chain": chain,
        "address": address,
        "details": details
    }

@router.get("/transaction/{tx_hash}")
async def lookup_transaction(tx_hash: str, chain: Optional[str] = None):
    """Lookup a transaction hash across common blockchains"""
    if not chain:
        chain = blockchain_service.identify_tx_hash_type(tx_hash)
    
    if not chain:
        # Default to bitcoin if unknown format but 64 chars
        chain = "bitcoin" if len(tx_hash) == 64 else "ethereum"

    details = await blockchain_service.get_transaction_details(chain, tx_hash)
    return {
        "success": True,
        "chain": chain,
        "hash": tx_hash,
        "details": details
    }

@router.post("")
async def track_wallet(
    address: str,
    currency: str = Query(..., pattern="^(BTC|ETH|XMR|USDT|USDC)$"),
    label: Optional[str] = None,
    is_watchlist: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Add a new wallet to track"""
    try:
        # Check if already exists
        result = await db.execute(select(TrackedWallet).where(TrackedWallet.address == address))
        existing = result.scalar_one_or_none()
        if existing:
            return {"success": True, "message": "Wallet already tracked", "wallet_id": str(existing.id)}

        new_wallet = TrackedWallet(
            address=address,
            currency=currency,
            label=label or f"Manual Tracking: {address[:8]}",
            is_watchlist=is_watchlist,
            risk_level="medium" if is_watchlist else "low"
        )
        db.add(new_wallet)
        await db.commit()
        await db.refresh(new_wallet)
        return {"success": True, "wallet_id": str(new_wallet.id)}
    except Exception as e:
        logger.error(f"Failed to add wallet: {e}")
        raise HTTPException(500, detail=str(e))

@router.get("")
async def list_wallets(
    watchlist_only: bool = False,
    currency: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List tracked wallets"""
    try:
        query = select(TrackedWallet)
        if watchlist_only:
            query = query.where(TrackedWallet.is_watchlist == True)
        if currency:
            query = query.where(TrackedWallet.currency == currency.upper())
            
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0
        
        result = await db.execute(query.order_by(desc(TrackedWallet.created_at)).limit(limit).offset(offset))
        wallets = result.scalars().all()
        
        return {
            "success": True,
            "total": total,
            "wallets": wallets
        }
    except Exception as e:
        logger.error(f"Failed to list wallets: {e}")
        raise HTTPException(500, detail="Failed to fetch wallets")

@router.get("/{wallet_id}")
async def get_wallet_details(wallet_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed info for a specific wallet"""
    try:
        wallet_uuid = uuid.UUID(wallet_id)
        result = await db.execute(select(TrackedWallet).where(TrackedWallet.id == wallet_uuid))
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            raise HTTPException(404, "Wallet not found")
            
        # Fetch real-time data
        chain = blockchain_service.identify_address_type(wallet.address)
        details = {}
        if chain:
            details = await blockchain_service.get_address_details(chain, wallet.address)
            
            # Update cache if successful
            if "error" not in details:
                wallet.cached_balance = str(details.get("balance", 0))
                wallet.cached_usd_value = str(details.get("balance_usd", 0))
                wallet.last_balance_check = datetime.utcnow()
                await db.commit()

        return {
            "success": True,
            "wallet": wallet,
            "live_data": {
                "balance": details.get("balance", wallet.cached_balance or "0.00"),
                "balance_usd": details.get("balance_usd", wallet.cached_usd_value or "0.00"),
                "transaction_count": details.get("transaction_count", 0),
                "first_seen": details.get("first_seen"),
                "last_seen": details.get("last_seen"),
                "received_total": details.get("received_total", 0),
                "sent_total": details.get("sent_total", 0),
            }
        }
    except ValueError:
        raise HTTPException(400, "Invalid wallet ID format")
    except Exception as e:
        logger.error(f"Failed to get wallet details: {e}")
        raise HTTPException(500, detail=str(e))

@router.delete("/{wallet_id}")
async def stop_tracking_wallet(wallet_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a wallet from tracking"""
    try:
        wallet_uuid = uuid.UUID(wallet_id)
        result = await db.execute(select(TrackedWallet).where(TrackedWallet.id == wallet_uuid))
        wallet = result.scalar_one_or_none()
        
        if wallet:
            await db.delete(wallet)
            await db.commit()
            
        return {"success": True, "message": "Wallet tracking stopped"}
    except Exception as e:
        logger.error(f"Delete wallet failed: {e}")
        raise HTTPException(500, detail=str(e))
