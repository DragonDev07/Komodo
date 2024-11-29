from setuptools import setup, find_packages

setup(
    name="komodo",  # lowercase package name
    version="0.0.1",
    author="FurthestDrop",
    description="GTK Network Manager",
    license="GPL3+",
    packages=find_packages(),
    install_requires=[
        "pygobject",
        "loguru",
    ],
    entry_points={
        "gui_scripts": [
            "komodo=src.main:main",
        ],
    },
    data_files=[
        (
            "share/applications",
            ["data/applications/dev.furthestdrop.komodo.desktop"],
        ),
        # (
        #     "share/icons/hicolor/scalable/apps",
        #     ["data/icons/hicolor/scalable/apps/komodo.svg"],
        # ),
    ],
    include_package_data=True,  # Required for MANIFEST.in
)
