import math

import flet as ft
from PIL import Image


def main(page: ft.Page):
    page.title = "Photo Arranger for A4 Printing"
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

        # Define A4 dimensions at 300 DPI for print quality
        dpi = 300
        a4_mm_width = 210  # A4 width in mm (portrait)
        a4_mm_height = 297  # A4 height in mm
        # Convert to pixels
        canvas_width = int((a4_mm_width / 25.4) * dpi)
        canvas_height = int((a4_mm_height / 25.4) * dpi)

        # Sort images by area descending
        images.sort(key=lambda img: img.width * img.height, reverse=True)

        num_images = len(images)

        if num_images == 0:
            return

        # Find best cols that maximizes total used area (minimizes waste)
        best_cols = 1
        best_used = 0.0
        for cols in range(1, num_images + 1):
            rows = math.ceil(num_images / cols)
            cell_width = canvas_width / cols
            cell_height = canvas_height / rows
            total_used = 0.0
            for img in images:
                w, h = img.width, img.height
                scale_orig = min(cell_width / w, cell_height / h)
                area_orig = w * h * (scale_orig**2)
                scale_rot = min(cell_width / h, cell_height / w)
                area_rot = w * h * (scale_rot**2)
                total_used += max(area_orig, area_rot)
            if total_used > best_used:
                best_used = total_used
                best_cols = cols

        cols = best_cols
        rows = math.ceil(num_images / cols)

        cell_width = canvas_width / cols
        cell_height = canvas_height / rows

        # Create white canvas
        canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))

        # Place images on canvas
        for i in range(num_images):
            img = images[i]
            w, h = img.width, img.height
            scale_orig = min(cell_width / w, cell_height / h)
            scale_rot = min(cell_width / h, cell_height / w)
            rotate = scale_rot > scale_orig
            if rotate:
                img = img.rotate(90, expand=True)
                w, h = h, w
                scale = scale_rot
            else:
                scale = scale_orig

            new_w = int(w * scale)
            new_h = int(h * scale)
            resized_img = img.resize((new_w, new_h), Image.LANCZOS)

            row = i // cols
            col = i % cols
            x = int(col * cell_width)
            y = int(row * cell_height)

            paste_x = x + int((cell_width - new_w) / 2)
            paste_y = y + int((cell_height - new_h) / 2)

            canvas.paste(resized_img, (paste_x, paste_y))

            # Update the image in the list if rotated
            images[i] = img if rotate else images[i]

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
        ft.Column([
            ft.Text("Upload multiple photos and generate a printable A4 layout."),
            pick_button,
            generate_button,
            status,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    ))

ft.app(target=main)