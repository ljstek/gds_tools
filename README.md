# GDS tools - Python package for GDSII device design
This Python 3 package adds extra functionality to the existing `gdspy` package for scripted design of devices.

## Why?
This package was originally developed during a masters student project in collaboration with Microsoft Quantum Lab Delft and was developed further internally after this project finished. MSQLD has been using this package for the design of novel quantum devices and it aims to aid in the design of such devices for nanofabrication purposes. Previously, a lot of quantum device design was done in visual CAD programs such as AutoCAD. While these programs are very feature rich, it becomes difficult and time consuming to design structures that need to change size over their design lifetime. Scripted (or parametric) CAD can be a solution to this problem, as it can be used to define and generate structures based on a set of input parameters. This promises easy and quick implementation of design changes at the cost of slightly increased initial time investment to parametrize the designs.

The `gds_tools` package makes extensive use of the `gdspy` package. `gdspy` already has a lot of functionality built-in which is useful for the scripted design of structures. However, it lacks in the ability to easily define blocks of (physics related) structures and link them together. The goal of this package is to make life easier for people who design devices using `gdspy` and to offer a common toolset in which structures can be generated and connected.

## How?
Creating new devices using the `gds_tools` package is relatively straightforward. You begin by defining a bunch of geometrical shapes that you need by calling built-in functions of the `gds_tools` package. This will generate `gdspy` structures and add additional parameters to the `GDStructure` class from `gds_tools`, and return you the object handle. You can then manipulate multiple instances of this class by connecting them together with `.con(*)`, rotating them with `.rot(*)`, etc. Connected structures will move as if they are one single object (even though they are still individual `gdspy` polygon (or otherwise) instances). For example, if you issue a rotation on a `GDStructure` which has other members connected, all members will rotate by the same amount and keep their positions relative to their connection points.
All this happens transparently for the user, so no in-depth knowledge of the underlying code is required. This should allow for rapid development and prototyping compared to hand-drawn structures and devices.

## Initializing a GDStructure instance with your own geometry
First, define a `gdspy` structure using its built in functions (see the [gdspy docs](https://gdspy.readthedocs.io/en/latest/geometry.html)), define a dictionary containing the names (labels) and locations (`(x, y)` coordindates as tuple) of the endpoints to which a connection can be formed by other members, and also a dictionary containing the same labels and the sizes (widths) of the endpoints (useful when connecting another structure, so you know the size of the transmission line you're connection to for example). Then, create an instance of the `GDStructure` class by calling `gds_tools.GDStructure(gdspy_structure, endpoints, endpoint_sizes)`. You can now use this object to connect your `gdspy` structure to other `gdspy` structures, as long as they are put into their own `GDStructure` instance.

# MIT license
After seeing mostly internal use, it has been decided to attach the MIT license to this project and to share it with the wider community. Please see the `LICENSE` file in the project root for details. Full commit history is not available prior to publication for confidentiality reasons.

## Contribute!
If you use this package to create your devices, please strongly consider contributing back to this project! Your input and feedback is much appreciated.
