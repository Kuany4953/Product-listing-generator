"""A host with no model in it: start the server, ask what it offers, call each tool once.

    python3 client.py

This is everything an MCP host does before a model is involved: launch server.py as a child
process over stdio, discover its tools and their schemas, and call one by name with JSON
arguments. Claude Code does the same, then hands the schemas and docstrings to the model.

The request_generation call records a real pending request in pending.jsonl (git-ignored).
Nothing is generated and nothing is billed.
"""
import asyncio
import json
import sys

from mcp import Client, StdioServerParameters


async def main():
    server = StdioServerParameters(command=sys.executable, args=["server.py"])
    async with Client(server) as client:
        for t in (await client.list_tools()).tools:
            print(f"\n{t.name}: {t.description}")
            print("  schema:", json.dumps(t.input_schema.get("properties", {})))

        print("\n--- find_images('phone case', limit=2)")
        result = await client.call_tool("find_images", {"product": "phone case", "limit": 2})
        print(json.dumps(result.structured_content, indent=1))

        print("\n--- request_generation for a navy seagrass basket, 1 variation")
        brief = {"product_name": "Handwoven storage basket", "color": "Navy blue", "material": "Seagrass",
                 "background": "Plain white", "extra_details": "Has two leather handles"}
        result = await client.call_tool("request_generation", brief)
        print(json.dumps(result.structured_content, indent=1))

        print("\n--- request_generation with variations=9 (the schema says 1 to 5)")
        result = await client.call_tool("request_generation", {**brief, "variations": 9})
        print("is_error:", result.is_error, "|", result.content[0].text[:200])


if __name__ == "__main__":
    asyncio.run(main())
