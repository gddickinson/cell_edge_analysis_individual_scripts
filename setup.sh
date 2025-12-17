#!/bin/bash

echo "=========================================="
echo "Cell Edge Movement Analysis - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

echo "✓ Python 3 found"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Warning: Some dependencies may not have installed correctly"
    echo "Try manually: pip3 install numpy matplotlib scipy scikit-image tifffile"
fi

echo ""
echo "✓ Python dependencies installed"
echo ""

# Check tkinter
echo "Checking for tkinter..."
python3 -c "import tkinter" 2>/dev/null

if [ $? -ne 0 ]; then
    echo ""
    echo "Warning: tkinter not found. You may need to install it:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  Fedora/RHEL: sudo dnf install python3-tkinter"
    echo "  Arch: sudo pacman -S tk"
    echo "  macOS: tkinter should be included with Python"
    echo ""
else
    echo "✓ tkinter found"
fi

# Make scripts executable
echo ""
echo "Making scripts executable..."
chmod +x launch_gui.py
chmod +x cell_edge_analysis_gui.py
chmod +x step*.py
chmod +x run_all_steps.py

echo "✓ Scripts are now executable"
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To launch the GUI, run:"
echo "  python3 launch_gui.py"
echo ""
echo "Or directly:"
echo "  python3 cell_edge_analysis_gui.py"
echo ""
echo "For help, see GUI_USER_GUIDE.md"
echo ""
