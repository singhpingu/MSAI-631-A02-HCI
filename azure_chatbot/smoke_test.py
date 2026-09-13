"""Optional real Azure request; deliberately excluded from unittest discovery."""

import argparse

from azure_service import AzureSentimentService
from hybrid import HybridAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Make ONE real Azure sentiment request using a fixed harmless English sentence.")
    parser.add_argument("--send-to-azure", action="store_true", help="Explicitly authorize sending the printed sentence to Azure.")
    args = parser.parse_args()
    if not args.send_to_azure:
        parser.error("No request sent. Use --send-to-azure only after configuring your Free F0 resource.")
    text = "The setup instructions were clear and helpful."
    print(f"Sending one document to Azure: {text}")
    reply = HybridAdapter(AzureSentimentService()).respond(f"sentiment: {text}", cloud_consent=True)
    print(reply.text)
    if reply.source != "azure":
        print("Live cloud verification did not succeed.")
        return 1
    print("Live cloud verification succeeded. This is a real service result, not an offline test fixture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
