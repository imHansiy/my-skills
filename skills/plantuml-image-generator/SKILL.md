---
name: plantuml-image-generator
description: Triggered when the user requests an image (e.g., architecture, flowchart, sequence diagram) or needs a technical illustration inserted into a document. This skill dynamically generates and inserts images using the official PlantUML public API.
license: MIT
metadata:
  author: imHansiy
  version: "1.0.0"
---

# PlantUML Image Generator

## When to Apply
- When the user asks "draw a diagram for me" or "I need an architecture/flowchart/sequence/state-machine diagram".
- When the user requires inserting an illustration of business processes or structural diagrams into development documents, READMEs, or any Markdown files.
- When you need to visually explain complex code logic to the user for better understanding.

## Execution Rules
1. **Requirement Analysis & Code Generation**:
   - Extract the elements and relationships that need visualization based on the user's context.
   - Write standard PlantUML syntax code (must start with `@startuml` and end with `@enduml`).

2. **Core Encoding Logic (URL Generation)**:
   Convert the generated PlantUML code into `ENCODED_TEXT` using specific encoding rules:
   - First, encode the PlantUML source code into `UTF-8`.
   - Compress it using the `zlib` / `Deflate` algorithm.
   - Re-encode the compressed result using PlantUML's specialized Base64 dictionary (variant: `0-9, A-Z, a-z, -, _`).

3. **URL Assembly**:
   Append the generated `ENCODED_TEXT` to the official main service URL, supporting two mainstream formats:
   - PNG Raster Image: `http://www.plantuml.com/plantuml/png/{ENCODED_TEXT}`
   - SVG Vector Image (Recommended, scales without distortion): `http://www.plantuml.com/plantuml/svg/{ENCODED_TEXT}`

4. **Rendering & Insertion**:
   - Wrap the assembled URL using standard Markdown image syntax: `![Image Description/Alt](URL)`
   - Reply directly to the user with this Markdown line, or use file editing tools to insert it into the appropriate location in the document.

## Code Reference (Auto-Helper Script / Python Example)
If you need to write a script to quickly verify the encoding process, refer to the following conversion logic:

```python
import zlib
import base64

def generate_plantuml_url(uml_text: str, output_format: str = "svg") -> str:
    utf8_data = uml_text.encode('utf-8')
    compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed_data = compressor.compress(utf8_data) + compressor.flush()
    b64_str = base64.b64encode(compressed_data)
    trans = bytes.maketrans(
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
        b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    )
    encoded_str = b64_str.translate(trans).decode('utf-8').rstrip('=')
    return f"http://www.plantuml.com/plantuml/{output_format}/{encoded_str}"
```

## Input/Output Example (Edge Cases & Examples)

**Input Context**:
"Boss: Add a sequence diagram to the README explaining the user login process."

**Internal Execution (PlantUML Source)**:
```text
@startuml
User -> Server: Send username and password
Server -> Database: Validate credentials
Database --> Server: Return UserID and Token
Server --> User: Login successful
@enduml
```

**Your Final Output (Written directly in the document or feedback message)**:
```markdown
![User Login Sequence Diagram](http://www.plantuml.com/plantuml/svg/SoWkIImgAStDuKfCoKnELT2rKt3CJJ58I2nAp5K8I2rEBajCJbNmN4h5iKj2hG0uW55nWgIWHXyWDB4PqEIgvWhGgfE2Kz2rKt240000)
```
