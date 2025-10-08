import math
import os
import platform
import subprocess
from datetime import datetime

import flet as ft
from PIL import Image, ImageDraw, ImageFont
from rectpack import newPacker


def main(page: ft.Page):
    page.title = (
        "Efficient Photo Arranger - Packing photos in a print-ready collage in desired paper ratio"
    )
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 10
    page.window.height = 1000
    page.window.width = 1400
    page.update()

    # Lists to hold loaded images, their file paths, and scaling factors
    images = []
    file_paths = []
    scale_factors = []
    area_percentages = []
    last_output_path = [None]
    logo_path = [os.path.join("assets", "icon.png")]
    custom_logo_path = [None]
    save_directory = [os.getcwd()]  # Default to current working directory

    # Status text
    status = ft.Text("No photos selected yet!", size=14)

    # Checkbox for CMYK mode
    cmyk_mode = ft.Checkbox(
        label="CMYK color profile - use it for printing (saves as TIFF)", value=False
    )

    # Checkbox and input for padding
    padding_enabled = ft.Checkbox(
        label="White border between photos for easier cutting", value=False
    )
    padding_size = ft.TextField(label="Margin size (pixels)", value="10", width=150, disabled=True)

    # Checkbox and inputs for logo and watermark
    logo_enabled = ft.Checkbox(label="Add logo", value=True)
    watermark_enabled = ft.Checkbox(label="Add watermark text", value=True)
    watermark_text = ft.TextField(
        label="Watermark Text",
        value="Karrayan Office Equipment Store",
        width=300,
        multiline=True,
        min_lines=1,
        max_lines=3,
        content_padding=10,
    )
    font_size_dropdown = ft.Dropdown(
        label="Font Size",
        options=[
            ft.dropdown.Option("12"),
            ft.dropdown.Option("16"),
            ft.dropdown.Option("20"),
            ft.dropdown.Option("24"),
            ft.dropdown.Option("28"),
            ft.dropdown.Option("32"),
        ],
        value="24",
        width=100,
        disabled=not watermark_enabled.value,
    )
    typeface_dropdown = ft.Dropdown(
        label="Typeface",
        options=[
            ft.dropdown.Option("arial.ttf", text="Arial"),
            ft.dropdown.Option("times.ttf", text="Times New Roman"),
            ft.dropdown.Option("cour.ttf", text="Courier New"),
        ],
        value="arial.ttf",
        width=150,
        disabled=not watermark_enabled.value,
    )
    replace_logo_button = ft.ElevatedButton(
        "Replace Logo",
        on_click=lambda _: logo_file_picker.pick_files(
            allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg"]
    ),)
    logo_preview = ft.Image(
        src=logo_path[0] if os.path.exists(logo_path[0]) else "",
        width=50,
        height=50,
        fit=ft.ImageFit.CONTAIN,
        border_radius=5,
        visible=os.path.exists(logo_path[0]),
    )
    logo_preview_container = ft.Container(
        content=logo_preview,
        border=ft.border.all(1, ft.Colors.BLUE_500),
        border_radius=5,
        width=60,
        height=60,
        padding=5,
    )

    # Save directory selection
    save_dir_display = ft.Text(
        f"Save to: {os.path.basename(save_directory[0])}",
        size=12,
        width=200,
        tooltip=save_directory[0],
    )
    select_save_dir_button = ft.ElevatedButton(
        "Select Save Directory", on_click=lambda _: save_dir_picker.get_directory_path()
    )

    def on_padding_toggle(e):
        padding_size.disabled = not padding_enabled.value
        page.update()

    def on_watermark_toggle(e):
        watermark_text.disabled = not watermark_enabled.value
        font_size_dropdown.disabled = not watermark_enabled.value
        typeface_dropdown.disabled = not watermark_enabled.value
        page.update()

    padding_enabled.on_change = on_padding_toggle
    watermark_enabled.on_change = on_watermark_toggle

    # Paper ratio selection
    paper_ratios = {
        "A Series": math.sqrt(2),
        "B Series": 1.0 / math.sqrt(2),
        "C Series": 1.0 / math.sqrt(2),
        "Letter": 11.0 / 8.5,
        "Custom ratio": None,
    }
    current_ratio = paper_ratios["A Series"]
    custom_ratio = ft.TextField(
        label="Custom Ratio (e.g., 5:7 or 1.4286)", value="", width=150, visible=False
    )

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

    def update_ratio(e):
        nonlocal current_ratio
        selected_ratio = paper_ratio_dropdown.value
        if selected_ratio == "Custom ratio":
            custom_ratio.visible = True
            current_ratio = parse_ratio(custom_ratio.value)
            if current_ratio == 1.0:
                status.value = "Invalid custom ratio, using 1:1."
        else:
            custom_ratio.visible = False
            current_ratio = paper_ratios[selected_ratio]
        collage_preview.width = page.width * 0.4 / current_ratio
        page.update()

    def on_custom_ratio_change(e):
        nonlocal current_ratio
        if paper_ratio_dropdown.value == "Custom ratio":
            current_ratio = parse_ratio(custom_ratio.value)
            if current_ratio == 1.0:
                status.value = "Invalid custom ratio, using 1:1."
            collage_preview.width = page.width * 0.4 / current_ratio
            page.update()

    custom_ratio.on_change = on_custom_ratio_change
    paper_ratio_dropdown = ft.Dropdown(
        label="Paper Ratio",
        options=[
            ft.dropdown.Option("A Series"),
            ft.dropdown.Option("B Series"),
            ft.dropdown.Option("C Series"),
            ft.dropdown.Option("Letter"),
            ft.dropdown.Option("Custom ratio"),
        ],
        value="A Series",
        on_change=update_ratio,
        width=140,
    )

    # List view for uploaded photo previews
    def get_list_params():
        screen_width = page.width
        if screen_width < 600:
            return 100
        if screen_width < 900:
            return 120
        return 150

    photo_size = get_list_params()
    photo_list = ft.ListView(expand=True, spacing=10, padding=15, auto_scroll=True)

    # Image control for previewing the final collage
    def open_collage(e):
        if last_output_path[0]:
            try:
                if platform.system() == "Windows":
                    os.startfile(last_output_path[0])
                else:
                    opener = "open" if platform.system() == "Darwin" else "xdg-open"
                    subprocess.run([opener, last_output_path[0]])
                status.value = (
                    f"Opened collage '{os.path.basename(last_output_path[0])}' in default viewer."
                )
            except Exception as ex:
                status.value = f"Error opening collage: {str(ex)}"
            page.update()
        else:
            status.value = "No collage generated yet."

    collage_preview = ft.Image(
        src="",
        width=page.width * 0.4 / current_ratio,
        height=page.height * 0.4,
        fit=ft.ImageFit.CONTAIN,
        visible=False,
        border_radius=5,
    )
    collage_preview_container = ft.Container(
        content=collage_preview, border=ft.border.all(1, ft.Colors.BLUE_500), border_radius=5
    )
    collage_preview_gesture = ft.GestureDetector(
        content=collage_preview_container, on_double_tap=open_collage
    )

    # File picker handlers
    def handle_photo_upload(e: ft.FilePickerResultEvent):
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
                    continue
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
                                    border_radius=5,
                                ),
                                ft.Text(
                                    file_name,
                                    size=12,
                                    width=150,
                                    text_align=ft.TextAlign.LEFT,
                                ),
                                ft.Text(
                                    dimensions,
                                    size=12,
                                    width=100,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    "Area: 0.00%",
                                    size=12,
                                    width=100,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    value=f"Scale: {scale_pct}%",
                                    size=12,
                                    color=scale_color,
                                    width=100,
                                    text_align=ft.TextAlign.CENTER,
                                ),],
                                alignment=ft.MainAxisAlignment.START,
                                spacing=10,
                            ),
                            ft.Divider(),
                    ]))
                    added_count += 1
                except Exception as ex:
                    status.value = f"Error loading {f.name}: {str(ex)}"
                    page.update()
                    return
            status.value = (
                f"{'Loaded' if not images else 'Added'} {added_count} new images successfully."
            )
            collage_preview.visible = False
            page.update()

    def handle_logo_upload(e: ft.FilePickerResultEvent):
        if e.files:
            custom_logo_path[0] = e.files[0].path
            logo_preview.src = custom_logo_path[0]
            logo_preview.visible = True
            status.value = f"Logo replaced with '{os.path.basename(custom_logo_path[0])}'."

        else:
            status.value = "No logo file selected."

        page.update()
    def handle_save_dir_select(e: ft.FilePickerResultEvent):
        if e.path:
            save_directory[0] = e.path
            save_dir_display.value = f"Save to: {os.path.basename(save_directory[0])}"
            save_dir_display.tooltip = save_directory[0]
            status.value = f"Save directory set to '{save_directory[0]}'."

        else:
            status.value = "No directory selected, using default directory."

        page.update()
    file_picker = ft.FilePicker(on_result=handle_photo_upload)
    logo_file_picker = ft.FilePicker(on_result=handle_logo_upload)
    save_dir_picker = ft.FilePicker(on_result=handle_save_dir_select)
    page.overlay.extend([file_picker, logo_file_picker, save_dir_picker])

    # Add file button
    add_button = ft.IconButton(
        icon=ft.Icons.ADD,
        on_click=lambda _: file_picker.pick_files(
            allow_multiple=True, allowed_extensions=["jpg", "jpeg", "png"]
    ),)

    # Delete selected button
    def delete_selected(e):
        to_delete = []
        for i, ctrl in enumerate(photo_list.controls):
            checkbox = ctrl.controls[0].controls[0]
            if checkbox.value:
                to_delete.append(i)
        for i in sorted(to_delete, reverse=True):
            del images[i]
            del file_paths[i]
            del scale_factors[i]
            del area_percentages[i]
            del photo_list.controls[i]
        status.value = f"Deleted {len(to_delete)} images."
        collage_preview.visible = False
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
        collage_preview.visible = False
        for i, ctrl in enumerate(photo_list.controls):
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
        page.update()

    increase_button = ft.IconButton(
        icon=ft.Icons.ZOOM_IN, icon_color=ft.Colors.GREEN, on_click=increase_size
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
        collage_preview.visible = False
        for i, ctrl in enumerate(photo_list.controls):
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
        page.update()

    decrease_button = ft.IconButton(
        icon=ft.Icons.ZOOM_OUT, icon_color=ft.Colors.RED, on_click=decrease_size
    )

    # Select all button
    def select_all(e):
        selected_count = 0
        for ctrl in photo_list.controls:
            checkbox = ctrl.controls[0].controls[0]
            if not checkbox.value:
                checkbox.value = True
                selected_count += 1
        status.value = (
            f"Selected {selected_count} images."
            if selected_count > 0
            else "All images already selected."
        )
        page.update()

    select_all_button = ft.IconButton(
        icon=ft.Icons.CHECK_BOX, icon_color=ft.Colors.BLUE, on_click=select_all
    )

    # Deselect all button
    def deselect_all(e):
        deselected_count = 0
        for ctrl in photo_list.controls:
            checkbox = ctrl.controls[0].controls[0]
            if checkbox.value:
                checkbox.value = False
                deselected_count += 1
        status.value = (
            f"Deselected {deselected_count} images."
            if deselected_count > 0
            else "No images were selected."
        )
        page.update()

    deselect_all_button = ft.IconButton(
        icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, icon_color=ft.Colors.BLUE, on_click=deselect_all
    )

    # Invert selection button
    def invert_selection(e):
        toggled_count = 0
        for ctrl in photo_list.controls:
            checkbox = ctrl.controls[0].controls[0]
            checkbox.value = not checkbox.value
            toggled_count += 1
        status.value = (
            f"Inverted selection for {toggled_count} images."
            if toggled_count > 0
            else "No images to invert."
        )
        page.update()

    invert_selection_button = ft.IconButton(
        icon=ft.Icons.SWAP_HORIZ, icon_color=ft.Colors.BLUE, on_click=invert_selection
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
            collage_preview.visible = False
            page.update()
        else:
            status.value = "No images to clear."

    clear_selection_button = ft.IconButton(
        icon=ft.Icons.CLEAR_ALL, icon_color=ft.Colors.RED, on_click=clear_selection
    )

    # Function to find minimal canvas for a given ratio (height / width)
    def find_min_canvas(orig_sizes, num_images, ratio):
        padding = (
            int(padding_size.value) if padding_enabled.value and padding_size.value.isdigit() else 0
        )
        padding = max(0, padding)
        min_side_req = max(
            min(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors)
        )
        max_side_req = max(
            max(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors)
        )
        low = max(min_side_req, math.ceil(max_side_req / ratio))
        high = (
            sum(max(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors)) * 2
        )

        min_width = float('inf')
        min_height = float('inf')

        while low < high:
            mid = (low + high) // 2
            cw = mid
            ch = int(mid * ratio)
            packer = newPacker(rotation=True)
            for i, (w, h) in enumerate(orig_sizes):
                scaled_w = max(1, int(w * scale_factors[i]))
                scaled_h = max(1, int(h * scale_factors[i]))
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

    # Function to find free spaces in the canvas
    def find_free_spaces(canvas_width, canvas_height, rects, min_size=50):
        free_rects = [(0, 0, canvas_width, canvas_height)]
        new_free_rects = []
        for _, x, y, w, h, _ in rects:
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
            new_free_rects = []
        return [(x, y, w, h) for x, y, w, h in free_rects if w >= min_size and h >= min_size]

    # Generate and save collage
    def generate_layout(save_only=False):
        if not images:
            status.value = "No images loaded. Please upload photos first."
            page.update()
            return None, None, None

        orig_sizes = [(img.width, img.height) for img in images]
        num_images = len(images)

        if num_images == 0:
            status.value = "No images to pack."
            page.update()
            return None, None, None

        padding = (
            int(padding_size.value) if padding_enabled.value and padding_size.value.isdigit() else 0
        )
        padding = max(0, padding)

        # Use current_ratio for canvas dimensions
        portrait_w, portrait_h = find_min_canvas(orig_sizes, num_images, current_ratio)
        portrait_area = portrait_w * portrait_h if portrait_w != float('inf') else float('inf')
        landscape_w, landscape_h = find_min_canvas(orig_sizes, num_images, 1 / current_ratio)
        landscape_area = landscape_w * landscape_h if landscape_w != float('inf') else float('inf')

        if portrait_area <= landscape_area:
            canvas_width = portrait_w
            canvas_height = portrait_h
            orientation = "portrait"
        else:
            canvas_width = landscape_w
            canvas_height = landscape_h
            orientation = "landscape"

        if canvas_width == float('inf'):
            status.value = "Could not fit all images."
            page.update()
            return None, None, None

        # Pack photos and check for sufficient free space
        packer = newPacker(rotation=True)
        for i, (w, h) in enumerate(orig_sizes):
            scaled_w = max(1, int(w * scale_factors[i]))
            scaled_h = max(1, int(h * scale_factors[i]))
            packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=i)
        packer.add_bin(canvas_width, canvas_height)
        packer.pack()

        if len(packer.rect_list()) != num_images:
            # Increase canvas size incrementally until photos fit
            scale_factor = 1.05
            while len(packer.rect_list()) != num_images:
                canvas_width = int(canvas_width * scale_factor)
                canvas_height = int(canvas_height * scale_factor)
                packer = newPacker(rotation=True)
                for i, (w, h) in enumerate(orig_sizes):
                    scaled_w = max(1, int(w * scale_factors[i]))
                    scaled_h = max(1, int(h * scale_factors[i]))
                    packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=i)
                packer.add_bin(canvas_width, canvas_height)
                packer.pack()
                scale_factor += 0.05
                if scale_factor > 2.0:
                    status.value = "Could not fit all images even with larger canvas."
                    page.update()
                    return None, None, None

        canvas_area = canvas_width * canvas_height
        total_image_area = 0
        area_percentages.clear()
        all_rects = packer.rect_list()
        for _, x, y, w, h, rid in all_rects:
            orig_w, orig_h = orig_sizes[rid]
            scaled_w = max(1, int(orig_w * scale_factors[rid]))
            scaled_h = max(1, int(orig_h * scale_factors[rid]))
            if w == scaled_h + 2 * padding and h == scaled_w + 2 * padding:
                scaled_w, scaled_h = scaled_h, scaled_w
            image_area = scaled_w * scaled_h
            total_image_area += image_area
            if canvas_area > 0:
                area_pct = (image_area / canvas_area) * 100
            else:
                area_pct = 0.0
            area_percentages.append(area_pct)

        if canvas_area > 0:
            unused_pct = ((canvas_area - total_image_area) / canvas_area) * 100
        else:
            unused_pct = 0.0

        mode = "CMYK" if cmyk_mode.value else "RGB"
        canvas = Image.new(
            mode,
            (int(canvas_width), int(canvas_height)),
            (255, 255, 255) if mode == "RGB" else (0, 0, 0, 0),
        )

        for _, x, y, w, h, rid in all_rects:
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
            padded_img = Image.new(
                mode, (padded_w, padded_h), (255, 255, 255) if mode == "RGB" else (0, 0, 0, 0)
            )
            padded_img.paste(img_resized, (padding, padding))
            canvas.paste(padded_img, (x, y))

        # Add logo and/or watermark text in the largest free space if enabled
        logo_status = ""
        logo_added = False
        text_added = False
        shop_text = watermark_text.value.strip() if watermark_enabled.value else ""
        logo_available = logo_enabled.value and (
            custom_logo_path[0] or os.path.exists(logo_path[0])
        )
        should_add_elements = logo_available or shop_text

        if not should_add_elements:
            logo_status = (
                "No logo or watermark text selected."
                if (logo_enabled.value or watermark_enabled.value)
                else "Logo and watermark text disabled."
            )
        else:
            try:
                free_rects = find_free_spaces(canvas_width, canvas_height, all_rects, min_size=50)
                if not free_rects:
                    logo_status = "No free space available to add logo or watermark text."
                else:
                    # Select the largest free rectangle by area
                    largest_rect = max(free_rects, key=lambda r: r[2] * r[3], default=None)
                    if largest_rect:
                        fx, fy, fw, fh = largest_rect
                        draw = ImageDraw.Draw(canvas)
                        logo_w, logo_h, scaled_logo_w, scaled_logo_h = 0, 0, 0, 0
                        text_w, text_h = 0, 0
                        logo_x, logo_y = fx, fy

                        # Calculate text size if watermark text is enabled and non-empty
                        text_fits = shop_text
                        font_size = (
                            int(font_size_dropdown.value) if font_size_dropdown.value else 24
                        )
                        if shop_text:
                            try:
                                font = ImageFont.truetype(typeface_dropdown.value, size=font_size)
                            except:
                                font = ImageFont.load_default()
                            text_bbox = draw.textbbox((0, 0), shop_text, font=font)
                            text_w = text_bbox[2] - text_bbox[0]
                            text_h = text_bbox[3] - text_bbox[1]
                            # Adjust font size down if text doesn't fit
                            while text_w > fw or text_h > fh and font_size >= 12:
                                font_size -= 2
                                try:
                                    font = ImageFont.truetype(
                                        typeface_dropdown.value, size=font_size
                                    )
                                except:
                                    font = ImageFont.load_default()
                                text_bbox = draw.textbbox((0, 0), shop_text, font=font)
                                text_w = text_bbox[2] - text_bbox[0]
                                text_h = text_bbox[3] - text_bbox[1]
                            text_fits = text_w <= fw and text_h <= fh

                        # Calculate logo size if enabled and available
                        if logo_available:
                            current_logo_path = (
                                custom_logo_path[0] if custom_logo_path[0] else logo_path[0]
                            )
                            logo_img = Image.open(current_logo_path)
                            if cmyk_mode.value:
                                logo_img = logo_img.convert("CMYK")
                            logo_w, logo_h = logo_img.size
                            logo_scale = 0.98
                            if shop_text and text_fits:
                                scale = (
                                    min(fw / logo_w, (fh - text_h - 10) / logo_h, 1.0) * logo_scale
                                )
                            else:
                                scale = min(fw / logo_w, fh / logo_h, 1.0) * logo_scale
                            scaled_logo_w = int(logo_w * scale)
                            scaled_logo_h = int(logo_h * scale)

                        # Check if logo and text fit side by side
                        total_width = (
                            scaled_logo_w + 10 + text_w
                            if shop_text and logo_available and text_fits
                            else (
                                text_w
                                if shop_text and text_fits
                                else scaled_logo_w if logo_available else 0
                        ))
                        if (
                            total_width > fw
                            or max(scaled_logo_h, text_h if shop_text and text_fits else 0) > fh
                        ):
                            # Try fitting only logo or only text if both don't fit
                            if logo_available and shop_text and text_fits:
                                if scaled_logo_w <= fw and scaled_logo_h <= fh:
                                    total_width = scaled_logo_w
                                    text_fits = False
                                elif text_w <= fw and text_h <= fh:
                                    total_width = text_w
                                    scaled_logo_w = scaled_logo_h = 0
                                else:
                                    total_width = 0
                                    text_fits = False
                                    scaled_logo_w = scaled_logo_h = 0
                            elif shop_text and text_fits and text_w > fw:
                                text_fits = False
                                total_width = scaled_logo_w if logo_available else 0
                            elif logo_available and scaled_logo_w > fw:
                                scaled_logo_w = scaled_logo_h = 0
                                total_width = text_w if shop_text and text_fits else 0

                        # Paste logo if enabled and fits
                        if logo_available and scaled_logo_w > 0 and scaled_logo_h > 0:
                            logo_resized = logo_img.resize(
                                (scaled_logo_w, scaled_logo_h), Image.Resampling.LANCZOS
                            )
                            logo_x = fx + (fw - total_width) // 2
                            logo_y = fy + (fh - scaled_logo_h) // 2
                            canvas.paste(logo_resized, (logo_x, logo_y))
                            logo_added = True

                        # Paste text if enabled, not empty, and fits
                        if shop_text and text_fits:
                            text_x = (
                                (logo_x + scaled_logo_w + 10)
                                if logo_added
                                else fx + (fw - text_w) // 2
                            )
                            text_y = fy + (fh - text_h) // 2
                            text_color = (0, 0, 0) if mode == "RGB" else (0, 0, 0, 255)
                            draw.text((text_x, text_y), shop_text, font=font, fill=text_color)
                            text_added = True

                        if logo_added and text_added:
                            logo_status = "Logo and watermark text maximized in largest free space."
                        elif logo_added:
                            logo_status = (
                                "Logo maximized in largest free space, but watermark text does not fit."
                                if shop_text
                                else "Logo maximized in largest free space."
                            )
                        elif text_added:
                            logo_status = "Watermark text maximized in largest free space."
                        else:
                            logo_status = "Free space too small to add logo or watermark text."
                    else:
                        logo_status = "No suitable free space to add logo or watermark text."
            except Exception as ex:
                logo_status = f"Error loading or adding logo/watermark: {str(ex)}"

        for i, ctrl in enumerate(photo_list.controls):
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            area_pct = area_percentages[i]
            ctrl.controls[0].controls[3].value = f"Area: {area_pct:.2f}%"
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = "tiff" if cmyk_mode.value else "png"
        output_filename = f"a_series_photo_layout_{timestamp}.{file_ext}"
        output_path = os.path.join(save_directory[0], output_filename)
        preview_filename = (
            f"a_series_photo_layout_preview_{timestamp}.png" if cmyk_mode.value else output_filename
        )
        preview_path = os.path.join(save_directory[0], preview_filename)

        try:
            canvas.save(output_path)
            if cmyk_mode.value:
                rgb_canvas = canvas.convert("RGB")
                rgb_canvas.save(preview_path)
            if not save_only:
                collage_preview.src = preview_path
                collage_preview.visible = True
                last_output_path[0] = output_path
                status.value = (
                    f"Layout generated and saved as '{output_filename}' in '{save_directory[0]}'. "
                    f"Orientation: {orientation}. "
                    f"Canvas size: {canvas_width}x{canvas_height} pixels. "
                    f"Unused area percentage: {unused_pct:.2f}%. "
                    f"{logo_status} Double-tap the preview to open in default viewer."
                )
                page.update()
            return output_path, canvas_width, canvas_height
        except Exception as ex:
            status.value = f"Error saving file: {str(ex)}"
            page.update()
            return None, None, None

    generate_button = ft.ElevatedButton(
        "Arrange Photos into Canvas", on_click=lambda e: generate_layout()
    )

    page.add(
        ft.Column([
            ft.ResponsiveRow([
                ft.Column(
                    col={"xs": 12, "md": 6},
                    controls=[
                        ft.Text(
                            "Select multiple photos to generate a printable layout with desired proportions, minimizing waste area.",
                            size=12,
                        ),
                        ft.Text("Click + to add photos here:", size=16),
                        ft.Container(
                            content=photo_list,
                            height=page.height * 0.4,
                            border=ft.border.all(1, ft.Colors.BLACK),
                            border_radius=5,
                        ),
                        ft.Row([
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
                            spacing=10,
                        ),
                        ft.Divider(),
                        ft.Text("Settings:", size=16),
                        cmyk_mode,
                        ft.Row([
                            padding_enabled,
                            padding_size,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            spacing=10,
                        ),
                        ft.Row([
                            paper_ratio_dropdown,
                            custom_ratio,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            spacing=10,
                        ),
                        ft.Row([
                            logo_enabled,
                            logo_preview_container,
                            replace_logo_button,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            spacing=10,
                        ),
                        ft.Row([
                            watermark_enabled,
                            watermark_text,
                            font_size_dropdown,
                            typeface_dropdown,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            spacing=10,
                        ),
                        ft.Row([
                            select_save_dir_button,
                            save_dir_display,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            spacing=10,
                        ),
                        ft.Divider(),
                        generate_button,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    col={"xs": 12, "md": 6},
                    controls=[
                        ft.Text("Collage Preview (Double-tap to open):", size=14),
                        collage_preview_gesture,
                        status,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
    ))

    def on_resize(e):
        nonlocal photo_size
        photo_size = get_list_params()
        for ctrl in photo_list.controls:
            ctrl.controls[0].controls[1].width = photo_size
            ctrl.controls[0].controls[1].height = photo_size
            idx = photo_list.controls.index(ctrl)
            scale_pct = int((scale_factors[idx] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[idx] >= 1.0 else ft.Colors.RED
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
            ctrl.controls[0].controls[3].value = f"Area: {area_percentages[idx]:.2f}%"
        collage_preview.width = page.width * 0.4 / current_ratio
        collage_preview.height = page.height * 0.4
        # Ensure preview remains visible if it was already generated
        if last_output_path[0] and collage_preview.src:
            collage_preview.visible = True
        page.update()

    page.on_resize = on_resize

ft.app(target=main, assets_dir="assets")