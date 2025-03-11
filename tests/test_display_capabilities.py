import pytest
from feargreeddisplay import FearGreedDisplay

def test_display_capabilities():
    """Test display initialization and capabilities with visual demo"""
    import time
    from PIL import Image, ImageDraw, ImageFont
    import colorsys

    display = FearGreedDisplay()
    width = display.width
    height = display.height
    
    # Display specifications
    specs = {
        "Resolution": f"{width}x{height}",
        "Refresh Rate": "60Hz",
        "Interface": "SPI",
        "Colors": "18-bit (262K)",
        "Viewing Angle": "160°"
    }

    def create_rainbow_background(frame):
        """Create shifting rainbow background"""
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        for y in range(height):
            hue = (y / height + frame / 50) % 1.0
            rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(hue, 1, 1))
            draw.line([(0, y), (width, y)], fill=rgb)
        return image

    try:
        # Test sequence
        for frame in range(100):
            image = create_rainbow_background(frame)
            draw = ImageDraw.Draw(image)
            
            # Display specs with scrolling effect
            y_offset = -50 + frame
            for key, value in specs.items():
                if 0 <= y_offset <= height:
                    text = f"{key}: {value}"
                    # Draw text with shadow for better visibility
                    draw.text((11, y_offset+1), text, fill='black')
                    draw.text((10, y_offset), text, fill='white')
                y_offset += 20

            display.show_image(image)
            time.sleep(0.05)

        assert True, "Display test completed successfully"
        
    except Exception as e:
        pytest.fail(f"Display test failed: {str(e)}")

    finally:
        # Cleanup
        display.clear()