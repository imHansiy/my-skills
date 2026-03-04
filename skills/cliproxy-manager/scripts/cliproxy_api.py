import argparse
import requests
import json
import os
import sys

class CLIProxyManager:
    def __init__(self, base_url="http://localhost:8317", management_key=None):
        self.base_url = base_url.rstrip('/')
        self.management_key = management_key or os.environ.get('MANAGEMENT_PASSWORD')
        if not self.management_key:
            print("Error: Management key is missing. Use --key or set MANAGEMENT_PASSWORD environment variable.", file=sys.stderr)
            sys.exit(1)
        self.headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json"
        }

    def _call(self, method, endpoint, data=None, params=None):
        url = f"{self.base_url}/v0/management/{endpoint.lstrip('/')}"
        try:
            response = requests.request(method, url, headers=self.headers, json=data, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_msg = response.json().get('error', str(e))
                print(f"API Error: {error_msg}", file=sys.stderr)
            except:
                print(f"HTTP Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Network/Internal Error: {e}", file=sys.stderr)
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="CLIProxyAPI Management API Helper")
    parser.add_argument("--key", help="Management key (plaintext)")
    parser.add_argument("--url", default="http://localhost:8317", help="Base URL (default: http://localhost:8317)")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # GET command
    get_parser = subparsers.add_parser("get", help="GET resource")
    get_parser.add_argument("resource", choices=["config", "usage", "api-keys", "gemini-api-key", "claude-api-key", "openai-compatibility", "debug", "config-yaml", "auth-files"], help="Resource to fetch")
    get_parser.add_argument("--query", help="Query string (e.g., 'name=val')", action="append")

    # PUT command
    put_parser = subparsers.add_parser("put", help="PUT (overwrite) resource")
    put_parser.add_argument("resource", choices=["api-keys", "gemini-api-key", "claude-api-key", "openai-compatibility", "config-yaml"], help="Resource to update")
    put_parser.add_argument("--data", required=True, help="JSON data string or path to JSON file")

    # PATCH command
    patch_parser = subparsers.add_parser("patch", help="PATCH (partial update) resource")
    patch_parser.add_argument("resource", choices=["api-keys", "gemini-api-key", "claude-api-key", "openai-compatibility"], help="Resource to update")
    patch_parser.add_argument("--data", required=True, help="JSON data string (e.g., '{\"old\":\"k1\", \"new\":\"k2\"}')")

    # DELETE command
    delete_parser = subparsers.add_parser("delete", help="DELETE resource")
    delete_parser.add_argument("resource", choices=["api-keys", "gemini-api-key", "claude-api-key", "auth-files"], help="Resource to delete")
    delete_parser.add_argument("--query", help="Query string (e.g., 'value=k1' or 'index=0')", required=True)

    args = parser.parse_args()
    
    manager = CLIProxyManager(base_url=args.url, management_key=args.key)
    
    if args.command == "get":
        params = {}
        if args.query:
            for q in args.query:
                k, v = q.split('=')
                params[k] = v
        result = manager._call("GET", args.resource, params=params)
    elif args.command == "put":
        data = args.data
        if os.path.isfile(data):
            with open(data, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = json.loads(data)
        result = manager._call("PUT", args.resource, data=data)
    elif args.command == "patch":
        data = json.loads(args.data)
        result = manager._call("PATCH", args.resource, data=data)
    elif args.command == "delete":
        params = {}
        if args.query:
            k, v = args.query.split('=')
            params[k] = v
        result = manager._call("DELETE", args.resource, params=params)

    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
