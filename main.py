import math
from datetime import datetime

import flet as ft
from PIL import Image
from rectpack import newPacker


def main(page: ft.Page):
    page.title = "Photo Arranger for A-Series Printing with Rectpack"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 10
    page.update()

    # List to hold loaded images, their file paths, and scaling factors
    images = []
    file_paths = []
    scale_factors = []  # Scaling factor for each image (1.0 = original size)

    # Status text
    status = ft.Text("")

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

    # Grid view for uploaded photo previews
    def get_grid_params():
        # Adjust grid parameters based on screen width
        screen_width = page.width
        if screen_width < 600:  # Mobile
            return 2, 120  # 2 columns, smaller images
        if screen_width < 900:  # Tablet
            return 3, 130
        return 4, 150

    runs_count, max_extent = get_grid_params()
    photo_grid = ft.GridView(
        expand=True,
        runs_count=runs_count,
        max_extent=max_extent,
        spacing=10,
        run_spacing=10,
        padding=10,
        auto_scroll=True,
    )

    # Image control for previewing the final collage
    a_series_ratio = math.sqrt(2)
    collage_preview = ft.Image(
        src="",
        width=page.width * 0.4 / a_series_ratio,  # 40% of screen width, adjusted for aspect ratio
        height=page.height * 0.4,  # 40% of screen height
        fit=ft.ImageFit.CONTAIN,
        visible=False,
    )

    # File picker for multiple images
    file_picker = ft.FilePicker(on_result=handle_upload)
    page.overlay.append(file_picker)

    def handle_upload(e: ft.FilePickerResultEvent):
        if e.files:
            # Clear if no images exist to mimic initial upload
            if not images:
                images.clear()
                file_paths.clear()
                scale_factors.clear()
                photo_grid.controls.clear()
            added_count = 0
            for f in e.files:
                if f.path in file_paths:
                    continue  # Skip duplicate files
                try:
                    img = Image.open(f.path)
                    # Convert to CMYK if selected
                    if cmyk_mode.value:
                        img = img.convert("CMYK")
                    images.append(img)
                    file_paths.append(f.path)
                    scale_factors.append(1.0)  # Initialize scale factor to 1.0 (original size)
                    # Calculate scale percentage text and color
                    scale_pct = 0  # 100% is original size, 0% change
                    scale_color = ft.Colors.BLACK
                    # Add image preview with checkbox and scale percentage to grid view
                    photo_grid.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Image(
                                    src=f.path,
                                    width=max_extent - 20,
                                    height=max_extent - 20,
                                    fit=ft.ImageFit.CONTAIN,
                                    border_radius=5,
                                ),
                                ft.Checkbox(label=""),
                                ft.Text(value=f"{scale_pct}%", size=12, color=scale_color),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            alignment=ft.alignment.center,
                    ))
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

    # Add more button
    add_button = ft.IconButton(
        icon=ft.Icons.ADD,
        on_click=lambda _: file_picker.pick_files(
            allow_multiple=True, allowed_extensions=["jpg", "jpeg", "png"]
    ),)

    # Delete selected button
    def delete_selected(e):
        to_delete = []
        for i, ctrl in enumerate(photo_grid.controls):
            checkbox = ctrl.content.controls[1]  # The checkbox is the second control in the column
            if checkbox.value:
                to_delete.append(i)
        for i in sorted(to_delete, reverse=True):
            del images[i]
            del file_paths[i]
            del scale_factors[i]
            del photo_grid.controls[i]
        status.value = f"Deleted {len(to_delete)} images."
        collage_preview.visible = False
        page.update()

    trash_button = ft.IconButton(icon=ft.Icons.DELETE, on_click=delete_selected)

    # Increase size button
    def increase_size(e):
        selected_count = 0
        for i, ctrl in enumerate(photo_grid.controls):
            checkbox = ctrl.content.controls[1]
            if not checkbox.value:
                continue
            selected_count += 1
            scale_factors[i] *= 1.1
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.content.controls[2].value = f"{scale_pct}%"
            ctrl.content.controls[2].color = scale_color
        if selected_count == 0:
            status.value = "No photos selected to increase size."
        else:
            status.value = f"Increased size of {selected_count} selected photos by 10%."
        collage_preview.visible = False
        page.update()

    increase_button = ft.IconButton(
        icon=ft.Icons.ZOOM_IN, icon_color=ft.Colors.GREEN, on_click=increase_size
    )

    # Decrease size button
    def decrease_size(e):
        selected_count = 0
        for i, ctrl in enumerate(photo_grid.controls):
            checkbox = ctrl.content.controls[1]
            if not checkbox.value:
                continue
            selected_count += 1
            scale_factors[i] /= 1.1
            scale_factors[i] = max(scale_factors[i], 0.1)
            scale_pct = int((scale_factors[i] - 1.0) * 100)
            scale_color = ft.Colors.GREEN if scale_factors[i] >= 1.0 else ft.Colors.RED
            ctrl.content.controls[2].value = f"{scale_pct}%"
            ctrl.content.controls[2].color = scale_color
        if selected_count == 0:
            status.value = "No photos selected to decrease size."
        else:
            status.value = f"Decreased size of {selected_count} selected photos by 10%."
        collage_preview.visible = False
        page.update()

    decrease_button = ft.IconButton(
        icon=ft.Icons.ZOOM_OUT, icon_color=ft.Colors.RED, on_click=decrease_size
    )

    # Function to find minimal canvas for a given ratio (height / width)
    def find_min_canvas(orig_sizes, num_images, ratio):
        # Get padding value
        padding = (
            int(padding_size.value) if padding_enabled.value and padding_size.value.isdigit() else 0
        )
        padding = max(0, padding)  # Ensure non-negative
        min_side_req = max(
            min(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors)
        )
        max_side_req = max(
            max(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors)
        )
        low = max(min_side_req, math.ceil(max_side_req / ratio))
        high = (
            sum(max(w * s, h * s) + 2 * padding for (w, h), s in zip(orig_sizes, scale_factors)) * 2
        )  # Upper bound

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
                # Add padding to dimensions for packing
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

        # A-series aspect ratio (sqrt(2) ≈ 1.414)
        a_series_ratio = math.sqrt(2)

        # Original sizes
        orig_sizes = [(img.width, img.height) for img in images]
        num_images = len(images)

        if num_images == 0:
            status.value = "No images to pack."
            page.update()
            return None, None, None

        # Get padding value
        padding = (
            int(padding_size.value) if padding_enabled.value and padding_size.value.isdigit() else 0
        )
        padding = max(0, padding)  # Ensure non-negative

        # Find minimal canvas for portrait (tall) orientation
        portrait_w, portrait_h = find_min_canvas(orig_sizes, num_images, a_series_ratio)
        portrait_area = portrait_w * portrait_h if portrait_w != float('inf') else float('inf')

        # Find minimal canvas for landscape (wide) orientation
        landscape_w, landscape_h = find_min_canvas(orig_sizes, num_images, 1 / a_series_ratio)
        landscape_area = landscape_w * landscape_h if landscape_w != float('inf') else float('inf')

        # Choose the orientation with smaller area (higher fill ratio)
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

        # Pack with the chosen size
        packer = newPacker(rotation=True)
        for i, (w, h) in enumerate(orig_sizes):
            scaled_w = max(1, int(w * scale_factors[i]))
            scaled_h = max(1, int(h * scale_factors[i]))
            # Add padding to dimensions for packing
            packer.add_rect(scaled_w + 2 * padding, scaled_h + 2 * padding, rid=i)
        packer.add_bin(canvas_width, canvas_height)
        packer.pack()

        if len(packer.rect_list()) != num_images:
            status.value = "Packing failed unexpectedly."
            page.update()
            return None, None, None

        # Calculate unused area percentage
        total_image_area = sum(
            (w * s + 2 * padding) * (h * s + 2 * padding)
            for (w, h), s in zip(orig_sizes, scale_factors)
        )
        canvas_area = canvas_width * canvas_height
        if canvas_area > 0:
            unused_pct = ((canvas_area - total_image_area) / canvas_area) * 100
        else:
            unused_pct = 0.0

        # Create canvas
        mode = "CMYK" if cmyk_mode.value else "RGB"
        canvas = Image.new(
            mode,
            (int(canvas_width), int(canvas_height)),
            (255, 255, 255) if mode == "RGB" else (0, 0, 0, 0),
        )

        # Place images on canvas with padding
        all_rects = packer.rect_list()
        for _, x, y, w, h, rid in all_rects:
            img = images[rid]
            # Determine if rotated
            orig_w, orig_h = orig_sizes[rid]
            scaled_w = max(1, int(orig_w * scale_factors[rid]))
            scaled_h = max(1, int(orig_h * scale_factors[rid]))
            if w == scaled_h + 2 * padding and h == scaled_w + 2 * padding:
                img = img.rotate(90, expand=True)
                scaled_w, scaled_h = scaled_h, scaled_w  # Swap dimensions for rotated image
            # Resize image to scaled dimensions (without padding)
            img_resized = img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            # Create a new image with padding
            padded_w = scaled_w + 2 * padding
            padded_h = scaled_h + 2 * padding
            padded_img = Image.new(
                mode, (padded_w, padded_h), (255, 255, 255) if mode == "RGB" else (0, 0, 0, 0)
            )
            padded_img.paste(img_resized, (padding, padding))
            # Paste padded image onto canvas
            canvas.paste(padded_img, (x, y))

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = "tiff" if cmyk_mode.value else "png"
        output_path = f"a_series_photo_layout_{timestamp}.{file_ext}"
        preview_path = (
            f"a_series_photo_layout_preview_{timestamp}.png" if cmyk_mode.value else output_path
        )

        try:
            canvas.save(output_path)
            if cmyk_mode.value:
                # Convert CMYK to RGB for preview
                rgb_canvas = canvas.convert("RGB")
                rgb_canvas.save(preview_path)
            if not save_only:
                # Update preview
                collage_preview.src = preview_path
                collage_preview.visible = True
                status.value = f"Layout generated and saved as '{output_path}'. Orientation: {orientation}. Canvas size: {canvas_width}x{canvas_height} pixels. Unused area percentage: {unused_pct:.2f}%. Open this file in an image viewer to print."
                page.update()
            return output_path, canvas_width, canvas_height
        except Exception as ex:
            status.value = f"Error saving file: {str(ex)}"
            page.update()
            return None, None, None

    # Generate button
    generate_button = ft.ElevatedButton(
        "Generate A-Series Layout", on_click=lambda e: generate_layout()
    )

    # Responsive layout wrapped in a scrollable column
    page.add(
        ft.Column([
            ft.ResponsiveRow([
                ft.Column(
                    col={"xs": 12, "md": 6},  # Full width on small screens, half on medium+
                    controls=[
                        ft.Text(
                            "Upload multiple photos to generate a printable layout with A-series proportions, maximizing filled area."
                        ),
                        cmyk_mode,
                        padding_enabled,
                        padding_size,
                        ft.Text("Uploaded Photos:"),
                        ft.Container(
                            content=photo_grid,
                            height=page.height * 0.4,  # 40% of screen height
                            border=ft.border.all(1, ft.Colors.BLACK),
                            border_radius=5,
                        ),
                        ft.Row([
                            trash_button,
                            add_button,
                            increase_button,
                            decrease_button,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        generate_button,
                        status,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    col={"xs": 12, "md": 6},  # Full width on small screens, half on medium+
                    controls=[
                        ft.Text("Collage Preview:"),
                        collage_preview,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )],
            scroll=ft.ScrollMode.AUTO,  # Enable vertical scrolling
            expand=True,
    ))

    # Update layout on window resize
    def on_resize(e):
        runs_count, max_extent = get_grid_params()
        photo_grid.runs_count = runs_count
        photo_grid.max_extent = max_extent
        for ctrl in photo_grid.controls:
            ctrl.content.controls[0].width = max_extent - 20
            ctrl.content.controls[0].height = max_extent - 20
        collage_preview.width = page.width * 0.4 / a_series_ratio
        collage_preview.height = page.height * 0.4
        page.update()

    page.on_resize = on_resize

ft.app(target=main)