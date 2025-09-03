import math
import os
import platform
import subprocess
from datetime import datetime

import flet as ft
from PIL import Image
from rectpack import newPacker


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
    last_output_path = [None]  # Store last generated collage path

    # Status text
    status = ft.Text("", size=14)

    # Checkbox for CMYK mode
    cmyk_mode = ft.Checkbox(
        label="Use CMYK color profile for printing (saves as TIFF)", value=False
    )

    # Checkbox and input for padding
    padding_enabled = ft.Checkbox(
        label="Add padding border around photos for easier cutting", value=False
    )
    padding_size = ft.TextField(label="Padding size (pixels)", value="10", width=150, disabled=True)

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
    photo_list = ft.ListView(expand=True, spacing=10, padding=15, auto_scroll=True)

    # Image control for previewing the final collage
    a_series_ratio = math.sqrt(2)
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
        width=page.width * 0.4 / a_series_ratio,
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

    file_picker = ft.FilePicker(on_result=handle_upload)
    page.overlay.append(file_picker)

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

    # Generate and save collage
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

        padding = (
            int(padding_size.value) if padding_enabled.value and padding_size.value.isdigit() else 0
        )
        padding = max(0, padding)

        portrait_w, portrait_h = find_min_canvas(orig_sizes, num_images, a_series_ratio)
        portrait_area = portrait_w * portrait_h if portrait_w != float('inf') else float('inf')
        landscape_w, landscape_h = find_min_canvas(orig_sizes, num_images, 1 / a_series_ratio)
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

        packer = newPacker(rotation=True)
        for i, (w, h) in enumerate(orig_sizes):
            scaled_w = max(1, int(w * scale_factors[i]))
            scaled_h = max(1, int(h * scale_factors[i]))
            packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=i)
        packer.add_bin(canvas_width, canvas_height)
        packer.pack()

        if len(packer.rect_list()) != num_images:
            status.value = "Packing failed unexpectedly."
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

        for i, ctrl in enumerate(photo_list.controls):
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            area_pct = area_percentages[i]
            ctrl.controls[0].controls[3].value = f"Area: {area_pct:.2f}%"
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = "tiff" if cmyk_mode.value else "png"
        output_path = f"a_series_photo_layout_{timestamp}.{file_ext}"
        preview_path = (
            f"a_series_photo_layout_preview_{timestamp}.png" if cmyk_mode.value else output_path
        )

        try:
            canvas.save(output_path)
            if cmyk_mode.value:
                rgb_canvas = canvas.convert("RGB")
                rgb_canvas.save(preview_path)
            if not save_only:
                collage_preview.src = preview_path
                collage_preview.visible = True
                last_output_path[0] = output_path
                status.value = f"Layout generated and saved as '{output_path}'. Orientation: {orientation}. Canvas size: {canvas_width}x{canvas_height} pixels. Unused area percentage: {unused_pct:.2f}%. Double-tap the preview to open in default viewer."
                page.update()
            return output_path, canvas_width, canvas_height
        except Exception as ex:
            status.value = f"Error saving file: {str(ex)}"
            page.update()
            return None, None, None

    generate_button = ft.ElevatedButton(
        "Generate A-Series Layout", on_click=lambda e: generate_layout()
    )

    page.add(
        ft.Column([
            ft.ResponsiveRow([
                ft.Column(
                    col={"xs": 12, "md": 6},
                    controls=[
                        ft.Text(
                            "Upload multiple photos to generate a printable layout with A-series proportions, maximizing filled area.",
                            size=14,
                        ),
                        cmyk_mode,
                        padding_enabled,
                        padding_size,
                        ft.Text("Uploaded Photos:", size=14),
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
                        generate_button,
                        status,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    col={"xs": 12, "md": 6},
                    controls=[
                        ft.Text("Collage Preview (Double-tap to open):", size=14),
                        collage_preview_gesture,
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
        photo_size = get_list_params()
        for ctrl in photo_list.controls:
            ctrl.controls[0].controls[1].width = photo_size
            ctrl.controls[0].controls[1].height = photo_size
            scale_pct = int((scale_factors[photo_list.controls.index(ctrl)] - 1.0) * 100)
            scale_color = (
                ft.Colors.GREEN
                if scale_factors[photo_list.controls.index(ctrl)] >= 1.0
                else ft.Colors.RED
            )
            ctrl.controls[0].controls[4].value = f"Scale: {scale_pct}%"
            ctrl.controls[0].controls[4].color = scale_color
            ctrl.controls[0].controls[
                3
            ].value = f"Area: {area_percentages[photo_list.controls.index(ctrl)]:.2f}%"
        collage_preview.width = page.width * 0.4 / a_series_ratio
        collage_preview.height = page.height * 0.4
        page.update()

    page.on_resize = on_resize

ft.app(target=main)