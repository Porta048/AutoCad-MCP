# AutoCAD MCP Server <img src="img/claude-logo.png" alt="Claude" width="32">

Server MCP per controllare AutoCAD tramite Claude Desktop con linguaggio naturale.

<img src="img/schema.png" alt="Schema" width="400">

Documentazione in inglese: [readme-eng.md](readme-eng.md)

## Requisiti

- **Windows** (COM interface)
- **Python 3.10+**
- **AutoCAD** / GstarCAD / ZWCAD

## Installazione

```bash
git clone https://github.com/yourusername/autocad-mcp.git
cd autocad-mcp
pip install -e .
```

## Configurazione Claude Desktop

Aggiungi in `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "autocad": {
      "command": "autocad-mcp"
    }
  }
}
```

![Configurazione](img/cursor_config.png)

## Tools

| Tool | Descrizione |
|------|-------------|
| `draw_line` | Linea tra due punti |
| `draw_circle` | Cerchio (centro + raggio) |
| `draw_arc` | Arco con angoli |
| `draw_ellipse` | Ellisse |
| `draw_rectangle` | Rettangolo |
| `draw_polyline` | Polilinea |
| `draw_text` | Testo |
| `draw_hatch` | Pattern fill |
| `add_dimension` | Quota |
| `save_drawing` | Salva DWG |
| `process_command` | Comando naturale |

## Esempi

```
Disegna un cerchio rosso a (100, 100) con raggio 50
Crea un rettangolo da (0, 0) a (200, 100)
Aggiungi testo "Hello" a (50, 50)
```

## Colori

`1` Rosso | `2` Giallo | `3` Verde | `4` Ciano | `5` Blu | `6` Magenta | `7` Bianco

## Config CAD

In `src/autocad_mcp/config.json` imposta `cad.type`: `AUTOCAD`, `GCAD`, o `ZWCAD`

## License

MIT
