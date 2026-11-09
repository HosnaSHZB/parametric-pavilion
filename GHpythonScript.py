# ============================================================
# TRABECULAE PAVILION GENERATOR
# Rhino 7 + Grasshopper + GhPython
#
# Inputs:
# L, W, H, BaseH, UCount, VCount, Radius, BaseT
#
# Outputs:
# ShellMesh, Struts, Base, Nodes
# ============================================================

# ------------------------------------------------------------
# 1. IMPORT LIBRARIES
# ------------------------------------------------------------

import Rhino
import Rhino.Geometry as rg
import math

# ------------------------------------------------------------
# 2. DEFINE DEFAULT INPUT VALUES
# ------------------------------------------------------------

# Pavilion length
if L is None:
    L = 12.0

# Pavilion width
if W is None:
    W = 6.0

# Pavilion maximum height
if H is None:
    H = 4.0

# Base elevation
if BaseH is None:
    BaseH = 0.5

# Number of divisions along pavilion length
if UCount is None:
    UCount = 30

# Number of divisions along pavilion width
if VCount is None:
    VCount = 16

# Radius of structural members
if Radius is None:
    Radius = 0.035

# Thickness of the base platform
if BaseT is None:
    BaseT = 0.15

# Convert grid divisions to integers
UCount = max(3, int(UCount))
VCount = max(3, int(VCount))

# Prevent negative structural dimensions
L = max(0.1, float(L))
W = max(0.1, float(W))
H = max(0.1, float(H))
Radius = max(0.001, float(Radius))
BaseT = max(0.001, float(BaseT))


# ------------------------------------------------------------
# 3. DEFINE RHINO DOCUMENT TOLERANCE
# ------------------------------------------------------------

# This tolerance controls the accuracy of pipe creation.

try:
    tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
except:
    tol = 0.01

angle_tol = math.radians(1.0)


# ------------------------------------------------------------
# 4. CREATE THE PARAMETRIC PAVILION SURFACE
# ------------------------------------------------------------

# The pavilion is generated using a two-dimensional
# parametric coordinate system (u,v).
#
# u = longitudinal direction (0 to 1)
# v = transverse direction (-1 to 1)
#
# A sinusoidal function generates the undulating form.
# A second function creates the transverse curvature.

def pavilion_point(u, v):

    # Longitudinal position
    x = L * (u - 0.5)

    # Width variation along the pavilion
    # The absolute sine creates organic widening and narrowing.
    width_factor = 0.72 + 0.28 * abs(
        math.sin(2.0 * math.pi * u)
    )

    # Transverse position
    y = 0.5 * W * width_factor * v

    # Longitudinal height variation
    # This produces a raised region and a lower region.
    center_z = BaseH + H * (
        0.5 + 0.5 * math.sin(2.0 * math.pi * u)
    )

    # Transverse curvature
    # The center of the pavilion is higher than its edges.
    arch = 0.18 * H * (1.0 - v * v)

    # Final vertical coordinate
    z = center_z + arch

    # Return the three-dimensional point
    return rg.Point3d(x, y, z)


# ------------------------------------------------------------
# 5. GENERATE GRID POINTS
# ------------------------------------------------------------

# Create an empty mesh.
# This mesh will represent the pavilion reference surface.

ShellMesh = rg.Mesh()

# Store the generated points in a two-dimensional grid.
grid = []

# Store all lattice intersection points.
Nodes = []

# Loop through the longitudinal divisions.
for i in range(UCount + 1):

    # Calculate normalized longitudinal parameter.
    u = float(i) / float(UCount)

    # Create an empty row.
    row = []

    # Loop through the transverse divisions.
    for j in range(VCount + 1):

        # Convert index to normalized transverse parameter.
        v = -1.0 + 2.0 * float(j) / float(VCount)

        # Calculate the 3D point on the pavilion.
        pt = pavilion_point(u, v)

        # Add the point to the mesh vertices.
        index = ShellMesh.Vertices.Add(pt)

        # Save the point index.
        row.append(index)

        # Save the point itself.
        Nodes.append(pt)

    # Save the completed row.
    grid.append(row)


