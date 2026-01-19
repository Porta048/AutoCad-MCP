"""
Natural Language Processor for CAD Commands.

Parses natural language input and extracts CAD drawing parameters.
Supports both English and Chinese command syntax.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Color name to CAD color index mapping
COLOR_MAP: dict[str, int] = {
    # English
    "red": 1,
    "yellow": 2,
    "green": 3,
    "cyan": 4,
    "blue": 5,
    "magenta": 6,
    "white": 7,
    "gray": 8,
    "grey": 8,
    "black": 250,
    "orange": 30,
    "brown": 33,
    "purple": 200,
    "pink": 221,
    # Italian (masculine/feminine)
    "rosso": 1,
    "rossa": 1,
    "giallo": 2,
    "gialla": 2,
    "verde": 3,
    "ciano": 4,
    "blu": 5,
    "azzurro": 5,
    "azzurra": 5,
    "bianco": 7,
    "bianca": 7,
    "grigio": 8,
    "grigia": 8,
    "nero": 250,
    "nera": 250,
    "arancione": 30,
    "marrone": 33,
    "viola": 200,
    "rosa": 221,
    # Chinese
    "红": 1,
    "红色": 1,
    "黄": 2,
    "黄色": 2,
    "绿": 3,
    "绿色": 3,
    "青": 4,
    "青色": 4,
    "蓝": 5,
    "蓝色": 5,
    "洋红": 6,
    "洋红色": 6,
    "紫红": 6,
    "白": 7,
    "白色": 7,
    "灰": 8,
    "灰色": 8,
    "黑": 250,
    "黑色": 250,
    "橙": 30,
    "橙色": 30,
    "棕": 33,
    "棕色": 33,
    "紫": 200,
    "紫色": 200,
    "粉": 221,
    "粉色": 221,
    "粉红": 221,
}

# Shape keywords (English, Italian, and Chinese)
SHAPE_KEYWORDS: dict[str, str] = {
    # English
    "line": "line",
    "circle": "circle",
    "arc": "arc",
    "ellipse": "ellipse",
    "rectangle": "rectangle",
    "rect": "rectangle",
    "square": "rectangle",
    "polyline": "polyline",
    "polygon": "polyline",
    "text": "text",
    "dimension": "dimension",
    "hatch": "hatch",
    "fill": "hatch",
    # Italian
    "linea": "line",
    "cerchio": "circle",
    "arco": "arc",
    "ellisse": "ellipse",
    "rettangolo": "rectangle",
    "quadrato": "rectangle",
    "polilinea": "polyline",
    "poligono": "polyline",
    "testo": "text",
    "quota": "dimension",
    "quotatura": "dimension",
    "riempimento": "hatch",
    "tratteggio": "hatch",
    # Chinese
    "线": "line",
    "直线": "line",
    "圆": "circle",
    "圆形": "circle",
    "弧": "arc",
    "圆弧": "arc",
    "椭圆": "ellipse",
    "椭圆形": "ellipse",
    "矩形": "rectangle",
    "方形": "rectangle",
    "正方形": "rectangle",
    "多段线": "polyline",
    "折线": "polyline",
    "多边形": "polyline",
    "文字": "text",
    "文本": "text",
    "标注": "dimension",
    "尺寸": "dimension",
    "填充": "hatch",
    "图案填充": "hatch",
}

# Action keywords (English, Italian, and Chinese)
ACTION_KEYWORDS: dict[str, str] = {
    # English
    "draw": "draw",
    "create": "draw",
    "add": "draw",
    "make": "draw",
    "place": "draw",
    "insert": "draw",
    "modify": "modify",
    "change": "modify",
    "edit": "modify",
    "move": "move",
    "rotate": "rotate",
    "scale": "scale",
    "resize": "scale",
    "delete": "erase",
    "remove": "erase",
    "erase": "erase",
    "save": "save",
    # Italian
    "disegna": "draw",
    "crea": "draw",
    "aggiungi": "draw",
    "inserisci": "draw",
    "traccia": "draw",
    "modifica": "modify",
    "cambia": "modify",
    "sposta": "move",
    "ruota": "rotate",
    "scala": "scale",
    "ridimensiona": "scale",
    "elimina": "erase",
    "cancella": "erase",
    "rimuovi": "erase",
    "salva": "save",
    # Chinese
    "画": "draw",
    "绘制": "draw",
    "创建": "draw",
    "添加": "draw",
    "制作": "draw",
    "放置": "draw",
    "修改": "modify",
    "更改": "modify",
    "调整": "modify",
    "移动": "move",
    "旋转": "rotate",
    "缩放": "scale",
    "删除": "erase",
    "移除": "erase",
    "擦除": "erase",
    "保存": "save",
}


@dataclass
class ParsedCommand:
    """Parsed command result."""

    action: str
    shape: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    confidence: float = 0.0


class NLPProcessor:
    """Natural language processor for CAD commands."""

    # Regex patterns
    COORD_PATTERN = re.compile(r"\(?\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)?")
    NUMBER_PATTERN = re.compile(r"(-?\d+\.?\d*)")
    QUOTED_TEXT_PATTERN = re.compile(r'["\']([^"\']+)["\']|"([^"]+)"|「([^」]+)」')

    def __init__(self) -> None:
        """Initialize NLP processor."""
        self._color_pattern = self._build_color_pattern()

    def _build_color_pattern(self) -> re.Pattern[str]:
        """Build regex pattern for color matching."""
        # Sort by length (longest first) to match longer names first
        colors = sorted(COLOR_MAP.keys(), key=len, reverse=True)
        pattern = "|".join(re.escape(c) for c in colors)
        return re.compile(pattern, re.IGNORECASE)

    def extract_color(self, text: str) -> int | None:
        """
        Extract color from command text.

        Args:
            text: Command text to parse.

        Returns:
            CAD color index or None if no color found.
        """
        match = self._color_pattern.search(text)
        if match:
            color_name = match.group().lower()
            return COLOR_MAP.get(color_name)
        return None

    def extract_coordinates(self, text: str) -> list[tuple[float, float]]:
        """
        Extract coordinate pairs from text.

        Args:
            text: Text containing coordinates.

        Returns:
            List of (x, y) coordinate tuples.
        """
        coords = []
        for match in self.COORD_PATTERN.finditer(text):
            x = float(match.group(1))
            y = float(match.group(2))
            coords.append((x, y))
        return coords

    def extract_numbers(self, text: str) -> list[float]:
        """
        Extract all numbers from text.

        Args:
            text: Text containing numbers.

        Returns:
            List of extracted numbers.
        """
        return [float(m.group(1)) for m in self.NUMBER_PATTERN.finditer(text)]

    def extract_quoted_text(self, text: str) -> str | None:
        """
        Extract text within quotes.

        Args:
            text: Text to search.

        Returns:
            Quoted content or None.
        """
        match = self.QUOTED_TEXT_PATTERN.search(text)
        if match:
            # Return first non-None group
            return next((g for g in match.groups() if g), None)
        return None

    def identify_action(self, text: str) -> str | None:
        """
        Identify the action from command text.

        Args:
            text: Command text.

        Returns:
            Normalized action name or None.
        """
        text_lower = text.lower()
        for keyword, action in ACTION_KEYWORDS.items():
            if keyword.lower() in text_lower:
                return action
        return None

    def identify_shape(self, text: str) -> str | None:
        """
        Identify the shape from command text.

        Args:
            text: Command text.

        Returns:
            Normalized shape name or None.
        """
        text_lower = text.lower()
        for keyword, shape in SHAPE_KEYWORDS.items():
            if keyword.lower() in text_lower:
                return shape
        return None

    def parse_command(self, text: str) -> ParsedCommand:
        """
        Parse a natural language command.

        Args:
            text: Natural language command text.

        Returns:
            ParsedCommand with extracted information.
        """
        action = self.identify_action(text) or "draw"
        shape = self.identify_shape(text)

        if not shape:
            return ParsedCommand(
                action=action,
                raw_text=text,
                confidence=0.3,
            )

        # Dispatch to specific parser
        parser_method = getattr(self, f"_parse_{shape}", None)
        if parser_method:
            params = parser_method(text)
        else:
            params = self._parse_generic(text)

        # Add color if found
        color = self.extract_color(text)
        if color is not None:
            params["color"] = color

        return ParsedCommand(
            action=action,
            shape=shape,
            parameters=params,
            raw_text=text,
            confidence=0.8 if params else 0.5,
        )

    def _parse_generic(self, text: str) -> dict[str, Any]:
        """Generic parameter extraction."""
        params: dict[str, Any] = {}
        coords = self.extract_coordinates(text)
        if coords:
            params["points"] = coords
        return params

    def _parse_line(self, text: str) -> dict[str, Any]:
        """Parse line command parameters."""
        coords = self.extract_coordinates(text)

        if len(coords) >= 2:
            return {
                "start": coords[0],
                "end": coords[1],
            }

        # Default line
        logger.debug("Using default line parameters")
        return {
            "start": (0, 0),
            "end": (100, 100),
        }

    def _parse_circle(self, text: str) -> dict[str, Any]:
        """Parse circle command parameters."""
        coords = self.extract_coordinates(text)
        numbers = self.extract_numbers(text)

        params: dict[str, Any] = {}

        # Extract center
        if coords:
            params["center"] = coords[0]
        else:
            params["center"] = (0, 0)

        # Extract radius - look for explicit "radius" keyword
        radius_match = re.search(r"radius\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if not radius_match:
            radius_match = re.search(r"半径\s*[=:]?\s*(\d+\.?\d*)", text)

        if radius_match:
            params["radius"] = float(radius_match.group(1))
        elif coords and len(numbers) > 2:
            # Filter out coordinate numbers (2 per coordinate) and use remaining as radius
            coord_numbers = len(coords) * 2
            remaining_numbers = numbers[coord_numbers:]
            if remaining_numbers:
                params["radius"] = remaining_numbers[0]
            else:
                params["radius"] = 50
        elif not coords and numbers:
            # No coordinates, use first number as radius
            params["radius"] = numbers[0]
        else:
            params["radius"] = 50

        return params

    def _parse_arc(self, text: str) -> dict[str, Any]:
        """Parse arc command parameters."""
        coords = self.extract_coordinates(text)
        numbers = self.extract_numbers(text)

        params: dict[str, Any] = {
            "center": coords[0] if coords else (0, 0),
            "radius": 50,
            "start_angle": 0,
            "end_angle": 90,
        }

        # Look for specific parameters
        radius_match = re.search(r"radius\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if radius_match:
            params["radius"] = float(radius_match.group(1))

        start_match = re.search(r"start\s*(?:angle)?\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if start_match:
            params["start_angle"] = float(start_match.group(1))

        end_match = re.search(r"end\s*(?:angle)?\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if end_match:
            params["end_angle"] = float(end_match.group(1))

        # Chinese angle patterns
        start_cn = re.search(r"起始角\s*[=:]?\s*(\d+\.?\d*)", text)
        if start_cn:
            params["start_angle"] = float(start_cn.group(1))

        end_cn = re.search(r"终止角\s*[=:]?\s*(\d+\.?\d*)", text)
        if end_cn:
            params["end_angle"] = float(end_cn.group(1))

        return params

    def _parse_ellipse(self, text: str) -> dict[str, Any]:
        """Parse ellipse command parameters."""
        coords = self.extract_coordinates(text)
        numbers = self.extract_numbers(text)

        params: dict[str, Any] = {
            "center": coords[0] if coords else (0, 0),
            "major_axis": 100,
            "minor_axis": 50,
            "rotation": 0,
        }

        # Look for axis lengths
        major_match = re.search(r"major\s*(?:axis)?\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if major_match:
            params["major_axis"] = float(major_match.group(1))

        minor_match = re.search(r"minor\s*(?:axis)?\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if minor_match:
            params["minor_axis"] = float(minor_match.group(1))

        rotation_match = re.search(r"rotation\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if rotation_match:
            params["rotation"] = float(rotation_match.group(1))

        return params

    def _parse_rectangle(self, text: str) -> dict[str, Any]:
        """Parse rectangle command parameters."""
        coords = self.extract_coordinates(text)
        numbers = self.extract_numbers(text)

        if len(coords) >= 2:
            return {
                "corner1": coords[0],
                "corner2": coords[1],
            }

        # Try width/height
        width: float = 100.0
        height: float = 50.0

        width_match = re.search(r"width\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if width_match:
            width = float(width_match.group(1))

        height_match = re.search(r"height\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if height_match:
            height = float(height_match.group(1))

        # Chinese
        width_cn = re.search(r"宽\s*[=:]?\s*(\d+\.?\d*)", text)
        if width_cn:
            width = float(width_cn.group(1))

        height_cn = re.search(r"高\s*[=:]?\s*(\d+\.?\d*)", text)
        if height_cn:
            height = float(height_cn.group(1))

        return {
            "corner1": (0, 0),
            "corner2": (width, height),
        }

    def _parse_polyline(self, text: str) -> dict[str, Any]:
        """Parse polyline command parameters."""
        coords = self.extract_coordinates(text)

        # Check if should be closed
        closed = any(kw in text.lower() for kw in ["closed", "close", "闭合", "封闭"])

        if len(coords) >= 2:
            return {
                "points": coords,
                "closed": closed,
            }

        # Default polyline
        return {
            "points": [(0, 0), (50, 50), (100, 0)],
            "closed": closed,
        }

    def _parse_text(self, text: str) -> dict[str, Any]:
        """Parse text command parameters."""
        coords = self.extract_coordinates(text)
        content = self.extract_quoted_text(text) or "Text"

        params: dict[str, Any] = {
            "position": coords[0] if coords else (0, 0),
            "text": content,
            "height": 2.5,
            "rotation": 0,
        }

        # Look for height
        height_match = re.search(r"height\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if height_match:
            params["height"] = float(height_match.group(1))

        height_cn = re.search(r"高度\s*[=:]?\s*(\d+\.?\d*)", text)
        if height_cn:
            params["height"] = float(height_cn.group(1))

        # Look for rotation
        rotation_match = re.search(r"rotation\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if rotation_match:
            params["rotation"] = float(rotation_match.group(1))

        return params

    def _parse_dimension(self, text: str) -> dict[str, Any]:
        """Parse dimension command parameters."""
        coords = self.extract_coordinates(text)

        if len(coords) >= 2:
            # Calculate text position above midpoint
            mid_x = (coords[0][0] + coords[1][0]) / 2
            mid_y = (coords[0][1] + coords[1][1]) / 2 + 10

            return {
                "start": coords[0],
                "end": coords[1],
                "text_position": (mid_x, mid_y) if len(coords) < 3 else coords[2],
            }

        return {
            "start": (0, 0),
            "end": (100, 0),
            "text_position": (50, 10),
        }

    def _parse_hatch(self, text: str) -> dict[str, Any]:
        """Parse hatch command parameters."""
        coords = self.extract_coordinates(text)

        params: dict[str, Any] = {
            "boundary_points": coords if len(coords) >= 3 else [(0, 0), (100, 0), (100, 100), (0, 100)],
            "pattern_name": "SOLID",
            "pattern_scale": 1.0,
        }

        # Look for pattern name
        pattern_match = re.search(r"pattern\s*[=:]?\s*(\w+)", text, re.IGNORECASE)
        if pattern_match:
            params["pattern_name"] = pattern_match.group(1).upper()

        # Look for scale
        scale_match = re.search(r"scale\s*[=:]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if scale_match:
            params["pattern_scale"] = float(scale_match.group(1))

        return params

    def _parse_save(self, text: str) -> dict[str, Any]:
        """Parse save command parameters."""
        # Look for file path in quotes
        path = self.extract_quoted_text(text)

        # Or look for .dwg extension
        if not path:
            dwg_match = re.search(r"(\S+\.dwg)", text, re.IGNORECASE)
            if dwg_match:
                path = dwg_match.group(1)

        return {
            "file_path": path or "drawing.dwg",
        }
