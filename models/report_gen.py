import os
import csv
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')


def _level_color(level):
    return {'low': colors.green, 'medium': colors.orange, 'high': colors.red}.get(level, colors.grey)


def generate_pdf_report(comparison_data, result_data, output_filename):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, output_filename)

    doc = SimpleDocTemplate(path, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                 fontSize=20, textColor=colors.HexColor('#1a1a2e'),
                                 spaceAfter=6, alignment=TA_CENTER)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                               fontSize=10, textColor=colors.grey,
                               alignment=TA_CENTER, spaceAfter=16)

    story.append(Paragraph('Smart Code Plagiarism Detector', title_style))
    story.append(Paragraph('Plagiarism Analysis Report', sub_style))
    story.append(HRFlowable(width='100%', thickness=2,
                            color=colors.HexColor('#4361ee'), spaceAfter=16))

    # Metadata table
    meta = [
        ['Report ID', f"RPT-{comparison_data['id']:04d}",
         'Generated', datetime.now().strftime('%Y-%m-%d %H:%M')],
        ['File A', comparison_data.get('file1_name', 'N/A'),
         'File B', comparison_data.get('file2_name', 'N/A')],
        ['Language', comparison_data.get('file1_lang', 'N/A').upper(),
         'Compared By', comparison_data.get('compared_by_name', 'System')],
    ]
    meta_table = Table(meta, colWidths=[3*cm, 6.5*cm, 3*cm, 6.5*cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f4ff')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f0f4ff')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUND', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # Overall score section
    score = float(comparison_data['similarity_score'])
    level = comparison_data['plagiarism_level']
    lcolor = _level_color(level)

    score_data = [[f"{score:.1f}%", level.upper() + ' SIMILARITY']]
    score_table = Table(score_data, colWidths=[4*cm, 15*cm])
    score_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 28),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 14),
        ('TEXTCOLOR', (0, 0), (-1, -1), lcolor),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BOX', (0, 0), (-1, -1), 2, lcolor),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 20))

    # Algorithm breakdown
    story.append(Paragraph('Algorithm Breakdown', styles['Heading2']))
    algo_data = [
        ['Algorithm', 'Weight', 'Score', 'Contribution'],
        ['Token Matching', '30%',
         f"{float(comparison_data['token_similarity']):.1f}%",
         f"{float(comparison_data['token_similarity'])*0.3:.1f}%"],
        ['AST Analysis', '30%',
         f"{float(comparison_data['ast_similarity']):.1f}%",
         f"{float(comparison_data['ast_similarity'])*0.3:.1f}%"],
        ['Structure Similarity', '20%',
         f"{float(comparison_data['structure_similarity']):.1f}%",
         f"{float(comparison_data['structure_similarity'])*0.2:.1f}%"],
        ['Logic Similarity', '20%',
         f"{float(comparison_data['logic_similarity']):.1f}%",
         f"{float(comparison_data['logic_similarity'])*0.2:.1f}%"],
        ['FINAL SCORE', '100%', '', f"{score:.1f}%"],
    ]
    algo_table = Table(algo_data, colWidths=[6*cm, 3*cm, 4*cm, 6*cm])
    algo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4361ee')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f4ff')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUND', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    story.append(algo_table)
    story.append(Spacer(1, 20))

    # Detection summary
    if result_data:
        story.append(Paragraph('Detection Summary', styles['Heading2']))
        ml = result_data.get('matching_lines', 0)
        tl_a = result_data.get('total_lines_a', 0)
        tl_b = result_data.get('total_lines_b', 0)
        summary_data = [
            ['Metric', 'Value'],
            ['Matching Lines', str(ml)],
            ['Total Lines (File A)', str(tl_a)],
            ['Total Lines (File B)', str(tl_b)],
            ['Matching Blocks', str(len(result_data.get('matching_blocks', [])))],
            ['AST Function Matches', str(len(result_data.get('ast_matches', [])))],
        ]
        s_table = Table(summary_data, colWidths=[9*cm, 10*cm])
        s_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4361ee')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('ROWBACKGROUND', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(s_table)

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.grey))
    story.append(Paragraph(
        f'Generated by Smart Code Plagiarism Detector | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        ParagraphStyle('Footer', parent=styles['Normal'],
                       fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    return path


def generate_csv_report(comparison_data, output_filename):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, output_filename)

    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Smart Code Plagiarism Detector - Report'])
        writer.writerow([])
        writer.writerow(['Field', 'Value'])
        writer.writerow(['Report ID', f"RPT-{comparison_data['id']:04d}"])
        writer.writerow(['File A', comparison_data.get('file1_name', 'N/A')])
        writer.writerow(['File B', comparison_data.get('file2_name', 'N/A')])
        writer.writerow(['Language', comparison_data.get('file1_lang', 'N/A')])
        writer.writerow(['Similarity Score', f"{float(comparison_data['similarity_score']):.2f}%"])
        writer.writerow(['Plagiarism Level', comparison_data['plagiarism_level'].upper()])
        writer.writerow([])
        writer.writerow(['Algorithm', 'Weight', 'Score'])
        writer.writerow(['Token Matching', '30%', f"{float(comparison_data['token_similarity']):.2f}%"])
        writer.writerow(['AST Analysis', '30%', f"{float(comparison_data['ast_similarity']):.2f}%"])
        writer.writerow(['Structure Similarity', '20%', f"{float(comparison_data['structure_similarity']):.2f}%"])
        writer.writerow(['Logic Similarity', '20%', f"{float(comparison_data['logic_similarity']):.2f}%"])
        writer.writerow([])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    return path
