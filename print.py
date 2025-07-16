import json
from reportlab.lib.pagesizes import A4, A5, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from PIL import Image
import os
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# === Settings ===
JSON_PATH = "/Users/samzuehlke/Documents/work/kinderuni/to_print/batch_20250716_082722/star_generated_story_20250716_080332.json"
OUTPUT_PDF = "samuel_booklet.pdf"

# A4 landscape will fit two A5 pages side by side
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
A5_WIDTH, A5_HEIGHT = A5
MARGIN = 1 * cm

# Calculate positions for two A5 pages on A4
LEFT_PAGE_X = (PAGE_WIDTH - 2 * A5_WIDTH) / 2
RIGHT_PAGE_X = LEFT_PAGE_X + A5_WIDTH
PAGE_Y = (PAGE_HEIGHT - A5_HEIGHT) / 2

# Image settings
IMAGE_MAX_WIDTH = A5_WIDTH - 2 * MARGIN
IMAGE_MAX_HEIGHT = A5_HEIGHT / 2.5
IMAGE_TEXT_SPACING = 1.2 * cm  # Increased spacing between image and text

# Font settings
FONT_SIZE = 12  # Increased from 10 to 12

# === Load Data ===
with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

# Get folder name from JSON filename (first word before underscore)
folder_name = os.path.basename(JSON_PATH).split('_')[0]
IMAGE_DIR = f"accounts/{folder_name}"

segments = [data["story"][k] for k in sorted(data["story"]) if k.startswith("absatz")]

# === PDF Setup ===
pdf = canvas.Canvas(OUTPUT_PDF, pagesize=landscape(A4))
pdf.setFont("Helvetica", FONT_SIZE)

def get_text_dimensions(text, font_name, font_size):
    # Helper function to calculate text block dimensions
    lines = []
    line_len = int((A5_WIDTH - 2 * MARGIN) / (font_size * 0.6))  # Adjust for larger font
    
    for paragraph in text.split("\n"):
        while len(paragraph) > line_len:
            split_at = paragraph.rfind(" ", 0, line_len)
            if split_at == -1: split_at = line_len
            lines.append(paragraph[:split_at])
            paragraph = paragraph[split_at:].lstrip()
        if paragraph:
            lines.append(paragraph)
    
    return len(lines) * (font_size * 1.2), lines  # height, wrapped_lines

def draw_segment(x, y, segment, available_width):
    text = segment["text"]
    image_file = segment.get("image")
    image_path = os.path.join(IMAGE_DIR, image_file) if image_file else None
    
    # Calculate total content height and prepare content
    content_height = 0
    image_height = 0
    text_height = 0
    
    # Get image dimensions if present
    if image_file and os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            img_width, img_height = img.size
            aspect = img_height / img_width
            display_width = min(IMAGE_MAX_WIDTH, available_width - 2 * MARGIN)
            display_height = display_width * aspect
            
            if display_height > IMAGE_MAX_HEIGHT:
                display_height = IMAGE_MAX_HEIGHT
                display_width = display_height / aspect
            
            image_height = display_height
            content_height += display_height + IMAGE_TEXT_SPACING
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
    
    # Calculate text height
    text_height, wrapped_lines = get_text_dimensions(text, "Helvetica", FONT_SIZE)
    content_height += text_height
    
    # Calculate starting Y position to center all content vertically
    current_y = y + (A5_HEIGHT + content_height) / 2
    
    # Draw image if present
    if image_file and os.path.exists(image_path):
        try:
            # Center image horizontally
            image_x = x + (available_width - display_width) / 2
            pdf.drawInlineImage(image_path, image_x, current_y - image_height,
                              width=display_width, height=display_height)
            current_y -= image_height + IMAGE_TEXT_SPACING
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
    
    # Draw text
    text_obj = pdf.beginText()
    text_obj.setTextOrigin(x + MARGIN, current_y - text_height)
    text_obj.setFont("Helvetica", FONT_SIZE)
    
    # Center each line of text
    for line in wrapped_lines:
        # Calculate line width and center position
        line_width = pdf.stringWidth(line, "Helvetica", FONT_SIZE)
        center_x = x + (available_width - line_width) / 2
        
        # Draw the centered line
        pdf.drawString(center_x, current_y - FONT_SIZE, line)
        current_y -= FONT_SIZE * 1.2

# === Render Segments ===
pages_needed = (len(segments) + 1) // 2  # Round up division

for page in range(pages_needed):
    i = page * 2
    
    # Left page
    if i < len(segments):
        draw_segment(LEFT_PAGE_X, PAGE_Y, segments[i], A5_WIDTH)
    
    # Right page
    if i + 1 < len(segments):
        draw_segment(RIGHT_PAGE_X, PAGE_Y, segments[i + 1], A5_WIDTH)
    
    # Only add a new page if there's more content coming
    if page < pages_needed - 1:
        pdf.showPage()
        pdf.setFont("Helvetica", FONT_SIZE)

pdf.save()
print(f"PDF saved as: {OUTPUT_PDF}")