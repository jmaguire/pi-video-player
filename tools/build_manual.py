from pathlib import Path
import argparse
import math
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'outputs'
parser = argparse.ArgumentParser(description='Build the illustrated exhibition PDF manual.')
parser.add_argument('--output', type=Path, default=OUT / 'Two-Screen-Exhibition-Manual.pdf')
args = parser.parse_args()
PDF = args.output.resolve()
PDF.parent.mkdir(parents=True, exist_ok=True)
FONT_PATHS = {
    'Body': ['/System/Library/Fonts/Supplemental/Arial.ttf',
             '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
             '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'],
    'Bold': ['/System/Library/Fonts/Supplemental/Arial Bold.ttf',
             '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
             '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'],
    'Display': ['/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf',
                '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'],
    'Mono': ['/System/Library/Fonts/Supplemental/Courier New Bold.ttf',
             '/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf',
             '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'],
}
for name, candidates in FONT_PATHS.items():
    file = next((Path(path) for path in candidates if Path(path).is_file()), None)
    if file is None:
        raise RuntimeError('Missing fonts. Install Liberation fonts, or edit FONT_PATHS.')
    pdfmetrics.registerFont(TTFont(name, str(file)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Bold', italic='Body', boldItalic='Bold')
W, H = A4
M = 46
CW = W - 2*M
PAPER = HexColor('#F5F2EA')
INK = HexColor('#202321')
GRAY = HexColor('#59615D')
LINE = HexColor('#D8DCD4')
BLUE = HexColor('#2E4DDD')
CORAL = HexColor('#E26A4F')
GREEN = HexColor('#315D4A')
PALE_BLUE = HexColor('#E6EBFC')
PALE_CORAL = HexColor('#F9E5DE')
WHITE = HexColor('#FFFFFF')
c = canvas.Canvas(str(PDF), pagesize=A4, pageCompression=1)
c.setTitle('Two screens. One small computer. | Raspberry Pi 5 Exhibition Manual')
c.setAuthor('Exhibition setup guide')
c.setSubject('Artist-friendly two-video looping guide, with independent and synchronized playback options')

def box(x, top, w, h, fill, stroke=None, radius=0):
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    if radius:
        c.roundRect(x, H-top-h, w, h, radius, fill=1, stroke=bool(stroke))
    else:
        c.rect(x, H-top-h, w, h, fill=1, stroke=bool(stroke))

def line(x1, y1, x2, y2, color=LINE, width=1):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, H-y1, x2, H-y2)

def label(text, x, top, size=10, color=GRAY, font='Bold'):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawString(x, H-top-size, text)

def para(text, x=M, top=0, width=CW, size=11.7, color=INK, leading=None, font='Body'):
    style = ParagraphStyle('p', fontName=font, fontSize=size, leading=leading or size*1.43,
                           textColor=color, spaceAfter=0)
    p = Paragraph(text, style)
    _, height = p.wrap(width, H)
    if top + height > H-50:
        raise ValueError(f'Text runs off page {c.getPageNumber()}: {text[:70]} @ {top}+{height}')
    p.drawOn(c, x, H-top-height)
    return height

def heading(text, top, x=M, width=CW, size=19):
    return para(text, x, top, width, size=size, leading=size*1.1, font='Display')

def page(num, section, title, subtitle=''):
    box(0, 0, W, H, PAPER)
    label('TWO SCREENS / EXHIBITION FIELD GUIDE', M, 25, size=8.3, color=GREEN)
    label(section.upper(), M, 70, size=9.2, color=BLUE)
    title_h = para(title, M, 93, CW, size=35, leading=37, font='Display')
    top = 93 + title_h + 13
    if subtitle:
        top += para(subtitle, M, top, CW, size=12.3, color=GRAY) + 24
    else:
        top += 15
    line(M, H-45, W-M, H-45)
    label('RASPBERRY PI 5  /  OCTOBER 2026', M, H-31, size=7.3)
    c.setFont('Display', 11)
    c.setFillColor(INK)
    c.drawRightString(W-M, 24, f'{num:02d} / 19')
    c.bookmarkPage('page'+str(num))
    c.addOutlineEntry(title.replace('<br/>', ' '), 'page'+str(num), level=0)
    return top

def end():
    c.showPage()

def callout(title, text, top, color=PALE_BLUE, x=M, width=CW):
    padding=16
    style = ParagraphStyle('measure', fontName='Body', fontSize=11.4, leading=16.2)
    p = Paragraph(text, style)
    _, ph = p.wrap(width-2*padding, H)
    h = 20 + 16 + ph + 17
    if top+h>H-50:
        raise ValueError(f'Callout too tall page {c.getPageNumber()}: {top}+{h}')
    box(x, top, width, h, color, radius=5)
    label(title.upper(), x+padding, top+14, size=9.2, color=GREEN if color != PALE_CORAL else INK)
    para(text, x+padding, top+34, width-2*padding, size=11.4, leading=16.2)
    return top+h

def step(number, title, text, top):
    c.setFillColor(BLUE)
    c.circle(M+12, H-top-12, 12, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont('Display', 12)
    c.drawCentredString(M+12, H-top-16, str(number))
    h1 = para(title, M+38, top, CW-38, size=14.1, leading=17, font='Bold')
    h2 = para(text, M+38, top+h1+6, CW-38, size=11.6, leading=16.6)
    return top+h1+6+h2+21

def check(text, top, x=M, width=CW):
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.8)
    c.rect(x, H-top-12, 10, 10, fill=0, stroke=1)
    h = para(text, x+22, top-1, width-22, size=11.5, leading=16.4)
    return top+h+12

def table(rows, top, widths, header=None, size=11):
    if header:
        box(M, top, CW, 28, GREEN)
        x=M
        for text, w in zip(header, widths):
            label(text, x+11, top+8, size=9, color=WHITE)
            x+=w
        top+=28
    for n, row in enumerate(rows):
        paragraphs=[]
        for text, width in zip(row, widths):
            p = Paragraph(text, ParagraphStyle('cell', fontName='Body', fontSize=size, leading=size*1.38,
                                               textColor=INK))
            _, h = p.wrap(width-22, H)
            paragraphs.append((p,h))
        rh=max(h for p,h in paragraphs)+22
        if top+rh>H-50:
            raise ValueError(f'Table overflow p{c.getPageNumber()}')
        box(M, top, CW, rh, WHITE if n%2==0 else HexColor('#EBEEE7'))
        x=M
        for (p,h),w in zip(paragraphs,widths):
            p.drawOn(c,x+11,H-top-11-h)
            x+=w
        top+=rh
    return top

def code(lines, top, caption=None, size=11.6):
    if caption:
        top+=para(caption, M, top, CW, size=11.2)+9
    h=len(lines)*19+26
    if top+h > H-50:
        raise ValueError(f'Code runs off page {c.getPageNumber()}')
    box(M,top,CW,h,INK,radius=4)
    for i,text in enumerate(lines):
        if pdfmetrics.stringWidth(text,'Mono',size)>CW-28:
            raise ValueError('Code line too wide: '+text)
        label(text,M+14,top+12+i*19,size=size,color=WHITE,font='Mono')
    return top+h

def source_note(text, top):
    return top+para(text,M,top,CW,size=8.5,leading=11.8,color=GRAY)

def monitor(x, top, w, h, color, letter, caption='', art=True):
    box(x,top,w,h,INK,radius=5)
    box(x+5,top+5,w-10,h-10,color)
    if art:
        c.setFillColor(Color(1,1,1,alpha=0.25))
        c.circle(x+w*.64,H-top-h*.42,min(w,h)*.24,fill=1,stroke=0)
        c.setFillColor(Color(1,1,1,alpha=0.20))
        c.rect(x+w*.14,H-top-h*.85,w*.30,h*.45,fill=1,stroke=0)
    label(letter,x+13,top+9,size=21,color=WHITE,font='Display')
    box(x+w*.45,top+h,w*.1,9,INK)
    box(x+w*.30,top+h+9,w*.4,4,INK)
    if caption:
        para(caption,x,top+h+25,w,size=10.2,leading=14.2,font='Bold')

def arrow(x1,y1,x2,y2,color=GREEN,width=2):
    line(x1,y1,x2,y2,color,width)
    length=math.hypot(x2-x1,y2-y1)
    ux,uy=(x2-x1)/length,(y2-y1)/length
    for sign in (-1,1):
        line(x2-7*ux+sign*4*uy,y2-7*uy-sign*4*ux,x2,y2,color,width)

# 01 Cover
box(0,0,W,H,PAPER)
label('A PRACTICAL GUIDE FOR ARTISTS & DESIGNERS',M,39,9.3,GREEN)
para('Two screens.<br/>One small<br/>computer.',M,105,CW,size=59,leading=61,font='Display')
para('Looping video for a graduate exhibition',M,307,CW,size=18.2,leading=23,font='Body')
para('Raspberry Pi 5<br/>Independent loops + synchronized playback options',M,351,CW,size=12.2,leading=19,color=GRAY)
monitor(M,434,234,132,CORAL,'A')
monitor(M+269,434,234,132,BLUE,'B')
line(M+117,585,M+117,613,CORAL,2)
line(M+386,585,M+386,613,BLUE,2)
line(M+117,613,M+251,613,CORAL,2)
line(M+386,613,M+251,613,BLUE,2)
box(M+185,625,132,44,GREEN,radius=5)
label('RASPBERRY PI 5',M+202,639,10,WHITE)
para('Rehearse with the real Pi, screens and final files.<br/>Print the daily crew card on page 14.',M,707,CW,size=12.4,leading=18)
label('DUTCH DESIGN WEEK  /  EXHIBITION EDITION  /  OCTOBER 2026',M,801,7.6,GRAY)
c.bookmarkPage('page1')
c.addOutlineEntry('Two screens. One small computer.','page1',level=0)
end()

# 02 Decision
y=page(2,'Start here','Choose how the videos behave.',
       'Decide before exporting or ordering. This kit has not been tested on a physical Pi; book the full rehearsal now.')
y=table([
    ('<b>Separate loops</b><br/>A and B can have different lengths. Their timing can drift.',
     'One Pi, two HDMI cables.<br/><b>Follow pages 3-9.</b>'),
    ('<b>One shared timeline</b><br/>The relationship between A and B must stay fixed.',
     'One combined movie plus a professional cropping controller. Ask the venue / AV supplier about rental cost now.<br/><b>See pages 10-11.</b>'),
    ('<b>Exact frame timing</b><br/>A flash, movement or join must match across screens.',
     'Have an AV technician specify and test synchronized outputs and display delay.<br/><b>See page 11.</b>'),
],y,[257,CW-257],['THE ARTWORK NEEDS','THE PLAYBACK ROUTE'],size=11.1)
y+=23
y+=para('<b>Two players do not stay in sync.</b> Each runs its own timeline; loops and player restarts can separate them further. Choose the shared route if their timing matters.',M,y,CW,size=11.5,leading=16.2)
y+=26
y+=heading('Your route through the guide',y)+13
y=table([
    ('Prepare','Equipment, exports, SD card and cables','3-6'),
    ('Set up','Desktop settings, installer, movies and startup','7-9'),
    ('Adapt','Synchronization and sound','10-12'),
    ('Run','Rehearsal, daily crew card and troubleshooting','13-15'),
    ('Helper','Spare card, protected mode, diagnostics and sources','16-19'),
],y,[80,350,CW-430],size=10.5)
end()

# 03 Kit
y=page(3,'Before you begin','Gather the kit.',
       'Use a dedicated Pi and a fresh SD card. Allow a relaxed afternoon for setup, then an overnight rehearsal.')
y=table([
    ('1','<b>Raspberry Pi 5, 4 GB or 8 GB RAM</b><br/>Either is a sensible starting point for two 1080p movies.'),
    ('1','<b>Official Raspberry Pi 27 W USB-C power supply</b><br/>Use the appropriate EU plug for the venue.'),
    ('1','<b>Active Cooler or a Pi 5 case with a fan</b><br/>Fit it before powering on. Leave air space around the enclosure.'),
    ('1','<b>64 GB or larger microSD card + card reader</b><br/>Choose a reputable A2 card; allow room for the OS and both movies.'),
    ('2','<b>Powered HDMI screens + two micro-HDMI-to-HDMI cables</b><br/>For independent mode. Each screen needs its own power connection.'),
    ('1 set','<b>USB keyboard and mouse</b><br/>Keep them available throughout the exhibition.'),
    ('1','<b>Laptop, USB memory stick and setup-kit ZIP</b><br/>The laptop prepares the card; the USB stick transfers the kit and movies.'),
    ('A few','<b>Cable labels, spare HDMI cable and a spare prepared SD card</b><br/>Pack the monitor remotes, power strip and any speakers too.'),
],y,[54,CW-54],['QTY','ITEM'],size=10.6)
y+=14
y=callout('For the synchronized route',
          'Budget for a professional cropping controller and AV setup. Ask the venue or supplier about rental now; this can cost more than the Pi kit. Independent loops need no controller (pages 10-11).' ,y,PALE_CORAL)
y+=8
source_note('Hardware specifications: Raspberry Pi 5 [1]. The quantities, card capacity and spare kit above are practical recommendations.',y)
end()

# 04 Export
y=page(4,'Prepare the artwork','Export the exhibition files.',
       'Keep the master artwork on your laptop. Make playback copies for the Pi.')
y=table([
    ('File type','<b>MP4 with H.264 video</b>, 8-bit, standard SDR colour. MP4 is the file container; H.264 is the video format.'),
    ('Landscape screen','<b>1920 x 1080 pixels</b>. Start with 25 or 30 frames per second.'),
    ('Portrait screen','<b>1080 x 1920 pixels</b>. Export upright, then rotate the screen in desktop settings (page 7).'),
    ('Frame rate','Test both movies together. If supported, use 50 Hz for 25 fps or 60 Hz for 30 fps in Screens settings. Higher frame rates add work.'),
    ('Quality / bitrate','Start around <b>8-12 Mb/s per 1080p movie</b>. Inspect gradients and fine detail; adjust after testing.'),
    ('Sound','Silent work: export without audio, or keep the player muted. Sound work: use AAC audio and follow page 12.'),
    ('Filenames','Keep your own names. Put <b>one MP4 in folder A</b> and <b>one MP4 in folder B</b> (page 9). Move old versions out of these folders.'),
],y,[139,CW-139],['SETTING','INDEPENDENT LOOPS'],size=11.1)
y+=23
y=callout('Playback has to be rehearsed',
          'The Pi 5 can drive two 4K displays, but H.264 playback uses its CPU. Two 4K movies may overload this setup. Start with 1080p and active cooling; test both final files together. HEVC hardware support does not guarantee acceleration in every player build. [1, 2]',y)
y+=17
y+=para('<b>A clean loop:</b> remove accidental black frames and check the last-to-first-frame transition. Audio should also join cleanly. The player repeats the file, but cannot guarantee an invisible or gapless seam.',M,y,CW,size=11.5)
y+=13
source_note('For artwork that must stay in sync, prepare one combined movie using page 10 instead of these two separate files.',y)
end()

# 05 OS
y=page(5,'Step 1 / On your laptop','Give the Pi its operating system.',
       'The operating system turns the blank board into a small desktop computer.')
y=callout('This step erases the selected card',
          'Use the dedicated SD card and check its size before writing. Unplug other removable drives so you cannot choose them by mistake.',y,PALE_CORAL)
y+=24
y=step(1,'Install Raspberry Pi Imager.',
       'Get it from <link href="https://www.raspberrypi.com/software/" color="#2E4DDD">raspberrypi.com/software</link>. Open it and insert the microSD card using the reader.',y)
y=step(2,'Choose the device, OS and card.',
       'Choose <b>Raspberry Pi 5</b>, then <b>Raspberry Pi OS (64-bit) with Desktop</b> (Trixie). Select the dedicated microSD card. Use the desktop version; Lite has no desktop. [3, 4]',y)
y=step(3,'Set your account and location.',
       'Use a simple username such as <b>exhibit</b>, choose a password and record it privately. Set the keyboard layout you actually use. For the venue, choose the Netherlands / Amsterdam timezone and Wi-Fi country. Add Wi-Fi for setup. [3]',y)
y=step(4,'Write, verify and eject.',
       'Proceed through Imager\'s confirmation. Let writing and verification finish. Eject the card safely, then insert it into the Pi while the Pi is unplugged. [3]',y)
y=callout('You should now have',
          'A card ready to boot the desktop, plus your recorded username and password. The setup scripts use your actual account automatically; it does not have to be named pi.',y)
end()

# 06 Wires
y=page(6,'Step 2 / At the Pi','Connect the two screens.',
       'This wiring is for independent loops. Use the controller wiring on page 10 for the shared-timeline route.')
diagram_top=y
monitor(M,diagram_top,204,116,CORAL,'A','Video A / HDMI0')
monitor(W-M-204,diagram_top,204,116,BLUE,'B','Video B / HDMI1')
board_top=diagram_top+180
box(M+107,board_top,289,86,GREEN,radius=7)
label('RASPBERRY PI 5',M+128,board_top+17,17,WHITE,'Display')
label('USB-C power',M+121,board_top+56,8.5,WHITE)
label('HDMI0',M+234,board_top+56,9,WHITE)
label('HDMI1',M+317,board_top+56,9,WHITE)
arrow(M+245,board_top-10,M+102,diagram_top+156,CORAL)
arrow(M+327,board_top-10,W-M-102,diagram_top+156,BLUE)
y=board_top+107
y+=para('Connection diagram only; use the HDMI0 / HDMI1 markings on the actual board.',M,y,CW,size=8.9,color=GRAY)+19
y=step(1,'Label both ends of every HDMI cable.',
       'Put <b>A</b> on the cable from Pi HDMI0 to Screen A, and <b>B</b> on the cable from Pi HDMI1 to Screen B. Insert the keyboard, mouse and prepared SD card. [3]',y)
y=step(2,'Turn the screens on first.',
       'Use each monitor\'s remote or buttons to choose the HDMI input you plugged into. Then connect the Pi\'s USB-C power supply. Finish any first-boot prompts. [3]',y)
y=callout('You should see',
          'A desktop on the screens. If a screen says No Signal, first check its selected input, its power and the cable. A splitter is unnecessary for independent videos.',y)
end()

# 07 Desktop
y=page(7,'Step 3 / On the Pi desktop','Set the screens and startup.',
       'Open the Raspberry Pi menu, then Preferences > Control Centre. Menu wording can vary slightly with updates.')
y=table([
    ('<b>Screens</b>','Enable both displays and arrange them <b>side by side</b>. Choose an extended desktop, with mirroring off. Start at 1920 x 1080 on each landscape monitor. [5]'),
    ('<b>Portrait work</b>','In Screens, rotate the relevant display 90 or 270 degrees so the desktop is upright. Keep its native 1920 x 1080 mode; rotation makes the usable canvas 1080 x 1920. [5]'),
    ('<b>System</b>','Choose <b>Boot: To desktop</b> and turn <b>Desktop Auto Login ON</b>. Save or close the settings. [5]'),
    ('<b>Display</b>','Turn <b>Screen Blanking OFF</b>, then close the settings. [5]'),
    ('<b>Each monitor</b>','In its own on-screen menu, disable sleep timers, automatic power-off and input switching. Use a fit-to-screen / Just Scan mode if edges are cropped.'),
],y,[126,CW-126],['WHERE','WHAT TO SET'],size=10.6)
y+=17
y+=heading('Check the display names',y)+12
y=code(['wlr-randr'],y,'Open Terminal with <b>Ctrl + Alt + T</b>. Type this, then press Enter:')
y+=13
y+=para('You should see two outputs. They are usually <b>HDMI-A-1</b> (HDMI0) and <b>HDMI-A-2</b> (HDMI1). Confirm which screen is which in Screens settings; the installer will ask for their names. Do not assume left/right position proves the port mapping.',M,y,CW,size=11.5)
y+=6
y=callout('You should now have',
          'Two desktop areas, upright artwork, auto login and no screen blanking. In desktop appearance settings, use a <b>plain black background</b> so recovery looks less distracting.',y)
end()

# 08 Install
y=page(8,'Step 4 / On the Pi','Install the playback kit.',
       'Use this guided installer on the Pi. Keep this page beside you while it runs.')
y=step(1,'Unzip and copy the kit.',
       'Extract <b>Exhibition-Setup-Kit.zip</b> on your laptop. Copy the <b>exhibit-kit</b> folder to a USB stick. On the Pi, open File Manager and copy that whole folder into <b>Home</b>. Its name must stay <b>exhibit-kit</b>.',y)
y=step(2,'Open Terminal on the Pi.',
       'Press <b>Ctrl + Alt + T</b>. Type each line below, pressing Enter after each. Or copy and paste into Terminal with <b>Ctrl + Shift + V</b>. <b>~</b> means Home.',y)
y=code(['cd ~/exhibit-kit','bash install.sh'],y)
y+=14
y+=para('The Pi needs internet for this step. If asked, type your Pi password and press Enter; the password stays invisible. Let the installation finish. If it stops with an error, keep the message for your helper.',M,y,CW,size=11.4)
y+=21
y=step(3,'Answer the short setup questions.',
       'For two direct HDMI cables, choose <b>1: INDEPENDENT</b>. Select Screen A\'s output, then Screen B\'s. Choose <b>SILENT</b> or sound from Video A. For the controller route, choose <b>2: SHARED TIMELINE</b> and its input output (page 11).',y)
y=callout('Wait for SETUP COMPLETE',
          'The kit creates <b>Home > exhibit</b> with <b>A</b>, <b>B</b> and <b>Shared</b> folders, plus Start / Stop Exhibit controls. It saves a desktop backup and adds screen recovery and player restarts. Movies start in the next step.',y)
y+=13
source_note('Run the kit as your ordinary desktop user, without putting sudo before bash install.sh. The kit requests sudo only for package installation.',y)
end()

# 09 First Playback
y=page(9,'Step 5 / On the Pi','Copy the movies. Press play.',
       'The movies live on the Pi\'s SD card. A USB stick and internet are not needed during playback.')
y=step(1,'Copy into Home > exhibit.',
       'Open <b>A</b> and copy Screen A\'s MP4 into it. Open <b>B</b> and copy Screen B\'s MP4 into it. Keep the filenames you already use. Each folder must contain <b>only one MP4</b>. Shared mode uses <b>one MP4 in Shared</b>. Finish copying before ejecting the USB stick.',y)
y=step(2,'Start the exhibition.',
       'Double-click <b>Start Exhibit</b> on the desktop. If prompted, choose Execute / Allow Launching. You can also open it from the application menu or use the command below.',y)
y=code(['python3 ~/exhibit/control.py start'],y)
y+=17
y=callout('You should see',
          'Video A filling Screen A and Video B filling Screen B, with no player buttons or mouse pointer. Each repeats. If the artwork is narrower than the screen, black bars preserve its proportions.',y)
y+=23
y=step(3,'Reboot to prove automatic startup.',
       'Briefly press the Pi power button once and choose <b>Reboot / Restart</b> in its dialog. Leave both screens on. Movies should start by themselves. Allow about two minutes for the Pi; if a screen is late, the kit keeps waiting.',y)
y=step(4,'Check the work, not just the computer.',
       'Watch the beginning and at least two loop joins. Confirm the correct artwork, orientation, edge framing and sound. Then run the overnight rehearsal on page 13.',y)
source_note('The normal player keys are disabled to avoid accidental pauses. Use the Start / Stop controls instead of q, Escape or the space bar.',y)
end()

# 10 Shared Timeline
y=page(10,'Synchronized option / The artwork','Put both pictures in one movie.',
       'This suggested route uses one playback timeline and a separate device to crop it into two screen images.')
frame_top=y
frame_w=268
frame_h=151
fx=M
box(fx,frame_top,frame_w,frame_h,INK)
box(fx,frame_top,frame_w/2,frame_h/2,CORAL)
box(fx+frame_w/2,frame_top,frame_w/2,frame_h/2,BLUE)
label('A',fx+12,frame_top+9,25,WHITE,'Display')
label('B',fx+frame_w/2+12,frame_top+9,25,WHITE,'Display')
label('Unused black area',fx+55,frame_top+107,10,WHITE)
para('<b>One 3840 x 2160 frame</b><br/><br/>A: top left, 1920 x 1080<br/>B: top right, 1920 x 1080<br/><br/>Both share one timeline.',M+293,frame_top+2,CW-293,size=10.8,leading=15.3)
y=frame_top+171
y=step(1,'Build a combined composition in your video editor.',
       'Make a <b>3840 x 2160</b> canvas. Place A at the top left and B at the top right, each at 1920 x 1080 with no gap. Leave the bottom half black. Align both on one timeline and give the composition one agreed loop length.',y)
y=step(2,'Export one combined MP4.',
       'Try <b>HEVC / H.265, 8-bit SDR, 25 or 30 fps</b>. Keep your filename. Have the helper confirm hardware decoding (page 18), then rehearse the final 4K movie. [1, 2, 6]',y)
y=step(3,'Send one HDMI signal to a cropping controller.',
       'Connect Pi <b>HDMI0 to the controller input</b>. Connect controller outputs 1 and 2 to Screens A and B. Pi HDMI1 is unused during the show. Ask the technician to crop the two top regions separately. [9]',y)
y=callout('Arrange the controller and budget early',
          'An ordinary HDMI splitter duplicates the entire frame. You need a <b>video wall controller with independent crop regions</b>, preconfigured by the supplier. A Datapath Fx4-HDR is one documented example; arrange a rental or suitable equivalent with the venue. [9]',y,PALE_CORAL)
end()

# 11 Sync handoff
y=page(11,'Synchronized option / AV handoff','Give this page to the technician.',
       'The controller and displays need their own rehearsal. One shared movie preserves the content timing; display refresh and processing can still create a visible offset.')
y=table([
    ('<b>Input</b>','Pi HDMI0, <b>3840 x 2160 at 25 or 30 Hz</b>. Use a controller that accepts this timing and stores its mapping through power cycles.'),
    ('<b>Crop A</b>','Source rectangle <b>x=0, y=0, width=1920, height=1080</b> to output 1.'),
    ('<b>Crop B</b>','Source rectangle <b>x=1920, y=0, width=1920, height=1080</b> to output 2.'),
    ('<b>Outputs</b>','Set both to 1920 x 1080 at the same suitable refresh rate, without cropping the artwork. Configure rotation / scaling in the controller for portrait screens.'),
    ('<b>Timing test</b>','Use a temporary numbered-frame or flashing-marker version of the shared movie. Check both screens at startup, loop joins and after an hour. Match monitor picture modes and processing delay.'),
],y,[105,CW-105],['CHECK','REQUEST'],size=10.8)
y+=19
y+=heading('Use the Pi kit in shared mode',y)+10
y+=para('With the controller connected, install the kit (page 8), select <b>SHARED TIMELINE</b> and select the Pi output that feeds it. In Screens, set that output to the agreed 4K timing. Copy <b>one combined MP4</b> into <b>Home > exhibit > Shared</b>, then use the same Start / Stop controls. Only one player runs. Test controller power-on before Pi startup.',M,y,CW,size=11.3,leading=16.1)
y+=20
y=callout('If the 4K movie stutters',
          'A lower-load proof of concept uses a <b>1920 x 1080</b> canvas with A and B at <b>960 x 540</b> in the two top corners. Change the crop regions to match; the controller upscales them. Detail is reduced. If that is unacceptable, use an AV playback computer for the same combined-file route.',y)
y+=10
y+=para('<b>For exact frame timing:</b> ask the AV team to verify output timing and screen latency. Another route is two compatible BrightSign players on wired Ethernet with Enhanced Sync / PTP. Verify the models, formats and resynchronization at every loop. [10]',M,y,CW,size=10.8,leading=15.2)
end()

# 12 Audio
y=page(12,'Optional / Sound','Route the sound.',
       'A movie\'s screen position does not automatically choose its speaker output.')
y=table([
    ('<b>Silent artwork</b>','Choose SILENT during setup. Both videos stay muted.'),
    ('<b>One soundtrack</b>','Choose SOUND. Video A, or the shared movie, uses the desktop default sound output. Select it in the speaker menu and set the volume.'),
    ('<b>Separate sound</b>','Use the sound helper below. Choose a distinct HDMI or USB audio output for each movie. A shared output mixes both sounds.'),
],y,[155,CW-155],['YOUR WORK','SETUP'],size=11)
y+=20
y=code(['python3 ~/exhibit/audio.py'],y,'Open Terminal on the Pi and run:')
y+=16
y+=para('The helper stops playback and lists sound devices. Choose <b>0</b> for silence, or the number of the output you want for each movie. Click <b>Start Exhibit</b> again and listen at each screen. If the list is empty, connect or enable the audio device and try again.',M,y,CW,size=11.5)
y+=18
y+=para('<b>Test by listening:</b> use a temporary clip that says "A" or "B". Confirm the physical speakers. Recheck after changing monitors, HDMI cables or USB audio devices.',M,y,CW,size=11.5)
y+=22
y+=heading('A few practical choices',y)+12
y=check('The Pi 5 has no built-in 3.5 mm audio socket. Use HDMI audio, a USB audio device or speakers connected to the monitor. [1, 3]',y)
y=check('Avoid Bluetooth for timing-critical sound. Keep the chosen speakers and audio connections consistent during rehearsal and installation.',y)
y=check('For the shared movie, make one deliberate soundtrack or mix in your video editor. Ask the AV supplier how the controller handles sound.',y)
source_note('Audio selection and device listing use mpv\'s documented options [6]. The kit uses named devices when you select them.',y)
end()

# 13 Rehearse
y=page(13,'Before you travel','Rehearse the actual exhibition.',
       'This kit has not been tested on a physical Pi. The real Pi, final files and exact venue hardware must pass these checks before the show.')
y=check('<b>Picture and sound:</b> correct videos, upright portrait work, complete edges, smooth motion, intended speakers and no player interface or mouse pointer.',y)
y=check('<b>Loop joins:</b> watch several last-to-first-frame transitions. Check for black frames, a pause, frozen image or sound click. Repeat for the shared route.',y)
y=check('<b>Overnight:</b> run 8-12 hours with both final movies. Check again in the morning. Keep vents clear; watch for update notices or any desktop pop-ups over the artwork.',y)
y=check('<b>Screen recovery:</b> switch one monitor off, wait, then on again. Repeat with the other. If an output disappears, both movies stop; they should restart on their assigned screens once both outputs return. A brief misplaced image can occur before detection.',y)
y=check('<b>Slow screen:</b> start the Pi before one monitor, leaving that monitor off for more than two minutes. Turn it on; playback should begin without clicking Start Exhibit.',y)
y=check('<b>Opening and closing:</b> practise page 14 three times. Check the power button is reachable inside the plinth. Try Stop / Start Exhibit too.',y)
y=check('<b>Venue power:</b> with a tested spare card ready, ask the helper to test one mains-off / mains-on cycle after protected mode is enabled (page 17). Use the actual power strip; verify the monitors and controller also come back.',y)
y=check('<b>Offline:</b> finish setup and updates, then disconnect Wi-Fi / Ethernet and reboot. Confirm playback and absence of prompts. A helper should suppress any update notifier that interrupted rehearsal; retest.',y)
y+=9
y=callout('Before packing',
          'Finish all changes, make and boot-test the spare card (page 16), then protect both cards (page 17) and repeat startup checks. Give the crew page 14 and a helper phone number. Do not rely on the exhibition week to discover problems.',y)
end()

# 14 Crew card
y=page(14,'Print and keep beside the work','Daily crew card.',
       'Use this page after the setup has passed its full rehearsal.')
left=M
right=M+269
col=234
box(left,y,col,38,GREEN)
box(right,y,col,38,BLUE)
label('OPEN THE EXHIBITION',left+13,y+10,12,WHITE,'Display')
label('CLOSE THE EXHIBITION',right+13,y+10,12,WHITE,'Display')
ty=y+53
para('<b>1. Turn on both screens.</b><br/>Choose the correct HDMI inputs. In shared mode, turn on the controller too.<br/><br/><b>2. Power the Pi.</b><br/>Reconnect its power or briefly press the Pi\'s power button if it was shut down while still plugged in.<br/><br/><b>3. Wait for playback.</b><br/>Allow about two minutes. Both pictures should play automatically.<br/><br/><b>4. Check the work.</b><br/>Correct videos, orientation, sound and movement. Keep the vents clear.',left,ty,col,size=11.5,leading=17.1)
para('<b>1. Press the Pi power button twice.</b><br/>Two brief presses in quick succession start a clean shutdown. You can leave the videos playing. [12]<br/><br/><b>2. Wait for shutdown.</b><br/>The pictures disappear. Wait for the Pi\'s red standby light, then another 10 seconds. Use the cue checked in rehearsal.<br/><br/><b>3. Switch off the power.</b><br/>You may now turn off the power strip and screens.<br/><br/><b>Use brief presses.</b><br/>Do not hold the button down; that forces power off.',right,ty,col,size=11.5,leading=17.1)
y=ty+295
y=callout('If a picture is missing, misplaced or frozen',
          'Turn both screens on and check their HDMI inputs. Wait a few seconds for automatic recovery. If needed, connect the mouse and keyboard; press <b>Ctrl + Alt + T</b> and use the restart line below. Or choose <b>Start Exhibit</b> in the Pi menu under Sound &amp; Video.',y,PALE_CORAL)
y+=13
y=code(['python3 ~/exhibit/control.py start'],y,'<b>Restart the pictures:</b>',size=10.8)
y+=17
label('HELPER NAME / PHONE',M,y,8.8,GREEN)
line(M+138,y+15,W-M,y+15,GRAY,.7)
end()

# 15 Troubleshoot
y=page(15,'When something goes wrong','Start with the visible symptom.',
       'Use the simple checks first. Keep any error message for your helper.')
y=table([
    ('<b>No Signal</b>','Check monitor power, selected HDMI input and both cable ends. Start with the monitors on before the Pi. Try the spare cable.'),
    ('<b>Desktop, no movies</b>','Turn both screens on. Check that A and B (or Shared) each contain one MP4. Click Start Exhibit; keep any error message.'),
    ('<b>Videos on wrong screens</b>','Stop Exhibit. Check A / B cable labels. Ask the helper to rerun the installer with the correct output choices; movies are kept.'),
    ('<b>Both videos on one screen</b>','Turn both screens on, check HDMI inputs, then click <b>Start Exhibit</b>. If it repeats, ask the helper to inspect the connections (page 18).'),
    ('<b>Both screens look identical</b>','For independent mode, turn desktop mirroring off. Confirm that the two files are different. An ordinary splitter cannot provide two pictures.'),
    ('<b>Small picture / black bars</b>','The player preserves proportions. Match the export to the screen shape. Check screen rotation and the monitor\'s fit-to-screen setting.'),
    ('<b>Stops after a few minutes</b>','Check Pi screen blanking and the monitor\'s own sleep / power-off settings. A still-running frozen player needs a manual restart.'),
    ('<b>Jerky video / hot Pi</b>','Clear vents and check the fan and official power supply. Try the 1080p export settings. Keep both exact files running during your test.'),
    ('<b>Wrong or missing sound</b>','Check speaker power, mute and volume. Run the sound helper (page 12). Screen assignment and sound assignment are separate.'),
],y,[145,CW-145],['SYMPTOM','FIRST ACTION'],size=10.7)
y+=14
y=callout('Changes disappeared after a restart?',
          'Protected mode discards changes. Ask the helper to unlock it before changing movies or settings (page 17). Keep startup.log for the helper.',y)
end()

# 16 Spare card
y=page(16,'Helper / After the artwork is final','Make a working spare card.',
       'Do this while protected mode is OFF. The spare must boot the actual exhibition, including the final movies. [13]')
y=callout('The destination card will be erased',
          'Unplug other removable drives. Use a spare card with at least the original card\'s capacity. Confirm device names and sizes: the Pi\'s internal card is the source, never the destination.',y,PALE_CORAL)
y+=19
# Simplified labelled interface illustration, not a version-specific screenshot.
box(M,y,CW,123,WHITE,stroke=LINE,radius=5)
label('SD CARD COPIER / DEVICE CHOICES',M+16,y+12,9,GREEN)
label('Copy From Device',M+16,y+40,11,INK)
box(M+169,y+34,CW-187,27,PAPER,stroke=LINE,radius=3)
label('Internal Pi SD card  [source]',M+179,y+41,10,INK)
label('Copy To Device',M+16,y+79,11,INK)
box(M+169,y+73,CW-187,27,PALE_CORAL,stroke=LINE,radius=3)
label('USB reader + spare  [erased]',M+179,y+80,10,INK)
y+=135
y+=para('Illustration only. Read the actual device names and capacities on your Pi.',M,y,CW,size=9,color=GRAY)+17
y=step(1,'Connect the spare card.',
       'Click Stop Exhibit. Insert the spare into a USB card reader and connect it to the Pi. Leave the working card in the Pi\'s own slot.',y)
y=step(2,'Open SD Card Copier.',
       'Open <b>Accessories > SD Card Copier</b> in the Pi menu. Set <b>Copy From Device</b> to the internal card and <b>Copy To Device</b> to the USB spare. Check <b>New Partition UUIDs</b> if offered. Check both devices before Start. If absent, ask the helper to install piclone.',y)
y=step(3,'Copy, then test the spare.',
       'Wait for completion. Shut down cleanly (page 14), unplug Pi power, disconnect the USB reader and swap cards. Reconnect power with the screens on. Check automatic startup, both videos, loop joins and sound. Label the tested spare; protect each card separately using page 17.',y)
y+=para('<b>Pack a working backup.</b> Keep the spare in a labelled case and source movies / kit on your laptop. Never remove the Pi\'s card while powered.',M,y,CW,size=11.3,leading=16.1)
end()

# 17 Protected mode
y=page(17,'Helper / After the final rehearsal','Protect the finished installation.',
       'Optional protected exhibition mode reduces SD-card writes during venue power cuts. Clean shutdown is still the daily routine.')
y=callout('Finish and back up first',
          'When protection is active, movie and setting changes are temporary and vanish after reboot. Make the tested spare first (page 16). Tell the artist how to request a movie change.',y,PALE_CORAL)
y+=18
y=step(1,'Enable both kinds of protection.',
       'Stop Exhibit. Open <b>Preferences > Control Centre > Performance</b>. Beside <b>Overlay File System</b>, select Configure. Turn <b>Use Overlay ON</b> and <b>Write-protect Boot Partition ON</b>. Save, close and reboot. [5]',y)
y=step(2,'Verify the actual mounts after reboot.',
       'The first command below must report <b>overlay</b>. The second must include <b>ro</b> as a whole option (read-only). If either check fails, correct the settings before the power-cycle rehearsal.',y)
y=code(['findmnt -n -o FSTYPE /', 'findmnt -n -o OPTIONS /boot/firmware'],y,size=10.7)
y+=18
y=step(3,'Rehearse and label.',
       'Confirm both movies start, screen recovery works and sound is correct. Run the overnight and venue-power checks. Mark this card <b>PROTECTED - unlock before changes</b>. Repeat on the spare card.',y)
y+=heading('To change movies or settings later',y,size=18)+11
y+=para('Stop Exhibit. Turn <b>both protection settings OFF</b> in the same window, then reboot. Verify that / is no longer overlay and /boot/firmware includes rw. Only then change movies or settings. Rehearse, refresh the spare, re-enable both protections and reboot-test again.',M,y,CW,size=11.3,leading=16.1)
y+=16
source_note('Overlay changes live in RAM; boot protection is separate. Power or storage failures can still cause damage. If unlocking is refused, ask the helper to use raspi-config before changing files. [5]',y)
end()

# 18 Diagnostics
y=page(18,'Helper / Only when needed','Check decoding and connections.',
       'These checks run on the Pi. They are not part of the artist\'s daily opening routine.')
y+=heading('Confirm the 4K shared decoder',y,size=19)+12
y=code(['python3 ~/exhibit/diagnose.py shared'],y,'Run this with the final movie in Shared. It stops exhibition playback:')
y+=13
y+=para('The check plays briefly with the <b>same Wayland and decoder options as the kit</b>, then asks mpv which decoder is active. A named hardware decoder is the desired result; <b>no</b> means software decoding. It saves <b>decoding.log</b> in Home > exhibit. Click Start Exhibit afterwards. Hardware decoding still needs a whole-movie smoothness test. [6]',M,y,CW,size=11.2,leading=16)
y+=15
y=code(['python3 ~/exhibit/diagnose.py shared --decoder drm'],y,'Optional AV trial if auto chooses software:',size=10.2)
y+=10
y+=para('This is a trial only; it does not save a decoder choice. If it works, the AV helper must configure hwdec_shared in settings.json to drm while protection is off, then confirm normal playback and rehearse again. If neither works, investigate the media stack or use the AV-computer fallback. [6]',M,y,CW,size=10.8,leading=15.1)
y+=19
y+=heading('If screen recovery still fails',y,size=19)+11
y+=para('Check wlr-randr and startup.log, cables and monitor sleep settings. The watcher polls about once a second; it stops both independent players when an assigned output disappears, then restarts them after the outputs settle. Screen power-off that leaves HDMI connected is not detectable. Test the physical result.',M,y,CW,size=11.1,leading=15.6)
y+=14
y=code(['video=HDMI-A-1:1920x1080@60D', 'video=HDMI-A-2:1920x1080@60D'],y,'<b>Optional fixed-output example</b> for two compatible 1080p / 60 Hz screens:',size=10.7)
y+=12
y+=para('Back up /boot/firmware/cmdline.txt. Append both options, separated by spaces, to its <b>existing single line</b>; the display above wraps them only for readability. D forces a digital output. Match the real screen modes, test desktop arrangement / rotation and monitor off/on, and remove the additions if they cause problems. Unlock protection before editing. This is not a universal fix. [14]',M,y,CW,size=10.5,leading=14.5)
end()

# 19 References
y=page(19,'Reference / For the helper','Sources and useful checks.',
       'Official documentation was reviewed in October 2026. Use these clickable links if menus or AV equipment differ.')
y=code(['wlr-randr',
        "journalctl --user -u 'exhibit-*' -n 80 --no-pager",
        'vcgencmd get_throttled'],y,'Copyable helper commands are also in START-HERE.txt:',size=9.7)
y+=16
y+=para('<b>Validation:</b> scripts were checked with automated logic tests; every manual page was rendered and reviewed. No physical Pi, controller or venue monitors were available. Only rehearsal with the actual equipment can establish playback performance, recovery and timing.',M,y,CW,size=10.6,leading=15)
y+=20
y+=heading('Official references',y,size=19)+12
refs=[
 ('1','Raspberry Pi 5 specifications','https://www.raspberrypi.com/products/raspberry-pi-5/'),
 ('2','Raspberry Pi: H.264 / HEVC software environment','https://www.raspberrypi.com/news/optimising-raspberry-pi-5s-software-environment/'),
 ('3','Raspberry Pi: getting started and Imager','https://www.raspberrypi.com/documentation/computers/getting-started.html'),
 ('4','Raspberry Pi OS: current desktop / Trixie downloads','https://www.raspberrypi.com/software/operating-systems/'),
 ('5','Raspberry Pi: screens, rotation, login and blanking','https://www.raspberrypi.com/documentation/computers/configuration.html'),
 ('6','mpv: playback, looping, Wayland and audio options','https://mpv.io/manual/stable/'),
 ('7','labwc: window rules and app identifiers','https://labwc.github.io/labwc-config.5.html'),
 ('8','labwc: MoveToOutput and ToggleFullscreen','https://labwc.github.io/labwc-actions.5.html'),
 ('9','Datapath Fx4-HDR: cropping / multi-output controller','https://www.datapath.co.uk/datapath-products/video-wall-controllers/datapath-fx4-hdr/'),
 ('10','BrightSign: shared-clock synchronization architecture','https://docs.brightsign.biz/technical/video-wall-sync-architecture'),
 ('11','systemd: automatic service restart behaviour','https://github.com/systemd/systemd/blob/main/man/systemd.service.xml'),
 ('12','Raspberry Pi: power button and clean shutdown','https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-button'),
 ('13','Raspberry Pi: SD Card Copier source and documentation','https://github.com/raspberrypi-ui/piclone'),
 ('14','Linux kernel: forced digital video modes','https://www.kernel.org/doc/html/latest/fb/modedb.html'),
]
for number,title,url in refs:
    y+=para(f'<b>[{number}]</b> <link href="{escape(url)}" color="#2E4DDD">{escape(title)}</link>',M,y,CW,size=9.2,leading=12.7)+4
y+=8
source_note('Numbers in the guide refer to these clickable links. Controller crop coordinates and export settings are proposed configurations to rehearse, rather than manufacturer performance guarantees.',y)
end()
c.save()
print(PDF)
