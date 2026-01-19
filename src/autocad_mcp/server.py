"""
AutoCAD MCP Server.

Model Context Protocol server for controlling AutoCAD through Claude Desktop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)

from autocad_mcp.cad_controller import CADController
from autocad_mcp.config import load_config
from autocad_mcp.nlp_processor import NLPProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler("autocad_mcp.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class DrawingState:
    """Current state of the CAD drawing."""

    entities: list[dict[str, Any]] = field(default_factory=list)
    current_layer: str = "0"
    last_command: str = ""
    last_result: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entities": self.entities,
            "current_layer": self.current_layer,
            "last_command": self.last_command,
            "last_result": self.last_result,
            "entity_count": len(self.entities),
        }

    def add_entity(self, entity: dict[str, Any]) -> None:
        """Add an entity to the drawing state."""
        self.entities.append(entity)


class CADService:
    """High-level service for CAD operations."""

    def __init__(self) -> None:
        """Initialize CAD service."""
        self.config = load_config()
        self.controller = CADController(self.config.cad)
        self.nlp = NLPProcessor()
        self.state = DrawingState()
        self._initialized = False

    def ensure_initialized(self) -> bool:
        """Ensure CAD is initialized."""
        if self._initialized and self.controller.is_running():
            return True

        logger.info("Initializing CAD connection...")
        if self.controller.start():
            self._initialized = True
            return True

        logger.error("Failed to initialize CAD")
        return False

    def draw_line(
        self,
        start: list[float],
        end: list[float],
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """Draw a line."""
        if len(start) < 2 or len(end) < 2:
            return {"success": False, "error": "Coordinates must have at least 2 values"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        result = self.controller.draw_line(
            tuple(start), tuple(end), layer, color, lineweight
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"draw_line({start}, {end})"
            self.state.last_result = "success"
        return result

    def draw_circle(
        self,
        center: list[float],
        radius: float,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """Draw a circle."""
        if len(center) < 2:
            return {"success": False, "error": "Center must have at least 2 coordinates"}
        
        if radius <= 0:
            return {"success": False, "error": "Radius must be positive"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        result = self.controller.draw_circle(
            tuple(center), radius, layer, color, lineweight
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"draw_circle({center}, {radius})"
            self.state.last_result = "success"
        return result

    def draw_arc(
        self,
        center: list[float],
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """Draw an arc."""
        if len(center) < 2:
            return {"success": False, "error": "Center must have at least 2 coordinates"}
        
        if radius <= 0:
            return {"success": False, "error": "Radius must be positive"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        result = self.controller.draw_arc(
            tuple(center), radius, start_angle, end_angle, layer, color, lineweight
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"draw_arc({center}, {radius}, {start_angle}, {end_angle})"
            self.state.last_result = "success"
        return result

    def draw_ellipse(
        self,
        center: list[float],
        major_axis: float,
        minor_axis: float,
        rotation: float = 0.0,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """Draw an ellipse."""
        if len(center) < 2:
            return {"success": False, "error": "Center must have at least 2 coordinates"}
        
        if major_axis <= 0:
            return {"success": False, "error": "Major axis must be positive"}
        
        if minor_axis < 0:
            return {"success": False, "error": "Minor axis must be non-negative"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        result = self.controller.draw_ellipse(
            tuple(center), major_axis, minor_axis, rotation, layer, color, lineweight
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"draw_ellipse({center}, {major_axis}, {minor_axis})"
            self.state.last_result = "success"
        return result

    def draw_polyline(
        self,
        points: list[list[float]],
        closed: bool = False,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """Draw a polyline."""
        if len(points) < 2:
            return {"success": False, "error": "Polyline requires at least 2 points"}
        
        for i, pt in enumerate(points):
            if len(pt) < 2:
                return {"success": False, "error": f"Point {i} must have at least 2 coordinates"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        tuple_points = [tuple(p) for p in points]
        result = self.controller.draw_polyline(
            tuple_points, closed, layer, color, lineweight
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"draw_polyline({len(points)} points, closed={closed})"
            self.state.last_result = "success"
        return result

    def draw_rectangle(
        self,
        corner1: list[float],
        corner2: list[float],
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """Draw a rectangle."""
        if len(corner1) < 2 or len(corner2) < 2:
            return {"success": False, "error": "Corners must have at least 2 coordinates"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        result = self.controller.draw_rectangle(
            tuple(corner1), tuple(corner2), layer, color, lineweight
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"draw_rectangle({corner1}, {corner2})"
            self.state.last_result = "success"
        return result

    def draw_text(
        self,
        position: list[float],
        text: str,
        height: float = 2.5,
        rotation: float = 0.0,
        layer: str | None = None,
        color: int | None = None,
    ) -> dict[str, Any]:
        """Draw text."""
        if len(position) < 2:
            return {"success": False, "error": "Position must have at least 2 coordinates"}
        
        if not text:
            return {"success": False, "error": "Text cannot be empty"}
        
        if height <= 0:
            return {"success": False, "error": "Height must be positive"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        result = self.controller.draw_text(
            tuple(position), text, height, rotation, layer, color
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"draw_text('{text}')"
            self.state.last_result = "success"
        return result

    def draw_hatch(
        self,
        boundary_points: list[list[float]],
        pattern_name: str = "SOLID",
        pattern_scale: float = 1.0,
        layer: str | None = None,
        color: int | None = None,
    ) -> dict[str, Any]:
        """Draw a hatch pattern."""
        if len(boundary_points) < 3:
            return {"success": False, "error": "Hatch requires at least 3 boundary points"}
        
        for i, pt in enumerate(boundary_points):
            if len(pt) < 2:
                return {"success": False, "error": f"Point {i} must have at least 2 coordinates"}
        
        if not pattern_name:
            return {"success": False, "error": "Pattern name cannot be empty"}
        
        if pattern_scale <= 0:
            return {"success": False, "error": "Pattern scale must be positive"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        tuple_points = [tuple(p) for p in boundary_points]
        result = self.controller.draw_hatch(
            tuple_points, pattern_name, pattern_scale, layer, color
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"draw_hatch(pattern={pattern_name})"
            self.state.last_result = "success"
        return result

    def add_dimension(
        self,
        start: list[float],
        end: list[float],
        text_position: list[float],
        layer: str | None = None,
        color: int | None = None,
    ) -> dict[str, Any]:
        """Add a linear dimension."""
        if len(start) < 2 or len(end) < 2 or len(text_position) < 2:
            return {"success": False, "error": "All points must have at least 2 coordinates"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        if color is not None and (color < 0 or color > 255):
            return {"success": False, "error": "Color must be between 0 and 255"}

        result = self.controller.add_dimension(
            tuple(start), tuple(end), tuple(text_position), layer, color
        )
        if result["success"]:
            self.state.add_entity(result)
            self.state.last_command = f"add_dimension({start}, {end})"
            self.state.last_result = "success"
        return result

    def save_drawing(self, file_path: str) -> dict[str, Any]:
        """Save the drawing."""
        if not file_path:
            return {"success": False, "error": "File path cannot be empty"}
        
        if not file_path.strip():
            return {"success": False, "error": "File path cannot be whitespace"}
        
        if not self.ensure_initialized():
            return {"success": False, "error": "CAD not initialized"}

        result = self.controller.save_drawing(file_path)
        if result["success"]:
            self.state.last_command = f"save_drawing('{file_path}')"
            self.state.last_result = "success"
        return result

    def process_natural_language(self, command: str) -> dict[str, Any]:
        """Process a natural language command."""
        parsed = self.nlp.parse_command(command)
        self.state.last_command = command

        if not parsed.shape:
            return {
                "success": False,
                "error": f"Could not understand command: {command}",
                "parsed": {
                    "action": parsed.action,
                    "confidence": parsed.confidence,
                },
            }

        # Map shape to service method
        method_map = {
            "line": self._execute_line,
            "circle": self._execute_circle,
            "arc": self._execute_arc,
            "ellipse": self._execute_ellipse,
            "rectangle": self._execute_rectangle,
            "polyline": self._execute_polyline,
            "text": self._execute_text,
            "hatch": self._execute_hatch,
            "dimension": self._execute_dimension,
        }

        handler = method_map.get(parsed.shape)
        if handler:
            return handler(parsed.parameters)

        return {
            "success": False,
            "error": f"Unsupported shape: {parsed.shape}",
        }

    def _execute_line(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.draw_line(
            list(params.get("start", [0, 0])),
            list(params.get("end", [100, 100])),
            color=params.get("color"),
        )

    def _execute_circle(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.draw_circle(
            list(params.get("center", [0, 0])),
            params.get("radius", 50),
            color=params.get("color"),
        )

    def _execute_arc(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.draw_arc(
            list(params.get("center", [0, 0])),
            params.get("radius", 50),
            params.get("start_angle", 0),
            params.get("end_angle", 90),
            color=params.get("color"),
        )

    def _execute_ellipse(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.draw_ellipse(
            list(params.get("center", [0, 0])),
            params.get("major_axis", 100),
            params.get("minor_axis", 50),
            params.get("rotation", 0),
            color=params.get("color"),
        )

    def _execute_rectangle(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.draw_rectangle(
            list(params.get("corner1", [0, 0])),
            list(params.get("corner2", [100, 100])),
            color=params.get("color"),
        )

    def _execute_polyline(self, params: dict[str, Any]) -> dict[str, Any]:
        points = params.get("points", [[0, 0], [50, 50], [100, 0]])
        return self.draw_polyline(
            [list(p) for p in points],
            params.get("closed", False),
            color=params.get("color"),
        )

    def _execute_text(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.draw_text(
            list(params.get("position", [0, 0])),
            params.get("text", "Text"),
            params.get("height", 2.5),
            params.get("rotation", 0),
            color=params.get("color"),
        )

    def _execute_hatch(self, params: dict[str, Any]) -> dict[str, Any]:
        points = params.get("boundary_points", [[0, 0], [100, 0], [100, 100], [0, 100]])
        return self.draw_hatch(
            [list(p) for p in points],
            params.get("pattern_name", "SOLID"),
            params.get("pattern_scale", 1.0),
            color=params.get("color"),
        )

    def _execute_dimension(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.add_dimension(
            list(params.get("start", [0, 0])),
            list(params.get("end", [100, 0])),
            list(params.get("text_position", [50, 10])),
            color=params.get("color"),
        )


# Tool definitions
TOOLS: list[Tool] = [
    Tool(
        name="draw_line",
        description="Draw a straight line between two points in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "start": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Start point coordinates [x, y] or [x, y, z]",
                },
                "end": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "End point coordinates [x, y] or [x, y, z]",
                },
                "layer": {
                    "type": "string",
                    "description": "Layer name (optional)",
                },
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
                "lineweight": {
                    "type": "integer",
                    "description": "Line weight in hundredths of mm (optional)",
                },
            },
            "required": ["start", "end"],
        },
    ),
    Tool(
        name="draw_circle",
        description="Draw a circle with specified center and radius in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "center": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Center point coordinates [x, y] or [x, y, z]",
                },
                "radius": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Circle radius",
                },
                "layer": {"type": "string", "description": "Layer name (optional)"},
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
                "lineweight": {
                    "type": "integer",
                    "description": "Line weight in hundredths of mm (optional)",
                },
            },
            "required": ["center", "radius"],
        },
    ),
    Tool(
        name="draw_arc",
        description="Draw an arc with specified center, radius, and angles in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "center": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Center point coordinates [x, y] or [x, y, z]",
                },
                "radius": {"type": "number", "minimum": 0, "description": "Arc radius"},
                "start_angle": {
                    "type": "number",
                    "description": "Start angle in degrees",
                },
                "end_angle": {
                    "type": "number",
                    "description": "End angle in degrees",
                },
                "layer": {"type": "string", "description": "Layer name (optional)"},
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
                "lineweight": {
                    "type": "integer",
                    "description": "Line weight in hundredths of mm (optional)",
                },
            },
            "required": ["center", "radius", "start_angle", "end_angle"],
        },
    ),
    Tool(
        name="draw_ellipse",
        description="Draw an ellipse with specified center, axes, and rotation in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "center": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Center point coordinates [x, y] or [x, y, z]",
                },
                "major_axis": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Length of major axis",
                },
                "minor_axis": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Length of minor axis",
                },
                "rotation": {
                    "type": "number",
                    "default": 0,
                    "description": "Rotation angle in degrees (optional)",
                },
                "layer": {"type": "string", "description": "Layer name (optional)"},
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
                "lineweight": {
                    "type": "integer",
                    "description": "Line weight in hundredths of mm (optional)",
                },
            },
            "required": ["center", "major_axis", "minor_axis"],
        },
    ),
    Tool(
        name="draw_polyline",
        description="Draw a polyline through multiple points in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "points": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 3,
                    },
                    "minItems": 2,
                    "description": "Array of points [[x1,y1], [x2,y2], ...]",
                },
                "closed": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to close the polyline",
                },
                "layer": {"type": "string", "description": "Layer name (optional)"},
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
                "lineweight": {
                    "type": "integer",
                    "description": "Line weight in hundredths of mm (optional)",
                },
            },
            "required": ["points"],
        },
    ),
    Tool(
        name="draw_rectangle",
        description="Draw a rectangle defined by two corner points in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "corner1": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "First corner coordinates [x, y] or [x, y, z]",
                },
                "corner2": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Opposite corner coordinates [x, y] or [x, y, z]",
                },
                "layer": {"type": "string", "description": "Layer name (optional)"},
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
                "lineweight": {
                    "type": "integer",
                    "description": "Line weight in hundredths of mm (optional)",
                },
            },
            "required": ["corner1", "corner2"],
        },
    ),
    Tool(
        name="draw_text",
        description="Add text at a specified position in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "position": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Text insertion point [x, y] or [x, y, z]",
                },
                "text": {"type": "string", "description": "Text content"},
                "height": {
                    "type": "number",
                    "default": 2.5,
                    "minimum": 0,
                    "description": "Text height (optional)",
                },
                "rotation": {
                    "type": "number",
                    "default": 0,
                    "description": "Rotation angle in degrees (optional)",
                },
                "layer": {"type": "string", "description": "Layer name (optional)"},
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
            },
            "required": ["position", "text"],
        },
    ),
    Tool(
        name="draw_hatch",
        description="Create a hatch pattern fill within a boundary in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "boundary_points": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 3,
                    },
                    "minItems": 3,
                    "description": "Boundary points forming a closed area",
                },
                "pattern_name": {
                    "type": "string",
                    "default": "SOLID",
                    "description": "Hatch pattern name (e.g., SOLID, ANSI31)",
                },
                "pattern_scale": {
                    "type": "number",
                    "default": 1.0,
                    "minimum": 0,
                    "description": "Pattern scale factor",
                },
                "layer": {"type": "string", "description": "Layer name (optional)"},
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
            },
            "required": ["boundary_points"],
        },
    ),
    Tool(
        name="add_dimension",
        description="Add a linear dimension annotation in AutoCAD",
        inputSchema={
            "type": "object",
            "properties": {
                "start": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Start point of dimension [x, y] or [x, y, z]",
                },
                "end": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "End point of dimension [x, y] or [x, y, z]",
                },
                "text_position": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Position for dimension text [x, y] or [x, y, z]",
                },
                "layer": {"type": "string", "description": "Layer name (optional)"},
                "color": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Color index 0-255 (optional)",
                },
            },
            "required": ["start", "end", "text_position"],
        },
    ),
    Tool(
        name="save_drawing",
        description="Save the current drawing to a DWG file",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Full path for the saved file (e.g., C:/drawings/myfile.dwg)",
                },
            },
            "required": ["file_path"],
        },
    ),
    Tool(
        name="process_command",
        description="Process a natural language command to control AutoCAD. Supports commands like 'draw a red circle at (100, 100) with radius 50'",
        inputSchema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Natural language command describing what to draw",
                },
            },
            "required": ["command"],
        },
    ),
]


# Global service instance
cad_service: CADService | None = None


def get_cad_service() -> CADService:
    """Get or create the CAD service instance."""
    global cad_service
    if cad_service is None:
        cad_service = CADService()
    return cad_service


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> str:
    """Handle a tool call and return the result as JSON string."""
    service = get_cad_service()

    try:
        if name == "draw_line":
            result = service.draw_line(
                arguments["start"],
                arguments["end"],
                arguments.get("layer"),
                arguments.get("color"),
                arguments.get("lineweight"),
            )
        elif name == "draw_circle":
            result = service.draw_circle(
                arguments["center"],
                arguments["radius"],
                arguments.get("layer"),
                arguments.get("color"),
                arguments.get("lineweight"),
            )
        elif name == "draw_arc":
            result = service.draw_arc(
                arguments["center"],
                arguments["radius"],
                arguments["start_angle"],
                arguments["end_angle"],
                arguments.get("layer"),
                arguments.get("color"),
                arguments.get("lineweight"),
            )
        elif name == "draw_ellipse":
            result = service.draw_ellipse(
                arguments["center"],
                arguments["major_axis"],
                arguments["minor_axis"],
                arguments.get("rotation", 0),
                arguments.get("layer"),
                arguments.get("color"),
                arguments.get("lineweight"),
            )
        elif name == "draw_polyline":
            result = service.draw_polyline(
                arguments["points"],
                arguments.get("closed", False),
                arguments.get("layer"),
                arguments.get("color"),
                arguments.get("lineweight"),
            )
        elif name == "draw_rectangle":
            result = service.draw_rectangle(
                arguments["corner1"],
                arguments["corner2"],
                arguments.get("layer"),
                arguments.get("color"),
                arguments.get("lineweight"),
            )
        elif name == "draw_text":
            result = service.draw_text(
                arguments["position"],
                arguments["text"],
                arguments.get("height", 2.5),
                arguments.get("rotation", 0),
                arguments.get("layer"),
                arguments.get("color"),
            )
        elif name == "draw_hatch":
            result = service.draw_hatch(
                arguments["boundary_points"],
                arguments.get("pattern_name", "SOLID"),
                arguments.get("pattern_scale", 1.0),
                arguments.get("layer"),
                arguments.get("color"),
            )
        elif name == "add_dimension":
            result = service.add_dimension(
                arguments["start"],
                arguments["end"],
                arguments["text_position"],
                arguments.get("layer"),
                arguments.get("color"),
            )
        elif name == "save_drawing":
            result = service.save_drawing(arguments["file_path"])
        elif name == "process_command":
            result = service.process_natural_language(arguments["command"])
        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception("Error handling tool call %s", name)
        return json.dumps({"success": False, "error": str(e)})


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("autocad-mcp")

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List available resources."""
        return [
            Resource(
                uri="drawing://current",
                name="Current Drawing State",
                description="Current state of the AutoCAD drawing including all entities",
                mimeType="application/json",
            )
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a resource by URI."""
        if uri == "drawing://current":
            service = get_cad_service()
            return json.dumps(service.state.to_dict(), ensure_ascii=False, indent=2)
        raise ValueError(f"Unknown resource: {uri}")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute a tool call."""
        logger.info("Tool call: %s with args: %s", name, arguments)
        result = await handle_tool_call(name, arguments)
        return [TextContent(type="text", text=result)]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        """List available prompts."""
        return [
            Prompt(
                name="cad-assistant",
                description="AutoCAD assistant system prompt for natural language CAD control",
                arguments=[
                    PromptArgument(
                        name="task",
                        description="The drawing task to accomplish",
                        required=False,
                    )
                ],
            )
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
        """Get a specific prompt."""
        if name == "cad-assistant":
            task = arguments.get("task", "") if arguments else ""
            return GetPromptResult(
                description="AutoCAD assistant for natural language control",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"""You are an AutoCAD assistant that helps users create CAD drawings through natural language commands.

You can:
- Draw basic shapes: lines, circles, arcs, ellipses, rectangles, polylines
- Add text and dimensions
- Create hatch patterns for fills
- Save drawings to DWG files

When the user describes what they want to draw, use the appropriate tools to create the entities in AutoCAD.

Coordinate system:
- Use (x, y) or (x, y, z) coordinates
- Positive X is right, positive Y is up
- Angles are in degrees, counter-clockwise from positive X axis

Colors (0-255 index):
- 1: Red, 2: Yellow, 3: Green, 4: Cyan, 5: Blue, 6: Magenta, 7: White

{f'Current task: {task}' if task else 'Waiting for drawing instructions...'}""",
                        ),
                    )
                ],
            )
        raise ValueError(f"Unknown prompt: {name}")

    return server


async def run_server() -> None:
    """Run the MCP server."""
    server = create_server()
    config = load_config()

    logger.info(
        "Starting %s v%s",
        config.server.name,
        config.server.version,
    )

    # Use stdio transport for Claude Desktop integration
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception("Server error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
