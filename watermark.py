import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import utils

logger = logging.getLogger("cevondocs")


def watermark_image(image_path: Path, doc_id: str, output_path: Path) -> None:
    """
    Opens source image, draws '{doc_id} | {timestamp}' in gray at bottom-right corner,
    and saves a separate watermarked image to output_path.
    Never modifies the original source image.
    """
    try:
        if not image_path.exists():
            logger.warning(f"Source image '{image_path}' does not exist for watermarking.")
            return

        img = Image.open(image_path).convert("RGBA")
        txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        timestamp = utils.now_iso()
        watermark_text = f"{doc_id} | {timestamp}"

        # Default font
        font = ImageFont.load_default()

        # Calculate bounding box for text positioning
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Margin from bottom-right corner
        margin = 15
        x = img.width - text_width - margin
        y = img.height - text_height - margin

        # Ensure text fits inside dimensions
        if x < 5:
            x = 5
        if y < 5:
            y = 5

        # Draw gray semi-transparent text (gray color with 180 alpha)
        draw.text((x, y), watermark_text, fill=(128, 128, 128, 180), font=font)

        # Composite watermark onto original image
        watermarked_img = Image.alpha_composite(img, txt_layer)

        # Convert back to RGB for PNG/JPEG saving if necessary
        output_img = watermarked_img.convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_img.save(output_path)

        logger.info(f"Watermarked image saved to '{output_path}'")
    except Exception as e:
        logger.error(f"Failed to apply watermark to '{image_path}': {e}")
        # Non-fatal error: log and continue
