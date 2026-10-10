import io
import os
import re
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, portrait
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from PIL import Image

from django.conf import settings
from .certificate_id import generate_certificate_id


class PDFGenerationError(Exception):
    pass


class PDFGenerator:
    """
    Handles the generation of PDF certificates using a background template image
    and dynamic text overlay via ReportLab.
    """

    def __init__(self):
        self._register_fonts()

    def _register_fonts(self):
        """Register all approved TrueType fonts with ReportLab."""
        for font_file, font_name in settings.APPROVED_FONTS.items():
            font_path = os.path.join(settings.FONTS_DIR, font_file)
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to register font {font_file}: {e}")

    def generate(self, template_path, participant_data, field_config):
        """
        Generate a PDF certificate for a participant.
        
        Args:
            template_path (str): Absolute path to the template image file.
            participant_data (dict): Data for this specific participant (name, course, date).
            field_config (dict): Configuration mapping field names to X/Y/font settings.
            
        Returns:
            tuple: (BytesIO buffer containing the PDF, generated certificate ID)
        """
        try:
            # 1. Determine image dimensions
            with Image.open(template_path) as img:
                width, height = img.size

            # 2. Setup the ReportLab canvas
            packet = io.BytesIO()
            # Set pagesize exactly to image pixel dimensions
            c = canvas.Canvas(packet, pagesize=(width, height))
            
            # 3. Draw the background image
            # In ReportLab, (0,0) is bottom-left. We draw the image from 0,0 to width,height
            c.drawImage(template_path, 0, 0, width=width, height=height)
            
            # 4. Generate Certificate ID (and inject into data)
            cert_id = generate_certificate_id()
            participant_data["certificate_id"] = cert_id
            
            # Ensure completion_date has a fallback if not provided
            if not participant_data.get("completion_date"):
                participant_data["completion_date"] = datetime.now().strftime("%Y-%m-%d")

            # 5. Overlay Text based on configuration
            for field, config in field_config.items():
                text = participant_data.get(field)
                if not text:
                    continue
                    
                text = str(text)
                
                # Extract config or defaults
                x = config.get("x", 0)
                # Note: Template config Y is often top-down (0 at top).
                # ReportLab Y is bottom-up (0 at bottom). 
                # We assume the config UI provides Y from the TOP, so we must invert it.
                # If the UI provided Y from bottom, we wouldn't subtract from height.
                # For this implementation, we assume Y is from TOP (standard web coordinates).
                y_from_top = config.get("y", 0)
                y = height - y_from_top
                
                font_size = config.get("font_size", settings.DEFAULT_FONT_SIZE)
                font_name = settings.APPROVED_FONTS.get(
                    config.get("font", settings.DEFAULT_FONT),
                    "Helvetica"  # Fallback to standard font if TTF not found
                )
                
                # Check if the specific font name was successfully registered, if not fallback
                if font_name not in pdfmetrics.getRegisteredFontNames():
                    font_name = "Helvetica"
                
                color_hex = config.get("color", settings.DEFAULT_FONT_COLOR)
                align = config.get("align", "left")
                
                # Apply styles
                c.setFont(font_name, font_size)
                c.setFillColor(HexColor(color_hex))
                
                # Draw text with alignment
                if align == "center":
                    c.drawCentredString(x, y, text)
                elif align == "right":
                    c.drawRightString(x, y, text)
                else:
                    c.drawString(x, y, text)
                    
            # 6. Save the canvas
            c.save()
            packet.seek(0)
            
            return packet, cert_id
            
        except Exception as e:
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")
