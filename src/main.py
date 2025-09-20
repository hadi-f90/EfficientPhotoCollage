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

        # Status label with wrapping
        self.status = toga.Label(
            "No photos selected yet!", style=Pack(width=500, margin=5, text_align="left")
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

        # Paper ratio selection - Fixed Selection widget
        paper_options = [
            "A Series",
            "B Series",
            "C Series",
            "Letter",
            "Custom ratio",
        ]
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

        # Buttons - Using simple buttons without icons for now
        self.add_button = toga.Button(
            "Add Photos", on_press=self.handle_upload, style=Pack(margin=5)
        )
        self.delete_button = toga.Button(
            "Delete Selected", on_press=self.delete_selected, style=Pack(margin=5)
        )
        self.increase_button = toga.Button(
            "Zoom In", on_press=self.increase_size, style=Pack(margin=5)
        )
        self.decrease_button = toga.Button(
            "Zoom Out", on_press=self.decrease_size, style=Pack(margin=5)
        )
        self.select_all_button = toga.Button(
            "Select All", on_press=self.select_all, style=Pack(margin=5)
        )
        self.deselect_all_button = toga.Button(
            "Deselect All", on_press=self.deselect_all, style=Pack(margin=5)
        )
        self.invert_button = toga.Button(
            "Invert Selection", on_press=self.invert_selection, style=Pack(margin=5)
        )
        self.clear_button = toga.Button(
            "Clear All", on_press=self.clear_selection, style=Pack(margin=5)
        )

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
            style=Pack(
                direction=ROW,
                margin=5,
                justify_content="center",
        ),)

        # Generate button
        self.generate_button = toga.Button(
            "Arrange Photos into Canvas", on_press=self.generate_layout, style=Pack(margin=5)
        )

        # Collage preview and buttons
        self.collage_preview = toga.ImageView(style=Pack(flex=1, margin=5))
        self.open_preview_button = toga.Button(
            "Open Preview",
            on_press=self.open_collage,
            style=Pack(width=120, margin=5),
            enabled=False,
        )
        self.print_button = toga.Button(
            "Print", on_press=self.print_collage, style=Pack(width=120, margin=5), enabled=False
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
                toga.Box(
                    children=[self.open_preview_button, self.print_button],
                    style=Pack(direction=ROW, justify_content="center", margin=5),
            ),],
            style=Pack(direction=COLUMN, margin=10, flex=1),
        )

        # Main box
        main_box = toga.Box(
            children=[left_box, right_box],
            style=Pack(direction=ROW),
        )

        # Main window - resizable by default
        self.main_window = toga.MainWindow(size=(1200, 800), resizable=True, title="Photo Arranger")
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
                self.status.text = "Invalid custom ratio, using 1:1."
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
                self.status.text = "Invalid custom ratio, using 1:1."
            self.status.refresh()
            self.on_resize(None)

    async def handle_upload(self, widget):
        try:
            # Fixed: Use the new dialog method with simple file extensions
            file_dialog = toga.OpenFileDialog(
                title="Select Photos",
                multiple_select=True,
                file_types=["jpeg", "png"],
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
                        self.status.text = (
                            f"Skipped {os.path.basename(path)}: Only JPG and PNG supported."
                        )
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

                        # Create row for photo
                        checkbox = toga.Switch(value=False, style=Pack(margin=2, width=20))
                        # Fix: Ensure absolute path and refresh image view
                        abs_path = os.path.abspath(path)
                        img_view = toga.ImageView(
                            toga.Image(abs_path), style=Pack(width=150, height=150, margin=2)
                        )
                        name_label = toga.Label(
                            os.path.basename(path), style=Pack(width=150, margin=2)
                        )
                        dim_label = toga.Label(
                            f"{img.width}x{img.height}",
                            style=Pack(width=100, margin=2, text_align="center"),
                        )
                        area_label = toga.Label(
                            "Area: 0.00%", style=Pack(width=100, margin=2, text_align="center")
                        )
                        scale_label = toga.Label(
                            "Scale: 0%", style=Pack(width=100, margin=2, text_align="center")
                        )

                        row = toga.Box(
                            children=[
                                checkbox,
                                img_view,
                                name_label,
                                dim_label,
                                area_label,
                                scale_label,
                            ],
                            style=Pack(direction=ROW, justify_content="start", margin=5),
                        )

                        # Store references to widgets for later updates
                        row.checkbox = checkbox
                        row.area_label = area_label
                        row.scale_label = scale_label
                        row.img_view = img_view  # Store for refresh
                        row.img_index = len(self.photo_rows)

                        self.photo_rows.append(row)
                        self.photo_container.add(row)
                        self.photo_container.add(toga.Divider(style=Pack(margin=2)))
                        row.refresh()
                        img_view.refresh()
                        added_count += 1
                    except Exception as ex:
                        self.status.text = f"Error loading {os.path.basename(path)}: {str(ex)}"
                        self.status.refresh()
                        continue

                self.photo_container.refresh()
                self.photo_scroll.refresh()
                self.status.text = f"Added {added_count} new images successfully."
                self.collage_preview.image = None
                self.open_preview_button.enabled = False
                self.print_button.enabled = False
                self.collage_preview.refresh()
                self.open_preview_button.refresh()
                self.print_button.refresh()
                self.status.refresh()
        except Exception as e:
            self.status.text = f"Error opening file dialog: {str(e)}"
            self.status.refresh()

    def delete_selected(self, widget):
        to_delete = [i for i, row in enumerate(self.photo_rows) if row.checkbox.value]

        for i in sorted(to_delete, reverse=True):
            # Remove divider and row
            try:
                divider_index = self.photo_container.children.index(self.photo_rows[i]) + 1
                if divider_index < len(self.photo_container.children):
                    self.photo_container.remove(self.photo_container.children[divider_index])
                self.photo_container.remove(self.photo_rows[i])
            except (ValueError, IndexError):
                pass  # Row might already be removed

            del self.photo_rows[i]
            del self.images[i]
            del self.file_paths[i]
            del self.scale_factors[i]
            del self.area_percentages[i]

        self.status.text = f"Deleted {len(to_delete)} images."
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
        selected_count = 0
        for i, row in enumerate(self.photo_rows):
            if row.checkbox.value:
                selected_count += 1
                self.scale_factors[i] *= 1.1
        if selected_count == 0:
            self.status.text = "No photos selected to increase size."
        else:
            self.status.text = f"Increased size of {selected_count} selected photos by 10%."
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
        selected_count = 0
        for i, row in enumerate(self.photo_rows):
            if row.checkbox.value:
                selected_count += 1
                self.scale_factors[i] /= 1.1
                self.scale_factors[i] = max(self.scale_factors[i], 0.1)
        if selected_count == 0:
            self.status.text = "No photos selected to decrease size."
        else:
            self.status.text = f"Decreased size of {selected_count} selected photos by 10%."
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
        selected_count = 0
        for row in self.photo_rows:
            if not row.checkbox.value:
                row.checkbox.value = True
                selected_count += 1
            row.checkbox.refresh()
        self.status.text = (
            f"Selected {selected_count} images."
            if selected_count > 0
            else "All images already selected."
        )
        self.status.refresh()

    def deselect_all(self, widget):
        deselected_count = 0
        for row in self.photo_rows:
            if row.checkbox.value:
                row.checkbox.value = False
                deselected_count += 1
            row.checkbox.refresh()
        self.status.text = (
            f"Deselected {deselected_count} images."
            if deselected_count > 0
            else "No images were selected."
        )
        self.status.refresh()

    def invert_selection(self, widget):
        toggled_count = 0
        for row in self.photo_rows:
            row.checkbox.value = not row.checkbox.value
            toggled_count += 1
            row.checkbox.refresh()
        self.status.text = (
            f"Inverted selection for {toggled_count} images."
            if toggled_count > 0
            else "No images to invert."
        )
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
            self.status.text = "Cleared all images."
            self.collage_preview.image = None
            self.open_preview_button.enabled = False
            self.print_button.enabled = False
            self.collage_preview.refresh()
            self.open_preview_button.refresh()
            self.print_button.refresh()
        else:
            self.status.text = "No images to clear."
        self.status.refresh()

    def update_photo_list(self):
        for i, row in enumerate(self.photo_rows):
            if i >= len(self.scale_factors):
                continue

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
                system = platform.system()
                if system == "Windows":
                    # Use start with /p for print
                    os.startfile(self.last_output_path, "print")
                elif system == "Darwin":  # macOS
                    subprocess.run(["lpr", self.last_output_path], check=False)
                else:  # Linux
                    subprocess.run(["lp", self.last_output_path], check=False)
                self.status.text = (
                    f"Sending '{os.path.basename(self.last_output_path)}' to printer."
                )
            except Exception as ex:
                self.status.text = f"Error printing: {str(ex)}"
        else:
            self.status.text = "No collage to print."
        self.status.refresh()

    def find_min_canvas(self, orig_sizes, num_images, ratio):
        padding = (
            int(self.padding_size.value)
            if self.padding_enabled.value and self.padding_size.value.isdigit()
            else 0
        )
        padding = max(0, padding)
        min_side_req = max(
            min(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, self.scale_factors)
        )
        max_side_req = max(
            max(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, self.scale_factors)
        )
        low = max(min_side_req, math.ceil(max_side_req / ratio))
        high = (
            sum(
                max(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, self.scale_factors)
            )
            * 2
        )

        min_width = float("inf")
        min_height = float("inf")

        while low < high:
            mid = (low + high) // 2
            cw = mid
            ch = int(mid * ratio)
            packer = newPacker(rotation=True)
            for i, (w, h) in enumerate(orig_sizes):
                scaled_w = max(1, int(w * self.scale_factors[i]))
                scaled_h = max(1, int(h * self.scale_factors[i]))
                packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=i)
            packer.add_bin(cw, ch)
            packer.pack()
            if len(packer.rect_list()) == num_images:
                high = mid
                min_width = cw
                min_height = ch
            else:
                low = mid + 1

        return int(min_width), int(min_height)

    @staticmethod
    def find_free_spaces(canvas_width, canvas_height, rects, min_size=50):
        free_rects = [(0, 0, canvas_width, canvas_height)]
        for _, x, y, w, h, _ in rects:
            new_free_rects = []
            for fx, fy, fw, fh in free_rects:
                if x + w <= fx or fx + fw <= x or y + h <= fy or (fy + fh <= y):
                    new_free_rects.append((fx, fy, fw, fh))
                    continue
                if fx < x:
                    new_free_rects.append((fx, fy, x - fx, fh))
                if fx + fw > x + w:
                    new_free_rects.append((x + w, fy, fx + fw - (x + w), fh))
                if fy < y:
                    new_free_rects.append((fx, fy, fw, y - fy))
                if fy + fh > y + h:
                    new_free_rects.append((fx, y + h, fw, fy + fh - (y + h)))
            free_rects = new_free_rects
        return [(x, y, w, h) for x, y, w, h in free_rects if w >= min_size and h >= min_size]

    def generate_layout(self, widget):
        if not self.images:
            self.status.text = "No images loaded. Please upload photos first."
            self.status.refresh()
            return

        orig_sizes = [(img.width, img.height) for img in self.images]
        num_images = len(self.images)

        padding = (
            int(self.padding_size.value)
            if self.padding_enabled.value and self.padding_size.value.isdigit()
            else 0
        )
        padding = max(0, padding)

        portrait_w, portrait_h = self.find_min_canvas(orig_sizes, num_images, self.current_ratio)
        portrait_area = portrait_w * portrait_h if portrait_w != float("inf") else float("inf")
        landscape_w, landscape_h = self.find_min_canvas(
            orig_sizes, num_images, 1 / self.current_ratio
        )
        landscape_area = landscape_w * landscape_h if landscape_w != float("inf") else float("inf")

        if portrait_area <= landscape_area:
            canvas_width = portrait_w
            canvas_height = portrait_h
            orientation = "portrait"
        else:
            canvas_width = landscape_w
            canvas_height = landscape_h
            orientation = "landscape"

        if canvas_width == float("inf"):
            self.status.text = "Could not fit all images."
            self.status.refresh()
            return

        packer = newPacker(rotation=True)
        for i, (w, h) in enumerate(orig_sizes):
            scaled_w = max(1, int(w * self.scale_factors[i]))
            scaled_h = max(1, int(h * self.scale_factors[i]))
            packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=i)
        packer.add_bin(canvas_width, canvas_height)
        packer.pack()

        if len(packer.rect_list()) != num_images:
            scale_factor = 1.05
            max_attempts = 40  # Prevent infinite loop
            attempt = 0
            while len(packer.rect_list()) != num_images and attempt < max_attempts:
                canvas_width = int(canvas_width * scale_factor)
                canvas_height = int(canvas_height * scale_factor)
                packer = newPacker(rotation=True)
                for i, (w, h) in enumerate(orig_sizes):
                    scaled_w = max(1, int(w * self.scale_factors[i]))
                    scaled_h = max(1, int(h * self.scale_factors[i]))
                    packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=i)
                packer.add_bin(canvas_width, canvas_height)
                packer.pack()
                scale_factor += 0.05
                attempt += 1
                if scale_factor > 2.0:
                    self.status.text = "Could not fit all images even with larger canvas."
                    self.status.refresh()
                    return

        canvas_area = canvas_width * canvas_height
        total_image_area = 0
        self.area_percentages.clear()
        all_rects = packer.rect_list()

        for _, x, y, w, h, rid in all_rects:
            orig_w, orig_h = orig_sizes[rid]
            scaled_w = max(1, int(orig_w * self.scale_factors[rid]))
            scaled_h = max(1, int(orig_h * self.scale_factors[rid]))
            if w == scaled_h + 2 * padding and h == scaled_w + 2 * padding:
                scaled_w, scaled_h = scaled_h, scaled_w
            image_area = scaled_w * scaled_h
            total_image_area += image_area
            area_pct = (image_area / canvas_area) * 100 if canvas_area > 0 else 0.0
            self.area_percentages.append(area_pct)

        unused_pct = (
            ((canvas_area - total_image_area) / canvas_area) * 100 if canvas_area > 0 else 0.0
        )

        mode = "CMYK" if self.cmyk_mode.value else "RGB"
        canvas = Image.new(
            mode,
            (int(canvas_width), int(canvas_height)),
            (255, 255, 255) if mode == "RGB" else (0, 0, 0, 0),
        )

        for _, x, y, w, h, rid in all_rects:
            img = self.images[rid]
            orig_w, orig_h = orig_sizes[rid]
            scaled_w = max(1, int(orig_w * self.scale_factors[rid]))
            scaled_h = max(1, int(orig_h * self.scale_factors[rid]))
            if w == scaled_h + 2 * padding and h == scaled_w + 2 * padding:
                img = img.rotate(90, expand=True)
                scaled_w, scaled_h = scaled_h, scaled_w
            img_resized = img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            padded_w = scaled_w + 2 * padding
            padded_h = scaled_h + 2 * padding
            padded_img = Image.new(
                mode, (padded_w, padded_h), (255, 255, 255) if mode == "RGB" else (0, 0, 0, 0)
            )
            padded_img.paste(img_resized, (padding, padding))
            canvas.paste(padded_img, (x, y))

        # Add logo and shop note (simplified for now)
        logo_status = "Logo and shop note added to free space."
        try:
            # Try to add logo if assets/icon.png exists
            logo_path = os.path.join("assets", "icon.png")
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                if self.cmyk_mode.value:
                    logo_img = logo_img.convert("CMYK")
                free_rects = self.find_free_spaces(
                    canvas_width, canvas_height, all_rects, min_size=50
                )
                if free_rects:
                    largest_rect = max(free_rects, key=lambda r: r[2] * r[3], default=None)
                    if largest_rect:
                        fx, fy, fw, fh = largest_rect
                        logo_w, logo_h = logo_img.size
                        scale = min(fw / logo_w, fh / logo_h, 0.5)  # Max 50% of free space
                        if scale > 0:
                            scaled_w = int(logo_w * scale)
                            scaled_h = int(logo_h * scale)
                            if scaled_w > 0 and scaled_h > 0:
                                logo_resized = logo_img.resize(
                                    (scaled_w, scaled_h), Image.Resampling.LANCZOS
                                )
                                logo_x = fx + (fw - scaled_w) // 2
                                logo_y = fy + (fh - scaled_h) // 2
                                canvas.paste(logo_resized, (logo_x, logo_y))
        except Exception as ex:
            logo_status = f"Could not add logo: {str(ex)}"

        self.update_photo_list()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = "tiff" if self.cmyk_mode.value else "png"
        output_path = f"a_series_photo_layout_{timestamp}.{file_ext}"
        preview_path = (
            f"a_series_photo_layout_preview_{timestamp}.png"
            if self.cmyk_mode.value
            else output_path
        )

        try:
            canvas.save(output_path)
            if self.cmyk_mode.value:
                rgb_canvas = canvas.convert("RGB")
                rgb_canvas.save(preview_path)
                self.collage_preview.image = toga.Image(preview_path)
            else:
                self.collage_preview.image = toga.Image(output_path)

            self.last_output_path = output_path
            self.open_preview_button.enabled = True
            self.print_button.enabled = True
            self.status.text = (
                f"Layout generated and saved as '{output_path}'. Orientation: {orientation}. "
                f"Canvas size: {canvas_width}x{canvas_height} pixels. Unused area: {unused_pct:.2f}%. "
                f"{logo_status}"
            )
            self.collage_preview.refresh()
            self.open_preview_button.refresh()
            self.print_button.refresh()
            self.status.refresh()
        except Exception as ex:
            self.status.text = f"Error saving file: {str(ex)}"
            self.status.refresh()

    def open_collage(self, widget):
        if self.last_output_path and os.path.exists(self.last_output_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(self.last_output_path)
                else:
                    opener = "open" if platform.system() == "Darwin" else "xdg-open"
                    subprocess.run([opener, self.last_output_path], check=True)
                self.status.text = (
                    f"Opened collage '{os.path.basename(self.last_output_path)}' in default viewer."
                )
            except Exception as ex:
                self.status.text = f"Error opening collage: {str(ex)}"
        else:
            self.status.text = "No collage generated yet."
        self.status.refresh()

    def on_resize(self, window):
        width, height = window.size if window else (1200, 800)
        photo_size = 150
        if width < 600:
            photo_size = 100
        elif width < 900:
            photo_size = 120

        for row in self.photo_rows:
            row.children[1].style = Pack(width=photo_size, height=photo_size)
            if hasattr(row, 'img_view'):
                row.img_view.refresh()
            row.children[1].refresh()
            row.refresh()

        # Update preview size
        preview_height = min(height * 0.4, 400)
        preview_max_width = width / 2 - 80  # account for button and padding
        preview_width = (
            preview_height / self.current_ratio if self.current_ratio > 0 else preview_height
        )

        # Ensure preview fits within available space
        if preview_width > preview_max_width:
            preview_width = preview_max_width
            preview_height = preview_width * self.current_ratio

        self.collage_preview.style = Pack(width=preview_width, height=preview_height)
        self.collage_preview.refresh()


def main():
    return PhotoArranger("Photo Arranger", "com.example.photoarranger")


if __name__ == "__main__":
    app = main()
    app.main_loop()