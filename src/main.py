import math
import os
import platform
import subprocess
from datetime import datetime

import toga
from PIL import Image
from rectpack import newPacker
from toga.constants import COLUMN, HIDDEN, ROW, VISIBLE
from toga.style import Pack


class PhotoArranger(toga.App):
    def startup(self):
        self.images = []
        self.file_paths = []
        self.scale_factors = []
        self.area_percentages = []
        self.last_output_path = None
        self.photo_rows = []
        self.current_ratio = math.sqrt(2)  # Default A Series
        self.paper_ratios = {
            "A Series": math.sqrt(2),
            "B Series": 1.0 / math.sqrt(2),
            "C Series": 1.0 / math.sqrt(2),
            "Letter": 11.0 / 8.5,
        }

        # Status text field for wrapping
        self.status = toga.TextField(
            value="No photos selected yet!",
            readonly=True,
            multiline=True,
            style=Pack(margin=5, height=60, flex=1),
        )

        # CMYK switch
        self.cmyk_mode = toga.Switch(
            "CMYK color profile - use it for printing (saves as TIFF)",
            value=False,
            style=Pack(margin=5),
        )

        # Padding switch and input
        self.padding_enabled = toga.Switch(
            "White border between photos for easier cutting",
            value=False,
            on_change=self.on_padding_toggle,
            style=Pack(margin=5),
        )
        self.padding_size = toga.TextInput(value="10", readonly=True, style=Pack(width=150))

        # Paper ratio selection
        paper_options = ["A Series", "B Series", "C Series", "Letter", "Custom ratio"]
        self.paper_ratio_selection = toga.Selection(
            items=paper_options,
            value="A Series",
            on_change=self.update_ratio,
            style=Pack(width=140, margin=5),
        )

        # Custom ratio input
        self.custom_ratio = toga.TextInput(
            placeholder="Custom Ratio (e.g., 5:7 or 1.4286)",
            on_change=self.on_custom_ratio_change,
            style=Pack(width=150, visibility=HIDDEN),
        )

        # Photo container
        self.photo_container = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=5))
        self.photo_scroll = toga.ScrollContainer(
            content=self.photo_container, horizontal=False, style=Pack(flex=1)
        )

        # Buttons
        self.add_button = toga.Button("Add Photos", on_press=self.handle_upload, style=Pack(margin=5))
        self.delete_button = toga.Button("Delete Selected", on_press=self.delete_selected, style=Pack(margin=5))
        self.increase_button = toga.Button("Zoom In", on_press=self.increase_size, style=Pack(margin=5))
        self.decrease_button = toga.Button("Zoom Out", on_press=self.decrease_size, style=Pack(margin=5))
        self.select_all_button = toga.Button("Select All", on_press=self.select_all, style=Pack(margin=5))
        self.deselect_all_button = toga.Button("Deselect All", on_press=self.deselect_all, style=Pack(margin=5))
        self.invert_button = toga.Button("Invert Selection", on_press=self.invert_selection, style=Pack(margin=5))
        self.clear_button = toga.Button("Clear All", on_press=self.clear_selection, style=Pack(margin=5))

        buttons_box = toga.Box(
            children=[
                self.add_button,
                self.delete_button,
                self.increase_button,
                self.decrease_button,
                self.select_all_button,
                self.deselect_all_button,
                self.invert_button,
                self.clear_button,
            ],
            style=Pack(direction=ROW, margin=5, justify_content="center"),
        )

        # Generate button
        self.generate_button = toga.Button(
            "Arrange Photos into Canvas", on_press=self.generate_layout, style=Pack(margin=5)
        )

        # Collage preview and buttons
        self.collage_preview = toga.ImageView(style=Pack(flex=1, margin=5))
        self.open_preview_button = toga.Button(
            "Open Preview", on_press=self.open_collage, style=Pack(width=120, margin=5), enabled=False
        )
        self.print_button = toga.Button(
            "Print Collage", on_press=self.print_collage, style=Pack(width=120, margin=5), enabled=False
        )
        preview_buttons_box = toga.Box(
            children=[self.open_preview_button, self.print_button],
            style=Pack(direction=ROW, justify_content="center", margin=5)
        )

        # Left column
        left_box = toga.Box(
            children=[
                toga.Label(
                    "Select multiple photos to generate a printable layout with desired proportions, minimizing waste area.",
                    style=Pack(margin=5),
                ),
                toga.Label("Photos:", style=Pack(margin=5, font_size=16)),
                self.photo_scroll,
                buttons_box,
                toga.Divider(style=Pack(margin=5)),
                toga.Label("Settings:", style=Pack(margin=5, font_size=16)),
                self.cmyk_mode,
                toga.Box(
                    children=[self.padding_enabled, self.padding_size],
                    style=Pack(direction=ROW, justify_content="center", margin=5),
                ),
                toga.Box(
                    children=[self.paper_ratio_selection, self.custom_ratio],
                    style=Pack(direction=ROW, justify_content="center", margin=5),
                ),
                toga.Divider(style=Pack(margin=5)),
                self.generate_button,
                self.status,
            ],
            style=Pack(direction=COLUMN, margin=10, flex=1),
        )

        # Right column
        right_box = toga.Box(
            children=[
                toga.Label("Collage Preview:", style=Pack(margin=5, font_size=14)),
                self.collage_preview,
                preview_buttons_box,
            ],
            style=Pack(direction=COLUMN, margin=10, flex=1),
        )

        # Main box
        main_box = toga.Box(children=[left_box, right_box], style=Pack(direction=ROW))

        # Main window
        self.main_window = toga.MainWindow(size=(1200, 800), title="Photo Arranger")
        self.main_window.content = main_box
        self.main_window.on_resize = self.on_resize
        self.main_window.show()

    def on_padding_toggle(self, widget):
        self.padding_size.readonly = not widget.value
        self.padding_size.refresh()

    @staticmethod
    def parse_ratio(ratio_str):
        if not ratio_str:
            return 1.0
        try:
            if ":" in ratio_str:
                width, height = map(float, ratio_str.split(":"))
                return height / width if width > 0 else 1.0
            return float(ratio_str)
        except ValueError:
            return 1.0

    def update_ratio(self, widget):
        selected = widget.value
        if selected == "Custom ratio":
            self.custom_ratio.style = Pack(visibility=VISIBLE)
            self.current_ratio = self.parse_ratio(self.custom_ratio.value)
            if self.current_ratio == 1.0:
                self.status.value = "Invalid custom ratio, using 1:1."
        else:
            self.custom_ratio.style = Pack(visibility=HIDDEN)
            self.current_ratio = self.paper_ratios.get(selected, math.sqrt(2))
        self.custom_ratio.refresh()
        self.status.refresh()
        self.on_resize(None)

    def on_custom_ratio_change(self, widget):
        if self.paper_ratio_selection.value == "Custom ratio":
            self.current_ratio = self.parse_ratio(widget.value)
            if self.current_ratio == 1.0:
                self.status.value = "Invalid custom ratio, using 1:1."
            self.status.refresh()
            self.on_resize(None)

    async def handle_upload(self, widget):
        try:
            file_dialog = toga.OpenFileDialog(
                title="Select Photos",
                multiple_select=True,
                file_types=["jpeg", "png", "jpg"],
            )
            files = await self.main_window.dialog(file_dialog)

            if files:
                if not self.images:  # Clear existing if first load
                    self.images.clear()
                    self.file_paths.clear()
                    self.scale_factors.clear()
                    self.area_percentages.clear()
                    self.photo_rows.clear()
                    self.photo_container.clear()

                added_count = 0
                for file_path in files:
                    path = str(file_path)
                    if path in self.file_paths:
                        continue
                    if not path.lower().endswith((".jpg", ".jpeg", ".png")):
                        self.status.value = f"Skipped {os.path.basename(path)}: Only JPG and PNG supported."
                        self.status.refresh()
                        continue
                    try:
                        img = Image.open(path)
                        if self.cmyk_mode.value:
                            img = img.convert("CMYK")
                        self.images.append(img)
                        self.file_paths.append(path)
                        self.scale_factors.append(1.0)
                        self.area_percentages.append(0.0)

                        checkbox = toga.Switch(value=False, style=Pack(margin=2))
                        img_view = toga.ImageView(toga.Image(path), style=Pack(width=150, height=150, margin=2))
                        name_label = toga.Label(os.path.basename(path), style=Pack(width=150, margin=2))
                        dim_label = toga.Label(f"{img.width}x{img.height}", style=Pack(width=100, margin=2, text_align="center"))
                        area_label = toga.Label("Area: 0.00%", style=Pack(width=100, margin=2, text_align="center"))
                        scale_label = toga.Label("Scale: 0%", style=Pack(width=100, margin=2, text_align="center"))

                        row = toga.Box(
                            children=[checkbox, img_view, name_label, dim_label, area_label, scale_label],
                            style=Pack(direction=ROW, justify_content="start", margin=5),
                        )

                        row.checkbox = checkbox
                        row.area_label = area_label
                        row.scale_label = scale_label
                        row.img_index = len(self.photo_rows)

                        self.photo_rows.append(row)
                        self.photo_container.add(row)
                        self.photo_container.add(toga.Divider(style=Pack(margin=2)))
                        added_count += 1
                        row.refresh()
                        img_view.refresh()
                    except Exception as ex:
                        self.status.value = f"Error loading {os.path.basename(path)}: {str(ex)}"
                        self.status.refresh()
                        print(f"Debug: Failed to load {path} - {str(ex)}")  # Debug print

                self.photo_container.refresh()
                self.photo_scroll.refresh()
                self.status.value = f"Added {added_count} new images successfully."
                if added_count == 0:
                    self.status.value = "No images were successfully added. Check file formats or paths."
                self.collage_preview.image = None
                self.open_preview_button.enabled = False
                self.print_button.enabled = False
                self.collage_preview.refresh()
                self.open_preview_button.refresh()
                self.print_button.refresh()
                self.status.refresh()
        except Exception as e:
            self.status.value = f"Error opening file dialog: {str(e)}"
            self.status.refresh()
            print(f"Debug: Dialog error - {str(e)}")  # Debug print

    def delete_selected(self, widget):
        to_delete = [i for i, row in enumerate(self.photo_rows) if row.checkbox.value]
        for i in sorted(to_delete, reverse=True):
            try:
                divider_index = self.photo_container.children.index(self.photo_rows[i]) + 1
                if divider_index < len(self.photo_container.children):
                    self.photo_container.remove(self.photo_container.children[divider_index])
                self.photo_container.remove(self.photo_rows[i])
            except (ValueError, IndexError):
                pass
            del self.photo_rows[i]
            del self.images[i]
            del self.file_paths[i]
            del self.scale_factors[i]
            del self.area_percentages[i]
        self.status.value = f"Deleted {len(to_delete)} images."
        self.collage_preview.image = None
        self.open_preview_button.enabled = False
        self.print_button.enabled = False
        self.update_photo_list()
        self.photo_container.refresh()
        self.photo_scroll.refresh()
        self.collage_preview.refresh()
        self.open_preview_button.refresh()
        self.print_button.refresh()
        self.status.refresh()

    def increase_size(self, widget):
        selected_count = sum(1 for row in self.photo_rows if row.checkbox.value)
        for i, row in enumerate(self.photo_rows):
            if row.checkbox.value:
                self.scale_factors[i] *= 1.1
        self.status.value = "No photos selected to increase size." if selected_count == 0 else f"Increased size of {selected_count} selected photos by 10%."
        self.collage_preview.image = None
        self.open_preview_button.enabled = False
        self.print_button.enabled = False
        self.update_photo_list()
        self.photo_container.refresh()
        self.photo_scroll.refresh()
        self.collage_preview.refresh()
        self.open_preview_button.refresh()
        self.print_button.refresh()
        self.status.refresh()

    def decrease_size(self, widget):
        selected_count = sum(1 for row in self.photo_rows if row.checkbox.value)
        for i, row in enumerate(self.photo_rows):
            if row.checkbox.value:
                self.scale_factors[i] /= 1.1
                self.scale_factors[i] = max(self.scale_factors[i], 0.1)
        self.status.value = "No photos selected to decrease size." if selected_count == 0 else f"Decreased size of {selected_count} selected photos by 10%."
        self.collage_preview.image = None
        self.open_preview_button.enabled = False
        self.print_button.enabled = False
        self.update_photo_list()
        self.photo_container.refresh()
        self.photo_scroll.refresh()
        self.collage_preview.refresh()
        self.open_preview_button.refresh()
        self.print_button.refresh()
        self.status.refresh()

    def select_all(self, widget):
        selected_count = sum(1 for row in self.photo_rows if not row.checkbox.value)
        for row in self.photo_rows:
            if not row.checkbox.value:
                row.checkbox.value = True
            row.checkbox.refresh()
        self.status.value = f"Selected {selected_count} images." if selected_count > 0 else "All images already selected."
        self.status.refresh()

    def deselect_all(self, widget):
        deselected_count = sum(1 for row in self.photo_rows if row.checkbox.value)
        for row in self.photo_rows:
            if row.checkbox.value:
                row.checkbox.value = False
            row.checkbox.refresh()
        self.status.value = f"Deselected {deselected_count} images." if deselected_count > 0 else "No images were selected."
        self.status.refresh()

    def invert_selection(self, widget):
        toggled_count = len(self.photo_rows)
        for row in self.photo_rows:
            row.checkbox.value = not row.checkbox.value
            row.checkbox.refresh()
        self.status.value = f"Inverted selection for {toggled_count} images." if toggled_count > 0 else "No images to invert."
        self.status.refresh()

    def clear_selection(self, widget):
        if self.images:
            self.images.clear()
            self.file_paths.clear()
            self.scale_factors.clear()
            self.area_percentages.clear()
            self.photo_rows.clear()
            self.photo_container.clear()
            self.photo_container.refresh()
            self.photo_scroll.refresh()
            self.status.value = "Cleared all images."
            self.collage_preview.image = None
            self.open_preview_button.enabled = False
            self.print_button.enabled = False
            self.collage_preview.refresh()
            self.open_preview_button.refresh()
            self.print_button.refresh()
        else:
            self.status.value = "No images to clear."
        self.status.refresh()

    def update_photo_list(self):
        for i, row in enumerate(self.photo_rows):
            if i < len(self.scale_factors):
                scale_pct = int((self.scale_factors[i] - 1.0) * 100)
                area_pct = self.area_percentages[i] if i < len(self.area_percentages) else 0.0
                row.area_label.text = f"Area: {area_pct:.2f}%"
                row.scale_label.text = f"Scale: {scale_pct}%"
                row.area_label.refresh()
                row.scale_label.refresh()
                row.refresh()

    def print_collage(self, widget):
        if self.last_output_path and os.path.exists(self.last_output_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(self.last_output_path, "print")
                elif platform.system() == "Darwin":
                    subprocess.run(["lp", self.last_output_path], check=True)
                else:
