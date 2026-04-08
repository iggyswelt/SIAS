#!/usr/bin/env python3
"""
HSM Sign Script - Sign Binance API requests via PKCS#11
Usage: python hsm_sign.py <message>
"""
import sys
import os
import subprocess

def sign_message(message: str) -> str:
    """
    Sign a message using the HSM-stored private key.
    The private key NEVER leaves the HSM.
    """
    # Path to PKCS#11 module
    PKCS11_MODULE = "/usr/lib/x86_64-linux-gnu/pkcs11/opensc-pkcs11.so"
    KEY_LABEL = "binance-trading"
    USER_PIN = "123456"  # In production, use environment variable
    
    # Sign the message using pkcs11-tool
    cmd = [
        "pkcs11-tool",
        "--module", PKCS11_MODULE,
        "--sign",
        "--mechanism", "ECDSA",
        "--login", "--pin", USER_PIN,
        "--label", KEY_LABEL,
        "--input-file", "-",
        "--output-file", "-"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=message.encode(),
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise Exception(f"Signing failed: {result.stderr.decode()}")
        
        return result.stdout.hex()
    
    except Exception as e:
        print(f"Error signing message: {e}", file=sys.stderr)
        return ""

def sign_binance_request(params: dict) -> str:
    """
    Sign Binance API request parameters.
    Creates query string and signs with HSM.
    """
    # Create query string from params
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    
    # Sign the query string
    signature = sign_message(query_string)
    
    return signature

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = sys.argv[1]
        signature = sign_message(message)
        print(signature)
    else:
        # Test with a simple message
        test_msg = "timestamp=1234567890&symbol=BTCUSDT"
        sig = sign_binance_request({"timestamp": "1234567890", "symbol": "BTCUSDT"})
        print(f"Test signature: {sig}")
