#!/usr/bin/env python3
"""
Script to generate placeholder images for the README screenshots.
Run this after installing Pillow: pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_image(filename, text, width=800, height=600):
    """Create a placeholder image with text."""
    # Create a new image with white background
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()

    # Draw the text centered
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2

    draw.text((x, y), text, fill='black', font=font)

    # Save the image
    img.save(filename)
    print(f"Created placeholder image: {filename}")

def main():
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')

    # Create patient_docs.png placeholder
    create_placeholder_image(
        os.path.join(docs_dir, 'patient_docs.png'),
        'Screenshot of Patient Document Upload Interface\n\nReplace with actual screenshot from:\nhttp://localhost:8000 -> "Upload Patient Docs" tab'
    )

    # Create ask_patient.png placeholder
    create_placeholder_image(
        os.path.join(docs_dir, 'ask_patient.png'),
        'Screenshot of Ask Patient Questions Interface\n\nReplace with actual screenshot from:\nhttp://localhost:8000 -> "Ask (Patient Docs)" tab'
    )

if __name__ == '__main__':
    main()