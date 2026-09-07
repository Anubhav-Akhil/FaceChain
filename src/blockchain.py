"""
blockchain.py — Stage 4 & 5: Write match data to Ethereum Sepolia and verify.

Uses web3.py to interact with the FaceVerification smart contract:
  - registerMatch(): store a SHA-256 hash + metadata on-chain
  - verifyMatch():   confirm the hash exists
  - getRecord():     retrieve the full stored record
"""

import json
from pathlib import Path

from web3 import Web3

from .utils import compute_data_hash, console, hex_to_bytes32


# ── Contract ABI ─────────────────────────────────────────────────
# This is the ABI for the FaceVerification.sol contract.
# Generated from the Solidity source.

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_dataHash", "type": "bytes32"},
            {"internalType": "string", "name": "_imageURL", "type": "string"},
            {"internalType": "string", "name": "_matchSource", "type": "string"},
            {"internalType": "string", "name": "_matchTitle", "type": "string"},
        ],
        "name": "registerMatch",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_dataHash", "type": "bytes32"}
        ],
        "name": "verifyMatch",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_dataHash", "type": "bytes32"}
        ],
        "name": "getRecord",
        "outputs": [
            {"internalType": "address", "name": "registrant", "type": "address"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "string", "name": "imageURL", "type": "string"},
            {"internalType": "string", "name": "matchSource", "type": "string"},
            {"internalType": "string", "name": "matchTitle", "type": "string"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "recordCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "dataHash", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "registrant", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "imageURL", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "matchSource", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "MatchRegistered",
        "type": "event",
    },
]

# Sepolia chain ID
SEPOLIA_CHAIN_ID = 11155111


