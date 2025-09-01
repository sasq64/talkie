"""Tests for the flexbox layout system"""

import pytest
from talkie.layout import flexbox_layout, Rectangle


class TestFlexboxLayout:
    """Test cases for the flexbox layout function"""

    def test_simple_horizontal_layout(self):
        """Test basic horizontal layout with fixed sizes"""
        xml = """<container size="400x100">
            <item1 size="100x50"/>
            <item2 size="200x60"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        # Find rectangles by name
        container = next(r for r in rectangles if r.name == "container")
        item1 = next(r for r in rectangles if r.name == "item1")
        item2 = next(r for r in rectangles if r.name == "item2")

        assert container == Rectangle("container", 0, 0, 400, 100)
        assert item1 == Rectangle("item1", 0, 0, 100, 50)
        assert item2 == Rectangle("item2", 100, 0, 200, 60)

    def test_simple_vertical_layout(self):
        """Test basic vertical layout with fixed sizes"""
        xml = """<container size="200x300" layout="vert">
            <item1 size="100x80"/>
            <item2 size="150x120"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        container = next(r for r in rectangles if r.name == "container")
        item1 = next(r for r in rectangles if r.name == "item1")
        item2 = next(r for r in rectangles if r.name == "item2")

        assert container == Rectangle("container", 0, 0, 200, 300)
        assert item1 == Rectangle("item1", 0, 0, 100, 80)
        assert item2 == Rectangle("item2", 0, 80, 150, 120)

    def test_flexible_sizing_horizontal(self):
        """Test flexible sizing in horizontal layout"""
        xml = """<container size="600x100">
            <fixed size="100x50"/>
            <flex/>
            <another size="200x60"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        fixed = next(r for r in rectangles if r.name == "fixed")
        flex = next(r for r in rectangles if r.name == "flex")
        another = next(r for r in rectangles if r.name == "another")

        assert fixed == Rectangle("fixed", 0, 0, 100, 50)
        assert flex == Rectangle("flex", 100, 0, 300, 100)  # Takes remaining space
        assert another == Rectangle("another", 400, 0, 200, 60)

    def test_flexible_sizing_vertical(self):
        """Test flexible sizing in vertical layout"""
        xml = """<container size="200x500" layout="vert">
            <fixed size="100x80"/>
            <flex/>
            <another size="150x120"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        fixed = next(r for r in rectangles if r.name == "fixed")
        flex = next(r for r in rectangles if r.name == "flex")
        another = next(r for r in rectangles if r.name == "another")

        assert fixed == Rectangle("fixed", 0, 0, 100, 80)
        assert flex == Rectangle("flex", 0, 80, 200, 300)  # Takes remaining space
        assert another == Rectangle("another", 0, 380, 150, 120)

    def test_percentage_sizes(self):
        """Test percentage-based sizing"""
        xml = """<container size="400x200">
            <half size="50%x100%"/>
            <quarter size="25%x50%"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        half = next(r for r in rectangles if r.name == "half")
        quarter = next(r for r in rectangles if r.name == "quarter")

        assert half == Rectangle("half", 0, 0, 200, 200)  # 50% of 400, 100% of 200
        assert quarter == Rectangle(
            "quarter", 200, 0, 100, 100
        )  # 25% of 400, 50% of 200

    def test_partial_sizes(self):
        """Test partial size specifications (width-only, height-only)"""
        xml = """<container size="300x150">
            <width_only size="100x"/>
            <height_only size="x75"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        width_only = next(r for r in rectangles if r.name == "width_only")
        height_only = next(r for r in rectangles if r.name == "height_only")

        assert width_only == Rectangle(
            "width_only", 0, 0, 100, 150
        )  # Width fixed, height fills
        assert height_only == Rectangle(
            "height_only", 100, 0, 200, 75
        )  # Height fixed, width fills

    def test_borders(self):
        """Test border handling"""
        xml = """<container size="200x100" border="10">
            <child1 size="50x30"/>
            <child2 size="60x40"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        container = next(r for r in rectangles if r.name == "container")
        child1 = next(r for r in rectangles if r.name == "child1")
        child2 = next(r for r in rectangles if r.name == "child2")

        assert container == Rectangle("container", 0, 0, 200, 100)
        # Children should be offset by border
        assert child1 == Rectangle("child1", 10, 10, 50, 30)
        assert child2 == Rectangle("child2", 60, 10, 60, 40)

    def test_gaps_horizontal(self):
        """Test gap handling in horizontal layout"""
        xml = """<container size="350x100" gap="20">
            <item1 size="100x50"/>
            <item2 size="100x60"/>
            <item3 size="100x40"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        item1 = next(r for r in rectangles if r.name == "item1")
        item2 = next(r for r in rectangles if r.name == "item2")
        item3 = next(r for r in rectangles if r.name == "item3")

        assert item1 == Rectangle("item1", 0, 0, 100, 50)
        assert item2 == Rectangle("item2", 120, 0, 100, 60)  # 100 + 20 gap
        assert item3 == Rectangle("item3", 240, 0, 100, 40)  # 220 + 20 gap

    def test_gaps_vertical(self):
        """Test gap handling in vertical layout"""
        xml = """<container size="200x350" layout="vert" gap="15">
            <item1 size="100x80"/>
            <item2 size="150x90"/>
            <item3 size="120x100"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        item1 = next(r for r in rectangles if r.name == "item1")
        item2 = next(r for r in rectangles if r.name == "item2")
        item3 = next(r for r in rectangles if r.name == "item3")

        assert item1 == Rectangle("item1", 0, 0, 100, 80)
        assert item2 == Rectangle("item2", 0, 95, 150, 90)  # 80 + 15 gap
        assert item3 == Rectangle("item3", 0, 200, 120, 100)  # 185 + 15 gap

    def test_borders_and_gaps_combined(self):
        """Test borders and gaps working together"""
        xml = """<container size="300x100" border="5" gap="10">
            <item1 size="80x60"/>
            <item2 size="90x70"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        item1 = next(r for r in rectangles if r.name == "item1")
        item2 = next(r for r in rectangles if r.name == "item2")

        # Children offset by border, with gap between them
        assert item1 == Rectangle("item1", 5, 5, 80, 60)
        assert item2 == Rectangle("item2", 95, 5, 90, 70)  # 5 + 80 + 10 = 95

    def test_nested_layouts(self):
        """Test nested layout containers"""
        xml = """<root size="400x200" layout="vert">
            <header size="400x50">
                <logo size="50x50"/>
                <title/>
            </header>
            <content>
                <sidebar size="100x150"/>
                <main/>
            </content>
        </root>"""

        rectangles = flexbox_layout(xml)

        header = next(r for r in rectangles if r.name == "header")
        logo = next(r for r in rectangles if r.name == "logo")
        title = next(r for r in rectangles if r.name == "title")
        content = next(r for r in rectangles if r.name == "content")
        sidebar = next(r for r in rectangles if r.name == "sidebar")
        main = next(r for r in rectangles if r.name == "main")

        assert header == Rectangle("header", 0, 0, 400, 50)
        assert logo == Rectangle("logo", 0, 0, 50, 50)
        assert title == Rectangle("title", 50, 0, 350, 50)  # Flexible width
        assert content == Rectangle("content", 0, 50, 400, 150)  # Flexible height
        assert sidebar == Rectangle("sidebar", 0, 50, 100, 150)
        assert main == Rectangle("main", 100, 50, 300, 150)  # Flexible width

    def test_min_size_vs_flexible_behavior(self):
        """Test difference between containers with fixed content vs truly flexible"""
        xml = """<root size="400x300" layout="vert">
            <toolbar>
                <button size="32x32"/>
            </toolbar>
            <content>
                <flex_child/>
            </content>
        </root>"""

        rectangles = flexbox_layout(xml)

        toolbar = next(r for r in rectangles if r.name == "toolbar")
        content = next(r for r in rectangles if r.name == "content")
        button = next(r for r in rectangles if r.name == "button")
        flex_child = next(r for r in rectangles if r.name == "flex_child")

        # Toolbar should size to fit its button (minimum size)
        assert toolbar.height == 32  # Just enough for button
        # Content should take remaining space
        assert content.height == 268  # 300 - 32
        assert button == Rectangle("button", 0, 0, 32, 32)
        assert flex_child == Rectangle("flex_child", 0, 32, 400, 268)

    def test_multiple_flex_children(self):
        """Test space distribution among multiple flexible children"""
        xml = """<container size="600x100">
            <fixed size="100x50"/>
            <flex1/>
            <flex2/>
            <flex3/>
        </container>"""

        rectangles = flexbox_layout(xml)

        fixed = next(r for r in rectangles if r.name == "fixed")
        flex1 = next(r for r in rectangles if r.name == "flex1")
        flex2 = next(r for r in rectangles if r.name == "flex2")
        flex3 = next(r for r in rectangles if r.name == "flex3")

        # Each flex child gets (600 - 100) / 3 = 166 pixels (with rounding)
        assert fixed == Rectangle("fixed", 0, 0, 100, 50)
        assert flex1 == Rectangle("flex1", 100, 0, 166, 100)
        assert flex2 == Rectangle("flex2", 266, 0, 166, 100)
        assert flex3 == Rectangle("flex3", 432, 0, 166, 100)

    def test_empty_container(self):
        """Test container with no children"""
        xml = """<empty size="200x100"/>"""

        rectangles = flexbox_layout(xml)

        assert len(rectangles) == 1
        assert rectangles[0] == Rectangle("empty", 0, 0, 200, 100)

    def test_zero_border_and_gap(self):
        """Test explicit zero border and gap"""
        xml = """<container size="200x100" border="0" gap="0">
            <child1 size="100x50"/>
            <child2 size="100x50"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        child1 = next(r for r in rectangles if r.name == "child1")
        child2 = next(r for r in rectangles if r.name == "child2")

        assert child1 == Rectangle("child1", 0, 0, 100, 50)
        assert child2 == Rectangle("child2", 100, 0, 100, 50)

    def test_example_from_requirements(self):
        """Test the original example from the requirements"""
        xml = """<window size="1280x720" layout="vert">
         <toolbar layout="horiz" border="5">
           <button0 size="32x32"/>
           <button1 size="32x32"/>
         </toolbar>
         <area border="5" gap="2">
           <content0/>
           <content1/>
         </area>
        </window>"""

        rectangles = flexbox_layout(xml)

        window = next(r for r in rectangles if r.name == "window")
        toolbar = next(r for r in rectangles if r.name == "toolbar")
        area = next(r for r in rectangles if r.name == "area")
        button0 = next(r for r in rectangles if r.name == "button0")
        button1 = next(r for r in rectangles if r.name == "button1")
        content0 = next(r for r in rectangles if r.name == "content0")
        content1 = next(r for r in rectangles if r.name == "content1")

        # Verify expected behavior
        assert window == Rectangle("window", 0, 0, 1280, 720)
        assert toolbar == Rectangle(
            "toolbar", 0, 0, 1280, 42
        )  # Sized to fit buttons + border
        assert area == Rectangle("area", 0, 42, 1280, 678)  # Takes remaining space
        assert button0 == Rectangle("button0", 5, 5, 32, 32)
        assert button1 == Rectangle("button1", 37, 5, 32, 32)
        assert content0 == Rectangle("content0", 5, 47, 634, 668)
        assert content1 == Rectangle("content1", 641, 47, 634, 668)

    def test_mixed_percentage_and_pixel_sizes(self):
        """Test mixing percentage and pixel sizes"""
        xml = """<container size="400x200">
            <fixed size="100x50"/>
            <percent size="25%x50%"/>
            <flex/>
        </container>"""

        rectangles = flexbox_layout(xml)

        fixed = next(r for r in rectangles if r.name == "fixed")
        percent = next(r for r in rectangles if r.name == "percent")
        flex = next(r for r in rectangles if r.name == "flex")

        assert fixed == Rectangle("fixed", 0, 0, 100, 50)
        assert percent == Rectangle(
            "percent", 100, 0, 100, 100
        )  # 25% of 400, 50% of 200
        assert flex == Rectangle("flex", 200, 0, 200, 200)  # Remaining space

    def test_large_border_edge_case(self):
        """Test edge case where border is larger than container"""
        xml = """<container size="50x50" border="30">
            <child size="10x10"/>
        </container>"""

        rectangles = flexbox_layout(xml)

        container = next(r for r in rectangles if r.name == "container")
        # Child should not appear if content area is too small
        children = [r for r in rectangles if r.name == "child"]

        assert container == Rectangle("container", 0, 0, 50, 50)
        assert (
            len(children) == 0
        )  # Child should not be rendered due to insufficient space

    def test_flexible_container_with_mixed_children(self):
        """Test container with both flexible and fixed children stays flexible"""
        xml = """<window layout="vert" size="1280x1024">
          <border layout="vert" border="20">
            <main/>
            <pane>
              <input size="x48"/>
            </pane>
          </border>
        </window>"""

        rectangles = flexbox_layout(xml)

        window = next(r for r in rectangles if r.name == "window")
        border = next(r for r in rectangles if r.name == "border")
        main = next(r for r in rectangles if r.name == "main")
        pane = next(r for r in rectangles if r.name == "pane")
        input_elem = next(r for r in rectangles if r.name == "input")

        # Border should take full window size (flexible)
        assert window == Rectangle("window", 0, 0, 1280, 1024)
        assert border == Rectangle("border", 0, 0, 1280, 1024)

        # Main should take remaining space after pane
        assert main == Rectangle(
            "main", 20, 20, 1240, 936
        )  # 1024 - 40 (border) - 48 (pane) = 936

        # Pane should be minimum size for input
        assert pane == Rectangle("pane", 20, 956, 1240, 48)  # 20 + 936 = 956
        assert input_elem == Rectangle("input", 20, 956, 1240, 48)
