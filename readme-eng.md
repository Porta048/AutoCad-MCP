# AutoCAD MCP Server <img src="img/claude-logo.png" alt="Claude" width="32">

MCP server to control AutoCAD through Claude Desktop using natural language.

<img src="img/schema.png" alt="Schema" width="400">

## Requirements

- **Windows** (COM interface)
- **Python 3.10+**
- **AutoCAD** / GstarCAD / ZWCAD

## Installation

```bash
git clone https://github.com/yourusername/autocad-mcp.git
cd autocad-mcp
pip install -e .
```

## Claude Desktop Configuration

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "autocad": {
      "command": "autocad-mcp"
    }
  }
}
```

![Configuration](img/cursor_config.png)

## Tools

| Tool | Description |
|------|-------------|
| `draw_line` | Line between two points |
| `draw_circle` | Circle (center + radius) |
| `draw_arc` | Arc with angles |
| `draw_ellipse` | Ellipse |
| `draw_rectangle` | Rectangle |
| `draw_polyline` | Polyline |
| `draw_text` | Text |
| `draw_hatch` | Pattern fill |
| `add_dimension` | Dimension |
| `save_drawing` | Save DWG |
| `process_command` | Natural language command |

## Examples

```
Draw a red circle at (100, 100) with radius 50
Create a rectangle from (0, 0) to (200, 100)
Add text "Hello" at (50, 50)
```

## Colors

`1` Red | `2` Yellow | `3` Green | `4` Cyan | `5` Blue | `6` Magenta | `7` White

## CAD Config

In `src/autocad_mcp/config.json` set `cad.type`: `AUTOCAD`, `GCAD`, or `ZWCAD`

## License

MIT
