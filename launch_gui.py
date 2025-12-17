#!/usr/bin/env python3
"""
Simple launcher for Cell Edge Movement Analysis GUI
"""

import sys
import os

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = {
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
        'scipy': 'scipy',
        'skimage': 'scikit-image',
        'tifffile': 'tifffile',
        'tkinter': 'python3-tk (system package)'
    }
    
    missing = []
    
    for package, install_name in required_packages.items():
        try:
            if package == 'tkinter':
                import tkinter
            else:
                __import__(package)
        except ImportError:
            missing.append(install_name)
    
    if missing:
        print("=" * 60)
        print("MISSING DEPENDENCIES")
        print("=" * 60)
        print("\nThe following packages are required but not installed:\n")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nTo install missing packages, run:")
        print("  pip install numpy matplotlib scipy scikit-image tifffile")
        print("\nFor tkinter on Linux, you may need:")
        print("  sudo apt-get install python3-tk")
        print("=" * 60)
        return False
    
    return True

def main():
    """Launch the GUI application."""
    print("Cell Edge Movement Analysis GUI")
    print("=" * 60)
    
    # Check dependencies
    print("\nChecking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    print("✓ All dependencies found")
    
    # Import and launch GUI
    print("\nLaunching GUI...")
    try:
        from cell_edge_analysis_gui import AnalysisGUI
        import tkinter as tk
        
        root = tk.Tk()
        app = AnalysisGUI(root)
        
        print("✓ GUI launched successfully")
        print("\nClose this window or press Ctrl+C to exit")
        print("=" * 60 + "\n")
        
        root.mainloop()
        
    except Exception as e:
        print(f"\n✗ Error launching GUI: {str(e)}")
        print("\nPlease check the error message above and ensure:")
        print("  1. cell_edge_analysis_gui.py is in the current directory")
        print("  2. All dependencies are installed")
        print("  3. You have Python 3.6 or higher")
        sys.exit(1)

if __name__ == "__main__":
    main()
