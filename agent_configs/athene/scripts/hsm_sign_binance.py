#!/usr/bin/env python3
import sys
import os
import tempfile

def sign_with_hsm(message: str) -> str:
    PKCS11_MODULE = "/usr/lib/x86_64-linux-gnu/pkcs11/opensc-pkcs11.so"
    KEY_LABEL = "abydon-metamaus-ICA-4096"
    USER_PIN = os.environ.get('HSM_PIN', '8EB5E24A31A5')
    
    # Write message to temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(message)
        input_file = f.name
    
    output_file = input_file + '.sig'
    
    import subprocess
    cmd = [
        "pkcs11-tool", "--module", PKCS11_MODULE,
        "--sign", "--mechanism", "RSA-PKCS",
        "--login", "--pin", USER_PIN,
        "--label", KEY_LABEL,
        "--input-file", input_file,
        "--output-file", output_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"Signing failed: {result.stderr.decode()}")
        
        with open(output_file, 'rb') as f:
            sig = f.read()
        
        os.unlink(input_file)
        os.unlink(output_file)
        return sig.hex()
    except Exception as e:
        os.unlink(input_file) if os.path.exists(input_file) else None
        print(f"Error: {e}", file=sys.stderr)
        return ""

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "timestamp=1234567890&symbol=BTCUSDT"
    sig = sign_with_hsm(msg)
    print(sig if sig else "FAILED")
