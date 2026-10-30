"""Application visual theme."""

from __future__ import annotations

APP_STYLESHEET = """
QWidget {
    font-family: "Segoe UI";
    font-size: 10pt;
    color: #1F2937;
}
QMainWindow, #ContentArea, #ScrollContent {
    background: #F4F7F5;
}
QScrollArea {
    border: none;
    background: transparent;
}
#Header {
    background: #FFFFFF;
    border-bottom: 1px solid #E4E9E5;
}
#AppTitle {
    font-size: 24px;
    font-weight: 600;
    color: #1B5E20;
}
#AppSubtitle {
    font-size: 10pt;
    color: #6B7280;
}
#VersionChip {
    background: #E8F5E9;
    color: #2E7D32;
    border-radius: 11px;
    padding: 3px 11px;
    font-size: 9pt;
    font-weight: 600;
}
QFrame#Card {
    background: #FFFFFF;
    border: 1px solid #E2E8E3;
    border-radius: 12px;
}
QLabel#SectionTitle {
    font-size: 11pt;
    font-weight: 600;
    color: #111827;
}
QLabel#SectionHint, QLabel#MutedLabel {
    color: #6B7280;
    font-size: 9pt;
}
QLabel#PathLabel {
    color: #4B5563;
    font-size: 9pt;
}
QLabel#StatusLabel {
    color: #4B5563;
    font-weight: 500;
}
QFrame#DropZone {
    background: #FBFDFB;
    border: 1px dashed #A7C4AD;
    border-radius: 10px;
}
QFrame#DropZone[dragging="true"] {
    background: #F0F8F1;
    border: 2px dashed #2E7D32;
}
QLabel#FileBadge {
    background: #E8F5E9;
    color: #2E7D32;
    border-radius: 8px;
    padding: 5px 9px;
    font-size: 9pt;
    font-weight: 700;
}
QPushButton {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 7px 14px;
    color: #1F2937;
    font-weight: 500;
}
QPushButton:hover {
    background: #F8FAF9;
    border-color: #9CB8A2;
}
QPushButton:pressed {
    background: #EEF4EF;
}
QPushButton:disabled {
    color: #9CA3AF;
    background: #F3F4F6;
    border-color: #E5E7EB;
}
QPushButton#PrimaryButton {
    background: #2E7D32;
    border: 1px solid #2E7D32;
    border-radius: 9px;
    color: #FFFFFF;
    font-size: 11pt;
    font-weight: 600;
    padding: 12px 20px;
}
QPushButton#PrimaryButton:hover {
    background: #256C2A;
    border-color: #256C2A;
}
QPushButton#PrimaryButton:pressed {
    background: #1E5B23;
    border-color: #1E5B23;
}
QPushButton#PrimaryButton:disabled {
    background: #A5C8A8;
    border-color: #A5C8A8;
    color: #F2F7F2;
}
QPushButton#DangerButton {
    color: #B91C1C;
    border-color: #FECACA;
    background: #FFF7F7;
}
QPushButton#DangerButton:hover {
    background: #FEF2F2;
    border-color: #FCA5A5;
}
QRadioButton, QCheckBox {
    spacing: 8px;
    color: #374151;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QLineEdit {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 7px;
    padding: 7px 9px;
    color: #4B5563;
    selection-background-color: #A5D6A7;
}
QLineEdit:focus {
    border-color: #81B886;
    background: #FFFFFF;
}
QProgressBar {
    background: #E5E7EB;
    border: none;
    border-radius: 4px;
    min-height: 8px;
    max-height: 8px;
}
QProgressBar::chunk {
    background: #2E7D32;
    border-radius: 4px;
}
QMenuBar {
    background: #FFFFFF;
    border-bottom: 1px solid #E4E9E5;
    padding: 2px 6px;
}
QMenuBar::item {
    background: transparent;
    padding: 5px 9px;
    border-radius: 5px;
}
QMenuBar::item:selected {
    background: #E8F5E9;
    color: #1B5E20;
}
QMenu {
    background: #FFFFFF;
    border: 1px solid #DDE5DF;
    border-radius: 7px;
    padding: 5px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 5px;
}
QMenu::item:selected {
    background: #E8F5E9;
    color: #1B5E20;
}
QMenu::separator {
    height: 1px;
    background: #EEF1EE;
    margin: 4px 8px;
}
#Footer {
    background: #FFFFFF;
    border-top: 1px solid #E4E9E5;
}
#Footer QLabel {
    color: #7B8580;
    font-size: 9pt;
}
QDialog {
    background: #FFFFFF;
}
QMessageBox {
    background: #FFFFFF;
}
QToolTip {
    background: #1F2937;
    color: #FFFFFF;
    border: none;
    padding: 5px 7px;
    border-radius: 4px;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #C9D3CC;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #AEBDB2;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""
