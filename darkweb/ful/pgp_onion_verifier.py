#!/usr/bin/env python3
import gnupg
import re
import subprocess
import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor

gpg = gnupg.GPG()

def curl_tor(url):
    cmd = [
        'curl', '-s', '--max-time', '60',
        '--socks5-hostname', '127.0.0.1:9150',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        url
    ]
    for attempt in range(3):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=70)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip(), None
        except:
            pass
        time.sleep(2)  # Backoff
    return None, "fetch failed"

def get_likelihood(score, bytes_fetched):
    if score == 4:
        return "Excellent"
    elif score == 3:
        return "Good"
    elif score == 2 or bytes_fetched > 100:  # Live site bonus
        return "Fair"
    else:
        return "Poor"

def verify_onion(onion):
    onion = onion.strip().replace('http://','').replace('https://','').split('/')[0]
    base = f"http://{onion}"
    bytes_fetched = 0
    score = 0

    # PGP Key Hunt (expanded)
    pgp_paths = ["/pgp", "/pgp.txt", "/pgp.asc", "/key.asc", "/pubkey.asc", 
                 "/u/HugBunter/pgp", "/key.txt", "/pgp-key.asc", "/public.asc", "/canary.txt"]
    pgp_text = None
    for p in pgp_paths:
        text, _ = curl_tor(f"{base}{p}")
        bytes_fetched += len(text or '')
        if text and "BEGIN PGP PUBLIC KEY" in text.upper():
            pgp_text = text
            score += 1
            break
    if not pgp_text:
        return get_likelihood(score, bytes_fetched), "No PGP key found", score

    if gpg.import_keys(pgp_text).count == 0:
        return get_likelihood(score, bytes_fetched), "Key import failed", score

    # Signed File Hunt
    signed_paths = ["/mirrors.txt", "/announcements.txt", "/pgp", "/pgp.txt", 
                    "/status.txt", "/canary.txt", "/proof.txt", "/mirrors"]
    signed_text = None
    for p in signed_paths:
        text, _ = curl_tor(f"{base}{p}")
        bytes_fetched += len(text or '')
        if text and "BEGIN PGP SIGNATURE" in text.upper():
            signed_text = text
            score += 1
            break
    if not signed_text:
        return get_likelihood(score, bytes_fetched), "No signed file", score

    verified = gpg.verify(signed_text)
    if not verified.valid:
        return get_likelihood(score, bytes_fetched), "Bad signature", score

    score += 1

    if onion in signed_text.lower():
        score += 1

    likelihood = get_likelihood(score, bytes_fetched)
    reason = f"Score: {score}/4 - {likelihood} legitimacy"
    return likelihood, reason, score

# ——— MAIN ———
start_time = time.time()

if not os.path.exists('onions.txt'):
    print("Error: onions.txt not found!")
else:
    with open('onions.txt') as f:
        onions = [line.strip() for line in f if line.strip()]

    results = []
    print(f"Verifying {len(onions)} onions via Tor + PGP...\n")
    for onion in onions:
        likelihood, reason, score = verify_onion(onion)
        print(f"{onion:<70} → {likelihood} ({score}/4) | {reason}")
        results.append({"onion": onion, "likelihood": likelihood, "score": score, "reason": reason})

    with open('verified.json', 'w') as f:
        json.dump(results, f, indent=2)

    run_time = time.time() - start_time
    minutes = int(run_time // 60)
    seconds = int(run_time % 60)
    print(f"\nDone! Run time: {minutes}m {seconds}s | JSON: verified.json")

    excellent = sum(1 for r in results if r["likelihood"] == "Excellent")
    good = sum(1 for r in results if r["likelihood"] == "Good")
    fair = sum(1 for r in results if r["likelihood"] == "Fair")
    print(f"Summary: {excellent} Excellent, {good} Good, {fair} Fair — ready for OSINT monitoring.")
