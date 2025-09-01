import math

import flet as ft
from PIL import Image
from rectpack import newPacker


def main(page: ft.Page):
    page.title = "Photo Arranger for A-Series Printing with Rectpack"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.update()

    # List to hold loaded images
    images = []

    # Status text
    status = ft.Text("")

    # File picker for multiple images
    file_picker = ft.FilePicker(on_result=handle_upload)
    page.overlay.append(file_picker)

    def handle_upload(e: ft.FilePickerResultEvent):
        if e.files:
            images.clear()
            for f in e.files:
                try:
                    img = Image.open(f.path)
                    images.append(img)
                except Exception as ex:
                    status.value = f"Error loading {f.name}: {str(ex)}"
                    page.update()
                    return
            status.value = f"Loaded {len(images)} images successfully."
            page.update()

    # Button to pick files
    pick_button = ft.ElevatedButton(
        "Upload Photos",
        on_click=lambda _: file_picker.pick_files(
            allow_multiple=True, allowed_extensions=["jpg", "jpeg", "png"]
    ),)

    # Function to find minimal canvas for a given ratio (height / width)
    def find_min_canvas(orig_sizes, num_images, ratio):
        # Calculate requirements
        min_side_req = max(min(w, h) for w, h in orig_sizes)
        max_side_req = max(max(w, h) for w, h in orig_sizes)
        low = max(min_side_req, math.ceil(max_side_req / ratio))
        high = sum(max(w, h) for w, h in orig_sizes) * 2  # Upper bound

        min_width = float('inf')
        min_height = float('inf')

        while low < high:
            mid = (low + high) // 2
            cw = mid
            ch = int(mid * ratio)
            packer = newPacker(rotation=True)
            for i, (w, h) in enumerate(orig_sizes):
                packer.add_rect(w, h, rid=i)
            packer.add_bin(cw, ch)
            packer.pack()
            if len(packer.rect_list()) == num_images:
                high = mid
                min_width = cw
                min_height = ch
            else:
                low = mid + 1

        return min_width, min_height

    # Generate button
    def generate_layout(e):
        if not images:
            status.value = "No images loaded. Please upload photos first."
            page.update()
            return

        # A-series aspect ratio (sqrt(2) ≈ 1.414)
        a_series_ratio = math.sqrt(2)

        # Original sizes
        orig_sizes = [(img.width, img.height) for img in images]
        num_images = len(images)

        if num_images == 0:
            status.value = "No images to pack."
            page.update()
            return

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
            return

        # Pack with the chosen size
        packer = newPacker(rotation=True)
        for i, (w, h) in enumerate(orig_sizes):
            packer.add_rect(w, h, rid=i)
        packer.add_bin(canvas_width, canvas_height)
        packer.pack()

        if len(packer.rect_list()) != num_images:
            status.value = "Packing failed unexpectedly."
            page.update()
            return

        # Calculate unused area percentage
        total_image_area = sum(w * h for w, h in orig_sizes)
        canvas_area = canvas_width * canvas_height
        if canvas_area > 0:
            unused_pct = ((canvas_area - total_image_area) / canvas_area) * 100
        else:
            unused_pct = 0.0

        # Create canvas
        canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))

        # Place images on canvas
        all_rects = packer.rect_list()
        for _, x, y, w, h, rid in all_rects:
            img = images[rid]
            # Determine if rotated
            orig_w, orig_h = orig_sizes[rid]
            if w == orig_h and h == orig_w:
                img = img.rotate(90, expand=True)
            # Paste onto canvas without resizing
            canvas.paste(img, (x, y))

        # Save the output
        output_path = "a_series_photo_layout.png"
        try:
            canvas.save(output_path)
            status.value = f"Layout generated and saved as '{output_path}'. Orientation: {orientation}. Canvas size: {canvas_width}x{canvas_height} pixels. Unused area percentage: {unused_pct:.2f}%"
        except Exception as ex:
            status.value = f"Error saving file: {str(ex)}"

        page.update()

    generate_button = ft.ElevatedButton("Generate A-Series Layout", on_click=generate_layout)

    # Add components to page
    page.add(
        ft.Column([
            ft.Text(
                "Upload multiple photos to generate a printable layout with A-series proportions, maximizing filled area."
            ),
            pick_button,
            generate_button,
            status,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    ))

ft.app(target=main)