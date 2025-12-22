"""
Module de tests unitaires.
"""

import sys

def test_python_version_3_12_12():
    """
    Vérifie que la version de l'interpréteur Python est exactement la 3.12.12.
    """
    major = sys.version_info.major
    minor = sys.version_info.minor
    micro = sys.version_info.micro
    assert major == 3
    assert minor == 12
    assert micro == 12
