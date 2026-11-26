# Checks

## Week 9: the server

The server is `server.py` (`MCPServer("listing")`, mcp 2.3.0), registered in `.mcp.json` as `listing`. Run on 2026-11-26.

### Tools
| Tool | No-key tests | What happened when Claude Code called it |
|---|---|---|
| `find_images` | 8 tests (11 cases): schema as specified, a match newest first with no paths, `limit` caps the list, wrong type (`limit: "five"`) is an error and the function did not run, out of range (`limit` 50 and 0, `product` empty and 81 characters) is an error and the function did not run, no match is `found: false`, no store yet is `found: false`, store unreadable is an error result | _TODO after the Claude Code session (step 6): what the model asked, what came back_ |
| `request_generation` | 6 tests (10 cases): schema as specified, wrong type (`variations: "two"`) is an error and nothing recorded, out of range (`variations` 9 and 0, a 200-character name, 301-character details, a blank color) is an error and nothing recorded, a brief naming a person is a normal `rejected` result and nothing recorded, pending file not writable is an error result, **side effect:** a valid request makes no network connection, never calls the generator, saves no image, records one pending line, and the key never appears in the result | _TODO after the Claude Code session: did the host ask permission, what the model told the seller_ |

Full suite: `python -m pytest` → 142 passed, 1 skipped (the billed `live` test, no key in the environment).

Each test file passed on its own, but in the full suite all 21 MCP tests first failed with `RuntimeError: Cannot run the event loop while another loop is running`. The Playwright browser tests run first and leave an event loop running in the main thread. Fix: `run_async` in `tests/conftest.py` runs each client session on a fresh loop in its own thread (commit "Server tests: run each MCP session on its own event loop").

### What a host receives: `python3 client.py`
This is everything a host learns before any model is involved: the tool names, the docstrings (the only thing the model reads to decide when to call a tool) and the JSON Schemas built from the type hints. The last call shows a bad argument stopped by the SDK before our function ran.

```
find_images: Find listing images already generated for a product, newest first, by product name.
Call this first whenever a seller wants images of a product, before request_generation:
if suitable images exist, offer those instead of paying for new ones. found is false when
nothing matches; that is an answer to give the seller, not an error.
  schema: {"product": {"description": "The product name, or part of it, e.g. 'storage basket'", "maxLength": 80, "minLength": 1, "title": "Product", "type": "string"}, "limit": {"default": 5, "description": "The most images to return", "maximum": 20, "minimum": 1, "title": "Limit", "type": "integer"}}

request_generation: Ask for new listing images of a product. Call this only when the seller has asked for new
images and find_images found nothing suitable. Images cost money, so nothing is generated here:
the request is recorded as pending for a person on the team to approve. Tell the seller it is
pending, not done. A brief that mentions people or real brands is refused; tell the seller why.
  schema: {"product_name": {"description": "What the product is, e.g. 'Handwoven storage basket'", "maxLength": 80, "minLength": 1, "title": "Product Name", "type": "string"}, "color": {"description": "The product's main color", "maxLength": 40, "minLength": 1, "title": "Color", "type": "string"}, "material": {"description": "What the product is made of", "maxLength": 40, "minLength": 1, "title": "Material", "type": "string"}, "background": {"description": "The scene behind the product, e.g. 'Plain white'", "maxLength": 80, "minLength": 1, "title": "Background", "type": "string"}, "style": {"anyOf": [{"maxLength": 80, "type": "string"}, {"type": "null"}], "default": null, "description": "Optional look, e.g. 'Minimal, natural light'", "title": "Style"}, "extra_details": {"anyOf": [{"maxLength": 300, "type": "string"}, {"type": "null"}], "default": null, "description": "Optional details to show, e.g. 'Has two leather handles'", "title": "Extra Details"}, "variations": {"default": 1, "description": "How many images (each one is billed)", "maximum": 5, "minimum": 1, "title": "Variations", "type": "integer"}}

--- find_images('phone case', limit=2)
{
 "found": true,
 "count": 2,
 "images": [
  {
   "id": "2491faa6-6eda-4a8c-8459-fdd1711c7354",
   "product_name": "iPhone 14 promax phone case",
   "color": "pink",
   "material": "leather",
   "background": "white",
   "variation": 2,
   "model": "black-forest-labs/flux.2-klein-4b",
   "created": "2026-11-02T19:44:39+00:00"
  },
  {
   "id": "fd328e0c-ea91-4134-b39c-e79d68118493",
   "product_name": "iPhone 14 promax phone case",
   "color": "pink",
   "material": "leather",
   "background": "white",
   "variation": 4,
   "model": "black-forest-labs/flux.2-klein-4b",
   "created": "2026-11-02T19:44:39+00:00"
  }
 ]
}

--- request_generation for a navy seagrass basket, 1 variation
{
 "generated": false,
 "pending": true,
 "request_id": "6892766f-6162-4db4-bdfe-2b1caef9a1d1",
 "variations": 1,
 "estimated_cost_usd": 0.014,
 "note": "Recorded for a person on the team to approve. No image was generated and nothing was spent."
}

--- request_generation with variations=9 (the schema says 1 to 5)
is_error: True | Error executing tool request_generation: 1 validation error for request_generationArguments
variations
  Input should be less than or equal to 5 [type=less_than_equal, input_value=9, input_type=int]
```

