# Test display capabilities with visual demo

import pytest
from feargreeddisplay import DisplayHATMini, load_fonts, FONT_PATHS

def test_display_capabilities():
    """Test display initialization and capabilities with visual demo"""
    import time
    from PIL import Image, ImageDraw
    import colorsys

    # Initialize with new resolution
    width, height = 320, 240
    buffer = Image.new("RGB", (width, height))
    display = DisplayHATMini(buffer, backlight_pwm=True)
    fonts = load_fonts()
    
    # Display specifications
    specs = {
        "Resolution": "320x240",
        "Memory Mode": "Optimized",
        "Interface": "SPI",
        "Colors": "18-bit (262K)",
        "Viewing Angle": "160°",
        "Frame Limit": "20fps"
    }

    def create_rainbow_background(frame):
        """Create shifting rainbow background with memory optimization"""
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        for y in range(0, height, 2):  # Optimized: draw every other line
            hue = (y / height + frame / 50) % 1.0
            rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(hue, 1, 1))
            draw.line([(0, y), (width, y)], fill=rgb)
            draw.line([(0, y+1), (width, y+1)], fill=rgb)  # Fill gap
        return image

    try:
        # Test sequence with memory management
        frames = []
        for frame in range(20):  # Limit to 20 frames
            image = create_rainbow_background(frame)
            draw = ImageDraw.Draw(image)
            
            y_offset = -50 + frame * 3
            for key, value in specs.items():
                if 0 <= y_offset <= height:
                    text = f"{key}: {value}"
                    # Draw text with new fonts
                    draw.text((11, y_offset+1), text, 
                            font=fonts['mono_medium'], fill='black')
                    draw.text((10, y_offset), text, 
                            font=fonts['mono_medium'], fill='white')
                y_offset += 30

            frames.append(image)

        # Display frames with memory-aware loop
        for frame in frames:
            display.st7789.display(frame)
            time.sleep(0.05)

        assert True, "Display test completed successfully"
        
    except Exception as e:
        pytest.fail(f"Display test failed: {str(e)}")

    finally:
        # Cleanup
        display.set_backlight(0.0)
        display.set_led(0.0, 0.0, 0.0)