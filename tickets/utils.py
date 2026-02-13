# tickets/utils.py - ULTRA-CLEAR PROFESSIONAL REDESIGN
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import qrcode
from django.conf import settings
from django.templatetags.static import static
import os
import requests
from io import BytesIO
import cloudinary
from cloudinary.utils import cloudinary_url


def download_image_from_url(url, max_size=(1000, 1000)):
    """Download and resize image from URL with maximum quality"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                    img = background
            # Resize with highest quality
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            # Enhance for ultra-clarity
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.3)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)
            return img
    except Exception as e:
        print(f"Error downloading image: {e}")
    return None


def create_rounded_rectangle_mask(size, radius):
    """Create ultra-smooth mask for rounded rectangles"""
    # Create at 4x resolution for ultra-smooth edges
    mask = Image.new('L', (size[0] * 4, size[1] * 4), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (size[0] * 4 - 1, size[1] * 4 - 1)], radius=radius * 4, fill=255)
    # Downsample with Lanczos for perfect antialiasing
    mask = mask.resize(size, Image.Resampling.LANCZOS)
    return mask


def add_gradient_overlay(img, color1, color2, alpha=0.5):
    """Add ultra-smooth gradient overlay"""
    width, height = img.size
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    for y in range(height):
        ratio = (y / height) ** 1.1
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        a = int(255 * alpha)
        draw.line([(0, y), (width, y)], fill=(r, g, b, a))
    
    return overlay


def generate_ticket_image(ticket):
    """
    Generate ULTRA-PROFESSIONAL ticket with PERFECT CLARITY
    Completely redesigned for maximum readability and visual impact
    """
    # LARGE dimensions for crystal-clear output
    width = 1800
    height = 750
    
    # Start with pure white base
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # === LEFT SECTION: Event Image (600px) ===
    left_width = 600
    event_image = None
    
    # Load event image
    try:
        if hasattr(ticket.event, 'banner_image') and ticket.event.banner_image:
            if hasattr(ticket.event.banner_image, 'url'):
                image_url = ticket.event.banner_image.url
                event_image = download_image_from_url(image_url, max_size=(left_width, height))
        
        if event_image is None and hasattr(ticket.event, 'thumbnail') and ticket.event.thumbnail:
            if hasattr(ticket.event.thumbnail, 'url'):
                image_url = ticket.event.thumbnail.url
                event_image = download_image_from_url(image_url, max_size=(left_width, height))
    except Exception as e:
        print(f"Error loading event image: {e}")
    
    if event_image:
        # Resize and crop perfectly
        img_width, img_height = event_image.size
        aspect = img_height / img_width
        target_aspect = height / left_width
        
        if aspect > target_aspect:
            new_width = left_width
            new_height = int(left_width * aspect)
        else:
            new_height = height
            new_width = int(height / aspect)
        
        event_image = event_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Enhance image quality dramatically
        enhancer = ImageEnhance.Contrast(event_image)
        event_image = enhancer.enhance(1.2)
        enhancer = ImageEnhance.Color(event_image)
        event_image = enhancer.enhance(1.15)
        enhancer = ImageEnhance.Sharpness(event_image)
        event_image = enhancer.enhance(1.4)
        
        # Crop to exact size
        left_offset = (new_width - left_width) // 2
        top_offset = (new_height - height) // 2
        event_image = event_image.crop((left_offset, top_offset, left_offset + left_width, top_offset + height))
        
        # Dark overlay for better contrast
        gradient = add_gradient_overlay(event_image, (20, 20, 35), (45, 45, 65), alpha=0.5)
        event_image = event_image.convert('RGBA')
        event_image = Image.alpha_composite(event_image, gradient)
        event_image = event_image.convert('RGB')
        
        img.paste(event_image, (0, 0))
    else:
        # Rich gradient fallback
        for y in range(height):
            ratio = y / height
            r = int(25 + ratio * 60)
            g = int(25 + ratio * 70)
            b = int(50 + ratio * 110)
            draw.rectangle([(0, y), (left_width, y + 1)], fill=(r, g, b))
    
    # === RIGHT SECTION: Ultra-Clean Design ===
    right_x = left_width
    right_width = width - left_width
    
    # Soft gradient background - MUCH LIGHTER for better contrast
    for y in range(height):
        ratio = y / height
        r = int(248 + ratio * 4)   # 248 -> 252
        g = int(249 + ratio * 4)   # 249 -> 253
        b = int(252 + ratio * 3)   # 252 -> 255
        draw.rectangle([(right_x, y), (width, y + 1)], fill=(r, g, b))
    
    # Load LARGER, crystal-clear fonts
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        heading_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        code_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 48)
        logo_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        code_font = ImageFont.load_default()
        logo_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # === PREMIUM BRANDING ===
    brand_y = 50
    
    # Try to load logo
    logo_loaded = False
    try:
        logo_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR, 'static', 'img', 'logo.jpg')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'img', 'logo.jpg')
        
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            # Ultra-sharp logo
            enhancer = ImageEnhance.Sharpness(logo_img)
            logo_img = enhancer.enhance(1.5)
            
            logo_size = (90, 90)
            logo_img = logo_img.resize(logo_size, Image.Resampling.LANCZOS)
            
            # Circular mask - 4x supersampling
            mask = Image.new('L', (logo_size[0] * 4, logo_size[1] * 4), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, logo_size[0] * 4 - 1, logo_size[1] * 4 - 1], fill=255)
            mask = mask.resize(logo_size, Image.Resampling.LANCZOS)
            
            # White border
            border_size = (102, 102)
            border_img = Image.new('RGBA', border_size, (0, 0, 0, 0))
            border_draw = ImageDraw.Draw(border_img)
            border_draw.ellipse([0, 0, border_size[0] - 1, border_size[1] - 1], 
                              fill=(255, 255, 255, 255), outline=(65, 105, 225, 255), width=4)
            
            # Shadow
            shadow_size = (110, 110)
            shadow_img = Image.new('RGBA', shadow_size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_img)
            for i in range(5):
                opacity = int(35 * (5 - i) / 5)
                shadow_draw.ellipse([i, i, shadow_size[0] - i - 1, shadow_size[1] - i - 1], 
                                   fill=(0, 0, 0, opacity))
            
            # Composite
            img_temp = img.convert('RGBA')
            img_temp.paste(shadow_img, (right_x + 65, brand_y + 2), shadow_img)
            img_temp.paste(border_img, (right_x + 69, brand_y), border_img)
            
            logo_output = Image.new('RGBA', logo_size, (0, 0, 0, 0))
            logo_output.paste(logo_img, (0, 0))
            logo_output.putalpha(mask)
            img_temp.paste(logo_output, (right_x + 75, brand_y + 6), logo_output)
            img = img_temp.convert('RGB')
            
            draw = ImageDraw.Draw(img, 'RGBA')
            # Sharp brand text
            draw.text((right_x + 185, brand_y + 20), "NEXTMEDIA", font=logo_font, fill=(15, 15, 30))
            draw.text((right_x + 185, brand_y + 62), "PREMIUM EVENTS", font=label_font, fill=(100, 100, 120))
            logo_loaded = True
    except Exception as e:
        print(f"Logo loading error: {e}")
    
    if not logo_loaded:
        draw.text((right_x + 70, brand_y + 20), "NEXTMEDIA", font=logo_font, fill=(15, 15, 30))
        draw.text((right_x + 70, brand_y + 62), "PREMIUM EVENTS", font=label_font, fill=(100, 100, 120))
    
    # Clean separator
    sep_y = brand_y + 115
    draw.rectangle([(right_x + 70, sep_y), (right_x + 380, sep_y + 3)], fill=(65, 105, 225))
    
    # === EVENT TITLE - MAXIMUM CLARITY ===
    title_y = 180
    event_title = ticket.event.title.upper()
    if len(event_title) > 26:
        event_title = event_title[:23] + "..."
    
    # Title with perfect contrast
    draw.text((right_x + 70, title_y), event_title, font=title_font, fill=(10, 10, 25))
    
    # === REDESIGNED INFO CARDS - ULTRA CLEAR ===
    cards_y = 285
    card_spacing = 105
    card_width = right_width - 440
    
    def draw_crystal_clear_card(base_img, y_pos, icon_emoji, label, value, accent_color):
        """Draw information card with MAXIMUM clarity and contrast"""
        # Pure WHITE card with strong shadow
        card_height = 85
        
        # Multi-layer shadow for depth
        shadow_layers = Image.new('RGBA', (card_width + 20, card_height + 20), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layers)
        for i in range(8):
            opacity = int(25 * (8 - i) / 8)
            offset = i
            shadow_draw.rounded_rectangle(
                [(offset, offset), (card_width + offset, card_height + offset)],
                radius=20, fill=(0, 0, 0, opacity)
            )
        
        # Paste shadow
        base_img_rgba = base_img.convert('RGBA')
        base_img_rgba.paste(shadow_layers, (right_x + 65, y_pos - 3), shadow_layers)
        
        # Pure white card
        card_bg = Image.new('RGBA', (card_width, card_height), (255, 255, 255, 255))
        card_draw = ImageDraw.Draw(card_bg)
        
        # Thick accent bar on left
        card_draw.rectangle([(0, 0), (8, card_height)], fill=accent_color + (255,))
        
        # Subtle top border
        card_draw.rectangle([(8, 0), (card_width, 2)], fill=accent_color + (100,))
        
        # Rounded mask
        card_mask = create_rounded_rectangle_mask((card_width, card_height), 20)
        base_img_rgba.paste(card_bg, (right_x + 70, y_pos), card_mask)
        base_img = base_img_rgba.convert('RGB')
        
        result_draw = ImageDraw.Draw(base_img, 'RGBA')
        
        # LARGE icon circle
        icon_x = right_x + 130
        icon_y = y_pos + 43
        
        # Glow effect
        for r in range(48, 38, -2):
            opacity = int(40 * (48 - r) / 10)
            result_draw.ellipse([(icon_x - r, icon_y - r), (icon_x + r, icon_y + r)],
                              fill=accent_color + (opacity,))
        
        # Main circle
        result_draw.ellipse([(icon_x - 38, icon_y - 38), (icon_x + 38, icon_y + 38)],
                          fill=accent_color + (255,))
        
        # Inner highlight
        result_draw.ellipse([(icon_x - 36, icon_y - 36), (icon_x + 36, icon_y + 36)],
                          fill=(min(accent_color[0] + 25, 255), 
                                min(accent_color[1] + 25, 255), 
                                min(accent_color[2] + 25, 255), 255))
        
        # Icon emoji - LARGE
        result_draw.text((icon_x - 16, icon_y - 18), icon_emoji, font=heading_font, fill=(255, 255, 255))
        
        # Label - BOLD uppercase
        result_draw.text((right_x + 190, y_pos + 18), label.upper(), 
                        font=label_font, fill=(80, 80, 100))
        
        # Value - EXTRA BOLD and LARGE
        result_draw.text((right_x + 190, y_pos + 44), value, 
                        font=text_font, fill=(10, 10, 25))
        
        return base_img
    
    # Date & Time Card - Royal Blue
    date_str = ticket.event.event_date.strftime('%B %d, %Y')
    time_str = ticket.event.event_start.strftime('%I:%M %p')
    img = draw_crystal_clear_card(img, cards_y, "📅", "Date & Time", 
                                  f"{date_str} • {time_str}", (65, 105, 225))
    
    # Venue Card - Emerald Green
    venue_name = ticket.event.venue
    if len(venue_name) > 36:
        venue_name = venue_name[:33] + "..."
    img = draw_crystal_clear_card(img, cards_y + card_spacing, "📍", "Venue", 
                                  venue_name, (16, 185, 129))
    
    # Ticket Holder Card - Vibrant Purple
    buyer_name = ticket.buyer_name.upper()
    if len(buyer_name) > 30:
        buyer_name = buyer_name[:27] + "..."
    img = draw_crystal_clear_card(img, cards_y + card_spacing * 2, "👤", "Ticket Holder", 
                                  buyer_name, (147, 51, 234))
    
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # === ULTRA-SHARP QR CODE ===
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=14,  # LARGER for better scanning
        border=4,
    )
    qr.add_data(f"https://nextmediahq.net/tickets/verify/?code={ticket.ticket_code}")
    qr.make(fit=True)
    
    # Generate with PERFECT contrast
    qr_img = qr.make_image(fill_color=(0, 0, 0), back_color=(255, 255, 255))
    qr_img = qr_img.resize((240, 240), Image.Resampling.NEAREST)  # NEAREST for crisp QR
    
    # QR container
    qr_size = (280, 280)
    qr_container = Image.new('RGBA', qr_size, (255, 255, 255, 255))
    qr_container.paste(qr_img, (20, 20))
    
    # Strong border
    qr_draw = ImageDraw.Draw(qr_container)
    qr_draw.rounded_rectangle([(0, 0), (qr_size[0] - 1, qr_size[1] - 1)], 
                             radius=25, outline=(65, 105, 225), width=6)
    
    # Shadow
    shadow_size = (295, 295)
    qr_shadow = Image.new('RGBA', shadow_size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(qr_shadow)
    for i in range(8):
        opacity = int(45 * (8 - i) / 8)
        shadow_draw.rounded_rectangle([(7 + i, 7 + i), (shadow_size[0] - 7 - i, shadow_size[1] - 7 - i)],
                                      radius=28, fill=(0, 0, 0, opacity))
    
    # Position
    qr_x = right_x + right_width - 310
    qr_y = 200
    
    # Composite
    img_temp = img.convert('RGBA')
    img_temp.paste(qr_shadow, (qr_x - 7, qr_y - 7), qr_shadow)
    
    qr_mask = create_rounded_rectangle_mask(qr_size, 25)
    img_temp.paste(qr_container, (qr_x, qr_y), qr_mask)
    img = img_temp.convert('RGB')
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # QR label
    draw.text((qr_x + 75, qr_y + 290), "SCAN TO VERIFY", 
             font=label_font, fill=(80, 80, 100))
    
    # === TICKET CODE - MAXIMUM VISIBILITY ===
    code_y = height - 115
    code_width = right_width - 380
    
    # White container with strong border
    code_height = 80
    
    # Shadow
    code_shadow = Image.new('RGBA', (code_width + 16, code_height + 16), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(code_shadow)
    for i in range(8):
        opacity = int(40 * (8 - i) / 8)
        shadow_draw.rounded_rectangle([(i, i), (code_width + i, code_height + i)],
                                      radius=18, fill=(0, 0, 0, opacity))
    
    # Paste shadow
    img_temp = img.convert('RGBA')
    img_temp.paste(code_shadow, (right_x + 62, code_y - 3), code_shadow)
    
    # Pure white background
    code_bg = Image.new('RGBA', (code_width, code_height), (255, 255, 255, 255))
    code_draw = ImageDraw.Draw(code_bg)
    
    # Strong blue border
    code_draw.rounded_rectangle([(0, 0), (code_width - 1, code_height - 1)],
                                radius=18, outline=(65, 105, 225), width=5)
    
    # Top accent
    code_draw.rectangle([(5, 5), (code_width - 6, 10)], fill=(65, 105, 225))
    
    code_mask = create_rounded_rectangle_mask((code_width, code_height), 18)
    img_temp.paste(code_bg, (right_x + 70, code_y), code_mask)
    img = img_temp.convert('RGB')
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Ticket code - perfectly centered
    code_bbox = draw.textbbox((0, 0), ticket.ticket_code, font=code_font)
    code_width_text = code_bbox[2] - code_bbox[0]
    code_x = right_x + 70 + ((code_width - code_width_text) // 2)
    
    # Draw code in deep black
    draw.text((code_x, code_y + 18), ticket.ticket_code, font=code_font, fill=(10, 10, 25))
    
    # === PREMIUM PERFORATIONS ===
    perf_y = 35
    while perf_y < height - 35:
        # Multi-layer shadow
        for i in range(4):
            offset = i * 2
            opacity = int(35 * (4 - i) / 4)
            draw.ellipse([(left_width - 16 + offset, perf_y - 16 + offset),
                         (left_width + 16 + offset, perf_y + 16 + offset)],
                        fill=(0, 0, 0, opacity))
        
        # Outer ring
        draw.ellipse([(left_width - 14, perf_y - 14), (left_width + 14, perf_y + 14)],
                    fill=(190, 190, 210))
        # Middle ring
        draw.ellipse([(left_width - 11, perf_y - 11), (left_width + 11, perf_y + 11)],
                    fill=(220, 220, 235))
        # Inner
        draw.ellipse([(left_width - 8, perf_y - 8), (left_width + 8, perf_y + 8)],
                    fill=(245, 245, 252))
        # Center
        draw.ellipse([(left_width - 6, perf_y - 6), (left_width + 6, perf_y + 6)],
                    fill=(255, 255, 255))
        
        perf_y += 40
    
    # === STATUS OVERLAY ===
    if ticket.is_used:
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        try:
            stamp_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 180)
        except:
            stamp_font = ImageFont.load_default()
        
        stamp_img = Image.new('RGBA', (1100, 550), (0, 0, 0, 0))
        stamp_draw = ImageDraw.Draw(stamp_img)
        
        stamp_text = "USED"
        bbox = stamp_draw.textbbox((0, 0), stamp_text, font=stamp_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (1100 - text_width) // 2
        y = (550 - text_height) // 2
        
        # Shadows
        stamp_draw.text((x + 8, y + 8), stamp_text, font=stamp_font, fill=(0, 0, 0, 100))
        stamp_draw.text((x + 4, y + 4), stamp_text, font=stamp_font, fill=(0, 0, 0, 60))
        
        # Main text
        stamp_draw.text((x, y), stamp_text, font=stamp_font, fill=(220, 38, 38, 255))
        
        # Double border
        stamp_draw.rounded_rectangle([(x - 70, y - 40), (x + text_width + 70, y + text_height + 40)],
                                     radius=20, outline=(220, 38, 38, 255), width=20)
        stamp_draw.rounded_rectangle([(x - 85, y - 55), (x + text_width + 85, y + text_height + 55)],
                                     radius=25, outline=(220, 38, 38, 200), width=10)
        
        stamp_img = stamp_img.rotate(-30, expand=False, fillcolor=(0, 0, 0, 0))
        
        stamp_x = (width - 1100) // 2
        stamp_y = (height - 550) // 2
        img = img.convert('RGBA')
        img.paste(stamp_img, (stamp_x, stamp_y), stamp_img)
        img = img.convert('RGB')
    
    # === FINAL ENHANCEMENT ===
    # Ultra-sharpen for perfect clarity
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.25)
    
    # Save with maximum quality
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', quality=100, optimize=False, dpi=(300, 300))
    buffer.seek(0)
    
    return buffer


def generate_bulk_tickets_pdf(tickets):
    """Generate ultra-clear PDF for professional printing"""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import io
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    page_width, page_height = landscape(letter)
    
    tickets_per_page = 2
    ticket_height = 5.6 * inch
    ticket_width = 13.5 * inch
    
    for i, ticket in enumerate(tickets):
        if i > 0 and i % tickets_per_page == 0:
            c.showPage()
        
        ticket_img_buffer = generate_ticket_image(ticket)
        ticket_img = ImageReader(ticket_img_buffer)
        
        if i % tickets_per_page == 0:
            y_pos = page_height - 0.6 * inch - ticket_height
        else:
            y_pos = page_height - 0.6 * inch - (2 * ticket_height) - 0.35 * inch
        
        x_pos = (page_width - ticket_width) / 2
        
        c.drawImage(ticket_img, x_pos, y_pos, width=ticket_width, height=ticket_height,
                   preserveAspectRatio=True, mask='auto')
        
        if i % tickets_per_page == 0 and i < len(tickets) - 1:
            cut_y = y_pos - 0.175 * inch
            c.setDash(6, 4)
            c.setStrokeColorRGB(0.5, 0.5, 0.5)
            c.setLineWidth(2)
            c.line(0.4 * inch, cut_y, page_width - 0.4 * inch, cut_y)
            
            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(0.3, 0.3, 0.3)
            c.drawString(0.4 * inch, cut_y - 0.2 * inch, "✂ Cut along dotted line")
    
    c.save()
    buffer.seek(0)
    return buffer