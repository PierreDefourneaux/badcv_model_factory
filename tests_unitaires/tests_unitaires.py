import sys
import pytest

def test_python_version():
    major = sys.version_info.major
    minor = sys.version_info.minor
    micro = sys.version_info.micro
    assert major == 3
    assert minor == 12
    assert micro == 12