#!/usr/bin/env python3
"""
deploy_contract.py — One-time script to compile and deploy FaceVerification.sol
to the Ethereum Sepolia testnet.

After deployment, the contract address is printed and should be added to your
.env file as CONTRACT_ADDRESS.

Usage:
    python deploy_contract.py

Prerequisites:
    - .env file with ALCHEMY_RPC_URL and PRIVATE_KEY set
    - Sepolia ETH in your wallet (free from https://sepoliafaucet.com/)
    - py-solc-x installed (pip install py-solc-x)
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)


def main():
    console.print(
        Panel(
            "[bold white]FaceVerification Contract Deployment[/]\n"
            "[dim]Deploying to Ethereum Sepolia Testnet[/]",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )

    # ── Load environment ─────────────────────────────────────────
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        console.print("[bold red]ERROR:[/] .env file not found. Copy .env.example → .env first.")
        sys.exit(1)

    load_dotenv(env_path)

    rpc_url = os.getenv("ALCHEMY_RPC_URL", "").strip()
    private_key = os.getenv("PRIVATE_KEY", "").strip()

    if not rpc_url or rpc_url.startswith("your_"):
        console.print("[bold red]ERROR:[/] Set ALCHEMY_RPC_URL in .env")
        sys.exit(1)
    if not private_key or private_key.startswith("your_"):
        console.print("[bold red]ERROR:[/] Set PRIVATE_KEY in .env")
        sys.exit(1)

    # ── Install Solidity compiler ────────────────────────────────
    console.print("\n[cyan]📦 Installing Solidity compiler (0.8.19)…[/]")

    try:
        from solcx import compile_standard, install_solc

        install_solc("0.8.19")
        console.print("   [green]✓ solc 0.8.19 installed[/]")
    except Exception as e:
        console.print(f"[bold red]ERROR:[/] Failed to install solc: {e}")
        sys.exit(1)

    # ── Read Solidity source ─────────────────────────────────────
    sol_path = Path(__file__).parent / "contracts" / "FaceVerification.sol"
    if not sol_path.exists():
        console.print(f"[bold red]ERROR:[/] Contract file not found: {sol_path}")
        sys.exit(1)

    sol_source = sol_path.read_text(encoding="utf-8")
    console.print(f"   [green]✓ Loaded contract source ({len(sol_source)} bytes)[/]")

    # ── Compile ──────────────────────────────────────────────────
    console.print("\n[cyan]🔨 Compiling contract…[/]")

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                "FaceVerification.sol": {"content": sol_source}
            },
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                    }
                },
                "optimizer": {
                    "enabled": True,
                    "runs": 200,
                },
            },
        },
        solc_version="0.8.19",
    )

    contract_data = compiled["contracts"]["FaceVerification.sol"]["FaceVerification"]
    abi = contract_data["abi"]
    bytecode = contract_data["evm"]["bytecode"]["object"]

    console.print(f"   [green]✓ Compiled successfully[/]")
    console.print(f"   ABI entries: {len(abi)}")
    console.print(f"   Bytecode: {len(bytecode)} hex chars")

    # Save ABI for reference
    abi_path = Path(__file__).parent / "contracts" / "abi.json"
    with open(abi_path, "w", encoding="utf-8") as f:
        json.dump(abi, f, indent=2)
    console.print(f"   [green]✓ ABI saved to {abi_path}[/]")

    # ── Deploy ───────────────────────────────────────────────────
    console.print("\n[cyan]🚀 Deploying to Sepolia…[/]")

    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        console.print(f"[bold red]ERROR:[/] Cannot connect to {rpc_url}")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")

    console.print(f"   Wallet  : {account.address}")
    console.print(f"   Balance : {balance_eth} ETH")

    if balance == 0:
        console.print(
            "[bold red]ERROR:[/] Wallet has 0 Sepolia ETH. "
            "Get free ETH from https://sepoliafaucet.com/"
        )
        sys.exit(1)

    # Build deploy transaction
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    tx = contract.constructor().build_transaction({
        "chainId": 11155111,
        "gas": 2000000,
        "gasPrice": gas_price,
        "nonce": nonce,
    })

    console.print("   Signing transaction…")
    signed_tx = w3.eth.account.sign_transaction(tx, account.key)

    console.print("   Sending to Sepolia…")
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hash_hex = tx_hash.hex()

    console.print(f"   Tx hash: [bold]{tx_hash_hex}[/]")
    console.print("   Waiting for confirmation (may take 15-30 seconds)…")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    if receipt["status"] != 1:
        console.print(f"[bold red]ERROR:[/] Deployment failed! Tx: {tx_hash_hex}")
        sys.exit(1)

    contract_address = receipt["contractAddress"]

    console.print(f"\n   [bold green]✓ Contract deployed successfully![/]")
    console.print(f"   [bold]Contract Address: {contract_address}[/]")
    console.print(f"   Block: {receipt['blockNumber']}")
    console.print(f"   Gas used: {receipt['gasUsed']}")
    console.print(
        f"   Etherscan: https://sepolia.etherscan.io/address/{contract_address}"
    )

    # ── Update .env ──────────────────────────────────────────────
    console.print(f"\n[cyan]📝 Updating .env with contract address…[/]")

    env_content = env_path.read_text(encoding="utf-8")

    if "CONTRACT_ADDRESS=" in env_content:
        # Replace existing line
        lines = env_content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("CONTRACT_ADDRESS="):
                new_lines.append(f"CONTRACT_ADDRESS={contract_address}")
            else:
                new_lines.append(line)
        env_content = "\n".join(new_lines) + "\n"
    else:
        env_content += f"\nCONTRACT_ADDRESS={contract_address}\n"

    env_path.write_text(env_content, encoding="utf-8")
    console.print(f"   [green]✓ CONTRACT_ADDRESS updated in .env[/]")

    console.print(
        Panel(
            f"[bold green]Deployment Complete![/]\n\n"
            f"Contract: [bold]{contract_address}[/]\n"
            f"You can now run the pipeline:\n"
            f"  [bold]python run_pipeline.py --image your_photo.jpg[/]",
            border_style="green",
            padding=(1, 2),
        )
    )


if __name__ == "__main__":
    main()