class BlockchainClient:
    """Interface to the FaceVerification smart contract on Ethereum Sepolia."""

    def __init__(self, rpc_url: str, private_key: str, contract_address: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(
                f"Cannot connect to Ethereum node at {rpc_url}. "
                "Check your ALCHEMY_RPC_URL in .env."
            )

        self.account = self.w3.eth.account.from_key(private_key)
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=CONTRACT_ABI,
        )

        console.print(f"\n[bold cyan]🔗 Blockchain:[/] Connected to Sepolia")
        console.print(f"   RPC      : {rpc_url[:50]}…")
        console.print(f"   Wallet   : {self.account.address}")
        console.print(f"   Contract : {contract_address}")

    def register_match(
        self,
        match_data: dict,
        image_url: str,
    ) -> dict:
        """
        Register a face-match record on the blockchain.

        Parameters
        ----------
        match_data : dict
            The match data dict (title, link, source, etc.)
        image_url : str
            The public URL of the face image that was searched.

        Returns
        -------
        dict with keys:
            - tx_hash   : str — transaction hash
            - data_hash : str — SHA-256 hash of the match data
            - block     : int — block number the tx was mined in
            - gas_used  : int — gas consumed
            - etherscan : str — link to view on Sepolia Etherscan
        """
        console.print(f"\n[bold cyan]⛓️  Stage 4:[/] Blockchain Registration")

        # Build the data to hash
        hash_payload = {
            "title": match_data.get("title", ""),
            "link": match_data.get("link", ""),
            "source": match_data.get("source", ""),
            "image_url": image_url,
        }
        data_hash_hex = compute_data_hash(hash_payload)
        data_hash_bytes = hex_to_bytes32(data_hash_hex)

        console.print(f"   Data hash (SHA-256): 0x{data_hash_hex}")

        # Check if record already exists on-chain to prevent contract revert
        try:
            already_exists = self.contract.functions.verifyMatch(data_hash_bytes).call()
            if already_exists:
                console.print(f"   [bold green]✓ Record is ALREADY registered on-chain for hash 0x{data_hash_hex}[/]")
                console.print(f"   Skipping duplicate transaction (tamper-proof record already exists).")
                return {
                    "tx_hash": "already_registered",
                    "data_hash": data_hash_hex,
                    "block": "Existing Block",
                    "gas_used": 0,
                    "already_registered": True,
                    "etherscan": f"https://sepolia.etherscan.io/address/{self.contract.address}",
                }
        except Exception as check_err:
            console.print(f"   [dim]Pre-check error (proceeding to tx): {check_err}[/]")

        # Build the transaction
        match_source = match_data.get("link", "")[:256]   # Limit string length
        match_title = match_data.get("title", "")[:256]

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        # Get current gas price with 25% buffer for fast mining
        gas_price = int(self.w3.eth.gas_price * 1.25)

        # Estimate gas dynamically with safe buffer
        try:
            estimated_gas = self.contract.functions.registerMatch(
                data_hash_bytes,
                image_url[:256],
                match_source,
                match_title,
            ).estimate_gas({"from": self.account.address})
            gas_limit = int(estimated_gas * 1.3)
        except Exception:
            gas_limit = 600000

        console.print(f"   Gas limit: {gas_limit} | Gas price: {gas_price}")

        tx = self.contract.functions.registerMatch(
            data_hash_bytes,
            image_url[:256],
            match_source,
            match_title,
        ).build_transaction({
            "chainId": SEPOLIA_CHAIN_ID,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": nonce,
        })

        console.print("   Signing transaction…")
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)

        console.print("   Sending to Sepolia…")
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        console.print(f"   Tx hash: [bold]{tx_hash_hex}[/]")
        console.print("   Waiting for confirmation…")

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

        if receipt["status"] != 1:
            raise RuntimeError(
                f"Transaction FAILED on-chain. Tx hash: {tx_hash_hex}"
            )

        etherscan_url = f"https://sepolia.etherscan.io/tx/0x{tx_hash_hex}"

        console.print(f"   [bold green]✓ Confirmed![/]")
        console.print(f"   Block    : {receipt['blockNumber']}")
        console.print(f"   Gas used : {receipt['gasUsed']}")
        console.print(f"   Etherscan: {etherscan_url}")

        return {
            "tx_hash": tx_hash_hex,
            "data_hash": data_hash_hex,
            "block": receipt["blockNumber"],
            "gas_used": receipt["gasUsed"],
            "etherscan": etherscan_url,
        }

    def verify_match(self, data_hash_hex: str) -> dict:
        """
        Verify a match record exists on-chain and retrieve it.

        Parameters
        ----------
        data_hash_hex : str
            The 64-char hex SHA-256 hash to look up.

        Returns
        -------
        dict with keys:
            - exists       : bool
            - registrant   : str (address)
            - timestamp    : int (unix)
            - imageURL     : str
            - matchSource  : str
            - matchTitle   : str
            - verified     : bool — True if on-chain hash matches input
        """
        console.print(f"\n[bold cyan]✅ Stage 5:[/] On-Chain Verification")

        data_hash_bytes = hex_to_bytes32(data_hash_hex)

        # Check existence
        exists = self.contract.functions.verifyMatch(data_hash_bytes).call()

        if not exists:
            console.print(f"   [bold red]✗ No record found for hash 0x{data_hash_hex}[/]")
            return {"exists": False, "verified": False}

        # Retrieve full record
        record = self.contract.functions.getRecord(data_hash_bytes).call()
        registrant, timestamp, image_url, match_source, match_title = record

        console.print(f"   [bold green]✓ Record found on-chain![/]")
        console.print(f"   Registrant  : {registrant}")
        console.print(f"   Timestamp   : {timestamp}")
        console.print(f"   Image URL   : {image_url[:80]}…")
        console.print(f"   Match Source : {match_source[:80]}…")
        console.print(f"   Match Title  : {match_title[:80]}…")
        console.print(f"   [bold green]✓ Data integrity VERIFIED — hash matches on-chain record[/]")

        return {
            "exists": True,
            "registrant": registrant,
            "timestamp": timestamp,
            "imageURL": image_url,
            "matchSource": match_source,
            "matchTitle": match_title,
            "verified": True,
        }