# ------------------------------------------------------------
# 6. CREATE TRIANGULAR MESH
# ------------------------------------------------------------

# Each rectangular grid cell is divided into two triangles.
#
# Alternating the diagonal direction creates a more
# distributed triangular structural network.

# Store all unique structural edges.
edge_set = set()

# Loop through all grid cells.
for i in range(UCount):

    for j in range(VCount):

        # Get the four corner vertex indices.
        a = grid[i][j]
        b = grid[i + 1][j]
        c = grid[i + 1][j + 1]
        d = grid[i][j + 1]

        # Alternate diagonal orientation.
        if (i + j) % 2 == 0:

            # First triangle
            ShellMesh.Faces.AddFace(a, b, c)

            # Second triangle
            ShellMesh.Faces.AddFace(a, c, d)

            # Store triangle edges.
            triangles = [
                (a, b, c),
                (a, c, d)
            ]

        else:

            # First triangle
            ShellMesh.Faces.AddFace(a, b, d)

            # Second triangle
            ShellMesh.Faces.AddFace(b, c, d)

            # Store triangle edges.
            triangles = [
                (a, b, d),
                (b, c, d)
            ]

        # Extract all three edges from each triangle.
        for tri in triangles:

            for k in range(3):

                # Get two consecutive vertex indices.
                p1 = tri[k]
                p2 = tri[(k + 1) % 3]

                # Sort indices to identify duplicate edges.
                edge = tuple(sorted((p1, p2)))

                # Add edge to the unique edge collection.
                edge_set.add(edge)


# Calculate mesh normals.
ShellMesh.Normals.ComputeNormals()

# Compact mesh storage.
ShellMesh.Compact()


# ------------------------------------------------------------
# 7. GENERATE TRABECULAR STRUCTURAL MEMBERS
# ------------------------------------------------------------

# Every unique triangular edge becomes a cylindrical member.
#
# RhinoCommon Brep.CreatePipe creates a solid pipe around
# each connecting line.

Struts = []

# Sort edges for consistent processing.
sorted_edges = sorted(list(edge_set))

# Process every structural edge.
for edge in sorted_edges:

    # Retrieve the two vertex indices.
    i1 = edge[0]
    i2 = edge[1]

    # Retrieve the corresponding 3D points.
    p1 = Nodes[i1]
    p2 = Nodes[i2]

    # Calculate member length.
    member_length = p1.DistanceTo(p2)

    # Skip extremely short members.
    if member_length <= tol:
        continue

    # Create a straight line between the two nodes.
    line = rg.LineCurve(p1, p2)

    # Generate a circular pipe around the line.
    # False = no local blending.
    # Round = rounded end caps.
    # True = fit the pipe to the rail.
    pipe_result = rg.Brep.CreatePipe(
        line,
        Radius,
        False,
        rg.PipeCapMode.Round,
        True,
        tol,
        angle_tol
    )

    # Add successfully generated pipe geometry.
    if pipe_result is not None:

        for pipe in pipe_result:

            if pipe is not None:
                Struts.append(pipe)


# ------------------------------------------------------------
# 8. GENERATE ELLIPTICAL BASE PLATFORM
# ------------------------------------------------------------

# Create a horizontal construction plane below the pavilion.

base_plane = rg.Plane(
    rg.Point3d(0, 0, -BaseT),
    rg.Vector3d.ZAxis
)

# Create an ellipse for the platform outline.
# The radii are proportional to pavilion dimensions.

base_ellipse = rg.Ellipse(
    base_plane,
    L * 0.58,
    W * 0.58
)

# Convert the ellipse to a NURBS curve.
base_curve = base_ellipse.ToNurbsCurve()

# Extrude the outline to create a solid platform.
Base = rg.Extrusion.Create(
    base_curve,
    BaseT,
    True
)

# ------------------------------------------------------------
# 9. FINAL OUTPUTS
# ------------------------------------------------------------
# ShellMesh = Triangular reference mesh
# Struts    = Solid cylindrical structural members
# Base      = Solid elliptical platform
# Nodes     = Structural intersection points
