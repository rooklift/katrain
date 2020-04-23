import json
import math
import random
import re

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import *
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput


class DarkLabel(Label):
    pass


class ScaledLightLabel(DarkLabel):
    pass


class StyledButton(Button):
    button_color = ListProperty([])
    button_color_down = ListProperty([])
    radius = ListProperty((0,))


class StyledToggleButton(StyledButton, ToggleButtonBehavior):
    value = StringProperty("")


class StyledSpinner(Spinner):
    pass


class ToggleButtonContainer(GridLayout):
    __events__ = ("on_selection",)

    options = ListProperty([])
    labels = ListProperty([])
    selected = StringProperty("")
    group = StringProperty(None)
    autosize = BooleanProperty(True)
    spacing = ListProperty((1, 1))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._build, 0)

    def on_selection(self, *args):
        pass

    def _build(self, _dt):
        self.rows = 1
        self.cols = len(self.options)
        self.group = self.group or str(random.random())
        if not self.selected and self.options:
            self.selected = self.options[0]
        if len(self.labels) < len(self.options):
            self.labels += self.options[len(self.labels) + 1 :]

        def state_handler(btn, *args):
            self.dispatch("on_selection")
            btn.state = "down"  # no toggle

        for i, opt in enumerate(self.options):
            state = "down" if opt == self.selected else "normal"
            self.add_widget(StyledToggleButton(group=self.group, text=self.labels[i], value=opt, state=state, on_press=state_handler))
        Clock.schedule_once(self._size, 0)

    def _size(self, _dt):
        if self.autosize:
            for tb in self.children:
                tb.size_hint = (tb.texture_size[0] + 25, 1)

    @property
    def value(self):
        for tb in self.children:
            if tb.state == "down":
                return tb.value
        if self.options:
            return self.options[0]


class BaseCircleWithText(DarkLabel):
    radius = NumericProperty(0.48)


class LabelledTextInput(TextInput):
    input_property = StringProperty("")
    multiline = BooleanProperty(False)

    @property
    def input_value(self):
        return self.text


class LabelledObjectInputArea(LabelledTextInput):
    multiline = BooleanProperty(True)

    @property
    def input_value(self):
        return json.loads(self.text.replace("'", '"').replace("True", "true").replace("False", "false"))


class LabelledCheckBox(CheckBox):
    input_property = StringProperty("")

    def __init__(self, text=None, **kwargs):
        if text is not None:
            kwargs["active"] = bool(text)
        super().__init__(**kwargs)

    @property
    def input_value(self):
        return bool(self.active)


class LabelledSpinner(StyledSpinner):
    input_property = StringProperty("")

    @property
    def input_value(self):
        return self.text


class LabelledFloatInput(LabelledTextInput):
    signed = BooleanProperty(True)
    pat = re.compile("[^0-9-]")

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if "." in self.text:
            s = re.sub(pat, "", substring)
        else:
            s = ".".join([re.sub(pat, "", s) for s in substring.split(".", 1)])
        r = super().insert_text(s, from_undo=from_undo)
        if not self.signed and "-" in self.text:
            self.text = self.text.replace("-", "")
        elif self.text and "-" in self.text[1:]:
            self.text = self.text[0] + self.text[1:].replace("-", "")
        return r

    @property
    def input_value(self):
        return float(self.text)


class LabelledIntInput(LabelledTextInput):
    pat = re.compile("[^0-9]")

    def insert_text(self, substring, from_undo=False):
        return super().insert_text(re.sub(self.pat, "", substring), from_undo=from_undo)

    @property
    def input_value(self):
        return int(self.text)


class CensorableLabel(BoxLayout):
    @property
    def text(self):
        return self.value.text


class ScoreGraph(Label):
    nodes = ListProperty([])
    line_points = ListProperty([])
    dot_pos = ListProperty([0, 0])
    highlighted_index = NumericProperty(None)
    min_scale = NumericProperty(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.on_size, 0)

    def initialize_from_game(self, root):
        self.nodes = [root]
        node = root
        while node.children:
            node = node.children[0]
            self.nodes.append(node)
        self.highlighted_index = 0

    def on_size(self, *args):
        nodes = self.nodes
        if nodes:
            values = [n.score if n and n.score else math.nan for n in nodes]
            nn_values = [n.score for n in nodes if n and n.score]
            val_range = min(nn_values or [0]), max(nn_values or [0])
            scale = math.ceil(max(self.min_scale, max(-val_range[0], val_range[1]) * 1.05))

            xscale = self.width * 0.9 / max(len(values) - 1, 15)
            available_height = self.height * (1 - 2 * self.marginy)
            line_points = [[self.pos[0] + self.marginx * self.width + i * xscale, self.pos[1] + available_height / 2 * (1 + val / scale)] for i, val in enumerate(values)]
            self.line_points = sum(line_points, [])
            self.range_label_top.text = f"B+{scale:.0f}"
            self.range_label_bottom.text = f"W+{scale:.0f}"

            if self.highlighted_index is not None:
                self.highlighted_index = min(self.highlighted_index, len(values) - 1)
                dot_point = line_points[self.highlighted_index]
                if math.isnan(dot_point[1]):
                    dot_point[1] = self.pos[1] + available_height / 2 * (1 + (nn_values or [0])[-1] / scale)
                self.dot_pos = [c - self.highlight_size / 2 for c in dot_point]

    def update_value(self, node):
        self.highlighted_index = index = node.depth
        self.nodes.extend([None] * max(0, index - (len(self.nodes) - 1)))
        self.nodes[index] = node
        if index + 1 < len(self.nodes) and (node is None or self.nodes[index + 1] not in node.children):
            self.nodes = self.nodes[: index + 1]  # on branch switching, don't show history from other branch
        if index == len(self.nodes) - 1:  # possibly just switched branch
            while node.children:  # add children back
                node = node.children[0]
                self.nodes.append(node)
        self.on_size()


def draw_text(pos, text, **kw):
    label = CoreLabel(text=text, bold=True, **kw)
    label.refresh()
    Rectangle(texture=label.texture, pos=(pos[0] - label.texture.size[0] / 2, pos[1] - label.texture.size[1] / 2), size=label.texture.size)


def draw_circle(pos, r, col):
    Color(*col)
    Ellipse(pos=(pos[0] - r, pos[1] - r), size=(2 * r, 2 * r))
