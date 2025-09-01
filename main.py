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

    # Generate button
    def generate_layout(e):
        if not images:
            status.value = "No images loaded. Please upload photos first."
            page.update()
            return

        # A-series aspect ratio (height/width ≈ 1.414)
        a_series_ratio = math.sqrt(2)  # ≈1.4142135623730951

        # Original sizes
        orig_sizes = [(img.width, img.height) for img in images]
        num_images = len(images)

        if num_images == 0:
            status.value = "No images to pack."
            page.update()
            return

        # Try packing with original sizes
        # Start with a small canvas and scale up until all images fit
        base_width = max(w for w, h in orig_sizes)  # Start with largest image width
        scale = 1.0
        step = 0.5
        max_attempts = 20

        for _ in range(max_attempts):
            canvas_width = int(base_width * scale)
            canvas_height = int(canvas_width * a_series_ratio)

            packer = newPacker(rotation=True)
            for i, (w, h) in enumerate(orig_sizes):
                packer.add_rect(w, h, rid=i)
            packer.add_bin(canvas_width, canvas_height)
            packer.pack()

            if len(packer.rect_list()) == num_images:
                break
            scale += step  # Increase canvas size

        if len(packer.rect_list()) != num_images:
            status.value = "Could not fit all images even with larger canvas."
            page.update()
            return

        # Create canvas with final dimensions
        canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))

        # Place images on canvas
        all_rects = packer.rect_list()
        for _, x, y, w, h, rid in all_rects:
            img = images[rid]
            # Determine if rotated
            if w == img.height and h == img.width:
                img = img.rotate(90, expand=True)
            # Paste onto canvas without resizing
            canvas.paste(img, (x, y))

        # Save the output
        output_path = "a_series_photo_layout.png"
        try:
            canvas.save(output_path)
            status.value = f"Layout generated and saved as '{output_path}'. Canvas size: {canvas_width}x{canvas_height} pixels."
        except Exception as ex:
            status.value = f"Error saving file: {str(ex)}"

        page.update()

    generate_button = ft.ElevatedButton("Generate A-Series Layout", on_click=generate_layout)

    # Add components to page
    page.add(
        ft.Column([
            ft.Text(
                "Upload multiple photos to generate a printable layout with A-series proportions."
            ),
            pick_button,
            generate_button,
            status,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    ))

ft.app(target=main)