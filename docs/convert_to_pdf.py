"""
Script to convert Markdown documentation to Professional PDF
"""

from fpdf import FPDF
import re
import os

def clean_text(text):
    """Remove or replace non-latin1 characters"""
    replacements = {
        '\u2192': '->',
        '\u2190': '<-',
        '\u2022': '*',
        '\u2014': '-',
        '\u2013': '-',
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u2026': '...',
        '\u25cf': '*',
        '\u2713': '[x]',
        '\u2717': '[ ]',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('latin-1', 'replace').decode('latin-1')


class ProfessionalPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.primary_color = (41, 98, 255)  # Blue
        self.secondary_color = (55, 65, 81)  # Dark gray
        self.accent_color = (16, 185, 129)   # Green
        
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, 'Presentation Agent Documentation', align='C')
            self.ln(15)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
        
    def cover_page(self, title, subtitle):
        self.add_page()
        # Background accent
        self.set_fill_color(*self.primary_color)
        self.rect(0, 0, 210, 100, 'F')
        
        # Title
        self.set_y(35)
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(255, 255, 255)
        self.multi_cell(0, 12, clean_text(title), align='C')
        
        # Subtitle
        self.set_y(70)
        self.set_font('Helvetica', '', 14)
        self.set_text_color(220, 220, 255)
        self.multi_cell(0, 8, clean_text(subtitle), align='C')
        
        # Info box
        self.set_y(120)
        self.set_font('Helvetica', '', 11)
        self.set_text_color(*self.secondary_color)
        self.multi_cell(0, 8, 'AI-Powered Presentation Generation System', align='C')
        
        self.set_y(140)
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(120, 120, 120)
        self.multi_cell(0, 8, 'November 2025', align='C')
        
    def section_title(self, title, level=1):
        title = clean_text(title)
        self.ln(5)
        
        if level == 1:
            self.set_font('Helvetica', 'B', 18)
            self.set_text_color(*self.primary_color)
            self.multi_cell(0, 10, title)
            # Underline
            self.set_draw_color(*self.primary_color)
            self.set_line_width(0.8)
            self.line(10, self.get_y(), 100, self.get_y())
            self.ln(8)
        elif level == 2:
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(*self.secondary_color)
            self.multi_cell(0, 9, title)
            self.ln(4)
        elif level == 3:
            self.set_font('Helvetica', 'B', 12)
            self.set_text_color(80, 80, 80)
            self.multi_cell(0, 8, title)
            self.ln(3)
        else:
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(100, 100, 100)
            self.multi_cell(0, 7, title)
            self.ln(2)
        
        self.set_text_color(0, 0, 0)
        
    def body_text(self, text):
        text = clean_text(text)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 6, text)
        self.ln(2)
        
    def code_block(self, code):
        code = clean_text(code)
        self.set_font('Courier', '', 7)
        self.set_fill_color(245, 247, 250)
        self.set_draw_color(220, 220, 220)
        
        # Draw border
        start_y = self.get_y()
        lines = code.split('\n')
        
        self.set_x(15)
        for line in lines:
            if len(line) > 90:
                line = line[:87] + '...'
            self.cell(180, 4, line, fill=True, new_x="LMARGIN", new_y="NEXT")
            self.set_x(15)
        
        self.ln(5)
        
    def table_header(self, cells):
        self.set_font('Helvetica', 'B', 9)
        self.set_fill_color(*self.primary_color)
        self.set_text_color(255, 255, 255)
        col_width = (self.w - 30) / len(cells)
        for cell in cells:
            cell_text = clean_text(str(cell)[:35])
            self.cell(col_width, 8, cell_text, border=1, align='C', fill=True)
        self.ln()
        self.set_text_color(0, 0, 0)
        
    def table_row(self, cells, alternate=False):
        self.set_font('Helvetica', '', 9)
        if alternate:
            self.set_fill_color(248, 250, 252)
        else:
            self.set_fill_color(255, 255, 255)
        col_width = (self.w - 30) / len(cells)
        for cell in cells:
            cell_text = clean_text(str(cell)[:35])
            self.cell(col_width, 7, cell_text, border=1, align='L', fill=True)
        self.ln()
        
    def bullet_point(self, text, level=0):
        text = clean_text(text)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(60, 60, 60)
        indent = 15 + (level * 8)
        
        # Bullet marker
        self.set_x(indent - 5)
        self.set_fill_color(*self.accent_color)
        if level == 0:
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*self.accent_color)
            self.cell(5, 6, '>')
        else:
            self.cell(5, 6, '-')
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 6, text)
        
    def info_box(self, text):
        text = clean_text(text)
        self.set_fill_color(239, 246, 255)
        self.set_draw_color(*self.primary_color)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*self.secondary_color)
        
        x = self.get_x()
        y = self.get_y()
        self.rect(15, y, 180, 15, 'DF')
        self.set_xy(20, y + 4)
        self.multi_cell(170, 6, text)
        self.ln(5)


