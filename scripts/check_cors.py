"""Quick script to verify CORS headers from the backend."""
import requests
import sys

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/catalog/sheet"
    headers = {"Origin": "http://localhost:3000"}
    try:
        resp = requests.get(url, headers=headers, params={
            "url": "https://docs.google.com/spreadsheets/d/1p3Iu4s3EONgkh4zz874h4cPZ3hD0v0KuTgiBi_RNS0o"
        }, timeout=5)
    except Exception as exc:
        print("request failed", exc)
        return
    print("status", resp.status_code)
    for k, v in resp.headers.items():
        if k.lower().startswith("access-control") or k.lower().startswith("access"):  # print a few
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()