### The stray print
With `print("hello")` added as the first line of `find_images`, `client.py` logged this on stderr:

```
Failed to parse JSONRPC message from server
Traceback (most recent call last):
  File ".venv/lib/python3.13/site-packages/mcp/client/stdio.py", line 222, in _parse_line
    message = types.jsonrpc_message_adapter.validate_json(line, by_name=False)
  File ".venv/lib/python3.13/site-packages/pydantic/type_adapter.py", line 466, in validate_json
    return self.validator.validate_json(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        data,
        ^^^^^
    ...<5 lines>...
        by_name=by_name,
        ^^^^^^^^^^^^^^^^
    )
    ^
pydantic_core._pydantic_core.ValidationError: 1 validation error for union[JSONRPCRequest,JSONRPCNotification,JSONRPCResponse,JSONRPCError]
  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='hello', input_type=str]
```

Over stdio, the server's stdout is the protocol: every line must be a JSON-RPC message. `hello` is not JSON, so the client failed to parse it. This SDK version logged the error and dropped the line, so the calls still answered. Another host may treat the same line as a broken connection. The print was removed. The server logs with `logging`, which goes to stderr.

### Server or skill?
The task needs a server because TP2 has two hosts, Claude Code and our own loop, and both must call the same tools with the same checks. The brief limits, the whole-word screener, the UUID-only store and the pending gate live once, in `server.py`, and neither host can skip them. A server also keeps the key in its own environment when billed tools arrive. `find_images` alone could have been a skill: a script that lists `generated/*.json` and filters by product name, run by Claude Code from its shell. We kept it in the server, because our own loop has no shell. The server's version also only reads records whose names are valid UUIDs and never returns file paths, so the model cannot wander into other files.

### The gate
`request_generation` is the tool that leads to spending, about $0.014 per image. **The server** checks the brief and screens it (a person or a real brand is refused, and nothing is recorded). Then it appends one line to `pending.jsonl`: a server-made UUID, `status: "pending"`, the brief, the number of variations and the estimated cost. It returns `generated: false, pending: true`. It never calls the generator or the network, and the side-effect test proves it. The server cannot ask the user to confirm, because it cannot see the user; it only answers the host. **The host** (Claude Code): _TODO after step 6: did it show a permission prompt for `request_generation`, and what did the model tell the seller?_ **A person** still has to read `pending.jsonl`, check the brief and the cost, and approve the request. The approval step runs the existing generator with `OPENROUTER_API_KEY` from the environment. It is not a tool, and it is not built yet (Week 10).

### Found along the way
- The screener blocks `Apple` but not `iPhone`. `request_generation` would record "iPhone 14 promax phone case", a real brand's product. That gap is from TP1, and two saved images already have that name. To fix in its own PR, with a screener test.
