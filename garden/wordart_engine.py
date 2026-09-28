import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

class WordArtEngine:
    """A self-contained WordArt generator using only Pillow."""

    def __init__(self, font_path):
        self.font_path = font_path

    def _get_font(self, size):
        try:
            return ImageFont.truetype(self.font_path, size)
        except IOError:
            # Fallback to a default font if the specified one is missing
            return ImageFont.load_default(size)

    def render(
        self,
        text,
        canvas_size=(1200, 400),
        style="outline",
        font_size=100,
        fill_color=(255, 255, 255),
        outline_color=(0, 0, 0),
        outline_width=3,
        shadow_color=(0, 0, 0, 128),
        shadow_offset=(5, 5),
        gradient_colors=None, # e.g. [(255,0,0), (0,0,255)]
    ):
        """
        Renders text with a given style and returns a PIL RGBA image.
        """
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = self._get_font(font_size)

        # Calculate text position to center it
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (canvas_size[0] - text_width) / 2
        y = (canvas_size[1] - text_height) / 2

        # --- Draw based on style ---
        if style == "shadow":
            # Draw shadow first
            draw.text(
                (x + shadow_offset[0], y + shadow_offset[1]),
                text, font=font, fill=shadow_color
            )
            # Draw main text on top
            draw.text((x, y), text, font=font, fill=fill_color)

        elif style == "outline":
            # Draw outline (thicker stroke) first, then fill
            draw.text(
                (x, y), text, font=font, fill=fill_color,
                stroke_width=outline_width, stroke_fill=outline_color
            )

        elif style == "gradient":
            if not gradient_colors:
                gradient_colors = [(255, 0, 0), (0, 0, 255)]
            
            # Create a mask for the text
            mask = Image.new("L", canvas_size, 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.text((x, y), text, font=font, fill=255)

            # Create a gradient image
            gradient = Image.new("RGBA", canvas_size)
            for i in range(canvas_size[1]):
                # Linear interpolation between colors
                ratio = i / canvas_size[1]
                r = int(gradient_colors[0][0] * (1 - ratio) + gradient_colors[1][0] * ratio)
                g = int(gradient_colors[0][1] * (1 - ratio) + gradient_colors[1][1] * ratio)
                b = int(gradient_colors[0][2] * (1 - ratio) + gradient_colors[1][2] * ratio)
                draw_grad = ImageDraw.Draw(gradient)
                draw_grad.line([(0, i), (canvas_size[0], i)], fill=(r, g, b, 255))

            # Composite gradient onto text
            img.paste(gradient, (0, 0), mask)

            # Optional: add a stroke on top for definition
            draw.text(
                (x, y), text, font=font, fill=None,
                stroke_width=outline_width, stroke_fill=outline_color
            )

        elif style == "neon":
            # Neon glow effect
            # 1. Draw a soft glow
            for i in range(3, 0, -1):
                glow_width = outline_width * i
                draw.text(
                    (x, y), text, font=font, fill=fill_color,
                    stroke_width=glow_width, stroke_fill=outline_color
                )
            # 2. Draw the core text sharply on top
            draw.text((x, y), text, font=font, fill=fill_color)

        else: # Default simple fill
            draw.text((x, y), text, font=font, fill=fill_color)

        return img