def parse_markdown(md_content, pdf, is_detailed=False):
    lines = md_content.split('\n')
    i = 0
    in_code_block = False
    code_buffer = []
    in_table = False
    table_rows = []
    row_count = 0
    
    # Skip first line if it's main title (we use cover page)
    if lines and lines[0].startswith('# '):
        i = 1
    
    while i < len(lines):
        line = lines[i]
        
        # Code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                pdf.code_block('\n'.join(code_buffer))
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue
            
        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue
            
        # Table handling
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells and not all(c.replace('-', '').strip() == '' for c in cells):
                if not in_table:
                    in_table = True
                    row_count = 0
                    pdf.table_header(cells)
                else:
                    pdf.table_row(cells, alternate=(row_count % 2 == 1))
                    row_count += 1
            i += 1
            continue
        elif in_table:
            in_table = False
            pdf.ln(5)
            
        # Headers
        if line.startswith('## '):
            pdf.section_title(line[3:].strip(), 1)
        elif line.startswith('### '):
            pdf.section_title(line[4:].strip(), 2)
        elif line.startswith('#### '):
            pdf.section_title(line[5:].strip(), 3)
        # Bullet points
        elif line.strip().startswith('- '):
            level = (len(line) - len(line.lstrip())) // 2
            pdf.bullet_point(line.strip()[2:], level)
        elif line.strip().startswith('* '):
            level = (len(line) - len(line.lstrip())) // 2
            pdf.bullet_point(line.strip()[2:], level)
        elif re.match(r'^\d+\.', line.strip()):
            pdf.bullet_point(line.strip(), 0)
        # Horizontal rule
        elif line.strip() == '---':
            if pdf.page_no() > 1:
                pdf.ln(3)
                pdf.set_draw_color(220, 220, 220)
                pdf.set_line_width(0.3)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
        # Empty lines
        elif line.strip() == '':
            pdf.ln(2)
        # Regular text
        else:
            text = line.strip()
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            if text:
                pdf.body_text(text)
                
        i += 1


def main():
    docs_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Document 1 - Bird Eye View
    pdf1 = ProfessionalPDF()
    pdf1.cover_page(
        "Presentation Agent",
        "Bird's Eye View"
    )
    pdf1.add_page()
    
    doc1_md = os.path.join(docs_dir, 'Document_1_Bird_Eye_View.md')
    with open(doc1_md, 'r', encoding='utf-8') as f:
        content = f.read()
    parse_markdown(content, pdf1)
    
    doc1_pdf = os.path.join(docs_dir, 'Document_1_Bird_Eye_View.pdf')
    pdf1.output(doc1_pdf)
    print(f"Created: {doc1_pdf}")
    
    # Document 2 - Detailed
    pdf2 = ProfessionalPDF()
    pdf2.cover_page(
        "Presentation Agent",
        "Detailed Technical Documentation"
    )
    pdf2.add_page()
    
    doc2_md = os.path.join(docs_dir, 'Document_2_Detailed_Explanation.md')
    with open(doc2_md, 'r', encoding='utf-8') as f:
        content = f.read()
    parse_markdown(content, pdf2, is_detailed=True)
    
    doc2_pdf = os.path.join(docs_dir, 'Document_2_Detailed_Explanation.pdf')
    pdf2.output(doc2_pdf)
    print(f"Created: {doc2_pdf}")
    
    print("\nPDF conversion complete!")


if __name__ == '__main__':
    main()
