import flet as ft
from PIL import Image, ImageOps
import math
import os

def main(page: ft.Page):
    page.title = "Photo Arranger for A4 Printing"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.update()

    # List to hold loaded images
    images = []

    # Status text
    status = ft.Text("")

    # File picker for multiple images
    file_picker = ft.FilePicker(on_result=lambda e: handle_upload(e))
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
            allow_multiple=True,
            allowed_extensions=["jpg", "jpeg", "png"]
        )
    )

    # Generate button
    def generate_layout(e):
        if not images:
            status.value = "No images loaded. Please upload photos first."
            page.update()
            return

        # Define A4 dimensions at 300 DPI for print quality
        dpi = 300
        a4_mm_width = 210  # A4 width in mm (portrait)
        a4_mm_height = 297  # A4 height in mm
        a_series_ratio = a4_mm_height / a4_mm_width  # ≈1.414

        # Convert to pixels
        a4_pixels_width = int((a4_mm_width / 25.4) * dpi)
        a4_pixels_height = int((a4_mm_height / 25.4) * dpi)

        # Canvas in portrait mode
        canvas_width = a4_pixels_width
        canvas_height = a4_pixels_height

        # Create white canvas
        canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))

        # Calculate average aspect ratio of images (height/width)
        aspects = [img.height / img.width for img in images if img.width > 0]
        if not aspects:
            status.value = "Invalid images loaded."
            page.update()
            return
        avg_aspect = sum(aspects) / len(aspects)

        num_images = len(images)

        # Find optimal columns to match A-series aspect ratio for the grid
        best_cols = 1
        best_diff = float("inf")
        for cols in range(1, num_images + 1):
            rows = math.ceil(num_images / cols)
            grid_aspect = (avg_aspect * rows) / cols
            diff = abs(grid_aspect - a_series_ratio)
            if diff < best_diff:
                best_diff = diff
                best_cols = cols

        cols = best_cols
        rows = math.ceil(num_images / cols)

        # Calculate cell dimensions
        cell_width = canvas_width // cols
        cell_height = canvas_height // rows

        # Place images on canvas
        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            x = col * cell_width
            y = row * cell_height

            # Resize image to fit cell while maintaining aspect ratio
            resized_img = ImageOps.fit(img, (cell_width, cell_height), method=Image.LANCZOS)

            # Paste onto canvas
            canvas.paste(resized_img, (x, y))

        # Save the output
        output_path = "a4_photo_layout.png"
        try:
            canvas.save(output_path)
            status.value = f"Layout generated and saved as '{output_path}'. You can print this file on A4 paper."
        except Exception as ex:
            status.value = f"Error saving file: {str(ex)}"

        page.update()

    generate_button = ft.ElevatedButton("Generate A4 Layout", on_click=generate_layout)

    # Add components to page
    page.add(
        ft.Column(
            [
                ft.Text("Upload multiple photos and generate a printable A4 layout."),
                pick_button,
                generate_button,
                status,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

ft.app(target=main)