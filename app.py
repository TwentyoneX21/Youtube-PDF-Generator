from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame
import io, json, os

app = Flask(__name__)

BG    = colors.HexColor("#0a0a0a")
FG    = colors.HexColor("#f5f4f0")
ACCENT= colors.HexColor("#ffffff")
MUTED = colors.HexColor("#999999")
CARD  = colors.HexColor("#1a1a1a")
BORDER= colors.HexColor("#333333")

def sty(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9, textColor=FG,
                leading=14, spaceAfter=0, spaceBefore=0, backColor=None)
    base.update(kw)
    return ParagraphStyle(name, **base)

def S(h=3): return Spacer(1, h*mm)
def rule(t=0.5, c=None): return HRFlowable(width="100%", thickness=t, color=c or BORDER, spaceAfter=2, spaceBefore=2)
def bul(text): return Paragraph(f"  \u2022  {text}", sty("bul", fontSize=8, leading=13, leftIndent=10, firstLineIndent=-8))

def bg_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()

def build_pdf(data):
    buffer = io.BytesIO()
    DW = 174*mm
    frame = Frame(18*mm, 14*mm, DW, A4[1]-28*mm, id="main")
    doc = BaseDocTemplate(buffer, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm)
    doc.addPageTemplates([PageTemplate(id="dark", frames=[frame], onPage=bg_page)])

    title_s  = sty("title", fontName="Helvetica-Bold", fontSize=20, textColor=ACCENT, leading=24)
    sub_s    = sty("sub",   fontSize=9, textColor=MUTED, leading=13)
    h1_s     = sty("h1",   fontName="Helvetica-Bold", fontSize=10, textColor=ACCENT, leading=14, spaceBefore=2, spaceAfter=2)
    h2_s     = sty("h2",   fontName="Helvetica-Bold", fontSize=9,  textColor=FG, leading=13, spaceAfter=1)
    body_s   = sty("body", fontSize=8, textColor=FG, leading=13)
    quote_s  = sty("qt",   fontSize=8, textColor=MUTED, leading=13, leftIndent=10, fontName="Helvetica-Oblique")

    def grid_table(rows, col_widths):
        t = Table(rows, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),CARD),("BOX",(0,0),(-1,-1),0.5,BORDER),
            ("INNERGRID",(0,0),(-1,-1),0.3,BORDER),
            ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#111111")),
            ("TEXTCOLOR",(0,0),(-1,0),MUTED),
        ]))
        return t

    story = []

    # Header
    hd = Table([[
        Paragraph("<b>21AUTOMATE.AI</b>", sty("hb", fontName="Helvetica-Bold", fontSize=8, textColor=FG)),
        Paragraph("PERSONAL NOTES", sty("hr", fontSize=7, textColor=MUTED, alignment=TA_RIGHT))
    ]], colWidths=[DW/2]*2)
    hd.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                             ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story += [hd, S(2), rule(2, ACCENT), S(3)]

    # Title
    story += [
        Paragraph(data.get("video_title", "Video Notes"), title_s), S(1),
        Paragraph(f"Speaker: {data.get('speaker', 'Unknown')}  |  Key Learnings and Personal Notes", sub_s),
        S(2), rule(), S(4),
    ]

    # Summary
    story.append(Paragraph("SUMMARY", h1_s))
    sum_t = Table([[Paragraph(data.get("summary", ""), body_s)]], colWidths=[DW])
    sum_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),CARD),("BOX",(0,0),(-1,-1),0.5,BORDER),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    story += [sum_t, S(4)]

    # Key Learnings
    story.append(Paragraph("KEY LEARNINGS", h1_s))
    story.append(S(2))
    for item in data.get("key_learnings", []):
        num   = str(item.get("number", "")).zfill(2)
        title = item.get("title", "")
        body  = item.get("body", "")
        row = [[
            Paragraph(f"<b>{num}</b>", sty(f"n{num}", fontName="Helvetica-Bold", fontSize=10, textColor=MUTED, alignment=TA_CENTER)),
            [Paragraph(title, h2_s), S(1), Paragraph(body, body_s)]
        ]]
        t = Table(row, colWidths=[12*mm, DW-12*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),CARD),("BOX",(0,0),(-1,-1),0.5,BORDER),
            ("LINEAFTER",(0,0),(0,-1),0.5,BORDER),
            ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
        ]))
        story += [t, S(1.5)]

    story.append(S(3))

    # Takeaways
    story.append(Paragraph("ACTIONABLE TAKEAWAYS", h1_s))
    tw_rows = [[bul(t)] for t in data.get("takeaways", [])]
    if tw_rows:
        tw_t = Table(tw_rows, colWidths=[DW])
        tw_t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),CARD),("BOX",(0,0),(-1,-1),0.5,BORDER),
            ("INNERGRID",(0,0),(-1,-1),0.3,BORDER),
            ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ]))
        story += [tw_t, S(4)]

    # Quotes
    story.append(Paragraph("MEMORABLE LINES", h1_s))
    q_rows = [[Paragraph(f'"{q}"', quote_s)] for q in data.get("quotes", [])]
    if q_rows:
        q_t = Table(q_rows, colWidths=[DW])
        q_t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),CARD),("BOX",(0,0),(-1,-1),0.5,BORDER),
            ("INNERGRID",(0,0),(-1,-1),0.3,BORDER),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        story += [q_t, S(4)]

    # Relevance
    if data.get("relevance"):
        story.append(Paragraph("RELEVANCE TO 21AUTOMATE.AI", h1_s))
        rel_t = Table([[Paragraph(data.get("relevance", ""), body_s)]], colWidths=[DW])
        rel_t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),CARD),("BOX",(0,0),(-1,-1),0.5,BORDER),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ]))
        story += [rel_t, S(4)]

    # Footer
    story.append(rule())
    ft = Table([[
        Paragraph("<b>21AUTOMATE.AI</b>", sty("fl", fontName="Helvetica-Bold", fontSize=7, textColor=MUTED)),
        Paragraph("Personal Notes", sty("fc", fontSize=7, textColor=MUTED, alignment=TA_CENTER)),
        Paragraph("2026", sty("fr", fontSize=7, textColor=MUTED, alignment=TA_RIGHT)),
    ]], colWidths=[DW/3]*3)
    ft.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                             ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(ft)

    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json(force=True)
        pdf_buffer = build_pdf(data)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="notes.pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "service": "21Automate PDF Generator"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
