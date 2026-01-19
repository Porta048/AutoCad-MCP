"""
AutoCAD COM Interface Controller.

Provides low-level access to AutoCAD, GstarCAD (GCAD), and ZWCAD
via Windows COM automation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autocad_mcp.config import CADConfig

logger = logging.getLogger(__name__)

# Valid lineweight values in AutoCAD (in hundredths of mm)
VALID_LINEWEIGHTS: frozenset[int] = frozenset({
    0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53,
    60, 70, 80, 90, 100, 106, 120, 140, 158, 200, 211
})

# CAD application COM ProgIDs
CAD_APP_IDS: dict[str, str] = {
    "AUTOCAD": "AutoCAD.Application",
    "GCAD": "GCAD.Application",
    "ZWCAD": "ZWCAD.Application",
}


@dataclass
class Point2D:
    """2D coordinate point."""

    x: float
    y: float

    def to_3d(self) -> tuple[float, float, float]:
        """Convert to 3D tuple with z=0."""
        return (self.x, self.y, 0.0)


@dataclass
class Point3D:
    """3D coordinate point."""

    x: float
    y: float
    z: float = 0.0

    def to_tuple(self) -> tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)


def _ensure_3d_point(point: tuple[float, ...]) -> tuple[float, float, float]:
    """Ensure point has 3 coordinates."""
    if len(point) == 2:
        return (point[0], point[1], 0.0)
    if len(point) >= 3:
        return (point[0], point[1], point[2])
    raise ValueError(f"Invalid point: {point}. Expected 2 or 3 coordinates.")


def validate_lineweight(value: int) -> int:
    """
    Validate and return a valid lineweight value.

    Args:
        value: Requested lineweight value.

    Returns:
        Valid lineweight (input if valid, 0 if invalid).
    """
    if value in VALID_LINEWEIGHTS:
        return value
    logger.warning("Invalid lineweight %d, using default 0", value)
    return 0


class CADController:
    """
    Controller for AutoCAD COM interface.

    Supports AutoCAD, GstarCAD, and ZWCAD through their COM automation APIs.
    """

    def __init__(self, config: CADConfig) -> None:
        """
        Initialize CAD controller.

        Args:
            config: CAD configuration settings.
        """
        self.config = config
        self.app: Any = None
        self.doc: Any = None
        self.model_space: Any = None
        self._com_initialized = False

    def _init_com(self) -> None:
        """Initialize COM library for current thread."""
        if self._com_initialized:
            return

        try:
            import pythoncom
            pythoncom.CoInitialize()
            self._com_initialized = True
            logger.debug("COM library initialized")
        except Exception as e:
            logger.warning("COM initialization warning: %s", e)

    def _cleanup_com(self) -> None:
        """Cleanup COM library."""
        if not self._com_initialized:
            return

        try:
            import pythoncom
            pythoncom.CoUninitialize()
            self._com_initialized = False
            logger.debug("COM library uninitialized")
        except Exception as e:
            logger.warning("COM cleanup warning: %s", e)

    def _create_variant_array(self, points: list[float]) -> Any:
        """
        Create a VARIANT array for CAD coordinates.

        Args:
            points: Flat list of coordinates [x1, y1, z1, x2, y2, z2, ...].

        Returns:
            COM VARIANT array suitable for CAD methods.
        """
        from array import array
        import pythoncom
        import win32com.client

        return win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            array("d", points)
        )

    def start(self) -> bool:
        """
        Start or connect to CAD application.

        Returns:
            True if connected successfully, False otherwise.
        """
        self._init_com()

        import win32com.client

        cad_type = self.config.type.upper()
        app_id = CAD_APP_IDS.get(cad_type)

        if not app_id:
            logger.error("Unsupported CAD type: %s", cad_type)
            return False

        # Try to connect to running instance first
        try:
            self.app = win32com.client.GetActiveObject(app_id)
            logger.info("Connected to running %s instance", cad_type)
        except Exception:
            # No running instance, start new one
            logger.info("Starting new %s instance...", cad_type)
            try:
                self.app = win32com.client.Dispatch(app_id)
                self.app.Visible = True
                logger.info("Waiting %ds for CAD startup...", self.config.startup_wait_time)
                time.sleep(self.config.startup_wait_time)
            except Exception as e:
                logger.error("Failed to start %s: %s", cad_type, e)
                return False

        # Get or create document
        try:
            if self.app.Documents.Count == 0:
                self.doc = self.app.Documents.Add()
                logger.info("Created new document")
            else:
                self.doc = self.app.ActiveDocument
                logger.info("Using active document: %s", self.doc.Name)

            self.model_space = self.doc.ModelSpace
            return True

        except Exception as e:
            logger.error("Failed to initialize document: %s", e)
            return False

    def is_running(self) -> bool:
        """Check if CAD application is running and accessible."""
        if self.app is None:
            return False

        try:
            # Try to access a property to verify connection
            _ = self.app.Visible
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close CAD connection and cleanup resources."""
        try:
            self.model_space = None
            self.doc = None
            self.app = None
            logger.info("CAD connection closed")
        except Exception as e:
            logger.warning("Error closing CAD connection: %s", e)
        finally:
            self._cleanup_com()

    def refresh_view(self) -> None:
        """Refresh the CAD viewport."""
        if self.doc:
            try:
                self.app.Update()
                self.doc.Regen(1)  # acActiveViewport
            except Exception as e:
                logger.warning("Failed to refresh view: %s", e)

    def create_layer(self, name: str, color: int = 7) -> bool:
        """
        Create a new layer.

        Args:
            name: Layer name.
            color: Layer color index (0-255).

        Returns:
            True if created successfully.
        """
        if not self.doc:
            return False

        try:
            # Check if layer exists
            layers = self.doc.Layers
            for i in range(layers.Count):
                if layers.Item(i).Name.lower() == name.lower():
                    logger.debug("Layer '%s' already exists", name)
                    return True

            # Create new layer
            layer = layers.Add(name)
            layer.Color = color
            logger.info("Created layer: %s", name)
            return True

        except Exception as e:
            logger.error("Failed to create layer '%s': %s", name, e)
            return False

    def _apply_entity_properties(
        self,
        entity: Any,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> None:
        """Apply common properties to an entity."""
        try:
            if layer:
                self.create_layer(layer)
                entity.Layer = layer

            if color is not None:
                entity.Color = color

            if lineweight is not None:
                entity.Lineweight = validate_lineweight(lineweight)

        except Exception as e:
            logger.warning("Failed to apply entity properties: %s", e)

    def draw_line(
        self,
        start: tuple[float, ...],
        end: tuple[float, ...],
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """
        Draw a line.

        Args:
            start: Start point (x, y) or (x, y, z).
            end: End point (x, y) or (x, y, z).
            layer: Optional layer name.
            color: Optional color index (0-255).
            lineweight: Optional lineweight value.

        Returns:
            Result dictionary with success status and entity info.
        """
        if not self.model_space:
            return {"success": False, "error": "CAD not initialized"}

        try:
            start_3d = _ensure_3d_point(start)
            end_3d = _ensure_3d_point(end)

            start_var = self._create_variant_array(list(start_3d))
            end_var = self._create_variant_array(list(end_3d))

            line = self.model_space.AddLine(start_var, end_var)
            self._apply_entity_properties(line, layer, color, lineweight)
            self.refresh_view()

            logger.info("Drew line from %s to %s", start_3d, end_3d)
            return {
                "success": True,
                "type": "line",
                "start": start_3d,
                "end": end_3d,
            }

        except Exception as e:
            logger.error("Failed to draw line: %s", e)
            return {"success": False, "error": str(e)}

    def draw_circle(
        self,
        center: tuple[float, ...],
        radius: float,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """
        Draw a circle.

        Args:
            center: Center point (x, y) or (x, y, z).
            radius: Circle radius.
            layer: Optional layer name.
            color: Optional color index (0-255).
            lineweight: Optional lineweight value.

        Returns:
            Result dictionary with success status and entity info.
        """
        if not self.model_space:
            return {"success": False, "error": "CAD not initialized"}

        try:
            center_3d = _ensure_3d_point(center)
            center_var = self._create_variant_array(list(center_3d))

            circle = self.model_space.AddCircle(center_var, radius)
            self._apply_entity_properties(circle, layer, color, lineweight)
            self.refresh_view()

            logger.info("Drew circle at %s with radius %s", center_3d, radius)
            return {
                "success": True,
                "type": "circle",
                "center": center_3d,
                "radius": radius,
            }

        except Exception as e:
            logger.error("Failed to draw circle: %s", e)
            return {"success": False, "error": str(e)}

    def draw_arc(
        self,
        center: tuple[float, ...],
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """
        Draw an arc.

        Args:
            center: Center point (x, y) or (x, y, z).
            radius: Arc radius.
            start_angle: Start angle in degrees.
            end_angle: End angle in degrees.
            layer: Optional layer name.
            color: Optional color index (0-255).
            lineweight: Optional lineweight value.

        Returns:
            Result dictionary with success status and entity info.
        """
        if not self.model_space:
            return {"success": False, "error": "CAD not initialized"}

        try:
            import math

            center_3d = _ensure_3d_point(center)
            center_var = self._create_variant_array(list(center_3d))

            # Convert degrees to radians
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)

            arc = self.model_space.AddArc(center_var, radius, start_rad, end_rad)
            self._apply_entity_properties(arc, layer, color, lineweight)
            self.refresh_view()

            logger.info(
                "Drew arc at %s with radius %s from %s° to %s°",
                center_3d, radius, start_angle, end_angle
            )
            return {
                "success": True,
                "type": "arc",
                "center": center_3d,
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle,
            }

        except Exception as e:
            logger.error("Failed to draw arc: %s", e)
            return {"success": False, "error": str(e)}

    def draw_ellipse(
        self,
        center: tuple[float, ...],
        major_axis: float,
        minor_axis: float,
        rotation: float = 0.0,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """
        Draw an ellipse.

        Args:
            center: Center point (x, y) or (x, y, z).
            major_axis: Length of major axis.
            minor_axis: Length of minor axis.
            rotation: Rotation angle in degrees.
            layer: Optional layer name.
            color: Optional color index (0-255).
            lineweight: Optional lineweight value.

        Returns:
            Result dictionary with success status and entity info.
        """
        if not self.model_space:
            return {"success": False, "error": "CAD not initialized"}

        try:
            import math

            center_3d = _ensure_3d_point(center)
            center_var = self._create_variant_array(list(center_3d))

            if major_axis <= 0:
                return {"success": False, "error": f"major_axis must be positive, got {major_axis}"}
            
            if minor_axis < 0:
                return {"success": False, "error": f"minor_axis must be non-negative, got {minor_axis}"}

            # Calculate major axis endpoint
            rotation_rad = math.radians(rotation)
            major_x = major_axis * math.cos(rotation_rad)
            major_y = major_axis * math.sin(rotation_rad)
            major_axis_var = self._create_variant_array([major_x, major_y, 0.0])

            # Ratio of minor to major axis (0-1)
            ratio = min(1.0, minor_axis / major_axis) if major_axis > 0 else 0.0

            ellipse = self.model_space.AddEllipse(center_var, major_axis_var, ratio)
            self._apply_entity_properties(ellipse, layer, color, lineweight)
            self.refresh_view()

            logger.info(
                "Drew ellipse at %s with axes %s/%s, rotation %s°",
                center_3d, major_axis, minor_axis, rotation
            )
            return {
                "success": True,
                "type": "ellipse",
                "center": center_3d,
                "major_axis": major_axis,
                "minor_axis": minor_axis,
                "rotation": rotation,
            }

        except Exception as e:
            logger.error("Failed to draw ellipse: %s", e)
            return {"success": False, "error": str(e)}

    def draw_polyline(
        self,
        points: list[tuple[float, ...]],
        closed: bool = False,
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """
        Draw a polyline.

        Args:
            points: List of points [(x1, y1), (x2, y2), ...].
            closed: Whether to close the polyline.
            layer: Optional layer name.
            color: Optional color index (0-255).
            lineweight: Optional lineweight value.

        Returns:
            Result dictionary with success status and entity info.
        """
        if not self.model_space:
            return {"success": False, "error": "CAD not initialized"}

        if len(points) < 2:
            return {"success": False, "error": "Polyline requires at least 2 points"}

        try:
            # Flatten points to array [x1, y1, z1, x2, y2, z2, ...]
            flat_points: list[float] = []
            points_3d = []
            for pt in points:
                pt_3d = _ensure_3d_point(pt)
                points_3d.append(pt_3d)
                flat_points.extend(pt_3d)

            points_var = self._create_variant_array(flat_points)

            polyline = self.model_space.AddPolyline(points_var)
            if closed:
                polyline.Closed = True
            self._apply_entity_properties(polyline, layer, color, lineweight)
            self.refresh_view()

            logger.info("Drew polyline with %d points, closed=%s", len(points), closed)
            return {
                "success": True,
                "type": "polyline",
                "points": points_3d,
                "closed": closed,
            }

        except Exception as e:
            logger.error("Failed to draw polyline: %s", e)
            return {"success": False, "error": str(e)}

    def draw_rectangle(
        self,
        corner1: tuple[float, ...],
        corner2: tuple[float, ...],
        layer: str | None = None,
        color: int | None = None,
        lineweight: int | None = None,
    ) -> dict[str, Any]:
        """
        Draw a rectangle.

        Args:
            corner1: First corner point (x, y) or (x, y, z).
            corner2: Opposite corner point (x, y) or (x, y, z).
            layer: Optional layer name.
            color: Optional color index (0-255).
            lineweight: Optional lineweight value.

        Returns:
            Result dictionary with success status and entity info.
        """
        c1 = _ensure_3d_point(corner1)
        c2 = _ensure_3d_point(corner2)

        # Create 4 corners
        points: list[tuple[float, ...]] = [
            (c1[0], c1[1], c1[2]),
            (c2[0], c1[1], c1[2]),
            (c2[0], c2[1], c2[2]),
            (c1[0], c2[1], c2[2]),
        ]

        result = self.draw_polyline(points, closed=True, layer=layer, color=color, lineweight=lineweight)
        if result["success"]:
            result["type"] = "rectangle"
            result["corner1"] = c1
            result["corner2"] = c2
            logger.info("Drew rectangle from %s to %s", c1, c2)
        return result

    def draw_text(
        self,
        position: tuple[float, ...],
        text: str,
        height: float = 2.5,
        rotation: float = 0.0,
        layer: str | None = None,
        color: int | None = None,
    ) -> dict[str, Any]:
        """
        Draw text.

        Args:
            position: Text insertion point (x, y) or (x, y, z).
            text: Text content.
            height: Text height.
            rotation: Rotation angle in degrees.
            layer: Optional layer name.
            color: Optional color index (0-255).

        Returns:
            Result dictionary with success status and entity info.
        """
        if not self.model_space:
            return {"success": False, "error": "CAD not initialized"}

        try:
            import math

            position_3d = _ensure_3d_point(position)
            position_var = self._create_variant_array(list(position_3d))

            text_entity = self.model_space.AddText(text, position_var, height)
            text_entity.Rotation = math.radians(rotation)
            self._apply_entity_properties(text_entity, layer, color)
            self.refresh_view()

            logger.info("Drew text '%s' at %s", text, position_3d)
            return {
                "success": True,
                "type": "text",
                "position": position_3d,
                "text": text,
                "height": height,
                "rotation": rotation,
            }

        except Exception as e:
            logger.error("Failed to draw text: %s", e)
            return {"success": False, "error": str(e)}

    def draw_hatch(
        self,
        boundary_points: list[tuple[float, ...]],
        pattern_name: str = "SOLID",
        pattern_scale: float = 1.0,
        layer: str | None = None,
        color: int | None = None,
    ) -> dict[str, Any]:
        """
        Draw a hatch pattern.

        Args:
            boundary_points: List of boundary points.
            pattern_name: Hatch pattern name (e.g., "SOLID", "ANSI31").
            pattern_scale: Pattern scale factor.
            layer: Optional layer name.
            color: Optional color index (0-255).

        Returns:
            Result dictionary with success status and entity info.
        """
        if not self.model_space:
            return {"success": False, "error": "CAD not initialized"}

        if len(boundary_points) < 3:
            return {"success": False, "error": "Hatch requires at least 3 boundary points"}

        try:
            # First create a closed polyline as boundary
            boundary_result = self.draw_polyline(boundary_points, closed=True)
            if not boundary_result["success"]:
                return boundary_result

            # Get the polyline reference immediately after creation
            polyline = self.model_space.Item(self.model_space.Count - 1)

            # Create hatch
            # PatternType: 0=User-defined (for SOLID), 1=Predefined, 2=Custom
            # Use 0 for SOLID and other user patterns, 1 for predefined patterns like ANSI31
            pattern_type = 1 if pattern_name.upper() != "SOLID" else 0
            hatch = self.model_space.AddHatch(pattern_type, pattern_name, True)
            hatch.PatternScale = pattern_scale

            # Create outer loop from polyline - must use proper COM array format
            import pythoncom
            import win32com.client
            outer_array = win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH,
                [polyline]
            )
            hatch.AppendOuterLoop(outer_array)

            hatch.Evaluate()
            self._apply_entity_properties(hatch, layer, color)
            self.refresh_view()

            logger.info("Drew hatch with pattern '%s' at scale %s", pattern_name, pattern_scale)
            return {
                "success": True,
                "type": "hatch",
                "pattern": pattern_name,
                "scale": pattern_scale,
            }

        except Exception as e:
            logger.error("Failed to draw hatch: %s", e)
            return {"success": False, "error": str(e)}

    def add_dimension(
        self,
        start: tuple[float, ...],
        end: tuple[float, ...],
        text_position: tuple[float, ...],
        layer: str | None = None,
        color: int | None = None,
    ) -> dict[str, Any]:
        """
        Add a linear dimension.

        Args:
            start: Start point of dimension.
            end: End point of dimension.
            text_position: Position for dimension text.
            layer: Optional layer name.
            color: Optional color index (0-255).

        Returns:
            Result dictionary with success status and entity info.
        """
        if not self.model_space:
            return {"success": False, "error": "CAD not initialized"}

        try:
            start_3d = _ensure_3d_point(start)
            end_3d = _ensure_3d_point(end)
            text_pos_3d = _ensure_3d_point(text_position)

            start_var = self._create_variant_array(list(start_3d))
            end_var = self._create_variant_array(list(end_3d))
            text_var = self._create_variant_array(list(text_pos_3d))

            # Calculate rotation angle (0 for horizontal, pi/2 for vertical)
            import math
            dx = end_3d[0] - start_3d[0]
            dy = end_3d[1] - start_3d[1]
            rotation = math.atan2(dy, dx)

            dim = self.model_space.AddDimAligned(start_var, end_var, text_var)
            self._apply_entity_properties(dim, layer, color)
            self.refresh_view()

            logger.info("Added dimension from %s to %s", start_3d, end_3d)
            return {
                "success": True,
                "type": "dimension",
                "start": start_3d,
                "end": end_3d,
                "text_position": text_pos_3d,
            }

        except Exception as e:
            logger.error("Failed to add dimension: %s", e)
            return {"success": False, "error": str(e)}

    def save_drawing(self, file_path: str) -> dict[str, Any]:
        """
        Save the current drawing.

        Args:
            file_path: Full path for the saved file.

        Returns:
            Result dictionary with success status.
        """
        if not self.doc:
            return {"success": False, "error": "No document to save"}

        try:
            from pathlib import Path

            # Ensure directory exists
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            self.doc.SaveAs(str(path.absolute()))
            logger.info("Saved drawing to %s", file_path)
            return {
                "success": True,
                "file_path": str(path.absolute()),
            }

        except Exception as e:
            logger.error("Failed to save drawing: %s", e)
            return {"success": False, "error": str(e)}

    def __del__(self) -> None:
        """Cleanup on destruction."""
        self.close()
