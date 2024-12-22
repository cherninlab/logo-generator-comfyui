import os
import json
import requests
import tempfile
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from urllib.parse import quote

class GoogleFontsLogoNode:
    """
    Custom node for online ComfyUI that generates logos using Google Fonts
    """
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.cached_fonts = {}
        
    def download_google_font(self, font_family):
        """Download and cache a font from Google Fonts"""
        # Convert font family name to URL-friendly format
        font_family_url = quote(font_family)
        
        # Check if font is already cached
        cache_path = os.path.join(self.temp_dir, f"{font_family}.ttf")
        if cache_path in self.cached_fonts:
            return self.cached_fonts[cache_path]
            
        try:
            # Get font file URL from Google Fonts API
            api_url = f"https://fonts.googleapis.com/css2?family={font_family_url}&display=swap"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(api_url, headers=headers)
            css_content = response.text
            
            # Extract the font file URL
            url_start = css_content.find("url(") + 4
            url_end = css_content.find(")", url_start)
            font_url = css_content[url_start:url_end]
            
            # Download the font file
            font_response = requests.get(font_url, headers=headers)
            
            # Save to temporary directory
            with open(cache_path, 'wb') as f:
                f.write(font_response.content)
            
            # Cache the font path
            self.cached_fonts[font_family] = cache_path
            return cache_path
            
        except Exception as e:
            print(f"Error downloading font {font_family}: {str(e)}")
            # Return path to default system font as fallback
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "logo_config": ("STRING", {
                    "multiline": True,
                    "default": json.dumps({
                        "text": "Your Logo",
                        "font_family": "Roboto",  # Google Fonts family name
                        "font_size": 72,
                        "font_color": "#000000",
                        "stroke_width": 0,
                        "stroke_color": "#FFFFFF",
                        "width": 800,
                        "height": 400,
                        "background_color": "#FFFFFF",
                        "x_position": "center",
                        "y_position": "center",
                        "rotation": 0,
                        "spacing": 0,
                        "background_transparency": 0  # 0-255, 0 is fully opaque
                    }, indent=2)
                })
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate_logo"
    OUTPUT_NODE = True
    CATEGORY = "image/generator"

    def _parse_position(self, pos_value, total_size, object_size):
        """Convert position value to actual pixel coordinate"""
        if isinstance(pos_value, (int, float)):
            return int(pos_value)
        elif pos_value == "center":
            return (total_size - object_size) // 2
        elif pos_value == "right" or pos_value == "bottom":
            return total_size - object_size
        else:  # "left" or "top" or default
            return 0

    def generate_logo(self, logo_config):
        """Generate logo image based on input configuration"""
        try:
            config = json.loads(logo_config)
            
            # Create base image with transparency support
            background_color = config.get('background_color', '#FFFFFF')
            if background_color.startswith('#'):
                # Convert hex to RGBA
                r = int(background_color[1:3], 16)
                g = int(background_color[3:5], 16)
                b = int(background_color[5:7], 16)
                a = 255 - config.get('background_transparency', 0)
                background_color = (r, g, b, a)
            
            img = Image.new('RGBA', 
                          (config.get('width', 800), 
                           config.get('height', 400)),
                          background_color)
            draw = ImageDraw.Draw(img)

            # Download and load font
            font_family = config.get('font_family', 'Roboto')
            font_size = config.get('font_size', 72)
            font_path = self.download_google_font(font_family)
            font = ImageFont.truetype(font_path, font_size)

            # Get text size for positioning
            text = config.get('text', 'Your Logo')
            bbox = draw.textbbox((0, 0), text, font=font, spacing=config.get('spacing', 0))
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Calculate position
            x = self._parse_position(config.get('x_position', 'center'), 
                                   config.get('width', 800), 
                                   text_width)
            y = self._parse_position(config.get('y_position', 'center'), 
                                   config.get('height', 400), 
                                   text_height)

            # Draw text with optional stroke
            stroke_width = config.get('stroke_width', 0)
            if stroke_width > 0:
                draw.text((x, y), text,
                         font=font,
                         fill=config.get('stroke_color', '#FFFFFF'),
                         stroke_width=stroke_width,
                         spacing=config.get('spacing', 0))

            draw.text((x, y), text,
                     font=font,
                     fill=config.get('font_color', '#000000'),
                     spacing=config.get('spacing', 0))

            # Apply rotation if specified
            rotation = config.get('rotation', 0)
            if rotation != 0:
                img = img.rotate(rotation, expand=True)

            # Convert to numpy array for ComfyUI compatibility
            img_array = np.array(img).astype(np.float32) / 255.0
            
            # Add batch dimension if needed
            if len(img_array.shape) == 3:
                img_array = img_array[None, ...]
                
            return (img_array,)

        except Exception as e:
            print(f"Error generating logo: {str(e)}")
            # Return a simple error image
            error_img = np.zeros((1, 400, 800, 4), dtype=np.float32)
            return (error_img,)

# Node class for registration
NODE_CLASS_MAPPINGS = {
    "GoogleFontsLogo": GoogleFontsLogoNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GoogleFontsLogo": "Logo Generator (Google Fonts)"
}
