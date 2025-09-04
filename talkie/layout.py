"""Flexbox-like layout system for XML UI definitions"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class Rectangle:
    """Final positioned rectangle for a UI element"""

    name: str
    x: int
    y: int
    width: int
    height: int


@dataclass
class LayoutNode:
    """Intermediate representation of a UI element before layout"""

    name: str
    size: tuple[str | None, str | None]  # (width_spec, height_spec)
    layout: str = "horiz"  # "horiz" or "vert"
    border: int = 0
    gap: int = 0
    children: list["LayoutNode"] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)


def parse_xml_to_tree(xml: str) -> LayoutNode:
    """Parse XML string into intermediate LayoutNode tree"""
    root = ET.fromstring(xml.strip())
    return _parse_element_to_node(root)


def _parse_element_to_node(element: ET.Element) -> LayoutNode:
    """Convert XML element to LayoutNode recursively"""
    # Parse size attribute
    size_str = element.get("size", "")
    width_spec, height_spec = _parse_size_spec(size_str)

    # Parse other layout attributes
    layout = element.get("layout", "horiz")
    border = int(element.get("border", "0"))
    gap = int(element.get("gap", "0"))

    # Parse children
    children = [_parse_element_to_node(child) for child in element]

    # Store all attributes for future extensibility
    attributes = dict(element.attrib)

    return LayoutNode(
        name=element.tag,
        size=(width_spec, height_spec),
        layout=layout,
        border=border,
        gap=gap,
        children=children,
        attributes=attributes,
    )


def _parse_size_spec(size_str: str) -> tuple[str | None, str | None]:
    """Parse size specification like '1280x720', '32x', 'x32', '50%x100%'"""
    if not size_str:
        return None, None

    if "x" not in size_str:
        # Invalid format, treat as no size specified
        return None, None

    parts = size_str.split("x", 1)
    width_spec = parts[0] if parts[0] else None
    height_spec = parts[1] if len(parts) > 1 and parts[1] else None

    return width_spec, height_spec


def layout_tree_to_rectangles(
    root: LayoutNode, container_size: tuple[int, int]
) -> list[Rectangle]:
    """Convert LayoutNode tree to positioned Rectangle list"""
    rectangles: list[Rectangle] = []
    _layout_node_recursive(root, 0, 0, container_size[0], container_size[1], rectangles)
    return rectangles


def _layout_node_recursive(
    node: LayoutNode,
    x: int,
    y: int,
    width: int,
    height: int,
    rectangles: list[Rectangle],
) -> None:
    """Recursively layout a node and its children"""
    # Add this node's rectangle
    rectangles.append(Rectangle(node.name, x, y, width, height))

    if not node.children:
        return

    # Calculate content area (inside border)
    content_x = x + node.border
    content_y = y + node.border
    content_width = width - 2 * node.border
    content_height = height - 2 * node.border

    if content_width <= 0 or content_height <= 0:
        return

    # Calculate child sizes and positions
    if node.layout == "vert":
        _layout_children_vertical(
            node, content_x, content_y, content_width, content_height, rectangles
        )
    else:  # "horiz"
        _layout_children_horizontal(
            node, content_x, content_y, content_width, content_height, rectangles
        )


def _layout_children_horizontal(
    node: LayoutNode,
    content_x: int,
    content_y: int,
    content_width: int,
    content_height: int,
    rectangles: list[Rectangle],
) -> None:
    """Layout children horizontally"""
    children = node.children
    if not children:
        return

    # Calculate total gap space
    total_gap = node.gap * (len(children) - 1) if len(children) > 1 else 0

    # Parse child widths
    child_widths: list[int | None] = []
    fixed_width_total = 0
    flex_count = 0

    for child in children:
        width = _parse_dimension(child.size[0], content_width)
        if width is None:
            flex_count += 1
            child_widths.append(None)
        else:
            child_widths.append(width)
            fixed_width_total += width

    # Distribute remaining width to flex children
    remaining_width = content_width - fixed_width_total - total_gap
    flex_width = remaining_width // flex_count if flex_count > 0 else 0

    # Position children
    current_x = content_x
    for i, child in enumerate(children):
        # Calculate child dimensions
        child_width = child_widths[i] if child_widths[i] is not None else flex_width
        child_height = _parse_dimension(child.size[1], content_height) or content_height

        # Recursively layout child
        _layout_node_recursive(
            child, current_x, content_y, child_width, child_height, rectangles
        )

        # Advance position
        current_x += child_width
        if i < len(children) - 1:  # Add gap except after last child
            current_x += node.gap


def _layout_children_vertical(
    node: LayoutNode,
    content_x: int,
    content_y: int,
    content_width: int,
    content_height: int,
    rectangles: list[Rectangle],
) -> None:
    """Layout children vertically"""
    children = node.children
    if not children:
        return

    # Calculate total gap space
    total_gap = node.gap * (len(children) - 1) if len(children) > 1 else 0

    # Parse child heights and calculate minimum required sizes
    child_heights = []
    fixed_height_total = 0
    flex_count = 0

    for child in children:
        height = _parse_dimension(child.size[1], content_height)
        if height is None:
            # For flex children, check if they need minimum space or can be flexible
            min_height = _calculate_min_height(child)
            if min_height > 0 and _requires_minimum_height(child):
                # Use minimum size for children that require it
                child_heights.append(min_height)
                fixed_height_total += min_height
            else:
                # Truly flexible children
                flex_count += 1
                child_heights.append(None)
        else:
            child_heights.append(height)
            fixed_height_total += height

    # Distribute remaining height to flex children
    remaining_height = content_height - fixed_height_total - total_gap
    flex_extra = (
        remaining_height // flex_count if flex_count > 0 and remaining_height > 0 else 0
    )

    # Position children
    current_y = content_y
    for i, child in enumerate(children):
        # Calculate child dimensions
        child_width = _parse_dimension(child.size[0], content_width) or content_width

        if child_heights[i] is None:
            # This is a truly flexible child
            child_height = flex_extra
        else:
            # This is a fixed or minimum size child
            child_height = child_heights[i]

        # Recursively layout child
        _layout_node_recursive(
            child, content_x, current_y, child_width, child_height, rectangles
        )

        # Advance position
        current_y += child_height
        if i < len(children) - 1:  # Add gap except after last child
            current_y += node.gap


def _requires_minimum_height(node: LayoutNode) -> bool:
    """Check if a node requires minimum height and cannot be flexible"""
    if not node.children:
        return False

    if node.layout == "horiz":
        # Horizontal layout: height is determined by tallest child
        # Only requires minimum if ALL children have fixed heights
        for child in node.children:
            if child.size[1] is None and not _requires_minimum_height(child):
                # Has at least one flexible child, so can be flexible
                return False
        return True
    else:
        # Vertical layout: height is sum of children
        # Only requires minimum if ALL space is taken by fixed-height children
        has_flex_child = False
        for child in node.children:
            if child.size[1] is None and not _requires_minimum_height(child):
                has_flex_child = True
                break
        # If has flexible children, the container can also be flexible
        return not has_flex_child


def _has_fixed_size_content(node: LayoutNode) -> bool:
    """Check if a node has any fixed-size content that determines its minimum size"""
    if not node.children:
        return False

    # Check if any child has a fixed size
    for child in node.children:
        if child.size[0] is not None or child.size[1] is not None:
            return True
        # Recursively check children
        if _has_fixed_size_content(child):
            return True

    return False


def _calculate_min_height(node: LayoutNode) -> int:
    """Calculate minimum height needed for a node based on its content"""
    if not node.children:
        # If no children, only need border space
        return node.border * 2

    if node.layout == "vert":
        # Vertical layout: sum of children heights plus gaps and border
        total_height = 0
        for child in node.children:
            child_height = _parse_dimension(child.size[1], 1000)
            if child_height is not None:
                total_height += child_height
            else:
                # For flex children, use their minimum height
                total_height += _calculate_min_height(child)

        # Add gaps
        if len(node.children) > 1:
            total_height += node.gap * (len(node.children) - 1)

        # Add border
        total_height += node.border * 2

        return total_height
    else:
        # Horizontal layout: max child height plus border
        max_height = 0
        for child in node.children:
            child_height = _parse_dimension(child.size[1], 1000)
            if child_height is not None:
                max_height = max(max_height, child_height)
            else:
                # For flex children, use their minimum height
                child_min = _calculate_min_height(child)
                max_height = max(max_height, child_min)

        return max_height + node.border * 2


def _parse_dimension(spec: str | None, container_size: int) -> int | None:
    """Parse dimension specification (pixels, percentage, or None for flex)"""
    if not spec:
        return None

    if spec.endswith("%"):
        # Percentage
        percent = float(spec[:-1])
        return int(container_size * percent / 100)
    else:
        # Assume pixels
        return int(spec)


def find_node_by_name(root: LayoutNode, name: str) -> LayoutNode | None:
    """Find a LayoutNode by name in the tree starting from root"""
    if root.name == name:
        return root

    for child in root.children:
        result = find_node_by_name(child, name)
        if result is not None:
            return result

    return None


@dataclass
class Layout:
    """Layout manager that owns the root node and provides layout operations"""

    root: LayoutNode

    def __init__(self, xml: str):
        self.root = parse_xml_to_tree(xml)

    def layout(
        self, width: int | None = None, height: int | None = None
    ) -> list[Rectangle]:
        """Calculate layout and return positioned rectangles"""
        # Get root container size from the root node
        root_width = width or _parse_dimension(self.root.size[0], 0) or 800
        root_height = height or _parse_dimension(self.root.size[1], 0) or 600

        return layout_tree_to_rectangles(self.root, (root_width, root_height))

    def set_size(
        self, name: str, width: int | None = None, height: int | None = None
    ) -> None:
        """Set the size of a node by name"""
        node = find_node_by_name(self.root, name)
        if node is not None:
            width_spec = str(width) if width is not None else None
            height_spec = str(height) if height is not None else None
            node.size = (width_spec, height_spec)

    def find(self, name: str) -> LayoutNode | None:
        """Find a node by name in the layout tree"""
        return find_node_by_name(self.root, name)


def flexbox_layout(xml: str) -> list[Rectangle]:
    """Main function: parse XML and produce positioned rectangles"""
    layout = Layout(xml)
    return layout.layout()
