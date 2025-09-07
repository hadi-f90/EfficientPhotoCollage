import math
import os
import platform
import subprocess
from datetime import datetime

import flet as ft
from PIL import Image, ImageDraw, ImageFont
from rectpack import SORT_AREA, newPacker


def main(page: ft.Page):
    page.title = "Photo Arranger for A-Series Printing with Rectpack"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 10
    page.update()

    # Lists to hold loaded images, their file paths, and scaling factors
    images = []
    file_paths = []
    scale_factors = []  # Scaling factor for each image (1.0 = original size)
    area_percentages = []  # Store area percentage for each image after layout
    last_output_paths = []  # Store paths of all generated canvases

    # Status text
    status = ft.Text("", size=14)

    # Checkbox for CMYK mode
    cmyk_mode = ft.Checkbox(label="Use CMYK color profile for printing (saves as TIFF)", value=False)

    # Checkbox and input for padding
    padding_enabled = ft.Checkbox(label="Add padding border around photos for easier cutting", value=False)
    padding_size = ft.TextField(label="Padding size (pixels)", value="10", width=150, disabled=True)

    # Input for number of canvases
    def validate_num_canvases(e):
        try:
            num = int(num_canvases_input.value)
            if num < 1:
                num_canvases_input.value = "1"
                status.value = "Number of canvases must be at least 1."
            elif num > len(images):
                num_canvases_input.value = str(len(images))
                status.value = f"Number of canvases cannot exceed number of images ({len(images)})."
        except ValueError:
            num_canvases_input.value = "1"
            status.value = "Please enter a valid number of canvases."
        page.update()

    num_canvases_input = ft.TextField(
        label="Number of canvases (pages)",
        value="1",
        width=150,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=validate_num_canvases
    )

    def on_padding_toggle(e):
        padding_size.disabled = not padding_enabled.value
        page.update()

    padding_enabled.on_change = on_padding_toggle

    # List view for uploaded photo previews
    def get_list_params():
        screen_width = page.width
        if screen_width < 600:  # Mobile
            return 100  # Smaller photo preview
        if screen_width < 900:  # Tablet
            return 120
        return 150

    photo_size = get_list_params()
    photo_list = ft.ListView(
        expand=True,
        spacing=10,
        padding=15,
        auto_scroll=True
    )

    # Carousel for previewing all canvases
    a_series_ratio = math.sqrt(2)
    current_preview_index = [0]  # Track current canvas index
    canvas_previews = ft.ListView(
        spacing=10,
        padding=10,
        height=page.height * 0.4,
        auto_scroll=False,
        visible=False
    )
    canvas_index_text = ft.Text("Canvas 1/0", size=12)

    def open_collages(e):
        if last_output_paths:
            for output_path in last_output_paths:
                try:
                    if platform.system() == "Windows":
                        os.startfile(output_path)
                    else:
                        opener = "open" if platform.system() == "Darwin" else "xdg-open"
                        subprocess.run([opener, output_path])
                except Exception as ex:
                    status.value = f"Error opening canvas '{os.path.basename(output_path)}': {str(ex)}"
                    page.update()
                    return
            status.value = f"Opened {len(last_output_paths)} canvas(es) in default viewer: {', '.join([os.path.basename(p) for p in last_output_paths])}."
            page.update()
        else:
            status.value = "No canvases generated yet."

    def show_prev_canvas(e):
        if current_preview_index[0] > 0:
            current_preview_index[0] -= 1
            canvas_previews.controls.clear()
            canvas_previews.controls.append(
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Image(
                            src=last_output_paths[current_preview_index[0]] if last_output_paths else "",
                            width=page.width * 0.4 / a_series_ratio,
                            height=page.height * 0.4,
                            fit=ft.ImageFit.CONTAIN,
                            border_radius=5
                        ),
                        border=ft.border.all(1, ft.Colors.BLUE_500),
                        border_radius=5
                    ),
                    on_double_tap=open_collages
                )
            )
            canvas_index_text.value = f"Canvas {current_preview_index[0] + 1}/{len(last_output_paths)}"
            prev_button.disabled = current_preview_index[0] == 0
            next_button.disabled = current_preview_index[0] == len(last_output_paths) - 1
            status.value = (
                f"Generated {len(last_output_paths)} canvas(es) saved as {', '.join([f'\'{os.path.basename(p)}\'' for p in last_output_paths])}. "
                f"Showing canvas {current_preview_index[0] + 1} of {len(last_output_paths)}. Double-tap to open all canvases."
            )
            page.update()

    def show_next_canvas(e):
        if current_preview_index[0] < len(last_output_paths) - 1:
            current_preview_index[0] += 1
            canvas_previews.controls.clear()
            canvas_previews.controls.append(
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Image(
                            src=last_output_paths[current_preview_index[0]] if last_output_paths else "",
                            width=page.width * 0.4 / a_series_ratio,
                            height=page.height * 0.4,
                            fit=ft.ImageFit.CONTAIN,
                            border_radius=5
                        ),
                        border=ft.border.all(1, ft.Colors.BLUE_500),
                        border_radius=5
                    ),
                    on_double_tap=open_collages
                )
            )
            canvas_index_text.value = f"Canvas {current_preview_index[0] + 1}/{len(last_output_paths)}"
            prev_button.disabled = current_preview_index[0] == 0
            next_button.disabled = current_preview_index[0] == len(last_output_paths) - 1
            status.value = (
                f"Generated {len(last_output_paths)} canvas(es) saved as {', '.join([f'\'{os.path.basename(p)}\'' for p in last_output_paths])}. "
                f"Showing canvas {current_preview_index[0] + 1} of {len(last_output_paths)}. Double-tap to open all canvases."
            )
            page.update()

    prev_button = ft.IconButton(
        icon=ft.Icons.ARROW_LEFT,
        on_click=show_prev_canvas,
        disabled=True
    )
    next_button = ft.IconButton(
        icon=ft.Icons.ARROW_RIGHT,
        on_click=show_next_canvas,
        disabled=True
    )

    # File picker handler
    def handle_upload(e: ft.FilePickerResultEvent):
        if e.files:
            if not images:
                images.clear()
                file_paths.clear()
                scale_factors.clear()
                area_percentages.clear()
                photo_list.controls.clear()
            added_count = 0
            for f in e.files:
                if f.path in file_paths:
                    continue  # Skip duplicate files
                if not f.path.lower().endswith(('.jpg', '.jpeg', '.png')):
                    status.value = f"Skipped {f.name}: Only JPG and PNG files are supported."
                    continue
                try:
                    img = Image.open(f.path)
                    if cmyk_mode.value:
                        img = img.convert("CMYK")
                    images.append(img)
                    file_paths.append(f.path)
                    scale_factors.append(1.0)
                    area_percentages.append(0.0)
                    scale_pct = 0
                    scale_color = ft.Colors.BLACK
                    file_name = os.path.basename(f.path)
                    dimensions = f"{img.width}x{img.height}"
                    photo_list.controls.append(
                        ft.Column([
                            ft.Row([
                                ft.Checkbox(label=""),
                                ft.Image(
                                    src=f.path,
                                    width=photo_size,
                                    height=photo_size,
                                    fit=ft.ImageFit.CONTAIN,
                                    border_radius=5
                                ),
                                ft.Text(file_name, size=12, width=150, text_align=ft.TextAlign.LEFT),
                                ft.Text(dimensions, size=12, width=100, text_align=ft.TextAlign.CENTER),
                                ft.Text("Area: 0.00%", size=12, width=100, text_align=ft.TextAlign.CENTER),
                                ft.Text(
                                    value=f"Scale: {scale_pct}%",
                                    size=12,
                                    color=scale_color,
                                    width=100,
                                    text_align=ft.TextAlign.CENTER
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            spacing=10),
                            ft.Divider()
                        ])
                    )
                    added_count += 1
                except Exception as ex:
                    status.value = f"Error loading {f.name}: {str(ex)}"
                    page.update()
                    return
            status.value = f"{'Loaded' if not images else 'Added'} {added_count} new images successfully."
            canvas_previews.visible = False
            canvas_index_text.value = "Canvas 1/0"
            page.update()

    file_picker = ft.FilePicker(on_result=handle_upload)
    page.overlay.append(file_picker)

    # Add file button
    add_button = ft.IconButton(
        icon=ft.Icons.ADD,
        on_click=lambda _: file_picker.pick_files(allow_multiple=True, allowed_extensions=["jpg", "jpeg", "png"])
    )

    # Delete selected button
    def delete_selected(e):
        to_delete = []
        for i, ctrl in enumerate(photo_list.controls):
            checkbox = ctrl.controls[0].controls[0]  # Checkbox in Row
            if checkbox.value:
                to_delete.append(i)
        for i in sorted(to_delete, reverse=True):
            del images[i]
            del file_paths[i]
            del scale_factors[i]
            del area_percentages[i]
            del photo_list.controls[i]
        status.value = f"Deleted {len(to_delete)} images."
        canvas_previews.visible = False
        canvas_index_text.value = "Canvas 1/0"
        for i, ctrl in enumerate(photo_list.controls):
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
            ctrl.controls[0].controls[3].value = "Area: 0.00%"
        page.update()

    trash_button = ft.IconButton(icon=ft.Icons.DELETE, on_click=delete_selected)

    # Increase size button
    def increase_size(e):
        selected_count = 0
        for i, ctrl in enumerate(photo_list.controls):
            checkbox = ctrl.controls[0].controls[0]
            if not checkbox.value:
                continue
            selected_count += 1
            scale_factors[i] *= 1.1
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
        if selected_count == 0:
            status.value = "No photos selected to increase size."
        else:
            status.value = f"Increased size of {selected_count} selected photos by 10%."
        canvas_previews.visible = False
        canvas_index_text.value = "Canvas 1/0"
        for i, ctrl in enumerate(photo_list.controls):
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
        page.update()

    increase_button = ft.IconButton(
        icon=ft.Icons.ZOOM_IN,
        icon_color=ft.Colors.GREEN,
        on_click=increase_size
    )

    # Decrease size button
    def decrease_size(e):
        selected_count = 0
        for i, ctrl in enumerate(photo_list.controls):
            checkbox = ctrl.controls[0].controls[0]
            if not checkbox.value:
                continue
            selected_count += 1
            scale_factors[i] /= 1.1
            scale_factors[i] = max(scale_factors[i], 0.1)
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
        if selected_count == 0:
            status.value = "No photos selected to decrease size."
        else:
            status.value = f"Decreased size of {selected_count} selected photos by 10%."
        canvas_previews.visible = False
        canvas_index_text.value = "Canvas 1/0"
        for i, ctrl in enumerate(photo_list.controls):
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
        page.update()

    decrease_button = ft.IconButton(
        icon=ft.Icons.ZOOM_OUT,
        icon_color=ft.Colors.RED,
        on_click=decrease_size
    )

    # Select all button
    def select_all(e):
        selected_count = 0
        for ctrl in photo_list.controls:
            checkbox = ctrl.controls[0].controls[0]
            if not checkbox.value:
                checkbox.value = True
                selected_count += 1
        status.value = f"Selected {selected_count} images." if selected_count > 0 else "All images already selected."
        page.update()

    select_all_button = ft.IconButton(
        icon=ft.Icons.CHECK_BOX,
        icon_color=ft.Colors.BLUE,
        on_click=select_all
    )

    # Deselect all button
    def deselect_all(e):
        deselected_count = 0
        for ctrl in photo_list.controls:
            checkbox = ctrl.controls[0].controls[0]
            if checkbox.value:
                checkbox.value = False
                deselected_count += 1
        status.value = f"Deselected {deselected_count} images." if deselected_count > 0 else "No images were selected."
        page.update()

    deselect_all_button = ft.IconButton(
        icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK,
        icon_color=ft.Colors.BLUE,
        on_click=deselect_all
    )

    # Invert selection button
    def invert_selection(e):
        toggled_count = 0
        for ctrl in photo_list.controls:
            checkbox = ctrl.controls[0].controls[0]
            checkbox.value = not checkbox.value
            toggled_count += 1
        status.value = f"Inverted selection for {toggled_count} images." if toggled_count > 0 else "No images to invert."
        page.update()

    invert_selection_button = ft.IconButton(
        icon=ft.Icons.SWAP_HORIZ,
        icon_color=ft.Colors.BLUE,
        on_click=invert_selection
    )

    # Clear current selection button
    def clear_selection(e):
        if images:
            images.clear()
            file_paths.clear()
            scale_factors.clear()
            area_percentages.clear()
            photo_list.controls.clear()
            status.value = "Cleared all images."
            canvas_previews.visible = False
            canvas_index_text.value = "Canvas 1/0"
            page.update()
        else:
            status.value = "No images to clear."

    clear_selection_button = ft.IconButton(
        icon=ft.Icons.CLEAR_ALL,
        icon_color=ft.Colors.RED,
        on_click=clear_selection
    )

    # Function to find minimal canvas for a given ratio and subset of images
    def find_min_canvas(orig_sizes, scale_factors_subset, ratio):
        padding = int(padding_size.value) if padding_enabled.value and padding_size.value.isdigit() else 0
        padding = max(0, padding)
        min_side_req = max(min(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors_subset)) if orig_sizes else 1
        max_side_req = max(max(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors_subset)) if orig_sizes else 1
        low = max(min_side_req, math.ceil(max_side_req / ratio))
        high = sum(max(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors_subset)) * 2 if orig_sizes else 1000

        min_width = float('inf')
        min_height = float('inf')

        while low < high:
            mid = (low + high) // 2
            cw = mid
            ch = int(mid * ratio)
            packer = newPacker(rotation=True, sort_algo=SORT_AREA)
            for i, (w, h) in enumerate(orig_sizes):
                scaled_w = max(1, int(w * scale_factors_subset[i]))
                scaled_h = max(1, int(h * scale_factors_subset[i]))
                packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=i)
            packer.add_bin(cw, ch)
            packer.pack()
            if len(packer.rect_list()) == len(orig_sizes):
                high = mid
                min_width = cw
                min_height = ch
            else:
                low = mid + 1

        return int(min_width), int(min_height)

    # Function to find free spaces in the canvas
    def find_free_spaces(canvas_width, canvas_height, rects, min_size=50):
        free_rects = [(0, 0, canvas_width, canvas_height)]
        for _, x, y, w, h, _ in rects:
            new_free_rects = []
            for fx, fy, fw, fh in free_rects:
                if x + w <= fx or fx + fw <= x or y + h <= fy or fy + fh <= y:
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

    # Generate and save collage(s)
    def generate_layout(save_only=False):
        if not images:
            status.value = "No images loaded. Please upload photos first."
            page.update()
            return None, None, None

        a_series_ratio = math.sqrt(2)
        orig_sizes = [(img.width, img.height) for img in images]
        num_images = len(images)

        if num_images == 0:
            status.value = "No images to pack."
            page.update()
            return None, None, None

        # Validate number of canvases
        try:
            num_canvases = int(num_canvases_input.value)
            if num_canvases < 1:
                num_canvases = 1
                num_canvases_input.value = "1"
                status.value = "Number of canvases must be at least 1."
                page.update()
            elif num_canvases > num_images:
                num_canvases = num_images
                num_canvases_input.value = str(num_images)
                status.value = f"Number of canvases cannot exceed number of images ({num_images})."
                page.update()
        except ValueError:
            num_canvases = 1
            num_canvases_input.value = "1"
            status.value = "Invalid number of canvases; defaulting to 1."
            page.update()

        padding = int(padding_size.value) if padding_enabled.value and padding_size.value.isdigit() else 0
        padding = max(0, padding)

        # Initialize attempt and scale_factor
        attempt = 0
        scale_factor = 1.5  # Start with larger canvas to spread photos

        # Determine optimal canvas size for all images (used as base for all canvases)
        portrait_w, portrait_h = find_min_canvas(orig_sizes, scale_factors, a_series_ratio)
        portrait_area = portrait_w * portrait_h if portrait_w != float('inf') else float('inf')
        landscape_w, landscape_h = find_min_canvas(orig_sizes, scale_factors, 1 / a_series_ratio)
        landscape_area = landscape_w * landscape_h if landscape_w != float('inf') else float('inf')

        orientation = "portrait" if portrait_area <= landscape_area else "landscape"
        base_canvas_width = portrait_w if orientation == "portrait" else landscape_w
        base_canvas_height = portrait_h if orientation == "portrait" else landscape_h

        # Scale up canvas size to encourage spreading photos
        base_canvas_width = int(base_canvas_width * scale_factor)
        base_canvas_height = int(base_canvas_height * scale_factor)

        # Distribute images across the specified number of canvases
        images_per_canvas = max(1, num_images // num_canvases)
        remainder = num_images % num_canvases
        image_splits = []
        start_idx = 0
        for i in range(num_canvases):
            num = images_per_canvas + (1 if i < remainder else 0)
            if num > 0:  # Only include non-empty splits
                image_splits.append((start_idx, start_idx + num))
                start_idx += num

        canvases = []
        canvas_sizes = []
        for split_idx, (start, end) in enumerate(image_splits):
            # Subset of images for this canvas
            subset_sizes = orig_sizes[start:end]
            subset_scale_factors = scale_factors[start:end]

            # Initialize packer for this subset
            packer = newPacker(rotation=True, sort_algo=SORT_AREA)
            for i, (w, h) in enumerate(subset_sizes):
                scaled_w = max(1, int(w * subset_scale_factors[i]))
                scaled_h = max(1, int(h * subset_scale_factors[i]))
                packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=start + i)

            # Add one bin for this canvas
            packer.add_bin(base_canvas_width, base_canvas_height)
            packer.pack()

            # If packing failed, increase canvas size
            if len(packer.rect_list()) != (end - start):
                local_scale_factor = scale_factor
                max_attempts = 10
                attempt = 0
                while len(packer.rect_list()) != (end - start) and attempt < max_attempts:
                    packer = newPacker(rotation=True, sort_algo=SORT_AREA)
                    for i, (w, h) in enumerate(subset_sizes):
                        scaled_w = max(1, int(w * subset_scale_factors[i]))
                        scaled_h = max(1, int(h * subset_scale_factors[i]))
                        packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=start + i)
                    packer.add_bin(int(base_canvas_width * local_scale_factor), int(base_canvas_height * local_scale_factor))
                    packer.pack()
                    attempt += 1
                    local_scale_factor += 0.05

                if len(packer.rect_list()) != (end - start):
                    status.value = f"Could not fit {end - start} images on canvas {split_idx + 1}."
                    page.update()
                    return None, None, None

            # Store rectangles for this canvas
            canvas_width = base_canvas_width if attempt == 0 else int(base_canvas_width * local_scale_factor)
            canvas_height = base_canvas_height if attempt == 0 else int(base_canvas_height * local_scale_factor)
            canvases.append((canvas_width, canvas_height, packer.rect_list()))
            canvas_sizes.append((canvas_width, canvas_height))

        if not canvases:
            status.value = "No canvases generated."
            page.update()
            return None, None, None

        # Create and save canvases
        mode = "CMYK" if cmyk_mode.value else "RGB"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_paths = []
        preview_paths = []
        total_unused_pct = 0
        total_canvas_area = 0
        area_percentages.clear()
        area_percentages.extend([0.0] * num_images)
        logo_statuses = []

        file_ext = "tiff" if cmyk_mode.value else "png"
        for canvas_idx, (canvas_width, canvas_height, rects) in enumerate(canvases):
            canvas_area = canvas_width * canvas_height
            total_canvas_area += canvas_area
            canvas_image_area = 0

            canvas = Image.new(mode, (int(canvas_width), int(canvas_height)), (255, 255, 255) if mode == "RGB" else (0, 0, 0, 0))

            for _, x, y, w, h, rid in rects:
                img = images[rid]
                orig_w, orig_h = orig_sizes[rid]
                scaled_w = max(1, int(orig_w * scale_factors[rid]))
                scaled_h = max(1, int(orig_h * scale_factors[rid]))
                if w == scaled_h + 2 * padding and h == scaled_w + 2 * padding:
                    img = img.rotate(90, expand=True)
                    scaled_w, scaled_h = scaled_h, scaled_w
                img_resized = img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
                padded_w = scaled_w + 2 * padding
                padded_h = scaled_h + 2 * padding
                padded_img = Image.new(mode, (padded_w, padded_h), (255, 255, 255) if mode == "RGB" else (0, 0, 0, 0))
                padded_img.paste(img_resized, (padding, padding))
                canvas.paste(padded_img, (x, y))
                image_area = scaled_w * scaled_h
                canvas_image_area += image_area
                if canvas_area > 0:
                    area_percentages[rid] = (image_area / canvas_area) * 100

            # Add logo and shop note in the smallest suitable free space
            logo_status = f"Canvas {canvas_idx + 1}: "
            try:
                logo_path = os.path.join("assets", "icon.png")
                logo_img = Image.open(logo_path)
                if cmyk_mode.value:
                    logo_img = logo_img.convert("CMYK")
                free_rects = find_free_spaces(canvas_width, canvas_height, rects, min_size=50)
                if free_rects:
                    # Prefer smallest suitable free space, prioritize bottom-right
                    suitable_rects = sorted(free_rects)
                    selected_rect = suitable_rects[0] if suitable_rects else None
                    if selected_rect:
                        fx, fy, fw, fh = selected_rect
                        logo_w, logo_h = logo_img.size
                        draw = ImageDraw.Draw(canvas)
                        shop_text = "Karrayan Office Equipment Store"
                        font_size = 24
                        text_fits = False
                        logo_scale = 0.98

                        while font_size >= 12 and not text_fits:
                            try:
                                font = ImageFont.truetype("arial.ttf", size=font_size)
                            except:
                                font = ImageFont.load_default()
                            text_bbox = draw.textbbox((0, 0), shop_text, font=font)
                            text_w = text_bbox[2] - text_bbox[0]
                            text_h = text_bbox[3] - text_bbox[1]

                            scale = min(fw / logo_w, (fh - text_h - 10) / logo_h, 1.0) * logo_scale
                            scaled_logo_w = int(logo_w * scale)
                            scaled_logo_h = int(logo_h * scale)

                            total_width = scaled_logo_w + 10 + text_w
                            if total_width <= fw and max(scaled_logo_h, text_h) <= fh:
                                text_fits = True
                            else:
                                font_size -= 2

                        if scaled_logo_w > 0 and scaled_logo_h > 0:
                            logo_resized = logo_img.resize((scaled_logo_w, scaled_logo_h), Image.Resampling.LANCZOS)
                            total_content_width = scaled_logo_w + 10 + text_w if text_fits else scaled_logo_w
                            logo_x = fx + (fw - total_content_width)  # Align to right
                            logo_y = fy + (fh - scaled_logo_h)  # Align to bottom
                            canvas.paste(logo_resized, (logo_x, logo_y))

                            if text_fits:
                                text_x = logo_x + scaled_logo_w + 10
                                text_y = fy + (fh - text_h)  # Align to bottom
                                text_color = (0, 0, 0) if mode == "RGB" else (0, 0, 0, 255)
                                draw.text((text_x, text_y), shop_text, font=font, fill=text_color)
                                logo_status += "Logo and shop note placed in smallest suitable free space (bottom-right)."
                            else:
                                logo_status += "Logo placed in smallest suitable free space (bottom-right), but shop note does not fit."
                        else:
                            logo_status += "Free space too small to add logo and shop note."
                    else:
                        logo_status += "No suitable free space to add logo and shop note."
                else:
                    logo_status += "No free space available to add logo and shop note."
            except Exception as ex:
                logo_status += f"Error loading or adding logo/shop note: {str(ex)}"
            logo_statuses.append(logo_status)

            # Save canvas

            output_path = f"a_series_photo_layout_{timestamp}_{canvas_idx + 1}.{file_ext}"
            canvas_preview_path = f"a_series_photo_layout_preview_{timestamp}_{canvas_idx + 1}.png" if cmyk_mode.value else output_path

            try:
                canvas.save(output_path)
                if cmyk_mode.value:
                    rgb_canvas = canvas.convert("RGB")
                    rgb_canvas.save(canvas_preview_path)
                output_paths.append(output_path)
                preview_paths.append(canvas_preview_path)
                canvas_unused_pct = ((canvas_area - canvas_image_area) / canvas_area) * 100 if canvas_area > 0 else 0
                total_unused_pct += canvas_unused_pct * (canvas_area / total_canvas_area) if total_canvas_area > 0 else 0
            except Exception as ex:
                logo_statuses[canvas_idx] = f"Canvas {canvas_idx + 1}: Error saving canvas: {str(ex)}"
                continue

        # Update UI with area percentages
        for i, ctrl in enumerate(photo_list.controls):
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            area_pct = area_percentages[i]
            ctrl.controls[0].controls[3].value = f"Area: {area_pct:.2f}%"
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color

        # Update canvas previews
        if not save_only and output_paths:
            canvas_previews.controls.clear()
            current_preview_index[0] = 0
            canvas_previews.controls.append(
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Image(
                            src=preview_paths[0] if preview_paths else "",
                            width=page.width * 0.4 / a_series_ratio,
                            height=page.height * 0.4,
                            fit=ft.ImageFit.CONTAIN,
                            border_radius=5
                        ),
                        border=ft.border.all(1, ft.Colors.BLUE_500),
                        border_radius=5
                    ),
                    on_double_tap=open_collages
                )
            )
            canvas_previews.visible = True
            canvas_index_text.value = f"Canvas 1/{len(output_paths)}"
            prev_button.disabled = True
            next_button.disabled = len(preview_paths) <= 1
            status.value = (
                f"Generated {len(canvases)} canvas(es) saved as {', '.join([f'\'{os.path.basename(p)}\'' for p in output_paths])}. "
                f"Orientation: {orientation}. "
                f"Average unused area: {total_unused_pct:.2f}%. "
                f"{' | '.join(logo_statuses)} Showing canvas 1 of {len(output_paths)}. Double-tap to open all canvases."
            )
            last_output_paths.clear()
            last_output_paths.extend(output_paths)
            page.update()

        if not output_paths:
            status.value = "Failed to generate any canvases."
            page.update()
            return None, None, None

        return output_paths, canvas_sizes, orientation

    generate_button = ft.ElevatedButton("Generate A-Series Layout", on_click=lambda e: generate_layout())

    page.add(
        ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Column(
                            col={"xs": 12, "md": 6},
                            controls=[
                                ft.Text("Upload multiple photos to generate a printable layout with A-series proportions, maximizing filled area.", size=14),
                                cmyk_mode,
                                padding_enabled,
                                padding_size,
                                num_canvases_input,
                                ft.Text("Uploaded Photos:", size=14),
                                ft.Container(
                                    content=photo_list,
                                    height=page.height * 0.4,
                                    border=ft.border.all(1, ft.Colors.BLACK),
                                    border_radius=5
                                ),
                                ft.Row(
                                    [
                                        add_button,
                                        trash_button,
                                        increase_button,
                                        decrease_button,
                                        select_all_button,
                                        deselect_all_button,
                                        invert_selection_button,
                                        clear_selection_button,
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                generate_button,
                                status,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Column(
                            col={"xs": 12, "md": 6},
                            controls=[
                                ft.Text("Canvas Previews (Double-tap to open all canvases):", size=14),
                                ft.Row(
                                    [
                                        prev_button,
                                        canvas_index_text,
                                        next_button
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                ft.Container(
                                    content=canvas_previews,
                                    border=ft.border.all(1, ft.Colors.BLUE_500),
                                    border_radius=5
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    )

    def on_resize(e):
        photo_size = get_list_params()
        for ctrl in photo_list.controls:
            ctrl.controls[0].controls[1].width = photo_size
            ctrl.controls[0].controls[1].height = photo_size
            scale_pct = int((scale_factors[photo_list.controls.index(ctrl)] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[photo_list.controls.index(ctrl)] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
            ctrl.controls[0].controls[3].value = f"Area: {area_percentages[photo_list.controls.index(ctrl)]:.2f}%"
        for ctrl in canvas_previews.controls:
            ctrl.content.content.width = page.width * 0.4 / a_series_ratio
            ctrl.content.content.height = page.height * 0.4
        page.update()

    page.on_resize = on_resize

ft.app(target=main, assets_dir="assets")